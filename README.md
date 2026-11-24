# node64 für Home Assistant

Custom Integration für die REST-API einer [node64](https://node64.de)-Node. Liest Status, Checks und Version aus. Es gibt keine Schreibzugriffe.

## Installation

1. HACS > Benutzerdefinierte Repositories > dieses Repo als Typ "Integration" hinzufügen.
2. node64 installieren und Home Assistant neu starten.
3. Einstellungen > Geräte & Dienste > Integration hinzufügen > node64.
4. Host oder IP, Port (Standard 8080) und einen API-Key der Node eintragen. Den Key legst du unter Einstellungen > API-Keys der Node an.

## Entitäten

- Pro Healthcheck ein Binary-Sensor (Problem), an wenn der Check `down` oder `degraded` ist.
- Sensoren für Anzahl gestörter Checks, Anzahl aller Checks und die Node-Version.

Die Daten werden alle 60 Sekunden abgefragt.
