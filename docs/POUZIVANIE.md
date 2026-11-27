# Podrobný návod

[Späť na úvod](../README.md) · [Inštalácia a aktualizácie](INSTALACIA.md)

### Spoločné odmeny

**Rodič → Odmeny → Nová odmena / Upraviť**: vyberte druh **Za body**, zadajte
kladnú cenu a zapnite **Spoločná odmena – účastníci sa skladajú bodmi**.

Každý aktívny účastník vidí spoločný priebeh v záložke Odmeny. Cez **Prispieť** zadá
vlastnú sumu, najviac do svojho zostatku a zostávajúcej ceny. Napríklad odmena za
10 bodov: Maty 6 hviezdičiek a Momo 4 srdiečka. Symboly sú osobné; 1 jednotka každého
symbolu znamená 1 bod. Rozdelenie nemusí byť rovnaké a celú cenu môže zaplatiť aj jeden.

- Body sa pri príspevku okamžite rezervujú. Priebeh ukazuje celkovú sumu aj príspevky
  jednotlivých účastníkov. Prispievať možno postupne počas viacerých dní.
- Počas zbierania môže účastník cez **Vrátiť môj príspevok** získať späť všetky svoje
  príspevky do daného zbierania. Zostatky ostatných sa nemenia.
- Po nazbieraní presnej ceny sa príspevky uzamknú a vznikne žiadosť rodičovi. Udalosť
  `family_quests_reward_requested` sa odošle až vtedy, nie pri každom príspevku.
  Doterajšia notifikačná automatizácia funguje aj pre spoločnú žiadosť; `person_name`
  obsahuje mená prispievateľov. Pribudli polia `shared` a `contributors` (ID → suma).
- Schválenie odmeny už nič navyše neodpočíta. Zamietnutie alebo rodičovské **Zrušiť
  zbieranie a vrátiť body** vráti presne každému jeho rezervované body. Rodič môže
  zrušiť aj ešte nedokončené zbieranie v záložke Odmeny.
- Po vybavení odmeny možno začať ďalšie zbieranie na rovnakú odmenu.
- Počas zbierania alebo čakania nemožno zmeniť cenu ani druh odmeny. Najprv zbieranie
  zrušte alebo vybavte. Pozastavenie odmeny zastaví nové príspevky, ale umožní vrátenie.
- Spoločné zbieranie je v tejto verzii pre bodové odmeny; kombinácia s podmienkou
  konkrétnej úlohy nie je dostupná. Existujúce osobné odmeny fungujú ako doteraz.
- V štatistikách sa každý príspevok započíta do rezervovaných/využitých bodov daného
  účastníka. Vrátenie príspevku zruší jeho účinok na hodnotenie.

## Od verzie 0.6.1: nastavenie upozornení

V **Rodič → Nastavenia → Upozornenia v HA** môžete súhrn vypnúť alebo zapnúť.
Predvolene zostáva zapnutý. Vypnutie odstráni aktuálny súhrn; opätovné zapnutie
zobrazí stále čakajúce úlohy a odmeny. Nastavenie prežije reštart a nemení mobilné upozornenia.

### Schválenie priamo z mobilu

Po aktualizácii na 0.6.1 a reštarte HA nahraďte doterajšiu automatizáciu
[aktuálnym YAML](../examples/parent-notifications.yaml). Upravte tieto dve hodnoty:

- `notify.mobile_app_tvoj_mobil`: notifikačná akcia rodičovského telefónu.
- `parent_path`: cesta k záložke s rodičovskou kartou, napr. `/dashboard-rodina/rodic`.
  Skopírujte skutočnú cestu z adresy pri otvorení svojej rodičovskej záložky.
  Uvedená cesta je príklad, automaticky sa nevytvorí.

Notifikácia má **Schváliť** a **Otvoriť rodičovskú kartu**. Aj kliknutie na správu otvorí
rovnakú záložku (Android `clickAction`, iOS `url`). V aplikácii musíte byť prihlásení
rodičovským účtom. Odkaz otvorí stránku dashboardu; nedokáže sám prepnúť vnútornú
záložku vlastnej karty, preto odporúčame samostatnú stránku s `mode: admin`.

