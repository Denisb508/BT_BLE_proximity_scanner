# BT BLE proximity scanner v2.0 - Mix Mode Offline

To je nadgrajena portable/offline verzija z bolj "mix-mode" logiko:
- score-based target detection
- target profili v `config\targets.json`
- anti-flapping (`POSSIBLE / PRESENT / LOST / ABSENT`)
- manj popup spama za unknown naprave
- gumb **Save selected as target** za hitro izdelavo fingerprint profila

## Online PC
1. Razpakiraj mapo.
2. Po potrebi preveri `wheels\` in `python\`.
3. Zapakiraj CELOTNO mapo in jo prenesi na offline PC.

## Offline PC
1. Razpakiraj mapo npr. v `C:\Tools\BT_BLE_proximity_scanner_v2`.
2. Zaženi `START_BLE.cmd`.
3. Če želiš zagon brez konzole, uporabi `START_BLE_SILENT.vbs`.

## Konfiguracija
- Glavne nastavitve: `config\config.json`
- Target profili: `config\targets.json`
- Offline baze: `app\manufacturers.json`, `app\name_patterns.json`, `app\service_uuids.json`, `app\mac_oui.json`
- Ročno shranjene naprave: `app\known_devices.json`

## Priporočen workflow
1. Zaženi app.
2. Počakaj, da se tvoja naprava pojavi na seznamu.
3. Označi jo in klikni **Save selected as target**.
4. Po potrebi popravi `config\targets.json`.
5. Testiraj prag `min_rssi` in `score_present`.

## Opombe
- Trenutna verzija temelji na BLE skeniranju, mix-mode scoring pa je pripravljen tudi za MAC/fingerprint logiko.
- Bluetooth Classic aktivno odkrivanje še ni ločen backend; v tej verziji je poudarek na robustnejši BLE/fingerprint logiki za offline Windows paket.
- Če offline PC nima Bluetooth LE adapterja ali gonilnika, se bo GUI odprl in prikazal napako, log pa bo v `app\logs\ble_monitor_debug.log`.
