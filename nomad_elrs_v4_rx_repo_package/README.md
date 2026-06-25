# RadioMaster Nomad as ExpressLRS v4 RX

This folder captures the working setup for flashing a **RadioMaster Nomad TX module as an ExpressLRS RX** using ELRS **v4.0.0 or newer**.

The custom target adds:

```text
Manufacturer: Radiomaster
Category:      rx_dual
Target key:    nomad-rx-fcc
Product name:  RadioMaster Nomad RX FCC
Firmware:      Unified_ESP32_LR1121_RX
Min version:   4.0.0
```

The important hardware addition is the Nomad fan-enable pin:

```json
"misc_fan_en": 2
```

On RX firmware, normal TX fan menu items such as `fan-mode` and `power-fan-threshold` are not expected to appear. The validation item is whether the active device `hardware.json` contains `misc_fan_en: 2`, and whether the fan/GPIO2 behaves correctly under power testing.

---

## Package contents

```text
.
├── README.md
├── install_nomad_rx_target.py
├── verify_nomad_rx_target.py
├── RX/
│   └── Radiomaster Nomad RX FCC.json
├── hardware-upload/
│   └── hardware-nomad-rx-fcc-v4-fan.json
├── targets-radiomaster-rx_dual-entry.json
├── examples/
│   └── super_defines.fcc915.example.txt
└── patches/
    └── force_fan_on_snippet.txt
```

### File roles

| File | Purpose |
|---|---|
| `install_nomad_rx_target.py` | Installs/updates the custom target inside an ExpressLRS source tree. |
| `verify_nomad_rx_target.py` | Verifies the local source tree and optionally checks a flashed device over WebUI. |
| `RX/Radiomaster Nomad RX FCC.json` | The RX hardware layout with `misc_fan_en: 2`. |
| `hardware-upload/hardware-nomad-rx-fcc-v4-fan.json` | Same layout, named for manual upload through WebUI if needed. |
| `targets-radiomaster-rx_dual-entry.json` | Reference target-registry entry inserted into `src/hardware/targets.json`. |
| `examples/super_defines.fcc915.example.txt` | Example FCC 915 build defines. |
| `patches/force_fan_on_snippet.txt` | Optional emergency fallback if the fan pin is present but RX firmware never asserts it. |

---

## Safety and setup notes

- Use the correct regulatory domain for your location and hardware.
- Do not run high RF power without a proper antenna or dummy load.
- For 1 W telemetry testing, confirm fan operation before enclosing or deploying the module.
- Both ends of the ELRS link must use the same major version. This package is for ELRS v4.x.
- For first flash after converting from TX-module firmware to RX firmware, use UART/USB flashing and erase flash first.

---

## Ubuntu 24.04 workflow

### 1. Get ExpressLRS v4

```bash
mkdir -p ~/elrs
cd ~/elrs
git clone --recursive https://github.com/ExpressLRS/ExpressLRS.git
cd ExpressLRS
git fetch --tags
```

Check out the ELRS v4 tag you want. Example:

```bash
git checkout 4.0.1
git submodule update --init --recursive
```

Use a newer v4.x tag if that is what the rest of your system is using.

### 2. Install Python / PlatformIO tools

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip unzip build-essential

