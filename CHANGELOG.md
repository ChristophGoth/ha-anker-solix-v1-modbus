# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier festgehalten.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.2] – 2026-09-17

### Behoben

* `zip_release` aus `hacs.json` entfernt. HACS las Manifest und `hacs.json`
  dadurch aus dem Release-Asset statt aus dem Repository, was die
  HACS-Validierung nicht auflösen konnte.

## [0.2.1] – 2026-09-17

### Geändert

* Releases entstehen jetzt vollständig in GitLab: das HACS-Zip wird dort als
  Release-Asset veröffentlicht und unverändert nach GitHub gespiegelt.
* Die Prüfungen von hassfest laufen in der Pipeline mit, die HACS-Validierung
  nach dem Spiegeln auf GitHub.

## [0.2.0] – 2026-09-17

### Hinzugefügt

* Sensor **Ladezustand (Klartext)**. Liest dasselbe Register wie *Ladestatus*,
  liefert aber `Charging` / `Connected` / `Idle` / `Error` als reinen Text ohne
  Geräteklasse. Gedacht für Werkzeuge, die Home Assistant über die REST-API
  auslesen — etwa [Leapmotor Mate](https://github.com/ProtossBlaster/leapmotor-mate):
  Ein Sensor der Geräteklasse `enum` liefert dort immer den Rohwert, nie die
  Übersetzung. Standardmäßig deaktiviert.
* Abschnitt *Anbindung an Drittanwendungen* im README, mit Zuordnungstabelle
  für Leapmotor Mate.

### Behoben

* **Strom L1/L2/L3 war um den Faktor 10 zu niedrig.** Die Register 20059–20061
  nutzen Gain 10, nicht die dokumentierten 100. Belegt bei 1388 W an L1 und
  224,0 V: Rohwert 62 ergibt 6,2 A (6,2 × 224,0 = 1388,8 W, 0,1 % Abweichung),
  mit Gain 100 wären es 0,62 A und 138,9 W.

  > **Hinweis zum Update.** Die Stromwerte springen einmalig um den Faktor 10
  > nach oben. Das ist die Korrektur, kein Messfehler. Automationen, die auf
  > diese Sensoren vergleichen, sind entsprechend anzupassen. Leistung, Energie
  > und Spannung waren nie betroffen.

* **MQTT-Verbindungsstatus stand dauerhaft auf „Verbindet".** Die Register 20099
  (OCPP) und 20100 (MQTT) teilten sich ein Mapping, obwohl sie unterschiedliche
  Codes verwenden: Bei OCPP bedeutet 1 *Verbindungsaufbau*, bei MQTT bereits
  *Verbunden*. Beide werden jetzt getrennt ausgewertet.
* Die Register 20035, 20037 und 20039 werden als INT32 vorzeichenbehaftet
  dekodiert, wie im Protokolldokument angegeben.
* Docstring des *Laden*-Switch korrigiert: Register 21000 speichert den
  Ladebefehl nicht, es liest dauerhaft 0. Der Switch wertet deshalb den
  Ladestatus aus der Telemetrie aus — Rücklesen hätte „aus" gemeldet, auch
  mitten im Ladevorgang.

### Verifiziert

An einem A5191 (Firmware 1.0.6.1) im laufenden Betrieb geprüft:

* Ladestatus in den Zuständen *Idle*, *Charging* und *Charging Completed*,
  Letzteres nach Stopp über die Anker-App wie über die Integration.
* Start/Stop über Register 21000 löst tatsächlich aus.
* Skalierung der Relais-Temperaturen (Gain 10). Relais 1 liefert auf diesem
  Gerät konstant −55,0 °C — ein Sentinel für „keine Messung", kein Messwert;
  die Entität bleibt deshalb *nicht verfügbar*.
* Einheit der CP-Spannung als Millivolt, über drei CP-Zustände gegen die
  Sollwerte nach IEC 61851 (12/9/6 V) auf 0,25 V genau.
* Sämtliche 45 dokumentierten Register sowie alle Wertelisten gegen das
  Protokolldokument abgeglichen.

## [0.1.0]

* Erste Veröffentlichung: Anker SOLIX V1 Smart EV Charger über Modbus TCP,
  vollständig lokal. Messwerte, Steuerung und Diagnose als Home-Assistant-Gerät.
