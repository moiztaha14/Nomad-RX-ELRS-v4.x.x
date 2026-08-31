#!/usr/bin/env python3
"""
setup_nomad_rx.py

Automated Windows setup for the RadioMaster Nomad-as-RX custom ExpressLRS v4 target.

Fork of ndd91/nomad-elrs-v4-rx — this script replaces the old manual
step-by-step README workflow with a single guided run.

Run with:
    python setup_nomad_rx.py
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_INSTALL_PATH = r"C:\elrs\ExpressLRS"
DEFAULT_TAG = "4.0.1"
ELRS_REPO_URL = "https://github.com/ExpressLRS/ExpressLRS.git"
TARGETS_REPO_URL = "https://github.com/ExpressLRS/targets.git"

MANUFACTURER = "radiomaster"
CATEGORY = "rx_dual"
TARGET_KEY = "nomad-rx-fcc"
LAYOUT_NAME = "Radiomaster Nomad RX FCC.json"


def stage_header(n: int, title: str) -> None:
    print()
    print(f"===== Stage {n}: {title} =====")


def tool_available(name: str) -> bool:
    return shutil.which(name) is not None


def ask_path(prompt: str, default: str) -> Path:
    raw = input(f"{prompt} [default: {default}]: ").strip()
    chosen = raw if raw else default
    return Path(chosen)


def stage1_setup_check() -> Path:
    stage_header(1, "Setup check")

    missing = []
    for tool in ("git", "python"):
        if tool_available(tool):
            print(f"OK:   {tool} found")
        else:
            print(f"FAIL: {tool} not found on PATH")
            missing.append(tool)

    # pio (PlatformIO) is installed later via pip into a venv (Stage 6),
    # so it's expected to be missing at this point. We just note that.
    if tool_available("pio"):
        print("OK:   pio found (already installed globally)")
    else:
        print("INFO: pio not found yet — this is expected, it will be installed in Stage 6")

    if missing:
        print()
        print("The following required tools are missing and must be installed first:")
        for tool in missing:
            print(f"  - {tool}")
        print("Install them, then re-run this script.")
        sys.exit(1)

    print()
    install_path = ask_path(
        "Where should ExpressLRS be installed?",
        DEFAULT_INSTALL_PATH,
    )
    print(f"Using install path: {install_path}")
    return install_path


def run(cmd: list[str], cwd: Path | None = None, capture: bool = False, env: dict | None = None) -> str:
    """Run a command, exit the script with a clear message if it fails."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=capture,
        env=env,
    )
    if result.returncode != 0:
        print(f"FAIL: command failed: {' '.join(cmd)}")
        if capture and result.stderr:
            print(result.stderr.strip())
        sys.exit(1)
    return result.stdout if capture else ""


def get_v4_tags(install_path: Path) -> list[str]:
    run(["git", "fetch", "--tags"], cwd=install_path)
    raw = run(["git", "tag", "-l", "4.*"], cwd=install_path, capture=True)
    tags = [t.strip() for t in raw.splitlines() if t.strip()]

    def sort_key(tag: str) -> tuple[int, int, int, int, int]:
        # Matches "4.0.1" or "4.0.0-RC2". RC tags sort BEFORE their
        # matching release (RC1 < RC2 < ... < final release).
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-RC(\d+))?$", tag)
        if not m:
            return (0, 0, 0, 0, 0)
        major, minor, patch, rc = m.groups()
        is_release = 1 if rc is None else 0
        rc_num = int(rc) if rc is not None else 0
        return (int(major), int(minor), int(patch), is_release, rc_num)

    return sorted(tags, key=sort_key)


def ask_tag(tags: list[str]) -> str:
    print()
    print("Available ExpressLRS v4.x tags:")
    for i, tag in enumerate(tags, start=1):
        marker = "  <- default" if tag == DEFAULT_TAG else ""
        print(f"  {i}. {tag}{marker}")

    while True:
        raw = input(
            f"Enter a tag name, or a number from the list [default: {DEFAULT_TAG}]: "
        ).strip()

        if not raw:
            chosen = DEFAULT_TAG
        elif raw.isdigit() and 1 <= int(raw) <= len(tags):
            chosen = tags[int(raw) - 1]
        else:
            chosen = raw

        if chosen in tags:
            return chosen

        print(f"'{chosen}' is not a valid tag in this repo. Try again.")


