#!/usr/bin/env python3
"""
Install the RadioMaster Nomad-as-RX custom hardware target for ExpressLRS 4.x.

Usage examples:
  python3 install_nomad_rx_target_v4.py ~/elrs/ExpressLRS
  python3 install_nomad_rx_target_v4.py ~/elrs/ExpressLRS/src
  python3 install_nomad_rx_target_v4.py ~/elrs/ExpressLRS/src/hardware

The script finds the hardware tree containing targets.json, RX/, and TX/.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

LAYOUT_NAME = "Radiomaster Nomad RX FCC.json"
TARGET_KEY = "nomad-rx-fcc"
MANUFACTURER = "radiomaster"
CATEGORY = "rx_dual"

LAYOUT: dict[str, Any] = {
    "serial_rx": 3,
    "serial_tx": 1,
    "serial1_rx": 5,
    "serial1_tx": 18,
    "radio_busy": 36,
    "radio_dio1": 37,
    "radio_miso": 33,
    "radio_mosi": 32,
    "radio_nss": 27,
    "radio_rst": 15,
    "radio_sck": 25,
    "radio_busy_2": 39,
    "radio_dio1_2": 34,
    "radio_nss_2": 13,
    "radio_rst_2": 21,
    "radio_dcdc": True,
    "radio_rfo_hf": True,
    "radio_rfsw_ctrl": [15, 0, 12, 8, 8, 6, 0, 5],
    "power_min": 0,
    "power_high": 6,
    "power_max": 6,
    "power_default": 3,
    "power_control": 0,
    "power_values": [120, 120, 120, 120, 120, 120, 100],
    "power_values2": [-17, -16, -14, -11, -7, -3, 5],
    "power_values_dual": [-18, -14, -8, -6, -2, 3, 5],
    "power_lna_gain": 12,
    "led_rgb": 22,
    "led_rgb_isgrb": True,
    "ledidx_rgb_status": [0, 1],
    "ledidx_rgb_boot": [0, 1],
    "button": 14,
    "button2": 12,
    "vbat_atten": -1,
    "misc_fan_en": 2,
    "customised": True,
}

TARGET_ENTRY: dict[str, Any] = {
    "product_name": "RadioMaster Nomad RX FCC",
    "lua_name": "RM Nomad RX",
    "layout_file": LAYOUT_NAME,
    "upload_methods": ["uart", "wifi", "betaflight"],
    "min_version": "4.0.0",
    "platform": "esp32",
    "firmware": "Unified_ESP32_LR1121_RX",
}


def find_hardware_dir(path: Path) -> Path:
    path = path.expanduser().resolve()
    candidates = [
        path,
        path / "hardware",
        path / "src" / "hardware",
    ]
    for candidate in candidates:
        if (candidate / "targets.json").exists() and (candidate / "RX").is_dir() and (candidate / "TX").is_dir():
            return candidate
    raise SystemExit(
        "Could not find ExpressLRS hardware directory. Pass the directory containing targets.json, RX/, and TX/."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="ExpressLRS repo root, src directory, or src/hardware directory")
    args = parser.parse_args()

    hardware_dir = find_hardware_dir(Path(args.path))
    targets_json = hardware_dir / "targets.json"
    rx_dir = hardware_dir / "RX"
    layout_path = rx_dir / LAYOUT_NAME

    data = json.loads(targets_json.read_text(encoding="utf-8"))

    backup = targets_json.with_suffix(".json.bak")
    if not backup.exists():
        shutil.copy2(targets_json, backup)
        print(f"Backed up {targets_json} -> {backup}")
    else:
        print(f"Backup already exists: {backup}")

    layout_path.write_text(json.dumps(LAYOUT, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {layout_path}")

    radiomaster = data.setdefault(MANUFACTURER, {"name": "Radiomaster"})
    radiomaster.setdefault("name", "Radiomaster")
    rx_dual = radiomaster.setdefault(CATEGORY, {})
    old = rx_dual.get(TARGET_KEY)
    rx_dual[TARGET_KEY] = TARGET_ENTRY
    if old:
        print(f"Updated {MANUFACTURER}.{CATEGORY}.{TARGET_KEY}")
    else:
        print(f"Added {MANUFACTURER}.{CATEGORY}.{TARGET_KEY}")

    targets_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {targets_json}")

    # Post-install checks.
    loaded = json.loads(layout_path.read_text(encoding="utf-8"))
    assert loaded.get("misc_fan_en") == 2
    print("Verified misc_fan_en = 2 in RX layout")
    print("Build target: RadioMaster Nomad RX FCC / Unified_ESP32_LR1121_RX")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
