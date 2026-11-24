# Vývoj a vydávanie

[Späť na úvod](../README.md)

## Lokálne overenie

Z koreňa repozitára, s Python 3.13 a Node 22:

```sh
python -m unittest discover -s tests -q
python -m compileall -q custom_components
node --check custom_components/family_quests/frontend/family-quests-card.js
node tests/frontend_smoke.cjs
python scripts/package_release.py
```

## Nová verzia

1. Upravte kód a testy, aktualizujte číslo verzie v manifeste a prípadné označenie verzie v karte.
2. Aktualizujte CHANGELOG.md a RELEASE_NOTES.md, overte migrácie starších dát.
3. Nahrajte zmenu na vetvu `main` a skontrolujte úspešný workflow Tests.
4. Zmena manifestu alebo RELEASE_NOTES.md na `main` spustí vydanie automaticky.
   Ručne ho možno spustiť cez **Actions → Release → Run workflow → main**.
5. Workflow znovu spustí testy, vytvorí ZIP a publikuje vydanie s tagom podľa manifestu.
6. Overte výsledné vydanie a následne ponuku aktualizácie v HACS.

Alternatívou je push tagu `vX.Y.Z` zhodného s manifestom. Existujúce vydanie sa
neprepisuje; pre opravu zvýšte verziu. Na publikovanie sa používa krátkodobý token
workflow, netreba ukladať osobný GitHub token. Workflow smie zapisovať len obsah repozitára.

HACS inštaluje `custom_components/family_quests` zo zdrojov vydania. Priložený ZIP je
pomôcka na ručnú inštaláciu; `zip_release` nie je nastavený. Repozitár musí byť verejný.
Nepridávajte HA zálohy, .storage, fotografie rodiny ani prihlasovacie údaje.