def stage2_get_expresslrs(install_path: Path) -> str:
    stage_header(2, "Get ExpressLRS firmware")

    if (install_path / ".git").is_dir():
        print(f"INFO: existing git repo found at {install_path}, reusing it")
    else:
        install_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Cloning ExpressLRS into {install_path} ...")
        run(["git", "clone", "--recursive", ELRS_REPO_URL, str(install_path)])
        print("OK:   clone complete")

    print("Fetching tags ...")
    tags = get_v4_tags(install_path)
    if not tags:
        print("FAIL: no 4.x tags found in the repo — something is wrong.")
        sys.exit(1)

    tag = ask_tag(tags)
    print(f"Using tag: {tag}")

    print(f"Checking out {tag} ...")
    run(["git", "checkout", tag], cwd=install_path)
    print("Updating submodules ...")
    run(["git", "submodule", "update", "--init", "--recursive"], cwd=install_path)
    print("OK:   ExpressLRS checked out and submodules updated")

    return tag


def stage3_get_targets(install_path: Path) -> Path:
    stage_header(3, "Get the targets repo")

    hardware_dir = install_path / "src" / "hardware"

    if hardware_dir.is_dir() and any(hardware_dir.iterdir()):
        print(f"INFO: {hardware_dir} already exists and is not empty, reusing it")
    else:
        print(f"Cloning ExpressLRS/targets into {hardware_dir} ...")
        run(["git", "clone", TARGETS_REPO_URL, str(hardware_dir)])
        print("OK:   targets repo cloned into src/hardware")

    if not (hardware_dir / "targets.json").is_file():
        print(f"FAIL: {hardware_dir / 'targets.json'} not found — clone may have failed.")
        sys.exit(1)
    if not (hardware_dir / "RX").is_dir():
        print(f"FAIL: {hardware_dir / 'RX'} not found — clone may have failed.")
        sys.exit(1)

    print("OK:   hardware directory looks valid (targets.json + RX/ present)")
    return hardware_dir


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: invalid JSON in {path}: {exc}")
        sys.exit(1)


def validate_layout(layout: dict) -> None:
    if layout.get("misc_fan_en") != 2:
        print("FAIL: RX layout validation failed: expected misc_fan_en: 2")
        sys.exit(1)
    required = ["radio_busy", "radio_dio1", "radio_nss", "radio_busy_2", "radio_dio1_2", "radio_nss_2"]
    for key in required:
        if key not in layout:
            print(f"FAIL: RX layout validation failed: missing {key}")
            sys.exit(1)


def validate_entry(entry: dict) -> None:
    if entry.get("firmware") != "Unified_ESP32_LR1121_RX":
        print("FAIL: target entry validation failed: firmware must be Unified_ESP32_LR1121_RX")
        sys.exit(1)
    if entry.get("layout_file") != LAYOUT_NAME:
        print(f"FAIL: target entry validation failed: layout_file must be {LAYOUT_NAME}")
        sys.exit(1)


def stage4_inject_target(hardware_dir: Path) -> None:
    stage_header(4, "Inject the Nomad RX target")

    layout_src = package_dir() / "data" / "RX" / LAYOUT_NAME
    entry_src = package_dir() / "data" / "targets-radiomaster-rx_dual-entry.json"

    if not layout_src.is_file():
        print(f"FAIL: missing package file: {layout_src}")
        sys.exit(1)
    if not entry_src.is_file():
        print(f"FAIL: missing package file: {entry_src}")
        sys.exit(1)

    layout = load_json(layout_src)
    target_blob = load_json(entry_src)
    if TARGET_KEY not in target_blob:
        print(f"FAIL: target entry file must contain key {TARGET_KEY}")
        sys.exit(1)
    entry = target_blob[TARGET_KEY]

    validate_layout(layout)
    validate_entry(entry)

    targets_json = hardware_dir / "targets.json"
    layout_dst = hardware_dir / "RX" / LAYOUT_NAME

    data = load_json(targets_json)
    radiomaster = data.setdefault(MANUFACTURER, {"name": "RadioMaster"})
    radiomaster.setdefault("name", "RadioMaster")
    category = radiomaster.setdefault(CATEGORY, {})
    action = "updated" if TARGET_KEY in category else "added"

    timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = targets_json.with_name(f"targets.json.bak-nomad-rx-{timestamp}")
    shutil.copy2(targets_json, backup)
    print(f"OK:   backed up targets.json -> {backup.name}")

    layout_dst.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    category[TARGET_KEY] = entry
    targets_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"OK:   {action} target {MANUFACTURER}.{CATEGORY}.{TARGET_KEY}")
    print(f"OK:   wrote layout file -> {layout_dst}")

    # Read back exactly what was written, to be sure.
    written_layout = load_json(layout_dst)
    written_targets = load_json(targets_json)
    written_entry = written_targets[MANUFACTURER][CATEGORY][TARGET_KEY]
    validate_layout(written_layout)
    validate_entry(written_entry)
    print("OK:   re-read and verified the written files")
    print("Build selector path: RadioMaster -> rx_dual -> RadioMaster Nomad RX FCC")


