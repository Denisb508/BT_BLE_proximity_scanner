# Release notes - BT BLE proximity scanner v2.0

## Added
- project rename to **BT BLE proximity scanner**
- mix-mode target scoring engine
- target profiles in `config\targets.json`
- anti-flapping states: `ABSENT`, `POSSIBLE`, `PRESENT`, `LOST`
- one-click creation of target profile from a discovered device
- cleaner status line and richer logging

## Changed
- reduced popup spam for unknown devices
- moved runtime settings into `config\config.json`
- improved offline layout for GitHub release packaging

## Notes
- this build focuses on robust BLE + fingerprint detection for offline Windows deployment
- active Bluetooth Classic discovery is not yet a separate scanner backend in this package