Schválenie rozpozná konkrétnu žiadosť a nemení body podľa termínu: pri neskorom splnení
zostanú neskoré body. Plné body uznajte v karte. Pri odmene sa rezervované body znova
neodpočítajú. Staré oznámenie po zrušení/vrátení úlohy novú úlohu neschváli.

Automatizácia čaká na odpoveď najviac 24 hodín a obsluhuje najviac 100 súbežných správ.
Reštart HA alebo znovunačítanie automatizácií čakanie ukončí. Vtedy použite otvorenie
karty; tlačidlo Schváliť v starej správe už nereaguje. Automatizáciu nemožno skúšať
voľbou Spustiť bez udalosti — otestujte ju novou žiadosťou dieťaťa.
Pri súbežnej zmene dát môže schválenie odmietnuť zastaraný stav; skontrolujte ho v karte.

Tlačidlo vyžaduje odomknutie na podporovaných systémoch (Android 12+ / iOS).
Automatizáciu smerujte iba na rodičovský telefón. Notifikácie neposielajte detskému
telefónu, ak mu nechcete umožniť schvaľovanie. Nová akcia integrácie je registrovaná
ako administrátorská; bežný účet ju nemôže volať priamo.

## Od verzie 0.6.0

### Školské dni a víkend

Vytvorte dve úlohy s rovnakými účastníkmi a režimom Každý samostatne:

| Nastavenie | Školské úlohy | Školské úlohy – víkend |
| --- | --- | --- |
| Opakovanie | Vybrané dni v týždni | Raz za víkend (piatok – nedeľa) |
| Dni | Po, Ut, St, Št | Výber dní sa nepoužíva |
| Splniť načas do | 19:00 každý vybraný deň | 19:00 v nedeľu |
| Uzavrieť úlohu o | napr. 22:00 | napr. 22:00 v nedeľu |
| Body načas / po termíne / postih | 3 / 1 / 2 | napr. 3 / 1 / 2 |

Postih zadávajte ako kladné číslo; automaticky sa odpočíta. Víkendovú úlohu stačí
splniť raz. Od piatka 00:00 do nedeľného termínu sú plné body, potom znížené až po
uzávierku. Úloha sa počas Po–Št nezobrazuje na detskej karte a ďalší piatok sa obnoví.
Termín je vrátane nastavenej sekundy, pri uzávierke je už plnenie zatvorené.
Všetky časy sú v časovom pásme HA. Po vytvorení v sobotu/nedeľu je dostupná ihneď.

### Rozdelenie ceny a vrátenie odmeny

Rodič → Odmeny → Upraviť → **Za body**, cena a **Spoločná odmena**. Deti si v karte
Odmeny cez **Prispieť** zvolia vlastnú sumu: napríklad Maty 6 a Momo 4 z ceny 10.
Môžu prispievať postupne; pomer nemusí byť rovnaký. Po nazbieraní ceny čaká odmena na rodiča.

Omylom potvrdenú odmenu nájdete v **Rodič → Odmeny → Potvrdené odmeny → Vrátiť odmenu**.
Po potvrdení sa odmena zruší a vrátia sa všetky zaplatené body, pri spoločnej odmene
presne pôvodným prispievateľom. Opakovaný klik body nezdvojnásobí. Odmenu možno vyžiadať
znova. Pri odmene viazanej na úlohu zostáva samotné splnenie úlohy zachované.
Toto je zrušenie odmeny s refundáciou, nie návrat do čakajúceho schválenia.

### Upozornenia a rodičovské tlačidlá

HA automaticky zobrazí súhrn čakajúcich žiadostí o odmenu a úloh na schválenie v paneli
upozornení. Po ich vybavení súhrn zmizne. Pre úlohy treba zapnúť **Vyžaduje schválenie rodičom**.
Upozornenie HA môže vidieť aj používateľ spoločného tabletu; nejde o súkromnú mobilnú správu.

