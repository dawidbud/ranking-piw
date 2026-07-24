#!/usr/bin/env python3
"""Przepisuje oceny/komentarze/nowe piwa z bazy Ligi Piw do Piwa.xlsx.

Uruchamiany cyklicznie przez GitHub Actions (.github/workflows/sync.yml).

Źródło danych: API na Cloudflare Worker + D1 (GET {apiUrl}/api/store).
Adres API jest w store-config.json (pole "apiUrl"). Po każdym udanym odczycie
zapisujemy wierną kopię do store-backup.json (zapas bezpieczeństwa w repo).

Kolumny arkusza "Ocenka": A lp, B marka, C nazwa, D %, E rodzaj, F OCENA,
G uwagi/komentarze, H link, I komentarze www, J oceny szczegółowo.

Zmienne środowiskowe do testów lokalnych:
  STORE_FILE — czytaj bazę z pliku zamiast z sieci
"""
import json
import os
import sys

import openpyxl

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
XLSX = os.path.join(ROOT, "Piwa.xlsx")
CONFIG = os.path.join(ROOT, "store-config.json")
BACKUP = os.path.join(ROOT, "store-backup.json")
FALLBACK_API = "https://liga-piw.budyta68.workers.dev"

COL_LP, COL_MARKA, COL_NAZWA, COL_ABV, COL_RODZAJ = 1, 2, 3, 4, 5
COL_OCENA, COL_UWAGI, COL_LINK, COL_KOM_WWW, COL_OCENY = 6, 7, 8, 9, 10


def norm(s):
    return " ".join(str(s if s is not None else "").lower().split())


def beer_id(marka, nazwa, rodzaj):
    return norm(marka) + "|" + norm(nazwa) + "|" + norm(rodzaj)


def fmt(n):
    return f"{n:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def norm_store(s):
    s = s if isinstance(s, dict) else {}
    return {"ratings": s.get("ratings") or {}, "comments": s.get("comments") or {}, "newBeers": s.get("newBeers") or []}


def read_api_url():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            url = json.load(f).get("apiUrl")
            if url:
                return url.rstrip("/")
    except (OSError, ValueError):
        pass
    return FALLBACK_API


def write_backup(store):
    with open(BACKUP, "w", encoding="utf-8") as f:
        json.dump(norm_store(store), f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_store():
    """Zwraca store z API (Worker + D1), albo z pliku przy testach lokalnych."""
    path = os.environ.get("STORE_FILE")
    if path:
        with open(path, encoding="utf-8") as f:
            return norm_store(json.load(f))

    import requests
    r = requests.get(read_api_url() + "/api/store", headers={"Accept": "application/json"}, timeout=30)
    r.raise_for_status()
    return norm_store(r.json())


def main():
    store = get_store()
    ratings = store["ratings"]
    comments = store["comments"]
    new_beers = store["newBeers"]

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

    for nb in new_beers:
        bid = nb.get("id") or beer_id(nb.get("marka"), nb.get("nazwa"), nb.get("rodzaj"))
        if bid in rows_by_id:
            continue
        last_row += 1
        max_lp += 1
        ws.cell(row=last_row, column=COL_LP, value=max_lp)
        ws.cell(row=last_row, column=COL_MARKA, value=nb.get("marka") or "")
        ws.cell(row=last_row, column=COL_NAZWA, value=nb.get("nazwa") or "")
        if isinstance(nb.get("abv"), (int, float)):
            ws.cell(row=last_row, column=COL_ABV, value=nb["abv"])
        ws.cell(row=last_row, column=COL_RODZAJ, value=nb.get("rodzaj") or "Inne")
        if nb.get("addedBy"):
            ws.cell(row=last_row, column=COL_UWAGI, value=f"dodane przez: {nb['addedBy']}")
        rows_by_id[bid] = last_row
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
        set_cell(row, COL_OCENA, round(sum(vals) / len(vals), 2))
        set_cell(row, COL_OCENY, "; ".join(f"{name}: {fmt(v)}" for name, v in sorted(user_ratings.items())))

    for bid, clist in comments.items():
        row = rows_by_id.get(bid)
        if not row or not clist:
            continue
        set_cell(row, COL_KOM_WWW,
                 " | ".join(f"{c.get('author', '?')}: {c.get('text', '')} ({c.get('date', '')})" for c in clist))

    if changed:
        wb.save(XLSX)
        print("Zapisano Piwa.xlsx")
    else:
        print("Brak zmian w Piwa.xlsx")

    # kopia zapasowa bazy w repo (wierny mirror — zapas bezpieczeństwa)
    write_backup(store)

    return 0


if __name__ == "__main__":
    sys.exit(main())