def check(condition: bool, ok_msg: str, fail_msg: str, failures: list) -> None:
    if condition:
        print(f"OK:   {ok_msg}")
    else:
        print(f"FAIL: {fail_msg}")
        failures.append(fail_msg)


def stage5_verify_local(hardware_dir: Path) -> None:
    stage_header(5, "Verify local install")

    failures: list = []
    targets_json = hardware_dir / "targets.json"
    layout_path = hardware_dir / "RX" / LAYOUT_NAME

    check(layout_path.is_file(), f"layout file exists: {layout_path.name}",
          f"missing layout file: {layout_path}", failures)

    data = load_json(targets_json)
    entry = data.get(MANUFACTURER, {}).get(CATEGORY, {}).get(TARGET_KEY)
    check(entry is not None, f"target entry exists: {MANUFACTURER}.{CATEGORY}.{TARGET_KEY}",
          "target entry not found in targets.json", failures)

    if entry:
        check(entry.get("product_name") == "RadioMaster Nomad RX FCC",
              "product name is RadioMaster Nomad RX FCC", "unexpected product_name", failures)
        check(entry.get("layout_file") == LAYOUT_NAME,
              "target points to Nomad RX layout", "target layout_file is wrong", failures)
        check(entry.get("firmware") == "Unified_ESP32_LR1121_RX",
              "target firmware is LR1121 RX", "target firmware is wrong", failures)

    if layout_path.is_file():
        layout = load_json(layout_path)
        check(layout.get("misc_fan_en") == 2,
              "RX layout contains misc_fan_en: 2", "RX layout missing misc_fan_en: 2", failures)
        check(layout.get("serial_rx") == 3 and layout.get("serial_tx") == 1,
              "primary UART is GPIO3/GPIO1", "primary UART does not match expected GPIO3/GPIO1", failures)

    if failures:
        print()
        print("FAIL: local verification failed:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("Local verification passed.")


REQUIRED_PACKAGES = ["platformio", "dronecan", "setuptools", "empy==3.3.4", "pexpect", "intelhex"]

REG_DOMAINS = {
    "1": ("FCC 915MHz (US)", "Regulatory_Domain_FCC_915"),
    "2": ("EU 868MHz", "Regulatory_Domain_EU_868"),
    "3": ("EU 868MHz (R9)", "Regulatory_Domain_EU_868_R9"),
    "4": ("AU 915MHz", "Regulatory_Domain_AU_915"),
    "5": ("IN 866MHz", "Regulatory_Domain_IN_866"),
}
DEFAULT_REG_DOMAIN_KEY = "1"

BUILD_ENV = "Unified_ESP32_LR1121_RX_via_UART"


def venv_paths(install_path: Path) -> tuple[Path, Path, Path]:
    venv_dir = install_path / ".venv"
    scripts_dir = venv_dir / "Scripts"
    return venv_dir, scripts_dir / "python.exe", scripts_dir / "pio.exe"


def stage6_python_env(install_path: Path) -> tuple[Path, Path]:
    stage_header(6, "Python environment + build tools")

    venv_dir, venv_python, venv_pio = venv_paths(install_path)

    if venv_python.is_file():
        print(f"INFO: existing virtual environment found at {venv_dir}, reusing it")
    else:
        print(f"Creating virtual environment at {venv_dir} ...")
        run([sys.executable, "-m", "venv", str(venv_dir)])
        print("OK:   virtual environment created")

    print("Upgrading pip ...")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "--no-cache-dir", "pip"])
    print(f"Installing packages: {', '.join(REQUIRED_PACKAGES)} ...")
    run([str(venv_python), "-m", "pip", "install", "--no-cache-dir", *REQUIRED_PACKAGES])
    print("OK:   packages installed")

    if not venv_pio.is_file():
        print(f"FAIL: pio.exe not found at {venv_pio} after install.")
        sys.exit(1)
    print(f"OK:   pio available at {venv_pio}")

    return venv_python, venv_pio


def ask_nonempty(prompt: str) -> str:
    while True:
        val = input(prompt).strip()
        if val:
            return val
        print("This can't be empty, try again.")


def ask_yes_no(prompt: str, default_yes: bool) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    raw = input(f"{prompt} {suffix}: ").strip().lower()
    if not raw:
        return default_yes
    return raw.startswith("y")