Pre mobil vložte [túto automatizáciu](../examples/parent-notifications.yaml) a nahraďte
`notify.mobile_app_tvoj_mobil` svojou akciou. Starú automatizáciu odmien nahraďte, aby sa
správy nezdvojovali. Udalosti sa posielajú po úspešnom uložení; pri reštarte sa spätne
neopakujú. Pri výpadku doručenia zostáva žiadosť v rodičovskom paneli.

Ak detskú kartu otvorí **správca HA**, pri čakajúcej úlohe uvidí **Schváliť**, pri
oneskorenej úlohe aj **Uznať za plné body**. Bežný detský účet tieto možnosti nemá.
Pri opakovanej úlohe sú schválenia v rozbalení jednotlivých splnení.

## Od verzie 0.4.0

Aktualizovať možno priamo z 0.1.0 alebo ktorejkoľvek medziverzie. Nahradia sa súbory
integrácie a karty; profily, body, úlohy, odmeny a história zostanú. Zálohu HA vytvorte
pred aktualizáciou, integráciu neodstraňujte. Nové detské štatistiky sú predvolene skryté.

### Rodičovské opravy

- **Zrušiť ospravedlnenie** je pri ospravedlnenej úlohe v rodičovskom prehľade.
  Pred uzávierkou sa dá znovu plniť, po uzávierke sa prípadný postih vyhodnotí raz.
  Ak ospravedlnenie umožnilo vyplatenie spoločnej úlohy, jeho zrušenie vráti skupinové
  body aj súvisiace odmeny; spoločná úloha čaká na všetkých neospravedlnených.
- **Uznať za plné body** je pri úlohe po termíne, aj po uzávierke. Funguje pri
  čakajúcom schválení, pri už pridelených znížených bodoch aj pri nesplnenej úlohe.
  Doplatí iba rozdiel, vráti automatický postih a zachová záznam rodičovského uznania.
  Opakované kliknutie body nezdvojí; Vrátiť odpočíta presnú sumu.
- Pri spoločnej úlohe stále platí podmienka splnenia všetkými. Pri delení jedného
  balíka bodov treba uznať všetkých oneskorených členov, aby bol celý balík plný.
- Skutočný čas kliknutia sa neprepisuje: v štatistike zostáva oneskorenie a odmena
  vyžadujúca splnenie načas sa tým automaticky neodomkne.

### Viackrát za deň

V editore úlohy zvoľte **Opakovanie → Viackrát za deň** a otvorte príslušné nastavenia.
Príklad: Upratanie stola, 1 bod za splnenie, denný limit 4, cieľ 0, odstup 5 minút.

- Dostupná celý miestny deň vo vybrané dni, na ďalší deň začne nový zoznam splnení.
  Polia denného termínu, uzávierky a oneskorených bodov sa ignorujú.
- **Denný limit**: 0 bez limitu; inak maximálny počet platných splnení vrátane čakajúcich.
- **Denný cieľ**: 0 dobrovoľná bonusová úloha, nikdy nemá postih za nesplnenie.
  Pri cieli napr. 3 je postih po polnoci iba jeden za nedosiahnutie cieľa, nie za každý
  chýbajúci pokus. Čakajúce schválenia sa do cieľa započítajú.
- **Odstup** v minútach; aj pri 0 zostáva dvojsekundová ochrana proti dvojitému kliknutiu.
- Režimy **Každý samostatne** a **Na striedačku**. Spoločné plnenie a Kto prvý pre tento
  typ zatiaľ nie sú dostupné; editor odmietne neplatnú kombináciu.
- Každé splnenie má vlastný čas, prípadné schválenie a rodičovské tlačidlo Vrátiť.
  Vrátené splnenie sa nezapočíta do limitu a body sa presne odpočítajú.
- Ospravedlnenie zruší zostávajúcu povinnosť daného dňa, zachová už získané body.
- Naviazanú odmenu možno žiadať raz za deň po aspoň jednom schválenom splnení.
  Vrátenie posledného schváleného splnenia zruší súvisiacu odmenu.
- Karta zobrazuje počet splnení, získané body, cenu ďalšieho splnenia, cieľ a limit.
  Štatistiky počítajú jednotlivé splnenia; chýbajúce plnenia do denného cieľa sa
  zobrazia ako otvorené a po polnoci ako nesplnené.

