# Anker SOLIX V1 Smart EV Charger — Home Assistant Integration

Liest den Anker SOLIX V1 Smart EV Charger per Modbus TCP aus und stellt ihn in
Home Assistant als Gerät mit Sensoren und Steuerelementen bereit. Lokal, ohne
Cloud.

## Voraussetzungen

Modbus TCP muss in der Anker-App aktiviert sein:

1. Anker-App öffnen, **V1 Smart EV Charger** wählen, **Einstellungen** antippen.
2. **Integrationen** öffnen.
3. **Modbus TCP** einschalten.

IP-Adresse und Port zeigt die App dort ebenfalls an. Die Wallbox akzeptiert
**maximal zwei gleichzeitige Modbus-Clients** — läuft parallel noch ein EMS oder
Debug-Tool, kann die Integration keine Verbindung mehr bekommen.

## Installation

### HACS

1. HACS → Integrationen → ⋮ → **Benutzerdefiniertes Repository hinzufügen**
2. URL dieses Repos eintragen, Kategorie **Integration**
3. Installieren, Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen** → *Anker SOLIX V1*

### Manuell

`custom_components/anker_solix_v1/` nach `<config>/custom_components/` kopieren
und Home Assistant neu starten.

## Entitäten

### Sensoren

| Entität | Einheit | Register |
|---|---|---|
| Ladestatus | — | 20097 |
| Ladeleistung | W | 20068 |
| Energie aktuelle Ladung | kWh | 20084 |
| Dauer aktuelle Ladung | s | 20082 |
| Spannung L1-N / L2-N / L3-N | V | 20053–20055 |
| Strom L1 / L2 / L3 | A | 20059–20061 |
| Wirk-/Blind-/Scheinleistung je Phase | W / var / VA | 20062–20081 |
| Phasenmodus, Lademodus | — | 20087, 20088 |
| CP-Signalstatus, CP-Spannung | — / V | 20092, 20091 |
| Temperatur Relais 1 / 2 | °C | 20093, 20094 |
| OCPP- / MQTT-Verbindung | — | 20099, 20100 |

Selten benötigte Sensoren (L2/L3 bei einphasigen Geräten, Diagnosewerte) sind
standardmäßig deaktiviert und lassen sich in der Entitätsliste einschalten.

### Binärsensoren

Lädt · Fahrzeug angeschlossen · Alarm · PWM aktiv · Lastmanagement ·
Solarüberschussladen

### Steuerung

| Entität | Typ | Register |
|---|---|---|
| Laden (an/aus) | Switch | 21000 |
| Laden starten / stoppen | Buttons | 21000 |
| Ladestrom-Begrenzung (6–32 A) | Number | 21001 |
| Boost-Modus | Switch | 21002 |
| Modbus-Timeout | Number | 21003 |
| Phasenwahl | Select | 21005 |

## Hinweise zum Betrieb

**Abfrageintervall.** Standard sind 5 s, einstellbar über die Optionen der
Integration. Die Verbindung bleibt dabei offen und wird nicht pro Abfrage neu
aufgebaut, damit die beiden Client-Slots der Wallbox nicht belegt werden.

**Timeout.** Register 21003 legt fest, wie lange die Wallbox ohne Modbus-Verkehr
wartet, bevor sie auf ihre eigene Steuerstrategie zurückfällt. Der Wert muss
deutlich über dem Abfrageintervall liegen.

**Ladestrom unter 6 A.** Die Wallbox pausiert laut Hersteller unterhalb von 6 A.
Die Ladestrom-Begrenzung bietet deshalb keine kleineren Werte an.

**Energiedashboard.** *Energie aktuelle Ladung* wird von der Wallbox zu Beginn
jeder Ladung zurückgesetzt und ist deshalb als `TOTAL` deklariert, nicht als
`TOTAL_INCREASING` — sonst würde Home Assistant jeden Reset als Zählerüberlauf
werten.

## Technische Grundlage

Basiert auf *Anker SOLIX V1 Smart EV Charger Modbus Protocol* V1.0.0
(30.11.2025), siehe [docs/](docs/). Drei Punkte wurden am echten Gerät
(A5191, SW 1.0.6.1) verifiziert und weichen von der Dokumentation ab:

* **Funktionscodes.** Der Block 20000–20100 antwortet ausschließlich auf FC4
  (Input Register), der Block 21000–21005 ausschließlich auf FC3/FC6 (Holding
  Register). Die Dokumentation unterscheidet nur nach RO/RW.
* **Wortreihenfolge.** 32-Bit-Werte sind Big-Endian (belegt über Nennleistung:
  `[0, 7400]` → 7400 W).
* **Einheitenspalte.** Bei 21001, 21003 und 21005 ist die Einheitenspalte der
  Dokumentation falsch; die Gain-Werte stimmen. 21001 = 320 entspricht den 32 A
  aus der App.

Zwei Werte sind noch nicht abschließend verifiziert und im Code markiert:
die Skalierung der **Relais-Temperaturen** (Dokumentation sagt Gain 1, die
Messwerte legen Gain 10 nahe) und die Einheit der **CP-Spannung**. Beides lässt
sich erst während einer echten Ladesession bestätigen.

Die **Alarmliste** (Register 20041–20052, je ein Bit pro Alarm) liegt nicht vor.
Die Register werden deshalb nur aggregiert als *Alarm*-Binärsensor ausgewertet;
die Rohwerte stehen als Attribute daran, falls die Liste später verfügbar wird.
