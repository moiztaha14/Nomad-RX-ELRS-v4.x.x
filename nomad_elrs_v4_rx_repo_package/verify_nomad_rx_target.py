#!/usr/bin/env python3
"""
Verify the RadioMaster Nomad-as-RX target locally, and optionally verify a flashed device WebUI.

Examples:
  python3 verify_nomad_rx_target.py ~/elrs/ExpressLRS
  python3 verify_nomad_rx_target.py ~/elrs/ExpressLRS --device-url http://10.0.0.1
  python3 verify_nomad_rx_target.py ~/elrs/ExpressLRS --device-url http://elrs_rx.local
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

MANUFACTURER = "radiomaster"
CATEGORY = "rx_dual"
TARGET_KEY = "nomad-rx-fcc"
LAYOUT_NAME = "Radiomaster Nomad RX FCC.json"


def looks_like_hardware_dir(path: Path) -> bool:
    return (path / "targets.json").is_file() and (path / "RX").is_dir() and (path / "TX").is_dir()


def find_hardware_dir(start: Path) -> Path:
    candidates = [
        start,
        start / "hardware",
        start / "src" / "hardware",
        start / "ExpressLRS" / "src" / "hardware",
    ]
    for candidate in candidates:
        if looks_like_hardware_dir(candidate):
            return candidate.resolve()
    raise SystemExit(
        "Could not find the ExpressLRS hardware directory. Pass the directory that contains targets.json, RX/, and TX/."
    )


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}") from exc


def check(condition: bool, ok: str, fail: str, failures: list[str]) -> None:
    if condition:
        print(f"OK:   {ok}")
    else:
        print(f"FAIL: {fail}")
        failures.append(fail)


def fetch_device_hardware(base_url: str) -> dict[str, Any]:
    base_url = base_url.rstrip("/")
    url = base_url + "/hardware.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not fetch {url}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Device returned invalid JSON from {url}: {exc}\nFirst 200 chars: {raw[:200]}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the Nomad RX FCC custom target and optional flashed device hardware.json.")
    parser.add_argument("path", nargs="?", default=".", help="ExpressLRS repo root, src directory, or src/hardware directory")
    parser.add_argument("--device-url", help="optional WebUI base URL, e.g. http://10.0.0.1 or http://elrs_rx.local")
    args = parser.parse_args()

    failures: list[str] = []
    hardware_dir = find_hardware_dir(Path(args.path).expanduser().resolve())
    targets_json = hardware_dir / "targets.json"
    layout_path = hardware_dir / "RX" / LAYOUT_NAME

    print(f"Checking local hardware directory: {hardware_dir}")
    check(layout_path.is_file(), f"layout file exists: {layout_path}", f"missing layout file: {layout_path}", failures)

    data = load_json(targets_json)
    entry = data.get(MANUFACTURER, {}).get(CATEGORY, {}).get(TARGET_KEY)
    check(entry is not None, f"target entry exists: {MANUFACTURER}.{CATEGORY}.{TARGET_KEY}", "target entry not found", failures)

    if entry:
        check(entry.get("product_name") == "RadioMaster Nomad RX FCC", "product name is RadioMaster Nomad RX FCC", "unexpected product_name", failures)
        check(entry.get("layout_file") == LAYOUT_NAME, "target points to Nomad RX layout", "target layout_file is wrong", failures)
        check(entry.get("firmware") == "Unified_ESP32_LR1121_RX", "target firmware is LR1121 RX", "target firmware is wrong", failures)
        check(entry.get("min_version") == "4.0.0", "target min_version is 4.0.0", "target min_version is wrong", failures)

    if layout_path.is_file():
        layout = load_json(layout_path)
        check(layout.get("misc_fan_en") == 2, "local RX layout contains misc_fan_en: 2", "local RX layout missing misc_fan_en: 2", failures)
        check(layout.get("serial_rx") == 3 and layout.get("serial_tx") == 1, "primary UART is GPIO3/GPIO1", "primary UART does not match expected GPIO3/GPIO1", failures)

    if args.device_url:
        print(f"Checking device hardware JSON: {args.device_url.rstrip('/')}/hardware.json")
        device_layout = fetch_device_hardware(args.device_url)
        check(device_layout.get("misc_fan_en") == 2, "device hardware.json contains misc_fan_en: 2", "device hardware.json missing misc_fan_en: 2", failures)
        check(device_layout.get("radio_busy") == 36, "device layout looks like Nomad/LR1121 pinout", "device layout does not look like expected Nomad pinout", failures)

    if failures:
        print("\nVerification failed.")
        return 1
    print("\nVerification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