### Štatistiky a ikony

**Rodič → Nastavenia → Štatistiky na detskej karte**: pri každom účastníkovi
Sprístupniť / Skryť. Rovnaká voľba je aj v úprave profilu. Bez povolenia zmizne
z detskej karty záložka Môj týždeň aj týždenný súhrn pod menom. Rodič svoje štatistiky
vidí stále. Voľba nemení zbieranie údajov ani výpočet bodov.

Ikona plnenia vpravo používa symbol bodov účastníka: prázdny pred splnením, vyplnený
po splnení. Hviezda, srdce, koník, diamant a dinosaurus sú lokálne SVG bez závislosti
od fontu. Rovnako SVG používajú stavy Čaká, Čas vypršal a Ospravedlnené. Pri inom
vlastnom emoji sa zachová vlastný znak a po splnení doplní SVG fajka; samotné vlastné
emoji a ľavé ikony úloh stále závisia od podpory zariadenia.

Overenie: 118 Python testov pravidiel a transakcií, JavaScript syntaktická kontrola
aj test karty s náhradou DOM. Test prechodu používa stav vytvorený skutočným kódom
0.1.0 (tests/fixtures/state_010.json). Testovací prehliadač tu nebolo možné spustiť;
živý HA ani fyzický tablet M2 neboli pri tejto aktualizácii dostupné na overenie.

## Od verzie 0.3.0: týždenné a dlhodobé úlohy

V **Rodič → Úlohy → Nová úloha / Upraviť → Opakovanie** vyberte:

| Režim | Správanie |
|---|---|
| Vybrané dni v týždni | Pôvodné denné úlohy s termínom a uzávierkou. |
| Raz za týždeň | Dostupná pondelok až nedeľa; ľubovoľný deň, jedna odmena na účastníka za týždeň. Obnova v pondelok 00:00 podľa času HA. |
| Dlhodobá / jednorazová do dátumu | Dostupná ihneď; dátum a dva časy určujú konečný termín a uzávierku. |
| Bez termínu (jednorazovo) | Zostáva dostupná do splnenia. Žiadna automatická obnova ani postih. |

**Príklad:** Upratať izbu → Raz za týždeň → Každý samostatne → 5 bodov.
Netreba vybrať konkrétny deň. Denné časy a vybrané dni sa pri týždennej úlohe ignorujú.
Voliteľný postih sa vyhodnotí až po skončení nedele, raz; predvolené 0 znamená bez postihu.
Týždenná úloha založená uprostred týždňa platí pre zvyšok aktuálneho týždňa.

Fungujú aj spoločné plnenie, prvý víťaz, schválenie, vrátenie bodov a naviazané odmeny.
Pri striedaní sa týždenná úloha posunie ďalšiemu účastníkovi nasledujúci týždeň.
Naviazaná odmena platí raz pre aktuálny výskyt: pri týždennej do konca týždňa,
pri dlhodobej do jej konečného dňa, pri úlohe bez termínu raz celkovo.

V štatistikách sa viacdňové splnenie a body pripíšu ku dňu kliknutia. Otvorená
viacdňová úloha sa zobrazuje raz v aktuálnom prehľade; po vypršaní patrí k poslednému
dňu obdobia. Úloha bez termínu nezanecháva v minulých týždňoch nesplnené povinnosti.
Rozpracovanému výskytu zostávajú pôvodné pravidlá; opakovanie alebo dátum mu nemožno
zmeniť. Pre iný harmonogram vytvorte novú úlohu. Aktualizácia nemaže dáta.


## Aktualizácia existujúcej inštalácie

Použite [návod na HACS alebo ručnú inštaláciu](INSTALACIA.md). Integráciu neodstraňujte.

## Týždenná štatistická karta

V rodičovskej karte je záložka **Štatistiky**. Detská záložka **Môj týždeň** sa zobrazí len po povolení rodičom v Nastaveniach.
Samostatnú kartu pridajte pomocou:

```yaml
type: custom:family-quests-card
mode: stats
person: Maty
```

