## Nové v 0.6.1

- Rodič → Nastavenia → Upozornenia v HA: zapnutie/vypnutie súhrnu čakajúcich žiadostí.
  Vypnutie ihneď odstráni súhrn, zapnutie zobrazí stále čakajúce žiadosti.
  Mobilné automatizácie zostávajú nezávislé.
- Aktualizovaný príklad mobilnej automatizácie pridáva **Schváliť** a **Otvoriť rodičovskú kartu**.
  Kliknutie na samotnú správu tiež otvorí rodičovský dashboard.
- Nová administrátorská akcia `family_quests.approve_notification` overí konkrétnu
  čakajúcu žiadosť. Staré upozornenie nemôže schváliť nové splnenie po vrátení úlohy.

Po aktualizácii cez HACS reštartujte HA a obnovte dashboard. Pre mobil nahraďte starú
notifikačnú automatizáciu súborom examples/parent-notifications.yaml a doplňte akciu
mobilu a cestu rodičovského dashboardu. Samotná aktualizácia integrácie nemení automatizácie.

Tlačidlo Schváliť platí počas behu automatizácie, najviac 24 hodín; reštart HA alebo
znovunačítanie automatizácií čakanie zruší. Otvorenie karty zostáva dostupné.
Schválenie úlohy zachová body podľa času splnenia; plné body navyše uznajte v karte.

Overenie: 135 Python testov, test logiky karty, syntax Python/JavaScript a YAML.
Živý HA a doručenie na fyzický mobil neboli dostupné na overenie.
