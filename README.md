# ha-losungen

Home-Assistant-Integration (HACS) für die **Losungen der Herrnhuter Brüdergemeine**
([losungen.de](https://www.losungen.de)). Sie stellt vier Sensoren bereit:

| Sensor | Inhalt | State |
|---|---|---|
| `sensor.losungen_tageslosung` | Text der Tageslosung | Losungstext |
| `sensor.losungen_tageslosung_bibelstelle` | Versangabe der Tageslosung | z. B. `Jesaja 55,10-11` |
| `sensor.losungen_lehrtext` | Text des Lehrtexts | Lehrtext |
| `sensor.losungen_lehrtext_bibelstelle` | Versangabe des Lehrtexts | z. B. `Lukas 8,15` |

(Die Entity-IDs ergeben sich aus Gerätename + Sensorname und können in HA umbenannt werden.)

Alle vier Sensoren tragen zusätzlich die Attribute `datum`, `wochentag`, `sonntag`
(liturgischer Sonntag, falls vorhanden), `losungstext`, `losungsvers`, `lehrtext` und
`lehrtextvers` — damit steht an jedem Sensor der komplette Tagesdatensatz zur Verfügung.
Die beiden Text-Sensoren haben außerdem das Attribut `text_markdown` (der Text mit
`*…*`/`**…**` statt der originalen `/…/`- und `#…#`-Markupzeichen, direkt für
Markdown-Cards nutzbar).

## Installation

**Über HACS:** Dieses Repo (`mattfromeurope/ha-losungen`) in HACS als benutzerdefiniertes
Repository (Kategorie *Integration*) hinzufügen, dann „Losungen" installieren und neu starten.
Danach unter *Einstellungen → Geräte & Dienste → Hinzufügen → „Losungen"* einrichten.

**Manuell:** `custom_components/losungen/` nach `config/custom_components/losungen/` kopieren,
Home Assistant neu starten, Integration über die UI hinzufügen.

## Datenquelle

Die Integration lädt einmal pro Jahrgang die offizielle XML-Datei der Evangelischen
Brüder-Unität von
`https://www.losungen.de/fileadmin/media-losungen/download/Losung_<Jahr>_XML.zip`
und liest daraus den Eintrag des aktuellen Tages (lokale Zeit). Solange sich das Datum
nicht ändert, wird ohne HTTP-Request aus dem Cache gelesen (Poll-Intervall: 30 Minuten).

Die „Free"-XML-Dateien enthalten Losungsvers (AT) und Lehrtext (NT) mit Bibelstellen und
sind von der Brüder-Unität ausdrücklich zur Internet-Veröffentlichung freigegeben —
mit der Auflage, beide Verse immer gemeinsam anzuzeigen (siehe Nutzungsbedingungen auf
losungen.de). Das ist mit diesen vier Sensoren erfüllt, solange Losung und Lehrtext
zusammen dargestellt werden.

## Markdown-Card-Beispiele

```yaml
type: markdown
content: |-
  # Losung — {{ state_attr('sensor.losungen_tageslosung', 'wochentag') }}, {{ state_attr('sensor.losungen_tageslosung', 'datum') }}
  > {{ states('sensor.losungen_tageslosung') }}
  > — {{ states('sensor.losungen_tageslosung_bibelstelle') }}

  > {{ states('sensor.losungen_lehrtext') }}
  > — {{ states('sensor.losungen_lehrtext_bibelstelle') }}
```

Mit Markdown-Formatierung (Einleitung kursiv, Hervorhebung fett):

```yaml
type: markdown
content: |-
  > {{ state_attr('sensor.losungen_tageslosung', 'text_markdown') }}
  > — {{ states('sensor.losungen_tageslosung_bibelstelle') }}
```

**Hinweis zum State-Limit:** Home Assistant begrenzt Sensor-States auf 255 Zeichen.
Längere Lehrtexte werden im State daher gekürzt; der vollständige Text steht immer im
Attribut (z. B. `state_attr('sensor.losungen_lehrtext', 'lehrtext')`):

```yaml
type: markdown
content: |-
  > {{ state_attr('sensor.losungen_lehrtext', 'lehrtext') }}
```

## Entwicklung

```bash
python scripts/validate_integration.py
python -m pytest tests/test_parse.py -q                 # ohne Home Assistant
python -m pytest tests -q                               # alle Tests (pip install homeassistant nötig)
```

Siehe [CONTRIBUTING.md](CONTRIBUTING.md) für den Branch-/PR-Workflow.