Pre druhú kartu použite `person: Momo`. Bez `person` bude prepínanie účastníkov.
Príklady sú aj v `../examples/weekly-card.yaml` a `../examples/two-weekly-cards.yaml`.

Karta obsahuje:

- Prepínanie aktuálneho a siedmich predchádzajúcich kalendárnych týždňov (pondelok–nedeľa, časové pásmo HA).
- Hotové / doteraz priradené úlohy, percentuálnu úspešnosť a body získané za úlohy.
- Počty splnení načas, neskorých, nesplnených, otvorených, čakajúcich a ospravedlnených úloh.
- Sedem denných stĺpcov a prehľad úspešnosti skupín/rutín.
- Krátke povzbudivé slovné hodnotenie založené na pravidlách, bez externého AI či cloudu.
- Odznaky: **Prvý krok** (aspoň 1 dokončenie), **Päť hotových** (aspoň 5), **Všetko načas** (aspoň 3 dokončenia a všetky načas), **Hotový deň** (aspoň jeden uplynutý deň s nenulovým počtom hodnotených úloh a všetkými hotovými).
- Rozpis: body za úlohy + bonusy − postihy/ručné odpočty − odmeny vrátane rezervácií.

Odznaky sú iba vizuálne a nepridávajú body. Zobrazujú sa podľa práve vybraného týždňa.
Dnešný deň sa za „Hotový deň“ považuje až nasledujúci deň, aby dodatočná dnešná úloha
nezneplatnila predčasne pridelený odznak. Aktuálny týždeň je jasne označený ako priebežný.

Výpočet nepenalizuje ospravedlnené úlohy ani nevíťazov dobrovoľných súťaží „Kto prvý“.
Pri spoločnej úlohe sa dokončenie započíta až po skutočnom uvoľnení odmeny celej skupine.
Čakajúce schválenie sa nezamieňa za nesplnenú úlohu. Vrátenie splnenia upraví štatistiky
a odznaky aj spätne; vrátené bodové operácie sa nezapočítavajú dvakrát.
Týždenné finančné súčty sa viažu na deň pôvodnej operácie, nie deň jej neskoršieho vrátenia.
Dni bez priradených úloh nezvyšujú ani neznižujú úspešnosť. Budúce dni sa ešte nehodnotia.
Osem týždňov je zobrazovaný rozsah, nie doba uchovávania: úplná história zostáva v úložisku.

## Poradie skupín úloh

**Rodičovská karta → Nastavenia → Poradie skupín úloh.** Šípkami ↑ / ↓ zmeňte poradie,
napríklad Ráno → Po škole → Večer. Uloží sa ihneď a platí pre všetkých účastníkov v detských
kartách aj pre prehľad rutín v štatistikách. Vnútri skupiny zostáva radenie podľa termínu.
Nové skupiny sa pripoja na koniec. Úlohy bez názvu skupiny patria do **Úlohy**.
Toto je poradie zobrazenia, nie podmienka: úlohy možno naďalej plniť v ľubovoľnom poradí.

## Budúci prechod z testovania do ostrej prevádzky

**Teraz nič nemažte, ak ešte testujete. Samotná aktualizácia reset nespúšťa.**

Keď nastane čas: vytvorte zálohu HA a v rodičovskej karte otvorte
**Nastavenia → Prechod z testovania do ostrej prevádzky → Pripraviť vymazanie testovania**.

Reset celej domácnosti:

- Vymaže všetky splnenia, bodovú históriu, postihy a žiadosti o odmeny; zostatky budú 0.
- Zachová profily, mená, fotky, symboly, ciele, definície úloh/odmien a poradie skupín.
- Je dostupný iba správcovi HA. Vyžaduje potvrdenie zálohy, presný text `VYMAZAT HISTORIU` a následné potvrdenie dialógu. Server overuje oprávnenie, text a potvrdenie zálohy.
- Predvolene začne novú evidenciu **zajtra**. Do konca dneška sa nové výskyty úloh nevytvoria a nevzniknú spätné postihy.
- Možno zvoliť **dnes**: úlohy s už uplynutou uzávierkou sa preskočia; dnešné ešte otvorené úlohy sa vytvoria podľa pôvodných pravidiel.
- Jednorazové úlohy s dátumom pred novým začiatkom sa neprenesú na iný dátum. V prípade potreby ich upravte.
- Obnova vymazanej histórie je možná len zo zálohy HA; nejde o bežnú akciu „Vrátiť“.

