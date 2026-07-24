# Liga Piw — backend na Cloudflare Workers + D1 (SQLite)

Ten folder zawiera cały backend. **Ty** zakładasz darmowe konto Cloudflare i wykonujesz
poniższe kroki, potem wysyłasz mi adres Workera (`https://liga-piw.<coś>.workers.dev`),
a ja przepinam stronę i robota na tę bazę.

Konto Cloudflare jest **darmowe i nie wymaga karty**. Limity darmowe (D1: 5 GB, miliony
odczytów) są dla tej apki nie do wyczerpania.

Pliki:
- `schema.sql` — tworzy tabele (ratings, comments, new_beers). Uruchom **raz**.
- `seed.sql` — wgrywa obecne dane (41 ocen + 4 komentarze z Piwa.xlsx). Uruchom **raz**, po schemacie.
- `src/index.js` — kod Workera (API: `GET /api/store`, `POST /api/rate|comment|beer`).
- `wrangler.toml` — konfiguracja (potrzebna tylko przy ścieżce z CLI).

---

## Ścieżka A — przez panel Cloudflare (bez instalowania niczego) ✅ zalecana

1. Wejdź na https://dash.cloudflare.com → załóż konto / zaloguj się.
2. **Utwórz bazę D1:** lewe menu → **Storage & Databases → D1 SQL Database → Create**.
   Nazwa: `liga-piw` → Create.
3. **Załaduj schemat i dane:** wejdź w bazę `liga-piw` → zakładka **Console**.
   - Wklej całą zawartość `schema.sql` → **Execute**.
   - Wklej całą zawartość `seed.sql` → **Execute**. (Powinno wejść 41 + 4 = 45 wierszy.)
   - Sprawdź: wpisz `SELECT COUNT(*) FROM ratings;` → powinno być **41**.
4. **Utwórz Workera:** lewe menu → **Workers & Pages → Create → Workers → Create Worker**.
   Nazwa: `liga-piw` → Deploy (na razie z domyślnym kodem).
5. **Wklej kod:** w Workerze → **Edit code** → skasuj wszystko i wklej całą zawartość
   `src/index.js` → **Deploy**.
6. **Podepnij bazę do Workera:** Worker `liga-piw` → **Settings → Bindings → Add →
   D1 database**. Variable name: `DB` (dokładnie te dwie litery), Database: `liga-piw` → Save.
   (Po dodaniu bindingu zrób jeszcze raz **Deploy**, żeby się zastosował.)
7. **Skopiuj adres Workera** — jest u góry, w formacie
   `https://liga-piw.<twoja-subdomena>.workers.dev`. Otwórz `https://<ten-adres>/api/store`
   w przeglądarce — powinien pokazać JSON z ocenami. **Wyślij mi ten adres.**

## Ścieżka B — przez terminal (jeśli wolisz CLI)

Wymaga zainstalowanego Node.js (https://nodejs.org). Potem w tym folderze:

```bash
npx wrangler login                                   # logowanie przez przeglądarkę
npx wrangler d1 create liga-piw                      # wypisze database_id → wklej do wrangler.toml
npx wrangler d1 execute liga-piw --remote --file=schema.sql
npx wrangler d1 execute liga-piw --remote --file=seed.sql
npx wrangler deploy                                  # wypisze adres https://liga-piw.<...>.workers.dev
```

Wyślij mi wypisany adres Workera.

---

## Co potem robię ja
- Przepinam `index.html` na endpointy Workera (oceny/komentarze/piwa lecą pojedynczymi,
  atomowymi zapisami — koniec z wyścigami i znikaniem danych).
- Przepinam robota `sync_excel.py` na `GET /api/store`, żeby dalej co pół godziny zapisywał
  oceny do `Piwa.xlsx`.
- Zostawiam kopię zapasową w repo jako zapas bezpieczeństwa.
- Wygaszamy jsonblob.
