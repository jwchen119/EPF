#!/usr/bin/env python3
"""
Publish a firmware build to the web installer (docs/).

    python docs/firmware/add_version.py 1.2.0 \
        --notes-en "What changed" --notes-zh "改了什麼" [--server jwchen119/epf:1.2.0]

Copies firmware.bin and firmware.factory.bin from the PlatformIO build
directory into docs/firmware/v<version>/, writes the two ESP Web Tools
manifests and SHA256SUMS.txt, and puts the version at the top of
versions.json as the latest. Build the firmware first (`pio run` in Arduino/).
"""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parents[1] / 'Arduino' / '.pio' / 'build' / 'firebeetle2_esp32c6'

# Must match FW_NAME in Arduino/config.h: a frame that reports this name over
# Improv Serial is recognised as running this firmware, so the installer
# offers "Update" and writes without erasing the flash.
FIRMWARE_NAME = 'EPF photo frame firmware'

def manifest(name, version, parts, prompt_erase):
    return {
        'name': name,
        'version': version,
        # A frame without Improv (firmware before 1.2.0) counts as a new
        # install and would be erased first unless asked to prompt. The update
        # manifest prompts so the user can keep the NVS settings; the factory
        # one rewrites everything anyway.
        'new_install_prompt_erase': prompt_erase,
        'builds': [{'chipFamily': 'ESP32-C6', 'parts': parts}],
    }

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('version', help='for example 1.2.0 (no leading v)')
    parser.add_argument('--notes-en', default='', help='release notes shown on the page, English')
    parser.add_argument('--notes-zh', default='', help='release notes shown on the page, Traditional Chinese')
    parser.add_argument('--server', default=None, help='matching Docker image tag, default jwchen119/epf:<version>')
    parser.add_argument('--date', default=date.today().isoformat())
    args = parser.parse_args()

    app_src = BUILD / 'firmware.bin'
    factory_src = BUILD / 'firmware.factory.bin'
    for src in (app_src, factory_src):
        if not src.is_file():
            sys.exit(f'{src} not found: run `pio run` in Arduino/ first')

    target = HERE / f'v{args.version}'
    target.mkdir(exist_ok=True)
    shutil.copyfile(app_src, target / 'app.bin')
    shutil.copyfile(factory_src, target / 'factory.bin')

    with open(target / 'SHA256SUMS.txt', 'w', newline='\n') as sums:
        for name in ('factory.bin', 'app.bin'):
            digest = hashlib.sha256((target / name).read_bytes()).hexdigest()
            sums.write(f'{digest} *{name}\n')

    (target / 'update.json').write_text(json.dumps(manifest(
        FIRMWARE_NAME, args.version,
        [{'path': 'app.bin', 'offset': 0x10000}], True), indent=2) + '\n', newline='\n')
    (target / 'factory.json').write_text(json.dumps(manifest(
        'EPF photo frame firmware (new frame)', args.version,
        [{'path': 'factory.bin', 'offset': 0}], False), indent=2) + '\n', newline='\n')

    versions_path = HERE / 'versions.json'
    data = json.loads(versions_path.read_text(encoding='utf-8')) if versions_path.exists() \
        else {'latest': None, 'versions': []}
    data['versions'] = [v for v in data['versions'] if v['version'] != args.version]
    data['versions'].insert(0, {
        'version': args.version,
        'date': args.date,
        'notes': {'en': args.notes_en, 'zh-TW': args.notes_zh},
        'server': args.server or f'jwchen119/epf:{args.version}',
    })
    data['latest'] = args.version
    versions_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')

    print(f'published v{args.version} to {target}')
    print(f'  app.bin     {app_src.stat().st_size:>9} bytes -> 0x10000 (update.json)')
    print(f'  factory.bin {factory_src.stat().st_size:>9} bytes -> 0x0     (factory.json)')

if __name__ == '__main__':
    main()