Nejde o automatické čistenie histórie ani o reset každého týždňa. Štatistiky sa od tohto
okamihu začnú plniť novými údajmi. Nevráti sa žiadna fyzicky odovzdaná odmena.

## Notifikácie žiadostí o odmenu

Funkcia z 0.1.2 ostáva zachovaná. Udalosť `family_quests_reward_requested` obsahuje
`person_name`, `reward_name`, `cost`, `symbol`, `request_id`, `requested_at`, `person_id`,
`reward_id`, `config_entry_id`. Vyšle sa až po uložení novej žiadosti; nie pri čítaní,
reštarte ani pri opakovaní tej istej operácie. V `../examples/reward-notification.yaml`
vymeňte `notify.mobile_app_tvoj_mobil` za skutočnú akciu svojho telefónu.
Živá udalosť negarantuje doručenie pri páde HA medzi uložením a vyslaním, uložená žiadosť
však zostáva v rodičovskej karte. Týždenné vyhodnotenie je zatiaľ v karte, neodosiela sa
samo pravidelnou notifikáciou.

## Overenie 0.5.0

Prešlo **118 automatických testov** pravidiel a transakcií, vrátane týždenných hraníc,
ospravedlnení, vrátenia bodov, poradia skupín, spätnej kompatibility, oprávnení a resetu
pri zlyhaní zápisu či opakovaní požiadavky. Test logiky karty s náhradou DOM pokrýva aj
nové štatistiky, prepínanie týždňov, poradie skupín a resetovací formulár.

Testy nepredstavujú živý HA ani reálny prehliadač/tablet. Nové rozloženie a celé spustenie
v HA treba overiť v domácnosti. Reset netreba skúšať na údajoch, ktoré chcete zachovať.

---

# Inštalácia a základné pravidlá

Vlastná **integrácie pre Home Assistant** a jednej vlastnej Lovelace karty s detským aj rodičovským režimom. Lokálne ukladanie v HA, bez cloudu a bez ďalšieho servera. Nemá závislosť od ChoreOps, Mushroom, button-card ani auto-entities.

**Stav:** testy pravidiel a transakcií prešli; skutočné spustenie v HAOS a na Huawei M2 ešte nebolo overené. Nejde o hotový produkt overený v domácnosti. ChoreOps počas skúšania ponechajte nainštalovaný. Nepoužívajte predchádzajúci upravený `chore_manager.py` pre túto integráciu.

## 3. Účty a rodičovské oprávnenia

- Rodičovský panel otvorte pod **správcovským účtom HA** (napr. Marek).
- Na spoločnom detskom tablete použite **samostatný účet HA bez administrátorských oprávnení**. Skrytie záložky alebo režim `child` neodoberá oprávnenia správcovskému účtu.
- Správa profilov, úloh, odmien, body +/−, schvaľovanie, ospravedlnenie a vrátenie sú kontrolované **na serveri**.
- Táto verzia používa spoločný rodinný tablet: bežný prihlásený používateľ môže prepínať aktívne profily, označiť ich úlohy, meniť symboly a požiadať o odmeny. Nejde o oddelené súkromné detské účty. Profily a história nie sú pred ostatnými používateľmi domácnosti utajené.

## 4. Bežná správa bez YAML

V rodičovskej karte:

- **Účastníci**: pridať alebo upraviť deti aj rodičov, meno, emoji, názov bodov, fotku, aktívny profil.
- Fotky: súbor v `/config/www/maty.jpg`, v profile cesta `/local/maty.jpg`. Voliteľné; inak sa zobrazí iniciála.
- **Úlohy**: názov, emoji, účastníci, režim, vybrané dni/jednorazový dátum, termín, uzávierka, body. Rozšírené: meškanie, postih, schvaľovanie, skupina/rutina, delenie spoločnej odmeny, aktívnosť.
- **Odmeny**: bodová cena, väzba na konkrétnu úlohu alebo kombinácia **Body + splnená úloha**; voliteľne požiadavka splniť načas.
- **Dnes**: rýchle −10/−2/−1/+1/+2/+10, vlastná suma s dôvodom, žiadosti o odmeny, schválenie, vrátenie a ospravedlnenie. Zobrazuje dnešné úlohy a posledných 7 dní, staršie čakajúce schválenia zostávajú viditeľné.
- **História**: posledných 100 bodových udalostí domácnosti filtrovaných podľa profilu; pri ručnej úprave je tlačidlo na jej presné vrátenie. Úplná história zostáva uložená v HA.
- Dieťa si samo vyberie vlastné emoji v **Môj symbol** a bodovú odmenu ako cieľ. Zmena symbolu nemení zostatok.

## 5. Pravidlá a hraničné situácie

### Čas a body

- Časy používajú časové pásmo nastavené v HA, napr. Europe/Bratislava.
- Príklad: do **19:45:00 vrátane** plná odmena, potom znížená, od **22:00:00** už splnenie nie je dostupné a vyhodnotí sa postih. Termín a uzávierka sú v tom istom miestnom dni.
- Pri schvaľovaní rozhoduje čas kliknutia dieťaťa, nie čas schválenia rodičom. Čakajúce schválenie nedostane automatický postih.
- Zostatok smie byť záporný. Body sú celé čísla.
- Týždenná štatistika počíta aktuálne platné splnenia a čistú bodovú zmenu priradenú k dňom tohto týždňa; zahŕňa aj odmeny a ručné úpravy.
- Výpadok HA: pri návrate sa vyhodnotia zachované výskyty a chýbajúce dni najviac 31 dní spätne. Pre dlhší výpadok sa zobrazí upozornenie; staršie nevytvorené dni nedostanú automatické postihy.
- Po reštarte sa už vykonaný postih ani odmena nepridelia znova.

### Režimy úloh

| Režim | Pravidlo |
|---|---|
| Každý samostatne | Vlastné splnenie, odmena a postih pre každého. |
| Kto prvý | Prvé prijaté kliknutie rezervuje úlohu jednému účastníkovi. Ostatným zmizne; nikto z nich nedostane postih. Platí aj počas čakania na schválenie. V tomto režime je automatický postih vždy 0. |
| Spoločne | Všetci neospravedlnení účastníci musia potvrdiť a prípadne dostať schválenie. Až potom sa odmeny pripíšu. Postih je iba pre toho, kto svoju časť vôbec neoznačil. |
| Na striedačku | Jeden účastník na plánovaný deň, v poradí vytvorených aktívnych profilov. Dni mimo harmonogramu poradie neposúvajú. Zmena zoznamu účastníkov môže zmeniť ďalšie poradie. |

Spoločná odmena: buď každý dostane svoje body podľa času, alebo sa rozdelí jeden spoločný balík. Ak niekto mešká, pri delení sa použije znížený balík. Celé body sa rozdelia rovnomerne, zvyšok v poradí profilov (napr. 5 → 3 + 2). Ospravedlnený nedostáva body a nezdržiava ostatných.

### Vrátenie, ospravedlnenie a úpravy

- **Vrátiť** ruší konkrétne splnenie a presne jeho body, nie predvolenú odmenu ani historický súčet. Opakovanie neodpočíta body znova.
- Pri spoločnej úlohe vrátenie jedného účastníka odoberie odmenu celej skupine, jeho časť sa otvorí a ostatným zostáva potvrdenie. Po opätovnom splnení sa skupina znovu vyhodnotí.
- Pri súťaži sa po vrátení uvoľní miesto pre nového víťaza.
- **Po uzávierke** vrátenie neotvorí už skončený časový interval. Znovu sa môže vyhodnotiť postih. Ak sa nemá trestať, použite následne **Ospravedlniť**.
- **Ospravedlniť** sa týka jedného výskytu úlohy a vracia prípadný postih. Už splnenú úlohu treba najprv vrátiť. Rodič môže použiť **Zrušiť ospravedlnenie**; po uzávierke sa prípadný postih vyhodnotí znova, iba raz.
- Úprava dnešnej úlohy platí ihneď, iba ak ešte nemá žiadne splnenie, ospravedlnenie či postih. Inak jej dnešný výskyt zachová pravidlá a zmena platí pre ďalšie dni. To platí aj pri deaktivovaní úlohy; rozpracovaný dnešný výskyt riešte ospravedlnením.
- „Všetci“ sa vyhodnotí pri vytvorení denného výskytu. Nový účastník sa automaticky pridá do ďalších výskytov, nie do už rozpracovaných.
- Profily a definície sa deaktivujú, nemažú: história zostáva zachovaná.