def ask_regulatory_domain() -> str:
    print()
    print("Regulatory domain:")
    for key, (label, _) in REG_DOMAINS.items():
        marker = "  <- default" if key == DEFAULT_REG_DOMAIN_KEY else ""
        print(f"  {key}. {label}{marker}")
    while True:
        raw = input(f"Choose a number [default: {DEFAULT_REG_DOMAIN_KEY}]: ").strip()
        chosen = raw if raw else DEFAULT_REG_DOMAIN_KEY
        if chosen in REG_DOMAINS:
            return REG_DOMAINS[chosen][1]
        print("Not a valid choice, try again.")


def ask_extra_defines() -> list[str]:
    print()
    print("Any additional custom defines? Enter one per line, blank line to finish.")
    print('(e.g. -DSOME_DEFINE=1)')
    defines = []
    while True:
        line = input("> ").strip()
        if not line:
            break
        defines.append(line)
    return defines


def stage7_build_config(install_path: Path) -> str:
    """Returns 'wifi' or 'ap' depending on how the device will be reachable."""
    stage_header(7, "Build configuration")

    domain_define = ask_regulatory_domain()
    binding_phrase = ask_nonempty("Enter your binding phrase (same on both ELRS devices): ")

    set_wifi_now = ask_yes_no(
        "Set a home Wi-Fi SSID/password now? (No = use the device's built-in AP instead)",
        default_yes=False,
    )

    ssid = password = None
    if set_wifi_now:
        ssid = ask_nonempty("Wi-Fi SSID: ")
        password = ask_nonempty("Wi-Fi password: ")

    extra_defines = ask_extra_defines()

    lines = [f"-D{domain_define}", f'-DMY_BINDING_PHRASE="{binding_phrase}"']
    if set_wifi_now:
        lines.append(f'-DHOME_WIFI_SSID="{ssid}"')
        lines.append(f'-DHOME_WIFI_PASSWORD="{password}"')
    else:
        lines.append('# -DHOME_WIFI_SSID="YourWiFiSSID"')
        lines.append('# -DHOME_WIFI_PASSWORD="YourWiFiPassword"')
    lines.extend(extra_defines)

    src_dir = install_path / "src"
    defines_path = src_dir / "super_defines.txt"
    defines_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK:   wrote {defines_path}")

    return "wifi" if set_wifi_now else "ap"


def stage8_build(install_path: Path, venv_pio: Path) -> None:
    stage_header(8, "Build")

    src_dir = install_path / "src"
    print(f"Running: pio run -e {BUILD_ENV}")
    print("You'll be asked to choose a firmware configuration during the build —")
    print(f"select \"RadioMaster Nomad RX FCC\".")
    print("(this can take a while on first build)")
    run([str(venv_pio), "run", "-e", BUILD_ENV], cwd=src_dir)
    print("OK:   build complete")


def parse_com_ports(pio_device_list_output: str) -> list[str]:
    ports = []
    for line in pio_device_list_output.splitlines():
        line = line.strip()
        if re.match(r"^COM\d+$", line):
            ports.append(line)
    return ports


def scan_com_ports(venv_pio: Path) -> list[str]:
    output = run([str(venv_pio), "device", "list"], capture=True)
    print(output)
    return parse_com_ports(output)


def ask_com_port(venv_pio: Path) -> str:
    while True:
        ports = scan_com_ports(venv_pio)
        if not ports:
            print("No COM ports found.")
            if ask_yes_no("Re-scan for devices?", default_yes=True):
                continue
            print("Cannot continue without a device connected.")
            sys.exit(1)

        print("Detected COM ports:")
        for i, port in enumerate(ports, start=1):
            print(f"  {i}. {port}")

        raw = input("Choose a port by number, or press Enter to re-scan: ").strip()
        if not raw:
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(ports):
            return ports[int(raw) - 1]
        print("Not a valid choice, try again.")


def stage9_flash(install_path: Path, venv_pio: Path, connect_mode: str) -> None:
    stage_header(9, "Flash")

    input("Connect the Nomad to this PC over USB now, then press Enter to continue...")

    port = ask_com_port(venv_pio)
    print(f"Using port: {port}")

    src_dir = install_path / "src"
    print("Note: you'll be asked to choose the firmware configuration again during")
    print("erase/upload — select \"RadioMaster Nomad RX FCC\" each time.")

    if not ask_yes_no(f"Erase flash on {port} now? This is destructive.", default_yes=False):
        print("Skipping erase and flash. You can re-run this stage later.")
        return
    print(f"Erasing {port} ...")
    run([str(venv_pio), "run", "-e", BUILD_ENV, "-t", "erase", "--upload-port", port],
        cwd=src_dir)
    print("OK:   erase complete")

    if not ask_yes_no(f"Flash firmware to {port} now?", default_yes=True):
        print("Skipping flash. You can re-run this stage later.")
        return
    print(f"Flashing {port} ...")
    run([str(venv_pio), "run", "-e", BUILD_ENV, "-t", "upload", "--upload-port", port],
        cwd=src_dir)
    print("OK:   flash complete")

    print()
    print("Power-cycle the Nomad, then connect to the RX WebUI:")
    if connect_mode == "wifi":
        print("  http://elrs_rx.local/   (or check your router for its IP)")
    else:
        print("  Connect to the device's own Wi-Fi AP, then open http://10.0.0.1/")


