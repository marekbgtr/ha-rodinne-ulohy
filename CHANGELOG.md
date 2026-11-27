# História verzií

## Nové v 0.6.0

- **Raz za víkend:** jedna úloha od piatka do nedele. Termín aj uzávierka platia
  v nedeľu; ďalší piatok vznikne nová úloha. Podporuje plné/neskoré body aj postih.
- **Vrátiť odmenu:** Rodič → Odmeny → Potvrdené odmeny. Zruší potvrdenú odmenu
  a vráti zaplatené body, pri spoločnej odmene každému presne jeho podiel.
- **Upozornenia v HA:** súhrn čakajúcich úloh a odmien sa vytvorí automaticky,
  aktualizuje pri zmenách a po vybavení zmizne.
- **Mobilné upozornenia:** príklad `examples/parent-notifications.yaml` pre oba typy
  žiadostí. Doplňte akciu svojho telefónu. Existujúce upozornenia na odmeny fungujú ďalej.
- **Rodič na detskej karte:** správca HA vidí aj tlačidlá Schváliť a Uznať za plné body.
  Bežný účet ich nevidí a server rodičovské operácie odmietne.
- Spoločná bodová odmena naďalej podporuje ľubovoľné príspevky, napríklad 6 + 4 bodov.

Pred aktualizáciou záloha HA. Aktualizovať cez HACS, reštart HA a obnovenie dashboardu.
Existujúcu integráciu neodstraňujte. Dáta sa zachovávajú; staré harmonogramy sa nemenia.

Overenie: 129 Python testov, kontrola syntaxe a test logiky karty s náhradou DOM.
Živý HA a fyzický tablet neboli pri vydávaní dostupné.


## 0.5.0

- Spoločné bodové odmeny, príspevky, schválenie a presné refundácie.
- Väčší priestor pre symbol splnenia a samostatná fajka.
- 118 testov serverovej logiky, kontrola syntaxe a test logiky karty.
- Príprava distribúcie cez GitHub, slovenského návodu a automatizovaného vydávania.

## 0.4.0

- Zrušenie ospravedlnenia a uznanie plných bodov po termíne.
- Opakované úlohy viackrát denne, voliteľné štatistiky a symboly splnenia.

## 0.3.0

- Týždenné a dlhodobé úlohy, štatistiky, poradie skupín a reset testovacej histórie.

## Staršie vydania

Profily, samostatné karty, režimy spoločných úloh, rodičovská správa, vrátenie bodov,
odmeny naviazané na úlohu a udalosť žiadosti o odmenu.