### Odmeny

- **Body + splnená úloha (kombinovaná odmena):** napr. rozprávka stojí 2 body a musí byť splnené dnešné pyžamo. Obe podmienky kontroluje server pre toho istého účastníka. Body za samotné pyžamo sa môžu použiť na cenu odmeny. Cena sa rezervuje pri žiadosti presne raz; potvrdenie už nič neodpočítava. Zamietnutie vráti cenu a umožní opakovať žiadosť. Po potvrdení je kombinovaná odmena vyčerpaná pre daný denný výskyt. Vrátenie úlohy zruší jej naviazanú odmenu, vráti cenu a odoberie body získané za samotnú úlohu. Napr. zostatok 10 → pyžamo +2 → odmena −3 → vrátenie úlohy +3 −2 = 10.

- Bodová odmena: pri žiadosti sa cena ihneď odpočíta ako rezervácia. Potvrdenie ju už neodpočítava. Zamietnutie ju presne vráti.
- Odmena za úlohu: bez míňania bodov, dostupná po jej skutočnom splnení/schválení, raz na osobu, odmenu a denný výskyt úlohy.
- Vrátenie úlohy zruší aj naviazanú žiadosť o odmenu. Už prečítanú rozprávku či odovzdanú odmenu nemožno fyzicky vziať späť; také prípady posúdi rodič.
- Bodové odmeny môže rodič potvrdzovať aj s odstupom. Zmeny definície odmeny nemenia cenu už rezervovanej žiadosti.

## 6. Prvý krátky test v HA

1. Otvorte detskú kartu → Maty → pyžamo. Zostatok sa zvýši podľa času.
2. V rodičovskej karte pri pyžame použite **Vrátiť** pred uzávierkou. Body aj stav sa majú vrátiť; Momo zostane nezmenená.
3. Pridajte testovaciu úlohu „Kto prvý“, splňte ju za jedného a skontrolujte skrytie druhému.
4. Pridajte spoločnú úlohu; po prvom kliknutí sa čaká, po druhom sa pridelia body.
5. Vyskúšajte bodovú odmenu: žiadosť → rezervácia → zamietnutie → vrátenie bodov.
6. Reštartujte HA a skontrolujte zostatky a stavy.
7. Až potom nastavte reálne postihy.

Všetky testovacie ručné zmeny možno vrátiť v histórii. Ukážkové profily nie sú import ChoreOps; jeho zostatky možno prípadne preniesť jednorazovou ručnou úpravou s dôvodom.

## 7. Ukladanie, zálohy a odstránenie

Dáta ukladá HA Store pod kľúčom `family_quests.<config_entry_id>` v `/config/.storage/`. Integrácia serializuje operácie, ukladá ich pred odpoveďou a pri chybe uloženia obnoví predchádzajúci stav. História sa v 0.5.0 automaticky neorezáva. Priebežné pravidelné zálohy HA preto zahŕňajú aj tieto údaje. Súbor `.storage` neupravujte ručne počas behu.

Odstránenie integrácie odstráni jej entity, ale dátový súbor ostáva pre prípad obnovy. Nové pridanie vytvorí novú položku konfigurácie a nové úložisko: nie je to spôsob resetu ani obnovy. Na obnovu použite zálohu HA.

Karta nemá offline frontu: pri strate pripojenia nezobrazí úspešné splnenie bez potvrdenia servera. Pri nejasnej odpovedi načíta skutočný stav.

