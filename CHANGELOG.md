# Changelog

## 0.2.0

- Monitor64: `binary_sensor.<host>_probleme` liefert die Attribute `problems`, `problem_summary` und `last_check_at`.
- Monitor64: `sensor.monitor64_probleme_gesamt` liefert das Attribut `hosts`.
- Monitor64 nutzt `/api/monitor64/overview` statt `/api/monitor64/hosts`.
- Entity-IDs, unique_ids und Gerätenamen unverändert.

## 0.1.0

- Erste Version: Healthchecks, Proxy64/CDN64, Monitor64, Honeypot64 als Unter-Einträge.
