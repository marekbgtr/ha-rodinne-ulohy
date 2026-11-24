# Inštalácia a aktualizácie

[Späť na úvod](../README.md)

## Prvá inštalácia cez HACS

Predpoklad: HACS už máte nainštalovaný; jeho dokumentácia je na https://www.hacs.xyz/.
Projekt používajte ako vlastný repozitár, bez čakania na zaradenie do katalógu.

1. V HACS otvorte **⋮ → Vlastné repozitáre / Custom repositories**.
2. Zadajte `https://github.com/marekbgtr/ha-rodinne-ulohy`, kategória **Integrácia / Integration**.
3. Vyhľadajte **Rodinné úlohy**, stiahnite vydanú verziu a reštartujte HA.
4. V **Nastavenia → Zariadenia a služby → Pridať integráciu** pridajte Rodinné úlohy.
5. Voliteľné ukážkové profily a úlohy majú nulové postihy na bezpečné skúšanie.

## Zdroj karty — iba raz

V **Nastavenia → Dashboardy → ⋮ → Zdroje** pridajte:

| Pole | Hodnota |
| --- | --- |
| URL | `/family_quests-static/family-quests-card.js` |
| Typ | JavaScript modul |

Ak Zdroje nevidíte, zapnite rozšírený režim vo svojom HA profile. Obnovte stránku.
Karta je súčasťou integrácie, nesťahuje sa zvlášť. [Príklady YAML](../examples).

## Prechod zo ZIP na HACS

1. Vytvorte zálohu HA vrátane konfigurácie a dát integrácií. Poznačte si zostatky.
2. Existujúcu integráciu **neodstraňujte**.
3. Pridajte repozitár do HACS a stiahnite ho. HACS má prevziať správu rovnakého
   priečinka `custom_components/family_quests`.
4. Reštartujte HA; integráciu už nepridávajte znova a existujúce karty ponechajte.
5. Ak zdroj karty obsahuje `?v=0.5.0` alebo staršie číslo, upravte existujúci zdroj
   na stabilnú adresu vyššie. Nevytvárajte druhý zdroj tej istej karty.
6. Úplne obnovte stránku na tablete a overte profily, body a úlohy.

Dáta sú uložené oddelene od kódu v HA Store. Nahradenie súborov ich nemá mazať.
Testy zahŕňajú načítanie dát 0.1.0; medziverzie netreba inštalovať postupne.
Pri chybe HACS nemažte integráciu ani jej úložisko; riešte konkrétnu hlášku.

## Ďalšie aktualizácie

**HACS → Rodinné úlohy → Aktualizovať → reštart HA → obnovenie stránky.**

Prečítajte si poznámky vydania a vytvorte zálohu. Aktualizácia zahŕňa serverovú časť
aj kartu. Na tablete môže byť potrebné zavrieť a otvoriť dashboard alebo vymazať
cache stránky. Nenačítavajte dve kópie karty naraz.

## Ručná inštalácia

Z vydania stiahnite `Rodinne-ulohy-VERSION.zip`, rozbaľte ho a skopírujte celý
`custom_components/family_quests` do `/config/custom_components/`. Reštartujte HA.
GitHub Source code ZIP má navyše vonkajší priečinok s názvom repozitára.
Do HA patrí iba priečinok integrácie, nie celý projekt.

## Riešenie problémov

| Príznak | Kontrola |
| --- | --- |
| Integrácia sa nezobrazuje | Umiestnenie súborov, reštart a protokol HA |
| Custom element doesn't exist | Zdroj JavaScript, typ modul, obnovenie stránky |
| Starý vzhľad | Duplicitné zdroje alebo cache tabletu |
| Rodičovská správa odmieta zmenu | Účet musí byť správca HA |
| Chýbajúce dáta po novom pridaní | Obnova pôvodnej konfigurácie zo zálohy |
