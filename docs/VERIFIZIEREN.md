# Register gegen echte Hardware verifizieren

Das Protokolldokument von Anker ist an mehreren Stellen falsch — Gain-Faktoren,
Einheitenspalten und das Rücklese-Verhalten eines Steuerregisters. Alle bislang
gefundenen Abweichungen stehen im [README](../README.md#technische-grundlage).

Wer an [`registers.py`](../custom_components/anker_solix_v1/registers.py) etwas
ändert, sollte deshalb **messen statt der Dokumentation zu glauben**. Dieses
Dokument beschreibt, wie das geht.

## Voraussetzungen

* `pymodbus` (`pip install "pymodbus>=3.6.0"`)
* Die Wallbox im Netz erreichbar, Modbus TCP in der Anker-App aktiviert
* Die Wallbox akzeptiert **höchstens zwei gleichzeitige Verbindungen**. Läuft
  Home Assistant bereits gegen sie, ist eine davon belegt.

## Abfragen mit dem echten Decoder

`registers.py` hat keine Home-Assistant-Abhängigkeiten und lässt sich direkt
importieren. So wird der produktive Decoder geprüft und nicht eine Nachbildung:

```python
import asyncio, sys
sys.path.insert(0, "custom_components/anker_solix_v1")
import registers as regs
from pymodbus.client import AsyncModbusTcpClient

HOST, PORT, UNIT = "192.0.2.10", 502, 1   # eigene Adresse eintragen


async def main():
    client = AsyncModbusTcpClient(HOST, port=PORT, timeout=8)
    assert await client.connect()
    try:
        rr = await client.read_input_registers(
            regs.INPUT_BLOCK_START, count=regs.INPUT_BLOCK_COUNT, device_id=UNIT
        )
    finally:
        client.close()

    words = list(rr.registers)
    values = {r.name: regs.decode(r, words) for r in regs.INPUT_REGISTERS}
    for name, value in sorted(values.items()):
        print(f"{name:<24} {value}")
    print("roh 20059:", words[59])   # Rohwert für eine Gain-Prüfung


asyncio.run(main())
```

Der Block 20000–20100 antwortet ausschließlich auf **FC4** (Input Register),
der Block 21000–21005 ausschließlich auf **FC3/FC6** (Holding Register).

## Drei Prüfmuster

### Gain über die Leistungsbilanz

Bei einphasigem Laden muss `Strom x Spannung` die gemeldete Wirkleistung
ergeben. So fiel auf, dass die Stromregister Gain 10 statt der dokumentierten
100 verwenden:

| Gain | Strom | × Spannung | gemeldet |
|---|---|---|---|
| 100 | 0,62 A | 138,9 W | 1388 W — 90 % daneben |
| 10 | 6,2 A | 1388,8 W | 1388 W — 0,1 % Abweichung |

Ein Faktor 10 oder 100 daneben fällt hier sofort auf. Mehrere Messungen im
Abstand weniger Sekunden erhärten das Ergebnis.

### Sensor oder Sentinel?

Ein **echter Sensor bewegt sich**. Register 20093 (Relais 1) las über einen
kompletten Ladevorgang hinweg konstant −550, bis auf die Stelle unverändert —
das ist ein Sentinel für „keine Messung" (−55,0 °C), kein Messwert. Register
20094 wanderte im selben Zeitraum von 251 auf 253, also 25,1 → 25,3 °C: ein
realer Sensor, der sich unter Last erwärmt.

Wer eine Skalierung prüft, misst daher **unter Last über mehrere Minuten**, nicht
einmalig im Leerlauf.

### Physikalische Sollwerte

Manche Register lassen sich gegen eine Norm prüfen. Die CP-Spannung traf in drei
Zuständen die Sollwerte nach IEC 61851 auf 0,25 V genau — damit war die Einheit
Millivolt belegt, ohne dass die Dokumentation sie nennt:

| CP-Zustand | gemessen | Sollwert |
|---|---|---|
| A (nicht verbunden) | 11,779 V | 12 V |
| B1 (verbunden) | 8,846 V | 9 V |
| C2 (ladend) | 5,826 V | 6 V |

## Ladezustände auslösen

Die Statuscodes lassen sich nur teilweise gezielt herbeiführen:

| Code | Zustand | Wie |
|---|---|---|
| 0 | `idle` | Kabel vom Fahrzeug trennen |
| 2 | `charging` | Laden starten |
| 5 | `charging_completed` | Laufende Ladung stoppen — über die App wie über die Integration |
| 1, 3, 4, 6, 7, 8 | übrige | nicht gezielt auslösbar (Fehler, Reservierung, Deaktivierung) |

## Steuerregister

Register 21000 **speichert den Ladebefehl nicht**: Nach einem Stopp liest es
dauerhaft 0, nie die geschriebene 2. Der *Laden*-Switch wertet deshalb den
Ladestatus aus der Telemetrie aus. Wer das auf Rücklesen umstellt, bekommt einen
Switch, der auch mitten im Ladevorgang „aus" meldet.

## Nach einer Änderung

Vor dem Commit prüfen, dass Adressen, Wortanzahl und Wertelisten konsistent
bleiben:

```sh
python ci/validate.py
```

Die Pipeline führt dieselbe Prüfung aus und lehnt ein Release ab, dessen
Manifest-Version nicht zum Tag passt.
