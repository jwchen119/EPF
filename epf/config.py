"""
Runtime configuration: the defaults, the live values, and the watcher that picks
up edits made to config.yaml outside the web UI.

The live settings are held in one dict that is only ever updated in place. Other
modules import this module and read `immich()` when they need a value; they must
not copy values out at import time, or they would be frozen at whatever the
config was when the process started.
"""
import copy
import os

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

# Written by the settings page and watched for external edits. Not configurable:
# the path is baked into the image, so /config has to be bind-mounted.
CONFIG_PATH = '/config/config.yaml'

DEFAULT_CONFIG = {
    'immich': {
        'url': 'http://192.168.1.10',   # Immich server URL ("localhost" is forbidden)
        'album': 'default_album',       # Album name
        'rotation': 270,                # 0/90/180/270
        'enhanced': 1.3,                # From 0.0 .. 1.0
        'contrast': 0.9,                # From 0.0 .. 1.0
        'strength': 0.8,                # From 0.0 .. 1.0
        'display_mode': 'fill',         # fit/fill
        'image_order': 'random',        # random/newest
        'dither_mode': 'classic',       # classic/classic_cc, see epf/dither.py
        # Fine-tuning for classic_cc, see epf/dither.py: the share of the colour
        # correction applied, a chroma multiplier, and CIELAB offsets towards
        # warm (b*) and magenta (a*)
        'cc_strength': 1.0,             # 0.0 .. 1.0
        'cc_chroma': 1.0,               # 0.5 .. 1.5
        'cc_warmth': 0.0,               # -10 .. 10
        'cc_tint': 0.0,                 # -10 .. 10
        'sleep_start_hour': 23,         # Sleep start time 23:00 (11:00 PM)
        'sleep_start_minute': 0,
        'sleep_end_hour': 6,            # Sleep end time 6:00 (6:00 AM)
        'sleep_end_minute': 0,
        'wakeup_interval': 60,          # Minutes
    },
    'notify': {
        'enabled': False,               # Master switch
        'battery_threshold': 20,        # Warn at or below this percentage
        'min_interval_hours': 12,       # Never warn more often than this
        # Which linked services actually receive warnings. On by default, so
        # linking one is enough; untick to leave a linked service out.
        'use_telegram': True,
        'use_line': True,
    },
}

# Deep-copied on purpose: a shallow copy would share the inner dict with
# DEFAULT_CONFIG, so updating the live settings would rewrite the defaults and
# the reset button would restore whatever was last saved.
current = copy.deepcopy(DEFAULT_CONFIG)

# Holds tracking.txt and events.jsonl. No photos are ever written here.
photodir = os.getenv('IMMICH_PHOTO_DEST', '/photos')
os.makedirs(photodir, exist_ok=True)

def immich():
    """ The live Immich settings. Read it per use, never cache the result. """
    return current['immich']

def notify():
    """ The live notification settings """
    return current['notify']

def sections():
    """ The names of the configuration sections, in a stable order """
    return list(DEFAULT_CONFIG.keys())

def apply(new_config):
    """
    Adopt new settings, in place, so every module that read this dict sees them.
    Unknown keys are ignored and missing ones keep their current value.
    """
    for section in DEFAULT_CONFIG:
        incoming = (new_config or {}).get(section) or {}
        current[section].update(incoming)

    settings = current['immich']
    print("Configuration updated: URL = {url}, Album = {album}, angle = {rotation}, "
          "enhance = {enhanced}, contrast = {contrast}, strength = {strength}, "
          "display_mode = {display_mode}, image_order = {image_order}".format(**settings))

def read_file(path=CONFIG_PATH):
    """
    Load config.yaml, falling back to the defaults if it cannot be read.

    Sections added after a file was written are filled in from the defaults, so
    an older config.yaml does not have to be edited by hand.
    """
    loaded = copy.deepcopy(DEFAULT_CONFIG)
    try:
        with open(path, 'r') as handle:
            stored = yaml.safe_load(handle) or {}
    except Exception as error:
        print(f"Error reading config file: {error}")
        return loaded

    for section in loaded:
        loaded[section].update((stored.get(section) or {}))
    return loaded

def write_file(new_config, path=CONFIG_PATH):
    """ Persist settings. Raises, so the caller can report the failure. """
    with open(path, 'w') as handle:
        yaml.safe_dump(new_config, handle)

def ensure_file(path=CONFIG_PATH):
    """ Create the directory and a default config.yaml when they are missing """
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        try:
            os.makedirs(directory)
            print(f"Created config directory: {directory}")
        except Exception as error:
            print(f"Error creating config directory: {error}")

    if not os.path.exists(path):
        try:
            write_file(DEFAULT_CONFIG, path)
            print(f"Created default configuration file: {path}")
        except Exception as error:
            print(f"Error creating config file: {error}")

class ConfigFileHandler(FileSystemEventHandler):
    """ Reloads the configuration when config.yaml changes on disk """

    def __init__(self, config_path, on_change):
        self.config_path = config_path
        self.on_change = on_change
        ensure_file(config_path)

    def on_modified(self, event):
        if event.src_path == self.config_path:
            print("File modification detected, reloading configuration...")
            self.on_change(read_file(self.config_path))

def start_watcher(on_change, config_path=CONFIG_PATH):
    """ Watch the config directory and hand new settings to on_change """
    handler = ConfigFileHandler(config_path, on_change)
    observer = Observer()
    observer.schedule(handler, path=os.path.dirname(config_path), recursive=False)
    observer.start()
    return observer
