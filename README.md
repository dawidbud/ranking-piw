# 🍺 Liga Piw

**Strona:** https://dawidbud.github.io/ranking-piw/ — dostęp ma każdy, kto ma link.

Wspólny ranking piw. Odwiedzający mogą oceniać (skala 0,25–5), komentować
i dodawać nowe piwa — wszystko zapisuje się we wspólnej bazie od razu,
a **robot (GitHub Actions) raz na godzinę przepisuje oceny do `Piwa.xlsx`**
w tym repozytorium.

## Jak to działa

- `Piwa.xlsx` (arkusz `Ocenka`) to główna baza piw: `lp`, `marka`, `nazwa`, `%`,
  `rodzaj`, `OCENA` (średnia), `uwagi/komentarze`, `link`, `komentarze www`,
  `oceny szczegółowo`.
- Oceny i komentarze z www trafiają najpierw do wspólnego magazynu JSON (jsonblob),
  a workflow `Zapis ocen do Excela` (co godzinę albo ręcznie z zakładki Actions)
  wpisuje je do Excela i commituje.
- Piwa można też dodawać ręcznie: edytuj `Piwa.xlsx` i wgraj do repo — strona
  zaktualizuje się sama po ok. minucie.