cd ~/elrs/ExpressLRS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install platformio dronecan setuptools empy==3.3.4 pexpect
```

### 3. Install this custom target

From wherever this folder lives:

```bash
python3 /path/to/nomad_elrs_v4_rx_repo_package/install_nomad_rx_target.py ~/elrs/ExpressLRS
```

The script also accepts any of these paths:

```text
~/elrs/ExpressLRS
~/elrs/ExpressLRS/src
~/elrs/ExpressLRS/src/hardware
```

It modifies:

```text
~/elrs/ExpressLRS/src/hardware/targets.json
~/elrs/ExpressLRS/src/hardware/RX/Radiomaster Nomad RX FCC.json
```

It also creates a timestamped backup of `targets.json`.

### 4. Verify local source files

```bash
python3 /path/to/nomad_elrs_v4_rx_repo_package/verify_nomad_rx_target.py ~/elrs/ExpressLRS
```

Expected final line:

```text
Verification passed.
```

You can also manually check:

```bash
grep -n "nomad-rx-fcc" ~/elrs/ExpressLRS/src/hardware/targets.json
grep -n "misc_fan_en" ~/elrs/ExpressLRS/src/hardware/RX/Radiomaster\ Nomad\ RX\ FCC.json
```

Expected fan result:

```json
"misc_fan_en": 2
```

### 5. Create build defines

```bash
cd ~/elrs/ExpressLRS/src
cp /path/to/nomad_elrs_v4_rx_repo_package/examples/super_defines.fcc915.example.txt super_defines.txt
nano super_defines.txt
```

At minimum, set:

```text
-DRegulatory_Domain_FCC_915
-DMY_BINDING_PHRASE="ReplaceWithYourBindingPhrase"
```

Keep the binding phrase the same on the other ELRS device.

### 6. Build

```bash
cd ~/elrs/ExpressLRS/src
pio run -e Unified_ESP32_LR1121_RX_via_UART
```

When prompted to choose the firmware configuration, do **not** leave it bare. Select:

```text
Radiomaster -> rx_dual -> RadioMaster Nomad RX FCC
```

or the equivalent target key:

```text
radiomaster.rx_dual.nomad-rx-fcc
```

### 7. Flash over UART/USB

Find the port:

```bash
pio device list
```

Erase and flash, replacing `/dev/ttyUSB0` with the actual port:

```bash
cd ~/elrs/ExpressLRS/src
pio run -e Unified_ESP32_LR1121_RX_via_UART -t erase --upload-port /dev/ttyUSB0
pio run -e Unified_ESP32_LR1121_RX_via_UART -t upload --upload-port /dev/ttyUSB0
```

If upload fails, put the ESP32 into bootloader mode, then run the upload again.

---

## Windows workflow

PowerShell commands:

```powershell
mkdir C:\elrs
cd C:\elrs
git clone --recursive https://github.com/ExpressLRS/ExpressLRS.git
cd C:\elrs\ExpressLRS
git fetch --tags
git checkout 4.0.1
git submodule update --init --recursive
```

Create and activate a Python environment:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install platformio dronecan setuptools empy==3.3.4 pexpect
```

Install the target:

```powershell
py C:\path\to\nomad_elrs_v4_rx_repo_package\install_nomad_rx_target.py C:\elrs\ExpressLRS
```

Verify:

```powershell
py C:\path\to\nomad_elrs_v4_rx_repo_package\verify_nomad_rx_target.py C:\elrs\ExpressLRS
```

Create `super_defines.txt`:

```powershell
cd C:\elrs\ExpressLRS\src
Copy-Item C:\path\to\nomad_elrs_v4_rx_repo_package\examples\super_defines.fcc915.example.txt .\super_defines.txt
notepad .\super_defines.txt
```

Build:

```powershell
cd C:\elrs\ExpressLRS\src
pio run -e Unified_ESP32_LR1121_RX_via_UART
```

Select:

```text
Radiomaster -> rx_dual -> RadioMaster Nomad RX FCC
```

Find the COM port:

```powershell
pio device list
```

Erase and flash, replacing `COM5` with the actual port:

```powershell
pio run -e Unified_ESP32_LR1121_RX_via_UART -t erase --upload-port COM5
pio run -e Unified_ESP32_LR1121_RX_via_UART -t upload --upload-port COM5
```

---

## Device verification after flashing

After flashing, power-cycle the Nomad. Connect to the RX WebUI by one of these methods:

```text
http://10.0.0.1/
http://elrs_rx.local/
```

Then check the active hardware JSON:

```text
http://10.0.0.1/hardware.json
```

or on Ubuntu:

```bash
curl http://10.0.0.1/hardware.json | grep -i fan
```

Expected:

```json
"misc_fan_en":2
```

Spacing may differ.

The verify script can also check the device:

```bash
python3 /path/to/nomad_elrs_v4_rx_repo_package/verify_nomad_rx_target.py ~/elrs/ExpressLRS --device-url http://10.0.0.1
```

Expected:

```text
OK:   device hardware.json contains misc_fan_en: 2
Verification passed.
```

---

## If the flashed device is missing `misc_fan_en`

This usually means one of these happened:

1. The firmware was built as a bare image.
2. The wrong target was selected.
3. A stale hardware override is still active in flash.
4. The target was installed into the wrong ExpressLRS checkout.

First try a clean rebuild and erase/flash:

```bash
cd ~/elrs/ExpressLRS/src
pio run -e Unified_ESP32_LR1121_RX_via_UART -t clean
rm -rf .pio/build/Unified_ESP32_LR1121_RX_via_UART
pio run -e Unified_ESP32_LR1121_RX_via_UART
pio run -e Unified_ESP32_LR1121_RX_via_UART -t erase --upload-port /dev/ttyUSB0
pio run -e Unified_ESP32_LR1121_RX_via_UART -t upload --upload-port /dev/ttyUSB0
```

If the firmware name is correct but `hardware.json` still lacks the fan pin, use the manual WebUI fallback:

1. Open the RX WebUI.
2. Go to the hardware layout page.
3. Upload:

```text
hardware-upload/hardware-nomad-rx-fcc-v4-fan.json
```

4. Save/reboot.
5. Recheck:

```text
http://10.0.0.1/hardware.json
```

---

## Fan test checklist

Do not depend on a visible fan option in the RX WebUI. Test the actual hardware behavior.

1. Attach antennas or RF dummy loads.
2. Power the Nomad from a known-good supply.
3. Confirm the active `hardware.json` contains `misc_fan_en: 2`.
4. Connect/link to the other ELRS v4 device.
5. Increase RX telemetry power step by step.
6. Probe GPIO2 or the fan-enable net with a DMM or scope.
7. Confirm fan spin and module temperature stabilization.

Expected outcomes:

| Result | Meaning |
|---|---|
| `misc_fan_en` present and fan spins | Target and fan behavior are working. |
| `misc_fan_en` present, GPIO2 goes high, fan does not spin | Fan supply, MOSFET, connector, or mechanical fan issue. |
| `misc_fan_en` present, GPIO2 never changes | RX firmware path may not be invoking fan control. See the fallback snippet. |
| Fan always on | Acceptable for platform testing if current and thermal behavior are acceptable. |

---

## Optional force-fan fallback

Use this only if:

```text
active hardware.json contains "misc_fan_en": 2
GPIO2 never asserts during high telemetry-power testing
```

See:

```text
patches/force_fan_on_snippet.txt
```

The fallback concept is:

```cpp
#ifdef NOMAD_RX_FORCE_FAN
    pinMode(2, OUTPUT);
    digitalWrite(2, HIGH);
#endif
```

and add this to `src/super_defines.txt`:

```text
-DNOMAD_RX_FORCE_FAN
```

For a 1 W telemetry platform, fan always-on is safer than fan never-on.

---

## Reusing this package after an ELRS update

After pulling a newer ELRS v4 tag or replacing the ExpressLRS source tree, rerun:

```bash
python3 /path/to/nomad_elrs_v4_rx_repo_package/install_nomad_rx_target.py ~/elrs/ExpressLRS
python3 /path/to/nomad_elrs_v4_rx_repo_package/verify_nomad_rx_target.py ~/elrs/ExpressLRS
```

Then rebuild and flash the same way.

This keeps the custom target reproducible without relying on memory or manual JSON edits.
