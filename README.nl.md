
[![en](https://img.shields.io/badge/lang-en-red.svg)](README.md)
[![nl](https://img.shields.io/badge/lang-nl-orange.svg)](README.nl.md)

![Version](https://img.shields.io/github/v/release/remmob/magna3 'Release') ![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg 'HACS Custom') [![total issues](https://img.shields.io/github/issues/remmob/magna3 'Total issues')](https://github.com/remmob/magna3/issues) ![Stars](https://img.shields.io/github/stars/remmob/magna3)

# Grundfos MAGNA3 – Modbus-integratie voor Home Assistant

Bewaak en bedien een **Grundfos MAGNA3**-circulatiepomp vanuit Home
Assistant via Modbus — met een **CIM 200**-module (Modbus RTU/serieel) of
een **CIM 500**-module (Modbus TCP). Geen cloud, geen Grundfos GO-app
nodig: alles draait lokaal, rechtstreeks uitgelezen van de pomp.

🇬🇧 English version: [README.md](README.md)

> **Disclaimer**: Dit is een onafhankelijke, door de community gebouwde integratie. Ze is niet verbonden met, goedgekeurd door, of ondersteund door Grundfos. "Grundfos" en het Grundfos-logo zijn handelsmerken van hun respectievelijke eigenaar, hier uitsluitend gebruikt om compatibele hardware te identificeren. De software wordt geleverd zoals ze is (zie [LICENSE](LICENSE)); het bedraden van je pomp en het aansluiten van een gateway gebeurt op eigen risico.

---

## Inhoudsopgave

- [Kenmerken](#kenmerken)
- [Vereisten](#vereisten)
- [Installatie](#installatie)
- [Configuratie](#configuratie)
- [Bediening](#bediening)
- [Instellingen & meldingen](#instellingen--meldingen)
- [Sensoren](#sensoren)
- [Bewaking van de verbinding](#bewaking-van-de-verbinding)
- [Problemen oplossen](#problemen-oplossen)
- [Technische referentie](#technische-referentie)
- [Bijdragen](#bijdragen)

---

## Kenmerken

- **Volledige pompbesturing** — pomp aan/uit, regelmodus wisselen (constante
  curve, constante druk, AUTOADAPT, FLOWLIMIT, …), setpoint en een maximale
  debietbegrenzing instellen, alarmen resetten — allemaal vanuit Home
  Assistant.
- **Uitgebreide meetdata** — opvoerhoogte, debiet, toerental, vermogen,
  energieverbruik, temperaturen, bedrijfsuren, aantal starts, en meer.
- **Uitsluitend lokaal pollen** — communiceert rechtstreeks met de
  CIM-module, geen internet of cloudaccount nodig.
- **Beide verbindingstypen** — zowel Modbus TCP (CIM 500) als Modbus
  RTU/serieel (CIM 200), volledig via de UI te configureren.
- **Slimme verbindingsbewaking** — detecteert niet alleen een verbroken
  Modbus-verbinding, maar ook het subtielere geval waarin de CIM-module
  blijft antwoorden met **bevroren** data omdat de interne verbinding met de
  pomp zelf is weggevallen.
- **Meldingen per categorie met stille uren** — verbindingsfouten, alarmen en
  waarschuwingen hebben elk hun eigen mobiele notify-services, meldingsonderwerp,
  vertraging en stille-uren-venster (houd niet-urgente mobiele meldingen 's nachts
  vast), als permanente en/of pushmelding.
- **Verstandige standaardinstellingen** — diagnostische en zelden benodigde
  sensoren staan standaard uit, zodat je entiteitenlijst overzichtelijk
  blijft; schakel ze per entiteit in wanneer je ze nodig hebt.

## Vereisten

- Home Assistant met de custom integration geïnstalleerd (zie hieronder).
- Een Grundfos MAGNA3-pomp voorzien van een **CIM 200**- (RS-485/Modbus RTU)
  of **CIM 500**-module (Modbus TCP).
- Netwerktoegang (TCP) of een seriële verbinding (RTU/USB-adapter) vanaf je
  Home Assistant-host naar de CIM-module. Een CIM 200 is ook via het
  netwerk te benaderen met een Modbus RTU-naar-TCP/IP-gateway — zie de
  opmerking onder [Configuratie](#configuratie).
- Python-afhankelijkheden (worden automatisch geïnstalleerd):
  `pymodbus>=3.6.9`, `pyserial>=3.5`.

## Installatie

> ℹ️ Nog niet in de HACS-standaardstore — installeer voorlopig via een custom repository of handmatig.

### HACS (custom repository)

1. Open **HACS** in Home Assistant.
2. Klik op het menu met de drie puntjes (⋮) rechtsboven.
3. Kies **Custom repositories**.
4. Voeg deze repository-URL toe: `https://github.com/remmob/magna3`.
5. Zet de categorie op **Integration** en klik op **Add**.
6. Zoek op **Grundfos MAGNA3** en download het.
7. **Herstart Home Assistant**.

Zie de [officiële HACS documentatie](https://hacs.xyz/docs/faq/custom_repositories/) voor meer details.

### Handmatig

1. Download of kopieer de map `custom_components/magna3` uit deze repository naar de
   map `config/custom_components/` van je Home Assistant-installatie.
2. **Herstart Home Assistant**.

## Configuratie

De configuratie verloopt volledig via de UI — geen YAML nodig.

**Instellingen → Apparaten & services → Integratie toevoegen → Grundfos MAGNA3**

De installatiewizard doorloopt een paar stappen:

1. **Naam & verbindingstype** — geef de pomp een naam, stel het Modbus
   unit-ID (slave-adres, 1–247) van de CIM-module in, en kies **TCP** of
   **Serieel**.
2. **Verbindingsgegevens**
   | Modus | Velden |
   |-------|--------|
   | TCP (CIM 500) | Host, poort (standaard `502`), scaninterval |
   | Serieel (CIM 200) | Seriële poort, baudrate, pariteit, stopbits, scaninterval |

   De CIM 200 staat standaard op **even pariteit, 1 stopbit**; ook *geen
   pariteit, 2 stopbits* wordt ondersteund als je die instelling hebt
   gewijzigd.

   > **Gebruik je een Modbus RTU-naar-TCP/IP-gateway met een CIM 200?** Kies
   > dan in de wizard **TCP** in plaats van Serieel, en wijs het IP-adres en
   > de poort van de gateway aan. De gateway regelt de RS-485/RTU-kant naar
   > de CIM 200; Home Assistant spreekt zelf alleen Modbus TCP met de
   > gateway. Zo kun je de pomp ook overal in je netwerk plaatsen in plaats
   > van een directe seriële/USB-verbinding met de HA-host nodig te hebben.
3. **Meldingen** — schakel eventueel alarm-, waarschuwings- en
   verbindingsmeldingen in en bepaal waar ze naartoe gaan (zie
   [Instellingen & meldingen](#instellingen--meldingen)).

Meerdere pompen? Voeg de integratie gewoon opnieuw toe — elke verbinding
(host+poort of seriële poort) kan maar één keer worden toegevoegd, Home
Assistant waarschuwt je als je dezelfde pomp dubbel probeert toe te voegen.

Al het bovenstaande kun je later nog wijzigen via **Configureren** op de
integratietegel (verbinding herconfigureren) of via de **Opties** van de
integratie (meldingen en scaninterval).

## Bediening

De integratie biedt een set entiteiten waarmee je de pomp daadwerkelijk
bedient:

| Entiteit | Type | Wat het doet |
|----------|------|--------------|
| **Bediening op afstand** | switch | Hoofdschakelaar: de pomp accepteert Modbus-commando's alleen zolang deze aan staat. |
| **Pomp** | switch | Zet de pomp aan/uit. |
| **Regelmodus** | select | Bepaalt hoe de pomp zichzelf regelt: constante curve, constante druk, proportionele druk, AUTOADAPT, FLOWLIMIT, en meer. |
| **Bedrijfsmodus** | select | Normaal (setpointregeling), minimaal toerental, of maximaal toerental. |
| **Setpoint** | number (schuif) | Streefwaarde voor de actieve regelmodus, 0–100 %, begrensd door het setpoint-bereik dat in de pomp zelf is ingesteld. |
| **Debietbegrenzing** | switch | Schakelt de maximale debietbegrenzing in/uit. |
| **Maximale-debietbegrenzing** | number | Het debietplafond (m³/h) dat geldt zolang de debietbegrenzing aan staat. |
| **Alarm resetten** | button | Wist het actuele alarm/de waarschuwing op de pomp. |

### Waarom "Bediening op afstand" belangrijk is

Grundfos-pompen accepteren Modbus-commando's alleen zolang **bediening op
afstand (Modbus-besturing)** op de pomp zelf actief is. Zet je de fysieke
R100-afstandsbediening om, gebruik je de lokale knoppen op de pomp, of
heeft de installateur hem in lokale modus laten staan, dan worden
schrijfpogingen vanuit Home Assistant anders stilzwijgend door de pomp
genegeerd.

Om dit voorspelbaar te maken, schakelt elke besturingsentiteit in deze
integratie **automatisch Bediening op afstand in** vóórdat er iets wordt
geschreven. Weigert de pomp om in afstandsmodus te gaan (bijvoorbeeld
omdat het bedieningspaneel vergrendeld is, of de pomp *geforceerd lokaal*
staat — zie de diagnostische sensor *Geforceerd lokaal*), dan krijg je een
duidelijke foutmelding in Home Assistant in plaats van een commando dat
stilletjes niets doet.

## Instellingen & meldingen

De meldingen zitten in **inklapbare secties** onder **Configureren → Opties** van de
integratie, zodat verbindingsfouten, alarmen en waarschuwingen elk apart in te stellen zijn.

**Algemeen**

| Instelling | Omschrijving |
|------------|--------------|
| Scaninterval | Hoe vaak de pomp wordt uitgelezen (standaard 30 s). |
| Permanente meldingen | Toon meldingen ook in het Home Assistant-meldingenpaneel. |

**Verbindingsfouten**, **Alarmen** en **Waarschuwingen** hebben elk een eigen sectie met:

| Instelling | Omschrijving |
|------------|--------------|
| Melden bij … | Meldingen voor deze categorie inschakelen. |
| Melden bij herstel | Meld ook zodra deze categorie is opgelost (het alarm/de waarschuwing is weg, of de verbinding is hersteld). |
| Mobiele notify-services | Welke `notify.*`-services (bijv. `mobile_app_*` van je telefoon) **deze** categorie ontvangen — zo kan bijv. een filterwaarschuwing wél je partner bereiken terwijl een verbindingsfout dat niet doet. |
| Meldingsonderwerp | De titel voor de meldingen van deze categorie — handig om meerdere pompen uit elkaar te houden. |
| Vertraging (seconden) | Hoe lang de situatie moet aanhouden voordat er gemeld wordt, zodat een code of hapering die meteen verdwijnt geen melding geeft. |
| Stille uren | Houd optioneel **mobiele** meldingen vast gedurende een ingestelde periode (bijv. 's nachts) en lever ze af zodra die voorbij is — elke categorie heeft een eigen venster. Permanente meldingen worden nooit vastgehouden. |

Verbindingsfoutmeldingen gaan af zowel wanneer de Modbus-verbinding wegvalt áls wanneer de
CIM-module niets meer van de pomp hoort (GENIbus-link weg).

## Sensoren

Alle numerieke procesgegevens worden als sensor aangeboden, correct
geschaald en met de juiste eenheid, zodat ze direct werken met het
Energiedashboard en de langetermijnstatistieken.

**Standaard ingeschakeld:** Opvoerhoogte, Debiet, Relatief vermogen,
Toerental, Actueel setpoint, Motorstroom, Mediumtemperatuur,
Elektronicatemperatuur, Vermogen, Energieverbruik, Bedrijfsuren, Aantal
starts.

**Diagnostisch / standaard uitgeschakeld** (per entiteit in te schakelen
indien gewenst): Frequentie, DC-tussenkringspanning, Procesterugkoppeling,
Externe druk 1, Specifiek energieverbruik, Externe temperatuur 2,
Verschildruk, Ingeschakelde tijd, Warmte-energie, Warmtevermogen, Verpompt
volume.

Daarnaast een set binaire sensoren voor de pompstatus: **In bedrijf**,
**Storing**, **Waarschuwing**, **Op vermogensgrens**, **Op maximaal/
minimaal toerental**, **Geforceerd lokaal**, en twee sensoren voor de
verbindingsgezondheid (zie hieronder).

Voor de volledige registerniveau-mapping (handig bij het debuggen of
uitbreiden van de integratie), zie
[Technische referentie](#technische-referentie).

## Bewaking van de verbinding

Er kunnen twee verschillende dingen misgaan, en deze integratie maakt
daarin onderscheid:

1. **CIM-verbinding** *(binary_sensor)* — kan Home Assistant überhaupt met
   de CIM-module praten via Modbus?
2. **Pompcommunicatie** *(binary_sensor)* — hoort de CIM-module zelf nog
   iets van de pomp via zijn interne GENIbus-verbinding?

Die tweede sensor bestaat omdat de CIM-module zijn **laatst bekende
waarden** over Modbus blijft serveren, ook wanneer de interne verbinding
met de pomp is weggevallen — de data lijkt dan nog geldig, maar is
bevroren. De integratie detecteert dit door de GENIbus-ontvangsttteller van
de pomp in de gaten te houden; staat die 3 polls op rij stil, dan gaat
*Pompcommunicatie* naar niet-verbonden en meldt de sensor
*Verbindingsstatus* `No pump data`.

## Problemen oplossen

- **Setpoint schrijven / regelmodus wisselen doet niets** — controleer of
  *Bediening op afstand* aan staat en *Geforceerd lokaal* uit. Staat het
  bedieningspaneel van de pomp vergrendeld op lokale bediening, dan worden
  Modbus-commando's bewust genegeerd.
- **Een sensor toont "niet beschikbaar"** — de pomp rapporteert `0xFFFF`
  voor registers die niet ondersteund worden op jouw specifieke model/
  configuratie; de integratie behandelt dit als "geen waarde" in plaats van
  een onzinnige meting.
- **"Pompcommunicatie" staat uit, "CIM-verbinding" staat aan** — de
  Modbus-verbinding met de CIM-module werkt, maar de CIM heeft zijn interne
  verbinding met de pomp verloren. Controleer de voeding van de pomp en de
  kabel tussen pomp en CIM-module.
- **Seriële verbinding (CIM 200) lukt niet** — controleer of baudrate en
  pariteit/stopbits overeenkomen met de instelling van de CIM 200
  (fabrieksinstelling: 19200 baud, even pariteit, 1 stopbit).
- **Alarmcodes** — de sensor **Alarm** / **Waarschuwing** toont naast de
  ruwe code ook een leesbare omschrijving (bijv. `Dry running`,
  `Overtemperature`); `0` betekent altijd "OK".

## Technische referentie

<details>
<summary>Registermapping, bitindelingen en schaaldetails (voor ontwikkelaars)</summary>

Deze sectie documenteert de onderliggende Modbus-registermapping, volgens
de Grundfos-documentatienummering (1-based) uit het functionele profiel
*"Modbus for Grundfos pumps"*. Documentatieregister `X` staat op de bus op
adres `X − 1`; de hub trekt hier intern automatisch 1 vanaf bij elke
lees-/schrijfactie. Alle registers zijn *holding registers* (function code
03 lezen / 06 schrijven); `0xFFFF` betekent *register niet beschikbaar* en
wordt als `None` behandeld. 32-bits waarden zijn verdeeld over twee
opeenvolgende registers (HI, HI+1), samengesteld als `(HI << 16) | LO`.

Voor efficiëntie worden registers in aaneengesloten blokken gelezen. Een
blok kan adressen bevatten die niet tot een entiteit worden verwerkt — dat
is leesefficiëntie, geen ontbrekende functie.

| Blok | Registers | Frequentie | Daadwerkelijk gebruikt |
|------|-----------|-----------|------------------------|
| Statisch | `00023–00024` | eenmalig bij opstart | `00023–00024` (CIM-versie, Modbus-adres) |
| Statisch | `00030–00036` | eenmalig bij opstart | `00030–00032`, `00034–00035` (producttype, softwareversie) |
| Statisch | `00212–00216` | eenmalig bij opstart | `00212`, `00215–00216` (nominale frequentie, setpoint-bereik) |
| Cyclisch | `00021–00028` | elke poll | alleen `00027–00028` (GENIbus RX-teller) |
| Cyclisch | `00101–00108` | elke poll | `00101–00104`, `00106` (besturingsblok) |
| Cyclisch | `00201–00208` | elke poll | `00201–00206` (status, modes, alarm/waarschuwing) |
| Cyclisch | `00301–00358` | elke poll | zie meetregistertabel hieronder |

#### Besturingsregisters (schrijfbaar)

| Register | Naam | Entiteit | Schaal / betekenis |
|----------|------|----------|--------------------|
| `00101` | ControlBits | switches + knop *Alarm resetten* | bitveld, zie hieronder |
| `00102` | ControlMode | select *Regelmodus* | enum, `CONTROL_MODES` |
| `00103` | OperationMode | select *Bedrijfsmodus* | enum, `OPERATION_MODES` |
| `00104` | Setpoint | number *Setpoint* | 0,01 % (0–100 % → 0–10000) |
| `00106` | MaxFlowLimit | number *Maximale-debietbegrenzing* | 0,01 m³/h bij schrijven |

**ControlBits (`00101`)** — read-modify-write bitveld, elke bit wordt
afzonderlijk gezet/gewist:

| Bit | Naam | Entiteit |
|-----|------|----------|
| 0 | RemoteAccess | switch *Bediening op afstand* |
| 1 | OnOff | switch *Pomp* |
| 2 | ResetAlarm | knop *Alarm resetten* (stijgende flank) |
| 5 | EnableMaxFlowLimit | switch *Debietbegrenzing* |

#### Statusregisters (alleen-lezen)

| Register | Naam | Entiteit | Betekenis |
|----------|------|----------|-----------|
| `00201` | StatusBits | zie bit-tabel hieronder | bitveld |
| `00202` | ProcessFeedback | sensor *Procesterugkoppeling* (diagnostisch) | procesfeedback in %, schaal 0,01 |
| `00203` | ActualControlMode | select *Regelmodus* (terugleeswaarde) | daadwerkelijk actieve regelmodus |
| `00204` | ActualOperationMode | select *Bedrijfsmodus* (terugleeswaarde) | daadwerkelijk actieve bedrijfsmodus |
| `00205` | AlarmCode | sensor *Alarm* | actuele alarmcode (`0` = OK) |
| `00206` | WarningCode | sensor *Waarschuwing* | actuele waarschuwingscode |

**StatusBits (`00201`)**:

| Bit | Naam | Entiteit | Betekenis |
|-----|------|----------|-----------|
| 2 | MaxFlowLimitEnabled | switch *Debietbegrenzing* (status) | max. debietbegrenzing actief |
| 5 | AtMaxPower | binary_sensor *Op vermogensgrens* (standaard uit) | pomp draait op maximaal vermogen |
| 6 | Rotation | binary_sensor *In bedrijf* | pomp draait |
| 8 | AccessMode | switch *Bediening op afstand* (status) | Modbus-besturing actief |
| 9 | OnOff | switch *Pomp* (status) | pomp aan/uit-status |
| 10 | Fault | binary_sensor *Storing* | alarm actief |
| 11 | Warning | binary_sensor *Waarschuwing* | waarschuwing actief |
| 12 | ForcedToLocal | binary_sensor *Geforceerd lokaal* (standaard uit) | pomp lokaal geforceerd |
| 13 | AtMaxSpeed | binary_sensor *Op maximaal toerental* (standaard uit) | pomp draait op maximaal toerental |
| 15 | AtMinSpeed | binary_sensor *Op minimaal toerental* (standaard uit) | pomp draait op minimaal toerental |

#### Meetregisters (alleen-lezen, `00301`–`00358`)

Temperaturen worden geleverd als kelvin × 100 en omgerekend naar °C
(`offset = −273,15`).

| Register | Grootheid | Eenheid | Schaal | Entiteit |
|----------|-----------|---------|--------|----------|
| `00301` | Opvoerhoogte | bar | 0,001 | sensor *Opvoerhoogte* |
| `00302` | Debiet | m³/h | 0,1 | sensor *Debiet* |
| `00303` | Relatieve prestatie | % | 0,01 | sensor *Relatief vermogen* |
| `00304` | Toerental | rpm | 1 | sensor *Toerental* |
| `00305` | Frequentie | Hz | 0,1 | sensor *Frequentie* (standaard uit) |
| `00308` | Actueel setpoint | % | 0,01 | sensor *Actueel setpoint* |
| `00309` | Motorstroom | A | 0,1 | sensor *Motorstroom* (diagnostisch) |
| `00310` | DC-tussenkringspanning | V | 0,1 | sensor *DC-tussenkringspanning* (standaard uit) |
| `00312`+`00313` | Vermogen | W | 1 | sensor *Vermogen* (32-bits) |
| `00316` | Externe druk 1 | bar | 0,001 | sensor *Externe druk 1* (standaard uit) |
| `00321` | Elektronicatemperatuur | °C | 0,01 (K) | sensor *Elektronicatemperatuur* (diagnostisch) |
| `00322` | Mediumtemperatuur | °C | 0,01 (K) | sensor *Mediumtemperatuur* |
| `00326` | Specifiek energieverbruik | Wh/m³ | 1 | sensor *Specifiek energieverbruik* (standaard uit) |
| `00327`+`00328` | Bedrijfsuren | h | 1 | sensor *Bedrijfsuren* (32-bits, diagnostisch) |
| `00329`+`00330` | Ingeschakelde uren | h | 1 | sensor *Ingeschakelde tijd* (32-bits, standaard uit) |
| `00332`+`00333` | Energieverbruik | kWh | 1 | sensor *Energieverbruik* (32-bits, totaal) |
| `00334`+`00335` | Aantal starts | – | 1 | sensor *Aantal starts* (32-bits, diagnostisch) |
| `00337` | Externe temperatuur 2 | °C | 0,01 (K) | sensor *Externe temperatuur 2* (standaard uit) |
| `00338` | Actueel gebruikerssetpoint | % | 0,01 | number *Setpoint* (terugleeswaarde) |
| `00339` | Drukverschil | bar | 0,001 | sensor *Verschildruk* (standaard uit) |
| `00345` | Actuele max. debietbegrenzing | m³/h | 0,01 | number *Maximale-debietbegrenzing* (terugleeswaarde) |
| `00352`+`00353` | Warmte-energie | kWh | 1 | sensor *Warmte-energie* (32-bits, standaard uit) |
| `00354`+`00355` | Warmtevermogen | W | 1 | sensor *Warmtevermogen* (32-bits, standaard uit) |
| `00357`+`00358` | Verpompt volume | m³ | 0,01 | sensor *Verpompt volume* (32-bits, standaard uit) |

> **Schaal debietbegrenzing:** zowel het schrijfregister `00106` als het
> terugleesregister `00345` gebruiken schaal 0,01 m³/h (`number.py`).

#### Statische identificatie- en configuratieregisters

Eenmalig gelezen bij opstart/herladen (`_read_static_data`); voeden de
apparaatinformatie en de grenzen van de schuif *Setpoint*, en hebben geen
eigen entiteit.

| Register | Betekenis | Verwerking |
|----------|-----------|-----------|
| `00023` | CIM-versienummer | ruwe waarde |
| `00024` | Actueel Modbus-adres | ruwe waarde |
| `00030` | Unit family | ruwe waarde |
| `00031` | Unit type | ruwe waarde |
| `00032` | Unit version | ruwe waarde |
| `00034`+`00035` | Product-softwareversie | BCD, geformatteerd als `x.y.z` |
| `00212` | Nominale frequentie | schaal 0,1 Hz |
| `00215` | Setpoint-bereik minimum | % (schaal 0,01) — begrenst number *Setpoint* |
| `00216` | Setpoint-bereik maximum | % (schaal 0,01) — begrenst number *Setpoint* |

#### Afgeleide entiteiten (geen eigen register)

| Entiteit | Bron |
|----------|------|
| binary_sensor *CIM-verbinding* | Modbus-verbinding HA ↔ CIM-module (`connection_status == OK`) |
| sensor *Verbindingsstatus* | `OK` / `Partial` / `Failed` / `No pump data` (diagnostisch) |
| binary_sensor *Pompcommunicatie* | GENIbus-verbinding CIM ↔ pomp, afgeleid van RX-teller `00027`+`00028` |

#### Bronbestanden

| Bestand | Inhoud |
|---------|--------|
| [`const.py`](const.py) | registernummers, leesblokken, schaal- en enum-definities |
| [`hub.py`](hub.py) | Modbus-communicatie, poll-coördinator, `X−1`-adressering |
| [`sensor.py`](sensor.py) / [`binary_sensor.py`](binary_sensor.py) | meet- en statussensoren |
| [`number.py`](number.py) | setpoint en maximale-debietbegrenzing (schrijven) |
| [`select.py`](select.py) | regelmodus en bedrijfsmodus (schrijven) |
| [`switch.py`](switch.py) | bediening op afstand, pomp aan/uit, debietbegrenzing (ControlBits) |
| [`button.py`](button.py) | alarm resetten (ControlBits bit 2) |

</details>

## Bijdragen

Issues en pull requests zijn welkom op
<https://github.com/remmob/magna3>. Meld je een bug, vermeld dan je
CIM-moduletype (200/500), verbindingsmodus, en de relevante regels uit het
Home Assistant-log.
