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
