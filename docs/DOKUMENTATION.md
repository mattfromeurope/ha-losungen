# Entwurfs- und Entwicklungsdokumentation – `ha-losungen`

Dieses Dokument beschreibt Architektur und Abläufe der Integration
`losungen` (Home Assistant, HACS) mit verschiedenen Sichten:

1. [Systemkontext](#1-systemkontext)
2. [Modul-/Paketübersicht](#2-modul--paketübersicht)
3. [UML-Klassendiagramm](#3-uml-klassendiagramm)
4. [ER-Diagramm (Datenmodell)](#4-er-diagramm-datenmodell)
5. [UML-Sequenzdiagramme](#5-uml-sequenzdiagramme)
6. [Programmablaufpläne (PAP)](#6-programmablaufpläne-pap)
7. [Struktogramme (Nassi-Shneiderman)](#7-struktogramme-nassi-shneiderman)
8. [EPK (ereignisgesteuerte Prozesskette)](#8-epk-ereignisgesteuerte-prozesskette)
9. [UML-Zustandsdiagramm](#9-uml-zustandsdiagramm)
10. [Datenmodell der Quelle (XML)](#10-datenmodell-der-quelle-xml)
11. [Fehlerbehandlung](#11-fehlerbehandlung)

Alle Mermaid-Diagramme rendern direkt auf GitHub. Die Struktogramme sind
ASCII-Zeichnungen (Nassi-Shneiderman hat in Mermaid keine native Entsprechung).

---

## 1. Systemkontext

Die Integration sitzt zwischen Home Assistant und der offiziellen
Download-Seite der Evangelischen Brüder-Unität:

```mermaid
flowchart LR
    subgraph HA["Home Assistant"]
        UI["Benutzer / Dashboard<br/>(Markdown-Cards)"]
        CE["Config Entry<br/>'Losungen'"]
        COORD["LosungenCoordinator<br/>(Cache: Jahr → Tag)"]
        SENS["4 Sensoren<br/>losungstext / losungsvers /<br/>lehrtext / lehrtextvers"]
    end

    subgraph EXT["Extern"]
        LOS["losungen.de<br/>Losung_&lt;Jahr&gt;_XML.zip<br/>(offizielle Jahres-Datei)"]
    end

    UI -- "states() / state_attr()" --> SENS
    CE -- "runtime_data" --> COORD
    COORD -- "liefert Tagesdaten" --> SENS
    COORD -- "1× pro Jahrgang:<br/>HTTPS GET (aiohttp)" --> LOS
    LOS -- "ZIP mit Jahres-XML" --> COORD
```

**Schnittstellen:**

| Richtung | Inhalt | Protokoll |
|---|---|---|
| losungen.de → Integration | ZIP mit `Losungen Free <Jahr>.xml` | HTTPS GET, `User-Agent` gesetzt, Timeout 60 s |
| Integration → HA | 4 Sensor-States + Attribute | HA Entity Platform (`sensor.py`) |
| HA → Integration | Config Entry anlegen/entladen | Config Flow + `async_setup_entry` |

---

## 2. Modul-/Paketübersicht

```mermaid
flowchart TB
    subgraph CC["custom_components/losungen/"]
        INIT["__init__.py<br/>Einstieg: setup/unload entry"]
        CF["config_flow.py<br/>UI-Einrichtung"]
        COORD["coordinator.py<br/>DataUpdateCoordinator + Cache"]
        API["api.py<br/>HTTP-Download (aiohttp)"]
        PARSER["parser.py<br/>ZIP/XML parsen (nur stdlib)"]
        ENT["entity.py<br/>Basisklasse + Gerät"]
        SENSOR["sensor.py<br/>4 Sensoren"]
        CONST["const.py<br/>Konstanten"]
        STR["strings.json + translations/"]
        MAN["manifest.json"]
    end

    CF --> INIT
    INIT --> COORD
    COORD --> API
    API --> PARSER
    INIT --> SENSOR
    SENSOR --> ENT
    SENSOR --> COORD
    SENSOR --> PARSER
    ENT --> COORD
    SENSOR --> CONST
    COORD --> CONST
    API --> CONST
    SENSOR --> STR
```

Abhängigkeitsrichtung: `sensor.py` und `coordinator.py` sind die zentralen
Module; `parser.py` ist bewusst HA-frei (nur Standardbibliothek) und damit
allein testbar.

---

## 3. UML-Klassendiagramm

```mermaid
classDiagram
    class ConfigFlow {
        +VERSION = 1
        +async_step_user()
    }
    class LosungenConfigFlow {
        +async_step_user()
    }
    ConfigFlow <|-- LosungenConfigFlow

    class DataUpdateCoordinator {
        +data
        +last_update_success
        +update_interval
        +_async_update_data()*
    }
    class LosungenCoordinator {
        -_cache: dict[int, dict[str, LosungDay]]
        +_async_update_data()
    }
    DataUpdateCoordinator <|-- LosungenCoordinator

    class LosungenAPIError { <<Exception>> }
    class LosungenConnectionError
    class LosungenParseError
    LosungenAPIError <|-- LosungenConnectionError
    LosungenParseError <|-- LosungenAPIError

    class LosungDay { <<dataclass, frozen>>
        +date: str
        +weekday: str
        +sunday: str
        +losungstext: str
        +losungsvers: str
        +lehrtext: str
        +lehrtextvers: str
        +losungstext_raw: str
        +lehrtext_raw: str
    }

    class CoordinatorEntity {
        +coordinator
        +available
    }
    class SensorEntity
    class LosungenEntity {
        +_attr_has_entity_name = True
        +__init__(coordinator, entry)
    }
    class SensorEntityDescription
    class LosungenSensorDescription { <<dataclass>>
        +value_fn: Callable
        +markdown_fn: Callable
    }
    class LosungenSensor {
        +entity_description
        +_today
        +native_value
        +extra_state_attributes
    }
    CoordinatorEntity <|-- LosungenEntity
    SensorEntity <|-- LosungenSensor
    LosungenEntity <|-- LosungenSensor
    SensorEntityDescription <|-- LosungenSensorDescription
    LosungenSensor *-- LosungenSensorDescription : entity_description
    LosungenSensor --> LosungenCoordinator : coordinator
    LosungenCoordinator --> LosungDay : data/cache
    LosungenCoordinator ..> LosungenAPIError : wirft UpdateFailed
```

**Vererbung (Pfeil mit leerer Spitze `◁--`):** eigene Klassen erweitern die
HA-Basisklassen. **Komposition (`*--`)**: der Sensor besitzt genau eine
Beschreibung. **Assoziation (`-->`)**: Sensor und Coordinator kennen einander.

---

## 4. ER-Diagramm (Datenmodell)

```mermaid
erDiagram
    CONFIG_ENTRY ||--|| COORDINATOR : "runtime_data"
    CONFIG_ENTRY ||--o{ SENSOR_ENTITY : "erzeugt 4 Sensoren"
    COORDINATOR ||--o{ LOSUNG_DAY : "cache: Jahr -> ISO-Datum"

    CONFIG_ENTRY {
        string entry_id PK
        string unique_id "DOMAIN"
        string title "Losungen"
    }
    COORDINATOR {
        int jahr PK "Cache-Schluessel"
        dict data "ISO-Datum -> LosungDay"
        bool last_update_success
    }
    LOSUNG_DAY {
        string date PK "ISO JJJJ-MM-TT"
        string weekday "Wtag"
        string sunday "liturgischer Sonntag"
        string losungstext "bereinigt"
        string losungsvers "Bibelstelle"
        string lehrtext "bereinigt"
        string lehrtextvers "Bibelstelle"
        string losungstext_raw "mit Markup"
        string lehrtext_raw "mit Markup"
    }
    SENSOR_ENTITY {
        string unique_id PK "entry_id + key"
        string key "losungstext|losungsvers|lehrtext|lehrtextvers"
        string state "Wert, max 255 Zeichen"
        json attributes "vollstaendiger Tagesdatensatz"
    }
```

**Kardinalitäten:** Ein Config Entry besitzt genau einen Coordinator
(`||--||`) und vier Sensoren (`||--o{`). Der Coordinator hält pro Jahr ein
dict von `LOSUNG_DAY`-Einträgen (`||--o{`).

---

## 5. UML-Sequenzdiagramme

### 5.1 Einrichtung über die UI (Config Flow + Setup)

```mermaid
sequenceDiagram
    autonumber
    actor U as Benutzer
    participant HA as Home Assistant
    participant CF as LosungenConfigFlow
    participant INIT as __init__.py
    participant CO as LosungenCoordinator
    participant API as api.py
    participant P as parser.py
    participant S as sensor.py

    U->>HA: "Losungen" hinzufügen
    HA->>CF: async_step_user()
    CF->>CF: unique_id = DOMAIN setzen
    alt schon konfiguriert
        CF-->>HA: abort "already_configured"
    else
        CF-->>HA: create_entry(title="Losungen")
    end
    HA->>INIT: async_setup_entry(entry)
    INIT->>CO: LosungenCoordinator(hass)
    INIT->>CO: async_config_entry_first_refresh()
    CO->>API: async_fetch_year(hass, 2026)
    API->>API: GET Losung_2026_XML.zip (aiohttp, Timeout 60s)
    API->>P: parse_losungen_zip(bytes) im Executor-Thread
    P-->>API: dict {ISO-Datum: LosungDay}
    API-->>CO: data
    CO->>CO: _cache = {2026: data}
    CO-->>INIT: data (heute enthalten?)
    INIT->>INIT: entry.runtime_data = coordinator
    INIT->>S: async_forward_entry_setups(SENSOR)
    S->>S: 4x LosungenSensor anlegen (unique_id = entry_id_key)
    S-->>HA: async_add_entities(...)
    HA-->>U: Gerät "Losungen" mit 4 Sensoren sichtbar
```

### 5.2 Poll-Update innerhalb desselben Tages (Cache-Treffer)

```mermaid
sequenceDiagram
    autonumber
    participant HA as Home Assistant (Timer)
    participant CO as LosungenCoordinator
    participant S as Sensoren

    HA->>CO: _async_update_data() nach 30 min
    CO->>CO: heute in _cache[2026]? ja
    CO-->>HA: gecachte Daten (KEIN HTTP-Request)
    HA->>S: Entities aktualisieren (last_update_success)
    S-->>HA: native_value / Attribute neu auswerten
```

### 5.3 Tageswechsel (Mitternacht) / erstes Laden nach Start

```mermaid
sequenceDiagram
    autonumber
    participant HA as Home Assistant
    participant CO as LosungenCoordinator
    participant API as api.py
    participant P as parser.py

    HA->>CO: _async_update_data()
    CO->>CO: heute in _cache? nein (neuer Tag / leerer Cache)
    CO->>API: async_fetch_year(hass, neues Jahr)
    API->>API: HTTPS GET Jahres-ZIP
    alt Download/Parsen OK
        API->>P: parse_losungen_zip(bytes)
        P-->>API: dict {ISO-Datum: LosungDay}
        API-->>CO: data
        CO->>CO: _cache = {jahr: data}
        CO-->>HA: data
    else Fehler (Netzwerk/404/bad ZIP)
        API-->>CO: LosungenConnectionError / LosungenParseError
        CO-->>HA: UpdateFailed -> Entities "unavailable", Retry beim nächsten Poll
    end
```

---

## 6. Programmablaufpläne (PAP)

PAP-Symbole in Mermaid: `([Start/Ende])` = Terminal, `[...]` = Verarbeitung,
`{...}` = Verzweigung, `[/.../]` = Ein-/Ausgabe.

### 6.1 `async_setup_entry` (Start der Integration)

```mermaid
flowchart TD
    A(["Start: async_setup_entry"]) --> B["Coordinator erzeugen"]
    B --> C["async_config_entry_first_refresh"]
    C --> D{"erstes Update erfolgreich?"}
    D -- "nein (UpdateFailed)" --> E(["Ende: HA wirft ConfigEntryNotReady,<br/>automatischer Retry später"])
    D -- ja --> F["entry.runtime_data = coordinator"]
    F --> G["Plattform SENSOR laden<br/>(async_forward_entry_setups)"]
    G --> H(["Ende: True – 4 Sensoren registriert"])
```

### 6.2 `LosungenCoordinator._async_update_data` ( Kern des Polls)

```mermaid
flowchart TD
    A(["Start: Poll alle 30 min"]) --> B["today = lokales Datum (ISO)<br/>year = today[:4]"]
    B --> C{"heute in _cache[year]?"}
    C -- ja --> D[/"Cache zurückgeben – kein HTTP"/]
    D --> Z(["Ende"])
    C -- nein --> E["async_fetch_year(hass, year)"]
    E --> F{"Download + Parsen OK?"}
    F -- "nein: LosungenAPIError" --> G["UpdateFailed werfen<br/>(Entities unavailable, Retry später)"]
    G --> Z
    F -- ja --> H{"heute in data enthalten?"}
    H -- nein --> I["UpdateFailed werfen"]
    I --> Z
    H -- ja --> J["_cache = {year: data}"]
    J --> K[/"data zurückgeben"/]
    K --> Z
```

### 6.3 `async_fetch_year` (Netzwerk + Parsen)

```mermaid
flowchart TD
    A(["Start: async_fetch_year(year)"]) --> B["url = BASE_URL.format(year)"]
    B --> C[/"aiohttp GET mit User-Agent, Timeout 60 s"/]
    C --> D{"HTTP-Status"}
    D -- 404 --> E["LosungenConnectionError werfen"]
    D -- "sonstiger Fehler" --> F["raise_for_status / ClientError fangen"]
    F --> E
    D -- 200 --> G[/"Body als Bytes lesen"/]
    G --> H["parse_losungen_zip im Executor-Thread<br/>(blockierende Arbeit nicht im Eventloop)"]
    H --> I{"parse OK?"}
    I -- "nein: BadZipFile/ParseError" --> J["LosungenParseError werfen"]
    I -- ja --> K[/"dict {ISO-Datum: LosungDay} zurückgeben"/]
    K --> Z(["Ende"])
    E --> Z
    J --> Z
```

### 6.4 `parse_losungen_zip` / `parse_losungen_xml`

```mermaid
flowchart TD
    A(["Start: parse_losungen_zip"]) --> B["zipfile.ZipFile(BytesIO(bytes))"]
    B --> C{"erste .xml in namelist?"}
    C -- nein --> D["LosungenParseError: ZIP ohne XML"]
    C -- ja --> E[/"zf.read(xml-name)"/]
    E --> F["parse_losungen_xml"]
    F --> G["ET.fromstring -> root"]
    G --> H{"ParseError?"}
    H -- ja --> I["LosungenParseError: ungültiges XML"]
    H -- nein --> J["for node in root.iter('Losungen')"]
    J --> K["date = normalize_date(<Datum>)"]
    K --> L{"date leer?"}
    L -- ja --> J
    L -- nein --> M["LosungDay bauen:<br/>Texte roh + clean_text(),<br/>Verse/Wtag/Sonntag ueber _text()"]
    M --> N["days[date] = LosungDay"]
    N --> J
    J --> O{"leere Ergebnismenge?"}
    O -- ja --> P["LosungenParseError: keine Einträge"]
    O -- nein --> Q[/"days zurückgeben"/]
    Q --> Z(["Ende"])
    D --> Z
    I --> Z
    P --> Z
```

### 6.5 `LosungenSensor.native_value` / `extra_state_attributes`

```mermaid
flowchart TD
    A(["Start: HA liest Entity-State"]) --> B{"coordinator.data vorhanden?"}
    B -- nein --> C["return None -> State 'unknown'"]
    B -- ja --> D["day = data.get(heute ISO)"]
    D --> E{"day = None?"}
    E -- ja --> C
    E -- nein --> F["value = value_fn(day)<br/>(z. B. day.lehrtext)"]
    F --> G{"len(value) > 255?"}
    G -- ja --> H["auf 254 Zeichen kürzen + '…'"]
    G -- nein --> I["value unverändert"]
    H --> J[/"State = value"/]
    I --> J
    J --> K["Attribute: datum, wochentag, sonntag,<br/>alle 4 Texte/Verse ungekürzt,<br/>bei Text-Sensoren: text_markdown"]
    K --> Z(["Ende"])
```

---

## 7. Struktogramme (Nassi-Shneiderman)

ASCII-Struktogramme der drei zentralen Funktionen. Rechteck = Anweisung,
umrandeter Bereich = Schleife, Dreieck/Ecke = Verzweigung.

### 7.1 `_async_update_data`

```
+----------------------------------------------------------+
| _async_update_data()                                     |
+----------------------------------------------------------+
| today = dt_util.now().date().isoformat()                 |
| year  = int(today[:4])                                   |
| cached = self._cache.get(year, {})                       |
+----------------------------------------------------------+
| IF today in cached:                                      |
|   +----------------------------------------------------+ |
|   | return cached            # Cache-Treffer, kein HTTP| |
|   +----------------------------------------------------+ |
+----------------------------------------------------------+
| try:                                                     |
|   data = await async_fetch_year(hass, year)              |
| except LosungenAPIError as err:                          |
|   +----------------------------------------------------+ |
|   | raise UpdateFailed(...)  # Entities unavailable     | |
|   +----------------------------------------------------+ |
+----------------------------------------------------------+
| IF today not in data:                                    |
|   +----------------------------------------------------+ |
|   | raise UpdateFailed('Kein Eintrag für today')        | |
|   +----------------------------------------------------+ |
+----------------------------------------------------------+
| self._cache = {year: data}                               |
| return data                                              |
+----------------------------------------------------------+
```

### 7.2 `parse_losungen_xml`

```
+----------------------------------------------------------+
| parse_losungen_xml(xml_data)                             |
+----------------------------------------------------------+
| try: root = ET.fromstring(xml_data)                      |
| except ParseError: raise LosungenParseError              |
+----------------------------------------------------------+
| days = {}                                                |
+----------------------------------------------------------+
| FOR node IN root.iter("Losungen"):                       |
|   +----------------------------------------------------+ |
|   | date = normalize_date(_text(node.find("Datum")))   | |
|   | IF date == "": continue                            | |
|   | losungstext_raw = _text(node.find("Losungstext"))  | |
|   | lehrtext_raw    = _text(node.find("Lehrtext"))     | |
|   | days[date] = LosungDay(date, weekday, sunday,      | |
|   |   clean_text(losungstext_raw), Losungsvers,        | |
|   |   clean_text(lehrtext_raw), Lehrtextvers, raw...)  | |
|   +----------------------------------------------------+ |
+----------------------------------------------------------+
| IF days == {}: raise LosungenParseError                  |
| return days                                              |
+----------------------------------------------------------+
```

### 7.3 `async_fetch_year`

```
+----------------------------------------------------------+
| async_fetch_year(hass, year)                             |
+----------------------------------------------------------+
| session = async_get_clientsession(hass)                  |
| url = BASE_URL.format(year=year)                         |
| try:                                                     |
|   +----------------------------------------------------+ |
|   | WITH asyncio.timeout(60):                          | |
|   |   response = await session.get(url, headers=...)  | |
|   |   IF status == 404: raise LosungenConnectionError  | |
|   |   response.raise_for_status()                      | |
|   |   payload = await response.read()                  | |
|   +----------------------------------------------------+ |
| except (ClientError, TimeoutError):                      |
|   +----------------------------------------------------+ |
|   | raise LosungenConnectionError from err             | |
|   +----------------------------------------------------+ |
+----------------------------------------------------------+
| return await hass.async_add_executor_job(                |
|            parse_losungen_zip, payload)  # Thread, nicht  |
|            # im Eventloop                                 |
+----------------------------------------------------------+
```

---

## 8. EPK (ereignisgesteuerte Prozesskette)

EPK-Notation: **Ereignisse** = Sechsecke `{{...}}`, **Funktionen** = abgerundete
Rechtecke `(...)`, **Konnektoren** (XOR = Entweder-Oder) = Rauten. Hier der
Poll-Zyklus der Integration als EPK:

```mermaid
flowchart LR
    E1{{"Ereignis:<br/>HA-Timer alle 30 min abgelaufen<br/>oder erster Start"}}
    E1 --> F1("Funktion:<br/>Coordinator._async_update_data")
    F1 --> X1{"XOR"}
    X1 -- "Cache-Treffer:<br/>heute schon geladen" --> E2{{"Ereignis:<br/>Daten aus Cache übernommen"}}
    X1 -- "Cache verfehlt:<br/>neuer Tag / leerer Cache" --> F2("Funktion:<br/>api.async_fetch_year:<br/>HTTP GET + ZIP/XML parsen")
    F2 --> X2{"XOR"}
    X2 -- OK --> E3{{"Ereignis:<br/>Jahrgang erfolgreich geladen<br/>und im Cache"}}
    X2 -- Fehler --> E4{{"Ereignis:<br/>Update fehlgeschlagen<br/>(Entities 'unavailable')"}}
    E2 --> F3("Funktion:<br/>HA verteilt Daten an Entities:<br/>native_value / Attribute neu lesen")
    E3 --> F3
    E4 --> F4("Funktion:<br/>Retry beim nächsten Poll<br/>(bzw. ConfigEntryNotReady beim Start)")
    F3 --> E5{{"Ereignis:<br/>Sensoren aktualisiert,<br/>Dashboard-Cards zeigen neue Werte"}}
    F4 --> E1
```

**Lesart:** Ein Ereignis stößt eine Funktion an; die Funktion endet in einem
neuen Ereignis. Der XOR-Konnektor `X2` trennt den Erfolgs- vom Fehlerpfad.

---

## 9. UML-Zustandsdiagramm

```mermaid
stateDiagram-v2
    [*] --> ConfigFlow: Benutzer fügt Integration hinzu
    ConfigFlow --> SetupInProgress: create_entry
    state SetupInProgress {
        [*] --> FirstRefresh
        FirstRefresh --> FirstRefresh: UpdateFailed (Retry)
        FirstRefresh --> Loaded: Daten OK
    }
    SetupInProgress --> Loaded: async_setup_entry erfolgreich
    Loaded --> Polling: 30-min-Timer
    state Polling {
        [*] --> UpdateOK
        UpdateOK --> UpdateOK: Cache-Treffer / erfolgreicher Poll
        UpdateOK --> UpdateFailed: Netzwerk-/Parse-Fehler
        UpdateFailed --> UpdateOK: nächster Poll erfolgreich
    }
    Loaded --> Unloaded: async_unload_entry
    Unloaded --> [*]

    state "Entity-Verfügbarkeit" as EntAvail
    UpdateOK --> EntAvail: available = true
    UpdateFailed --> EntAvail: available = false (State 'unavailable')
```

---

## 10. Datenmodell der Quelle (XML)

Die Jahres-ZIP enthält eine XML-Datei mit folgendem Aufbau:

```xml
<Losungsjahr>                      <!-- Wurzelelement (Name egal, wird ignoriert) -->
  <Losungen>                       <!-- ein Element PRO TAG -->
    <Datum>2026-11-23</Datum>      <!-- ISO oder TT.MM.JJJJ -->
    <Wtag>Montag</Wtag>
    <Sonntag>Letzter Sonntag des Kirchenjahres</Sonntag>
    <Losungstext>/Einleitung:/ Text mit #Hervorhebung#</Losungstext>
    <Losungsvers>Jesaja 55,10-11</Losungsvers>
    <Lehrtext>Text des Lehrtexts ...</Lehrtext>
    <Lehrtextvers>Lukas 8,15</Lehrtextvers>
  </Losungen>
  ...
</Losungsjahr>
```

| XML-Feld | Bedeutung | Ziel-Feld in `LosungDay` |
|---|---|---|
| `Datum` | Datum des Eintrags | `date` (normalisiert auf ISO) |
| `Wtag` | Wochentag | `weekday` |
| `Sonntag` | liturgischer Sonntag (oft leer) | `sunday` |
| `Losungstext` | Text der Tageslosung (mit `/…/`, `#…#`) | `losungstext` (clean_text) + `losungstext_raw` |
| `Losungsvers` | Bibelstelle der Losung | `losungsvers` |
| `Lehrtext` | Text des Lehrtexts | `lehrtext` + `lehrtext_raw` |
| `Lehrtextvers` | Bibelstelle des Lehrtexts | `lehrtextvers` |

---

## 11. Fehlerbehandlung

| Fehler | Wo | Reaktion |
|---|---|---|
| `LosungenConnectionError` (Netzwerk, Timeout, 404) | `api.py` | `coordinator.py` wirft `UpdateFailed` → Entities `unavailable`, Retry beim nächsten Poll (beim Start: `ConfigEntryNotReady` mit automatischem Retry) |
| `LosungenParseError` (kein ZIP / kein XML / ungültiges XML / keine Einträge) | `parser.py` | wie oben |
| Heutiger Tag fehlt in der Jahresdatei | `coordinator.py` | `UpdateFailed` |
| Text länger als 255 Zeichen | `sensor.py:_truncate` | State gekürzt mit `…`, voller Text im Attribut |
| Doppelter Config Entry | `config_flow.py` | `abort: already_configured` |
