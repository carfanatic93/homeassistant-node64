# Changelog

## 0.2.3

- Globaler Wartungssensor heißt jetzt "Wartung aktiv" (Gerätename nur einmal). unique_id unverändert.
- Monitor64: `maintenance_until` kommt aus dem Fenster, wenn der Host selbst kein Ende liefert. Zeitstempel mit Nanosekunden werden gelesen.
- Sammelsensoren für Hosts mit Problemen, Probleme gesamt und Checks gestört haben `in_wartung` und `ohne_wartung`. Der Status bleibt unverändert.

## 0.2.2

- Wartung: Monitor64-Hosts und Healthchecks-Checks zeigen `maintenance`, `maintenance_until`, `maintenance_reason`.
- Monitor64-Probleme mit `suppressed`, wenn sie in ein Wartungsfenster fallen.
- Neuer Sensor `binary_sensor.node64_wartung_aktiv` mit `windows`.

## 0.2.1

- Monitor64-Probleme werden übersetzt (Deutsch, Zahlen mit Komma). Unbekannte Schlüssel zeigen Schlüssel und Parameter.
- Neue Attribute je Problem: `detail_key` und `params`.

## 0.2.0

- Monitor64: `binary_sensor.<host>_probleme` liefert die Attribute `problems`, `problem_summary` und `last_check_at`.
- Monitor64: `sensor.monitor64_probleme_gesamt` liefert das Attribut `hosts`.
- Monitor64 nutzt `/api/monitor64/overview` statt `/api/monitor64/hosts`.
- Entity-IDs, unique_ids und Gerätenamen unverändert.

## 0.1.0

- Erste Version: Healthchecks, Proxy64/CDN64, Monitor64, Honeypot64 als Unter-Einträge.
