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

## Monitor64-Probleme als Attribute

`binary_sensor.<host>_probleme` (Problem) liefert die Details der aktuellen Probleme:

| Attribut | Inhalt |
|---|---|
| `problems` | Liste der Probleme, je Eintrag `message`, `severity`, `check`, `since` |
| `problem_summary` | Alle Meldungen in einem Text, getrennt durch `; `, max. 250 Zeichen |
| `last_check_at` | Zeitpunkt der letzten Prüfung des Hosts (ISO 8601) |

Ohne Problem: `problems: []` und `problem_summary: ""`.

`sensor.monitor64_probleme_gesamt` hat zusätzlich `hosts`: Liste der Hosts mit Problemen, je Eintrag `host`, `count`, `problem_summary`.

`problems`, `hosts` und `last_check_at` werden nicht im Recorder gespeichert, damit die Datenbank nicht wächst. `problem_summary` wird gespeichert.

Beispiel (Attribute eines gestörten Hosts):

```json
{
  "problems": [
    {
      "message": "proxmox-backup: Dienst gestoppt",
      "severity": "crit",
      "check": "svc-proxmox-backup",
      "since": "2026-11-24T08:15:00Z"
    }
  ],
  "problem_summary": "proxmox-backup: Dienst gestoppt",
  "last_check_at": "2026-11-24T08:31:12Z"
}
```

Die Werte im Beispiel sind konstruiert, nicht aus einer echten Node.