def read_local_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def fetch_hardware_json(ip: str):
    url = f"http://{ip.rstrip('/')}/hardware.json"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"FAIL: could not reach {url}: {exc}")
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print(f"FAIL: {url} did not return valid JSON — this may not be an ELRS device.")
        return None


def apply_force_fan_patch(install_path: Path) -> None:
    thermal_file = install_path / "src" / "lib" / "THERMAL" / "devThermal.cpp"
    old_str = "pinMode(GPIO_PIN_FAN_EN, OUTPUT);\n        enabled = true;"
    new_str = (
        "pinMode(GPIO_PIN_FAN_EN, OUTPUT);\n"
        "#ifdef NOMAD_RX_FORCE_FAN\n"
        "        digitalWrite(GPIO_PIN_FAN_EN, HIGH);\n"
        "#endif\n"
        "        enabled = true;"
    )

    content = thermal_file.read_text(encoding="utf-8")
    if "NOMAD_RX_FORCE_FAN" in content:
        print(f"INFO: {thermal_file.name} already patched, skipping")
        return
    if content.count(old_str) != 1:
        print(f"FAIL: could not safely patch {thermal_file} (expected text not found).")
        print("Apply the fallback manually — see data/patches/force_fan_on_snippet.txt")
        sys.exit(1)

    thermal_file.write_text(content.replace(old_str, new_str), encoding="utf-8")
    print(f"OK:   patched {thermal_file} with the force-fan fallback")

    defines_path = install_path / "src" / "super_defines.txt"
    with defines_path.open("a", encoding="utf-8") as f:
        f.write("-DNOMAD_RX_FORCE_FAN\n")
    print(f"OK:   added -DNOMAD_RX_FORCE_FAN to {defines_path}")


def stage10_post_flash(install_path: Path, venv_pio: Path, connect_mode: str) -> None:
    stage_header(10, "Post-flash device check")

    while True:
        ip = input("Device IP [default: 10.0.0.1]: ").strip() or "10.0.0.1"
        data = fetch_hardware_json(ip)

        if data is None:
            if ask_yes_no("Try a different IP?", default_yes=True):
                continue
            print("Skipping device check.")
            return

        if "radio_busy" not in data:
            print(f"FAIL: {ip} responded, but this doesn't look like an ELRS device's hardware.json.")
            if ask_yes_no("Try a different IP?", default_yes=True):
                continue
            return

        if data.get("misc_fan_en") != 2:
            print("FAIL: reached an ELRS device, but misc_fan_en is missing.")
            print("The wrong firmware config may have loaded — check Stage 8/9 output.")
            return

        print("OK:   hardware.json contains misc_fan_en: 2")
        break

    fan_ok = ask_yes_no("Is the fan actually spinning under load?", default_yes=True)
    if fan_ok:
        print()
        print("All done — Nomad RX flashed, configured, and fan confirmed working.")
        return

    print()
    print("Fan pin is present but not spinning. Applying the force-fan fallback and rebuilding.")
    apply_force_fan_patch(install_path)
    stage8_build(install_path, venv_pio)
    stage9_flash(install_path, venv_pio, connect_mode)
    stage10_post_flash(install_path, venv_pio, connect_mode)


def main() -> int:
    print("Nomad RX ELRS v4.x.x — automated setup (Windows)")
    install_path = stage1_setup_check()
    tag = stage2_get_expresslrs(install_path)
    hardware_dir = stage3_get_targets(install_path)
    stage4_inject_target(hardware_dir)
    stage5_verify_local(hardware_dir)
    venv_python, venv_pio = stage6_python_env(install_path)
    connect_mode = stage7_build_config(install_path)
    stage8_build(install_path, venv_pio)
    stage9_flash(install_path, venv_pio, connect_mode)
    stage10_post_flash(install_path, venv_pio, connect_mode)

    print()
    print("Setup complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
