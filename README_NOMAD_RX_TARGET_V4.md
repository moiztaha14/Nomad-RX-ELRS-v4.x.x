# RadioMaster Nomad as RX target for ExpressLRS 4.x

This package installs a custom `radiomaster.rx_dual.nomad-rx-fcc` hardware target for ExpressLRS 4.0.0 or newer.

Important fields:

```json
"firmware": "Unified_ESP32_LR1121_RX",
"min_version": "4.0.0",
"misc_fan_en": 2
```

Install from the ExpressLRS repo root, `src`, or `src/hardware`:

```bash
python3 install_nomad_rx_target_v4.py ~/elrs/ExpressLRS
```

Then verify:

```bash
grep -n "nomad-rx-fcc" ~/elrs/ExpressLRS/src/hardware/targets.json
grep -n "misc_fan_en" ~/elrs/ExpressLRS/src/hardware/RX/Radiomaster\ Nomad\ RX\ FCC.json
```

Build:

```bash
cd ~/elrs/ExpressLRS/src
pio run -e Unified_ESP32_LR1121_RX_via_UART -t clean
pio run -e Unified_ESP32_LR1121_RX_via_UART
```

Select `RadioMaster Nomad RX FCC` when prompted. Flash with a filesystem erase when converting or when the WebUI still shows an old hardware.json:

```bash
pio run -e Unified_ESP32_LR1121_RX_via_UART -t erase --upload-port /dev/ttyUSB0
pio run --target upload --environment Unified_ESP32_LR1121_RX_via_UART --upload-port /dev/ttyUSB0
```

After boot, check:

```text
http://10.0.0.1/hardware.json
```

It should contain:

```json
"misc_fan_en": 2
```

If it does not, upload `hardware-nomad-rx-fcc-v4-with-fan.json` through the WebUI Hardware Layout page or erase/reflash again.
