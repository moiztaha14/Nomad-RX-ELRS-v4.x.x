# Nomad RX ELRS v4.x.x

Fork of [ndd91/nomad-elrs-v4-rx](https://github.com/ndd91/nomad-elrs-v4-rx) — a custom
ExpressLRS v4 target for flashing a **RadioMaster Nomad TX module as an RX**.

This fork replaces the original manual, multi-step README workflow with a single
automated script for **Windows**. It also fixes a step that went stale after
ExpressLRS split hardware target definitions out into their own
[`ExpressLRS/targets`](https://github.com/ExpressLRS/targets) repository — the old
instructions never accounted for that move.

All credit for the original target definition, RX pinout, and fan-enable research
goes to [ndd91](https://github.com/ndd91). This fork only automates and updates the
install process.

---

## What this does

The custom target adds:

```text
Manufacturer: Radiomaster
Category:      rx_dual
Target key:    nomad-rx-fcc
Product name:  RadioMaster Nomad RX FCC
Firmware:      Unified_ESP32_LR1121_RX
Min version:   4.0.0
```

The key hardware addition is the Nomad's fan-enable pin:

```json
"misc_fan_en": 2
```

---

## Requirements

- Windows
- [Git](https://git-scm.com/downloads) installed and on `PATH`
- [Python 3](https://www.python.org/downloads/) installed and on `PATH`
- A RadioMaster Nomad module, connected over USB when you reach the flashing step

Everything else (PlatformIO, the ESP32 toolchain, Python build packages) is installed
automatically by the script into a local virtual environment — nothing is installed
system-wide.

---

## Usage

1. Clone this repo (or download it)
2. From inside the repo folder, run:

```powershell
python setup_nomad_rx.py
```

3. Follow the prompts. The script will:

   1. Check `git`/`python` are available and ask where to install ExpressLRS
   2. Clone ExpressLRS and let you pick a `4.x` version tag
   3. Clone the separate `ExpressLRS/targets` repo into `src/hardware` — **this is
      the step the original workflow was missing**
   4. Inject the Nomad RX target (layout + registry entry), with an automatic
      backup of `targets.json` first
   5. Verify everything was written correctly
   6. Set up a Python virtual environment and install PlatformIO + build dependencies
   7. Ask for your regulatory domain, binding phrase, and Wi-Fi (or built-in AP) preference
   8. Build the firmware — you'll be prompted once during the build to choose the
      firmware configuration from a list; select **"RadioMaster Nomad RX FCC"**
   9. Walk you through flashing over USB — with confirmation prompts before
      erasing or writing anything to the device (you'll be asked to choose the
      configuration again for erase and for upload — this is expected)
   10. Check the flashed device's `hardware.json` over its WebUI, confirm the fan
       pin is present, and ask whether the fan is actually spinning. If it isn't,
       it automatically applies and rebuilds with the force-fan fallback

The script is safe to re-run: it detects and reuses an existing ExpressLRS clone,
targets checkout, and virtual environment instead of redoing work.

---

## Repo structure

```text
.
├── README.md
├── setup_nomad_rx.py              # run this
├── data/
│   ├── targets-radiomaster-rx_dual-entry.json
│   ├── RX/Radiomaster Nomad RX FCC.json
│   ├── examples/super_defines.fcc915.example.txt
│   └── patches/force_fan_on_snippet.txt
└── legacy/                        # original manual scripts, kept for reference/credit
    ├── install_nomad_rx_target.py
    └── verify_nomad_rx_target.py
```

---

## Fan test checklist

Don't rely solely on the WebUI showing a fan option — confirm the hardware behaves
correctly:

1. Attach antennas or an RF dummy load
2. Power the Nomad from a known-good supply
3. Confirm `hardware.json` contains `misc_fan_en: 2` (the script does this for you)
4. Link to the other ELRS v4 device
5. Increase RX telemetry power step by step
6. Confirm the fan actually spins

If the fan pin is present but the fan never spins, the script offers to apply a
force-fan fallback automatically, rebuild, and reflash.

---

## Manual reference

The `legacy/` scripts document the original (pre-automation, Ubuntu + Windows)
manual process and are kept for reference and to preserve credit for the original
approach. They target the old ExpressLRS layout where hardware targets lived
inside the main repo, and are no longer the recommended way to install this target.

---

## Notes

- This fork's automated workflow has been tested on **Windows**, ExpressLRS `4.1.0`,
  flashing a Nomad module over UART/USB.
- Both ends of the ELRS link must run the same major version (v4.x here).
- For 1 W telemetry testing, confirm fan operation before enclosing or deploying
  the module.
