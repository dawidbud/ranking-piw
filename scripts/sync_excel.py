#!/usr/bin/env python3
"""Przepisuje oceny/komentarze/nowe piwa ze wspólnej bazy (jsonblob) do Piwa.xlsx.

Uruchamiany co godzinę przez GitHub Actions (.github/workflows/sync.yml).
Kolumny arkusza "Ocenka": A lp, B marka, C nazwa, D %, E rodzaj, F OCENA,
G uwagi/komentarze, H link, I komentarze www, J oceny szczegółowo.

Zmienne środowiskowe do testów lokalnych:
  STORE_FILE — czytaj bazę z pliku zamiast z sieci
  SKIP_PUT=1 — nie czyść newBeers w bazie po synchronizacji
"""
import json
import os
import sys

import openpyxl

STORE_URL = "https://jsonblob.com/api/jsonBlob/019f7c7b-fdba-74c1-ba07-61ceb04ca826"
XLSX = os.path.join(os.path.dirname(__file__), "..", "Piwa.xlsx")

COL_LP, COL_MARKA, COL_NAZWA, COL_ABV, COL_RODZAJ = 1, 2, 3, 4, 5
COL_OCENA, COL_UWAGI, COL_LINK, COL_KOM_WWW, COL_OCENY = 6, 7, 8, 9, 10


def norm(s):
    return " ".join(str(s if s is not None else "").lower().split())


def beer_id(marka, nazwa, rodzaj):
    return norm(marka) + "|" + norm(nazwa) + "|" + norm(rodzaj)


def fmt(n):
    s = f"{n:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def get_store():
    path = os.environ.get("STORE_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    import requests
    try:
        r = requests.get(STORE_URL, headers={"Accept": "application/json"}, timeout=30)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print("UWAGA: magazyn JSON nie istnieje (404) — pomijam synchronizację.")
            return {"ratings": {}, "comments": {}, "newBeers": []}
        raise
    return r.json()


def put_store(store):
    if os.environ.get("SKIP_PUT"):
        print("SKIP_PUT — pomijam czyszczenie newBeers w bazie")
        return
    import requests
    r = requests.put(STORE_URL, json=store, timeout=30)
    r.raise_for_status()


def main():
    store = get_store()
    ratings = store.get("ratings") or {}
    comments = store.get("comments") or {}
    new_beers = store.get("newBeers") or []

    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Ocenka"]

    rows_by_id = {}
    max_lp = 0
    last_row = 1
    for r in range(2, ws.max_row + 1):
        marka = ws.cell(row=r, column=COL_MARKA).value
        nazwa = ws.cell(row=r, column=COL_NAZWA).value
        if not marka and not nazwa:
            continue
        last_row = r
        rows_by_id[beer_id(marka, nazwa, ws.cell(row=r, column=COL_RODZAJ).value)] = r
        lp = ws.cell(row=r, column=COL_LP).value
        if isinstance(lp, (int, float)):
            max_lp = max(max_lp, int(lp))

    changed = False
    synced_new = []

    for nb in new_beers:
        bid = nb.get("id") or beer_id(nb.get("marka"), nb.get("nazwa"), nb.get("rodzaj"))
        if bid in rows_by_id:
            synced_new.append(bid)
            continue
        last_row += 1
        max_lp += 1
        ws.cell(row=last_row, column=COL_LP, value=max_lp)
        ws.cell(row=last_row, column=COL_MARKA, value=nb.get("marka") or "")
        ws.cell(row=last_row, column=COL_NAZWA, value=nb.get("nazwa") or "")
        if isinstance(nb.get("abv"), (int, float)):
            ws.cell(row=last_row, column=COL_ABV, value=nb["abv"])
        ws.cell(row=last_row, column=COL_RODZAJ, value=nb.get("rodzaj") or "Inne")
        dodal = nb.get("addedBy")
        if dodal:
            ws.cell(row=last_row, column=COL_UWAGI, value=f"dodane przez: {dodal}")
        rows_by_id[bid] = last_row
        synced_new.append(bid)
        changed = True
        print(f"+ nowe piwo: {nb.get('marka')} {nb.get('nazwa')}")

    def set_cell(row, col, value):
        nonlocal changed
        cur = ws.cell(row=row, column=col).value
        if isinstance(cur, float) and isinstance(value, (int, float)):
            if abs(cur - value) < 1e-9:
                return
        elif cur == value or (cur in (None, "") and value in (None, "")):
            return
        ws.cell(row=row, column=col, value=value)
        changed = True

    for bid, user_ratings in ratings.items():
        row = rows_by_id.get(bid)
        if not row or not user_ratings:
            continue
        vals = [v for v in user_ratings.values() if isinstance(v, (int, float))]
        if not vals:
            continue
        avg = round(sum(vals) / len(vals), 2)
        set_cell(row, COL_OCENA, avg)
        detail = "; ".join(f"{name}: {fmt(v)}" for name, v in sorted(user_ratings.items()))
        set_cell(row, COL_OCENY, detail)

    for bid, clist in comments.items():
        row = rows_by_id.get(bid)
        if not row or not clist:
            continue
        joined = " | ".join(
            f"{c.get('author', '?')}: {c.get('text', '')} ({c.get('date', '')})" for c in clist
        )
        set_cell(row, COL_KOM_WWW, joined)

    if changed:
        wb.save(XLSX)
        print("Zapisano Piwa.xlsx")
    else:
        print("Brak zmian w Piwa.xlsx")

    # usuń z bazy nowe piwa, które trafiły już do Excela (na świeżej kopii bazy)
    if synced_new and not os.environ.get("STORE_FILE"):
        fresh = get_store()
        before = len(fresh.get("newBeers") or [])
        fresh["newBeers"] = [
            nb for nb in (fresh.get("newBeers") or [])
            if (nb.get("id") or beer_id(nb.get("marka"), nb.get("nazwa"), nb.get("rodzaj"))) not in synced_new
        ]
        if len(fresh["newBeers"]) != before:
            put_store(fresh)
            print(f"Wyczyszczono {before - len(fresh['newBeers'])} zsynchronizowanych nowych piw z bazy")

    return 0


if __name__ == "__main__":
    sys.exit(main())
