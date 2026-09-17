# Anker SOLIX V1 Smart EV Charger — Home Assistant Integration

[![hacs][hacs-badge]][hacs-url]
[![release][release-badge]][release-url]
[![license][license-badge]](LICENSE)

Bindet den **Anker SOLIX V1 Smart EV Charger** per Modbus TCP in Home Assistant
ein — vollständig lokal, ohne Cloud und ohne Anker-Konto. Die Wallbox wird als
Gerät mit Messwerten und Steuerelementen angelegt.

<img src="image.webp" alt="Anker SOLIX V1 Smart EV Charger" width="280">

> **Status:** funktionsfähig, aber jung. Verifiziert gegen ein Gerät der Variante
> **A5191** (einphasig, 32 A, Firmware 1.0.6.1). Rückmeldungen zu anderen
> Varianten sind willkommen — siehe [Mitwirken](#mitwirken).

---

## Funktionsumfang

**Messwerte** — Ladeleistung, Energie und Dauer der laufenden Ladung, Spannungen
und Ströme je Phase, Wirk-, Blind- und Scheinleistung, Ladestatus, CP-Signal,
Relais-Temperaturen.

**Steuerung** — Laden starten und stoppen, Ladestrom zwischen 6 und 32 A
begrenzen, Boost-Modus, Phasenwahl, Modbus-Timeout.

Damit lässt sich die Wallbox in Automationen einbinden: Überschussladen nach
PV-Ertrag, dynamische Begrenzung nach Hausanschluss, Laden zu Niedrigtarifzeiten.

## Voraussetzungen

* Home Assistant 2024.12 oder neuer
* Anker SOLIX V1 Smart EV Charger im selben Netzwerk (LAN oder WLAN)
* In der Anker-App aktiviertes Modbus TCP

### Modbus TCP aktivieren

1. Anker-App öffnen, **V1 Smart EV Charger** wählen, **Einstellungen** antippen
2. **Integrationen** öffnen
3. **Modbus TCP** einschalten

Die App zeigt dort IP-Adresse und Port an. Eine feste IP-Adresse über die
DHCP-Reservierung des Routers wird empfohlen.

> **Nur zwei Clients gleichzeitig.** Die Wallbox akzeptiert höchstens zwei
> parallele Modbus-Verbindungen. Läuft bereits ein Energiemanager oder ein
> Debug-Tool darauf, bekommt die Integration unter Umständen keine Verbindung.
> Sie hält deshalb genau eine dauerhafte Verbindung offen, statt für jede
> Abfrage neu zu verbinden.

## Installation

### HACS (empfohlen)

1. HACS → **Integrationen** → ⋮ → **Benutzerdefiniertes Repository hinzufügen**
2. URL dieses Repositories eintragen, Kategorie **Integration**
3. *Anker SOLIX V1 Smart EV Charger* suchen und installieren
4. Home Assistant neu starten

### Manuell

Den Ordner `custom_components/anker_solix_v1/` nach `<config>/custom_components/`
kopieren und Home Assistant neu starten.

### Einrichten

**Einstellungen → Geräte & Dienste → Integration hinzufügen** → *Anker SOLIX V1*.
IP-Adresse eintragen; Port (502), Geräte-ID (1) und Abfrageintervall (5 s) sind
vorbelegt. Die Integration prüft die Verbindung und legt das Gerät unter seiner
Seriennummer an.

## Entitäten

### Messwerte

| Entität | Einheit | Register |
|---|---|---|
| Ladestatus | — | 20097 |
| Ladezustand (Klartext) | — | 20097 |
| Ladeleistung | W | 20068 |
| Energie aktuelle Ladung | kWh | 20084 |
| Dauer aktuelle Ladung | s | 20082 |
| Spannung L1-N / L2-N / L3-N | V | 20053–20055 |
| Spannung L1-L2 / L2-L3 / L3-L1 | V | 20056–20058 |
| Strom L1 / L2 / L3 | A | 20059–20061 |
| Wirkleistung gesamt und je Phase | W | 20062–20069 |
| Blindleistung je Phase | var | 20070–20075 |
| Scheinleistung je Phase | VA | 20076–20081 |
| Phasenmodus, Lademodus | — | 20087, 20088 |

### Status

| Entität | Typ |
|---|---|
| Lädt | Binärsensor |
| Fahrzeug angeschlossen | Binärsensor |
| Alarm | Binärsensor |
| Lastmanagement, Solarüberschussladen, PWM | Binärsensor |

### Steuerung

| Entität | Typ | Register |
|---|---|---|
| Laden | Switch | 21000 |
| Laden starten / stoppen | Buttons | 21000 |
| Ladestrom-Begrenzung (6–32 A) | Number | 21001 |
| Boost-Modus | Switch | 21002 |
| Modbus-Timeout | Number | 21003 |
| Phasenwahl | Select | 21005 |

### Diagnose

CP-Signalstatus, CP-Spannung, Relais-Temperaturen, LED-Helligkeit,
OCPP-/MQTT-Verbindungsstatus, Nennleistung, maximaler Ausgangsstrom.

Diagnosewerte und Entitäten für nicht genutzte Phasen sind standardmäßig
deaktiviert und lassen sich in der Entitätsliste des Geräts einschalten.

## Betriebshinweise

**Abfrageintervall.** Standard 5 s, in den Optionen der Integration änderbar
(2–300 s). Für reines Monitoring genügen 30 s; für Überschussladen sind 5 s
sinnvoll.

**Modbus-Timeout.** Register 21003 bestimmt, wie lange die Wallbox ohne
Modbus-Verkehr wartet, bevor sie auf ihre eigene Steuerstrategie zurückfällt.
Der Wert muss deutlich über dem Abfrageintervall liegen; Werkseinstellung 120 s.

**Ladestrom unter 6 A.** Die Wallbox pausiert unterhalb von 6 A. Die
Ladestrom-Begrenzung bietet deshalb keine kleineren Werte an.

**Energiedashboard.** *Energie aktuelle Ladung* wird von der Wallbox zu Beginn
jeder Ladung zurückgesetzt und ist deshalb als `TOTAL` deklariert, nicht als
`TOTAL_INCREASING` — andernfalls würde Home Assistant jeden Reset als
Zählerüberlauf interpretieren.

## Anbindung an Drittanwendungen

Werkzeuge, die Home Assistant über die REST-API auslesen — etwa
[Leapmotor Mate](https://github.com/ProtossBlaster/leapmotor-mate) —, erhalten
bei einem Sensor der Geräteklasse `enum` immer den Rohwert, nie die Übersetzung:
Zustandsübersetzungen wendet allein das HA-Frontend an. *Ladestatus* liefert
dort also `charger_paused` statt „Von Wallbox pausiert".

Für diesen Fall gibt es **Ladezustand (Klartext)**. Der Sensor führt dieselbe
Registerquelle auf vier englische Begriffe zusammen und trägt keine
Geräteklasse, wird also unverändert ausgeliefert:

| Ladestatus | Ladezustand (Klartext) |
|---|---|
| Lädt | `Charging` |
| Vorbereitung, von Wallbox/Fahrzeug pausiert, abgeschlossen, reserviert | `Connected` |
| Bereit, deaktiviert | `Idle` |
| Fehler | `Error` |

Der Sensor ist standardmäßig deaktiviert und wird in der Entitätsliste des
Geräts eingeschaltet. Innerhalb von Home Assistant bleibt *Ladestatus* die
bessere Wahl — er ist übersetzt und kennt alle neun Zustände einzeln.

**Zuordnung in Leapmotor Mate** (*Einstellungen → Wallbox*):

| Rolle | Entität |
|---|---|
| Ladeleistung | *Ladeleistung* (W) |
| Energie der Ladung | *Energie aktuelle Ladung* (kWh) |
| Status | *Ladezustand (Klartext)* |
| Maximaler Ladestrom | *Ladestrom-Begrenzung* |

Mate filtert die Auswahlliste nach Stichwörtern wie `wallbox` oder `charger`
im Entitätsnamen. Enthält der Gerätename keines davon, erscheinen die Entitäten
nicht von selbst: entweder unter *Einstellungen → Wallbox* eigene Suchbegriffe
hinterlegen, den Modus *Alle anzeigen* verwenden, oder das Gerät in Home
Assistant umbenennen. Ob geladen wird, leitet Mate übrigens aus der Leistung ab
(> 50 W), nicht aus dem Status.

## Beispielautomation

Ladestrom dem PV-Überschuss nachführen:

```yaml
automation:
  - alias: Wallbox auf PV-Überschuss regeln
    triggers:
      - trigger: state
        entity_id: sensor.pv_ueberschuss
    conditions:
      - condition: state
        entity_id: binary_sensor.anker_solix_v1_vehicle_connected
        state: "on"
    actions:
      - action: number.set_value
        target:
          entity_id: number.anker_solix_v1_charging_current_limit
        data:
          value: >-
            {{ [[(states('sensor.pv_ueberschuss') | float(0) / 230)
                 | round(0), 6] | max, 32] | min }}
```

## Technische Grundlage

Die Registerkarte beruht auf dem Dokument *Anker SOLIX V1 Smart EV Charger
Modbus Protocol* V1.0.0 (30.11.2025) und wurde an einem A5191 (Firmware 1.0.6.1)
überprüft. Sieben Punkte weichen von der Dokumentation ab und sind in
[`registers.py`](custom_components/anker_solix_v1/registers.py) festgehalten:

* **Funktionscodes.** Die Dokumentation nennt keine. Tatsächlich antwortet der
  Block 20000–20100 ausschließlich auf FC4 (Input Register), der Block
  21000–21005 ausschließlich auf FC3/FC6 (Holding Register).
* **Wortreihenfolge.** 32-Bit-Werte sind Big-Endian. Belegt über die
  Nennleistung: `[0, 7400]` ergibt 7400 W, Little-Endian dagegen 484 966 400 W.
* **Einheitenspalte.** Bei 21001, 21003 und 21005 ist sie falsch, die
  Gain-Spalte dagegen richtig. 21001 = 320 entspricht den 32 A aus der App.
  Auch 20039 ist betroffen: Die Spalte nennt KVA, der Wert 32 ist der
  maximale Ausgangsstrom in Ampere.
* **Gain der Stromregister.** Bei 20059–20061 nennt die Dokumentation 100,
  richtig ist 10. Bei 1388 W an L1 und 224,0 V liest 20059 den Wert 62:
  6,2 A ergeben 1388,8 W und damit die gemeldete Leistung, 0,62 A nur 138,9 W.
* **Rücklesen von 21000.** Der Ladebefehl wird nicht gespeichert: Nach einem
  Stopp über die Integration liest 21000 dauerhaft 0, nie die geschriebene 2.
  Der *Laden*-Switch wertet deshalb den Ladestatus aus statt das Register.
* **Einheit der CP-Spannung.** Die Dokumentation nennt keine; es sind
  Millivolt. Belegt über drei CP-Zustände einer Sitzung: 11779 bei A,
  8846 bei B1 und 5826 bei C2 treffen die Sollwerte nach IEC 61851
  (12/9/6 V) auf 0,25 V genau.
* **Verbindungsstatus 20099 und 20100.** Die beiden Register nutzen
  unterschiedliche Codes und werden getrennt ausgewertet: bei OCPP (20099)
  bedeutet 1 *Verbindungsaufbau* und 2 *Verbunden*, bei MQTT (20100)
  bedeutet 1 bereits *Verbunden*. Ein gemeinsames Mapping meldete eine
  bestehende MQTT-Verbindung dauerhaft als „Verbindungsaufbau".

Das Protokolldokument selbst ist urheberrechtlich geschützt und darf nicht
weitergegeben werden; es liegt diesem Repository deshalb nicht bei. Anker stellt
es auf Anfrage bereit.

### Offene Punkte

| Punkt | Stand |
|---|---|
| Relais-1-Temperatur | Liefert konstant −55,0 °C (Sentinel); Sensor auf dem A5191 offenbar nicht bestückt |
| Alarmliste (20041–20052) | Bit-Zuordnung liegt nicht vor |

Die zwölf Alarmregister werden zu einem einzelnen *Alarm*-Binärsensor
zusammengefasst; die Rohwerte hängen als Attribute daran, sodass sich eine
Bit-Zuordnung nachrüsten lässt, sobald die Liste verfügbar ist.

## Änderungen

Alle Versionen und ihre Änderungen stehen im [Changelog](CHANGELOG.md).

## Mitwirken

Besonders hilfreich sind Rückmeldungen zu **dreiphasigen Geräten** und anderen
Modellvarianten — die Verifikation erfolgte bislang nur an einem einphasigen
A5191.

Bei einem Fehlerbericht helfen: Modellnummer, Firmware-Version, Auszug aus dem
Home-Assistant-Log und, wenn möglich, die Rohwerte der betroffenen Register.

## Haftungsausschluss

Dieses Projekt steht in keiner Verbindung zu Anker Innovations Ltd. „Anker" und
„Anker SOLIX" sind Marken ihrer jeweiligen Inhaber. Die Nutzung erfolgt auf
eigene Verantwortung: Die Integration kann Ladevorgänge starten, stoppen und den
Ladestrom verändern.

## Lizenz

[MIT](LICENSE)

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[hacs-url]: https://hacs.xyz
[release-badge]: https://img.shields.io/github/v/release/ChristophGoth/ha-anker-solix-v1-modbus?display_name=tag
[release-url]: https://github.com/ChristophGoth/ha-anker-solix-v1-modbus/releases
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg
