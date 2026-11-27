# Rodinné úlohy

**Úlohy, vlastné body a odmeny pre celú rodinu — priamo v Home Assistante.**

[![Tests](https://github.com/marekbgtr/ha-rodinne-ulohy/actions/workflows/tests.yml/badge.svg)](https://github.com/marekbgtr/ha-rodinne-ulohy/actions/workflows/tests.yml)
[![Release](https://img.shields.io/github/v/release/marekbgtr/ha-rodinne-ulohy)](https://github.com/marekbgtr/ha-rodinne-ulohy/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Jednoduchá detská karta na tablet a samostatná rodičovská správa. Každý môže zbierať
hviezdičky, srdiečka, koníky alebo vlastný symbol. Údaje zostávajú vo vašom HA.
Bez závislosti od ChoreOps, ďalšieho servera alebo platenej služby.

**[Inštalácia a aktualizácie](docs/INSTALACIA.md)** · **[Podrobný návod](docs/POUZIVANIE.md)** · **[Príklady kariet](examples)** · **[História verzií](CHANGELOG.md)**

## Nové v 0.6.0

Víkendové úlohy, vrátenie potvrdenej odmeny, upozornenia na schválenie a rodičovské
tlačidlá priamo na detskej karte. [Nastavenie a príklady](docs/POUZIVANIE.md).

## Čo dokáže

| Pre deti | Pre rodičov |
| --- | --- |
| Splnenie úlohy jedným kliknutím | Správa úloh a odmien cez formuláre |
| Vlastná karta, fotografia a symbol bodov | Bonusy, mínusové body a presné vrátenie |
| Denné, víkendové, týždenné aj dlhodobé úlohy | Termín, uzávierka a ospravedlnenie |
| Spoločné zbieranie na odmenu | Schválenie plných bodov aj po termíne |
| Voliteľné štatistiky a cieľ odmeny | Týždenné vyhodnotenie a poradie skupín |

Úlohu možno prideliť jednému, viacerým alebo všetkým: každý samostatne, spoločne,
na striedačku alebo „kto prvý“. Opakované úlohy umožňujú viac splnení denne.
Pri spoločnej odmene sa účastníci zložia vlastnými bodmi; pri zamietnutí sa každému
vráti presne jeho príspevok.

## Začnite tu

1. V HACS pridajte tento repozitár ako **Vlastný repozitár**, kategória **Integrácia**.
2. Stiahnite Rodinné úlohy a reštartujte HA.
3. Pridajte integráciu cez **Nastavenia → Zariadenia a služby**.
4. Raz pridajte JavaScript zdroj `/family_quests-static/family-quests-card.js`.
5. Na dashboard vložte manuálnu kartu:

```yaml
type: custom:family-quests-card
mode: child
person: Maty
```

Pre rodiča použite `mode: admin` a vynechajte `person`. Pre spoločnú detskú kartu
s prepínaním profilov tiež vynechajte `person`.

**Používate ZIP verziu?** Integráciu neodstraňujte a nepridávajte znova.
[Prechod na HACS](docs/INSTALACIA.md#prechod-zo-zip-na-hacs) zachová existujúcu konfiguráciu.

## Pred používaním

- Je to vlastná **integrácia + Lovelace karta**, nie doplnok Supervisor.
- Rodičovská správa vyžaduje správcu HA. Na detskom tablete použite samostatný účet
  bez administrátorských oprávnení. Skrytie rodičovskej karty nestačí.
- Profily nie sú oddelené prihlasovacie účty. Bežní používatelia domácnosti môžu
  prepínať aktívnych účastníkov; riešenie je určené pre spoločný rodinný tablet.
- Cieľová minimálna verzia je HA Core 2025.6; táto hranica nie je overená živým testom.
- Automatické testy nenahrádzajú skúšku v reálnom HA a na tablete. Vlastné emoji
  sa na starších zariadeniach môžu vykresľovať odlišne.

## Vývoj

[Testy a vydávanie verzií](docs/VYVOJ.md). Pri nahlásení chyby uveďte verziu HA,
integrácie, zariadenie a kroky reprodukcie. Neprikladajte tokeny ani súkromné údaje rodiny.

Licencia [MIT](LICENSE).
