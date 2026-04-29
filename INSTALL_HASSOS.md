# HassOS Installation ohne FTP

Nutze diese Datei, wenn du nur ueber die Home-Assistant-Oberflaeche installieren moechtest.

## 1. HACS installieren, falls noch nicht vorhanden

[![HACS installieren](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=cb646a50_get&repository_url=https%3A%2F%2Fgithub.com%2Fhacs%2Faddons)

Nach der HACS-Installation Home Assistant neu starten und HACS einmal einrichten.

## 2. Christian Laux EcoTracker Repository in HACS oeffnen

[![Repository in HACS oeffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&owner=diy3d-de&repository=HA-EcoTrackerIR)

Dann in HACS auf `Herunterladen` klicken und Home Assistant neu starten.

## 3. Integration einrichten

[![Integration hinzufuegen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=everhome_ecotracker)

Danach Client ID, Client Secret und den everHome OAuth-Code eingeben.

Hinweis: Der HACS-Button funktioniert erst, wenn dieses Projekt als GitHub-Repository unter `diy3d-de/HA-EcoTrackerIR` veroeffentlicht wurde.
