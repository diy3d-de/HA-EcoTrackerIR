# everHome EcoTracker fuer Home Assistant

Inoffizielle Custom Integration, um EcoTracker-Daten aus der everHome Cloud oder direkt ueber die lokale EcoTracker-API in Home Assistant als Sensoren bereitzustellen.

Dies ist keine offizielle Integration von everHome und keine offizielle Home-Assistant-Core-Integration.

## One-Click-Installation fuer HassOS

Diese Installation braucht keinen FTP-, Samba- oder Terminal-Zugriff auf deinen Home-Assistant-Server. Voraussetzung ist nur HACS.

[![Repository in HACS oeffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?category=integration&owner=diy3d-de&repository=HA-EcoTrackerIR)

1. Klicke auf den Button `Repository in HACS oeffnen`.
2. Waehle deine Home-Assistant-Instanz aus.
3. HACS oeffnet das Repository `diy3d-de/HA-EcoTrackerIR`.
4. Klicke auf `Herunterladen`.
5. Starte Home Assistant neu.
6. Klicke danach auf diesen Button, um die Integration einzurichten:

[![Integration hinzufuegen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=everhome_ecotracker)

Falls HACS noch nicht installiert ist, installiere zuerst HACS fuer Home Assistant OS/Supervised:

[![HACS installieren](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=cb646a50_get&repository_url=https%3A%2F%2Fgithub.com%2Fhacs%2Faddons)

## Warum OAuth statt direkter Passwort-Eingabe?

everHome dokumentiert fuer die Cloud-API OAuth2. Die Anmeldung mit E-Mail-Adresse und Passwort passiert auf der everHome-Webseite im OAuth-Login. Die Integration speichert danach nur OAuth-Tokens, nicht dein everHome-Passwort.

Quellen:

- everHome Cloud-API: <https://everhome.cloud/de/entwickler>
- everHome EcoTracker lokale API: <https://everhome.cloud/de/entwickler/ecotracker>

## Datenquelle waehlen

Beim Hinzufuegen der Integration kannst du zwischen zwei Datenquellen waehlen:

- `everHome Cloud`: nutzt die dokumentierte everHome Cloud-API mit OAuth2.
- `EcoTracker lokal`: liest direkt `http://<EcoTracker-IP>/v1/json`.

Fuer den lokalen Modus muss der lokale HTTP-Server in der everHome App aktiviert sein. Laut everHome ist diese Option standardmaessig eingeschaltet. Du kannst als Adresse entweder nur die IP, z. B. `192.168.1.50`, oder die komplette URL `http://192.168.1.50/v1/json` eintragen.

In den Integrationsoptionen kannst du das Aktualisierungsintervall aendern. Ein Cloud-Eintrag kann dort auch auf lokale Daten umgestellt und spaeter wieder zurueck auf Cloud gesetzt werden.

## Manuelle Installation

1. Kopiere den Ordner `custom_components/everhome_ecotracker` nach `custom_components` deiner Home-Assistant-Installation.
2. Starte Home Assistant neu.
3. Oeffne `Einstellungen > Geraete & Dienste > Integration hinzufuegen`.
4. Suche nach `everHome EcoTracker`.

## everHome OAuth-Anwendung anlegen

1. Oeffne <https://everhome.cloud/de/entwickler>.
2. Melde dich an.
3. Erstelle unter `Meine Anwendungen` eine OAuth2-Anwendung.
4. Verwende als Redirect URI z. B. `http://localhost:12345`.
5. Notiere `Client ID` und `Client Secret`.

Beim Einrichten in Home Assistant zeigt die Integration eine everHome-Login-URL. Oeffne sie, melde dich mit E-Mail-Adresse und Passwort an und erlaube den Zugriff. Danach wirst du auf die Redirect URI weitergeleitet. Auch wenn der Browser dort eine Fehlerseite zeigt: In der Adresszeile steht `?code=...`. Diesen Code kopierst du in Home Assistant.

## Sensoren

Die Integration erzeugt Sensoren fuer alle numerischen Werte aus der gewaehlten Quelle.

Im Cloud-Modus ruft sie `https://everhome.cloud/device?include=properties` ab. Im lokalen Modus ruft sie `http://<EcoTracker-IP>/v1/json` ab.

Das Standard-Intervall ist auf 5 Sekunden gesetzt. Das ist die schnellste sinnvolle Nahe-Echtzeit-Aktualisierung fuer die dokumentierte everHome Cloud-REST-API.

Bekannte EcoTracker-Werte werden passend klassifiziert:

- Leistung in Watt: `power`, `powerAvg`, `powerPhase1`, `powerPhase2`, `powerPhase3`
- Zaehlerstaende in kWh: `energyCounterIn`, `energyCounterInT1`, `energyCounterInT2`, `energyCounterOut`, `energyCounterIOut`

Die everHome-Dokumentation beschreibt EcoTracker-Zaehlerstaende als Wh. Die Integration wandelt diese Werte fuer Home Assistant in kWh um.

## Dashboard-Beispiel

```yaml
type: entities
title: EcoTracker
entities:
  - sensor.ecotracker_leistung
  - sensor.ecotracker_leistung_durchschnitt
  - sensor.ecotracker_zaehlerstand_bezug
  - sensor.ecotracker_zaehlerstand_einspeisung
```

Die konkreten Entity-IDs koennen je nach Geraetename abweichen.

## Hinweis zum Wechsel Cloud/Lokal

Wenn du die Integration direkt im lokalen Modus anlegst, werden keine Cloud-Zugangsdaten gespeichert. Fuer die Cloud-Nutzung legst du in diesem Fall einen zweiten Eintrag im Cloud-Modus an.
