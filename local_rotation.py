"""No-repeat rotation for the local photo source.

Every image in the local folder is shown once (in random order) before any
image repeats. Shown filenames are persisted one per line so the cycle
survives server restarts. Newly added images join the current cycle; deleted
images are dropped from the shown set automatically.
"""

import os
import random
from typing import FrozenSet, Iterable, Optional, Tuple


def load_shown(path: str) -> FrozenSet[str]:
    """Return the filenames already shown in the current cycle (empty if unknown)."""
    try:
        with open(path, encoding='utf-8') as f:
            return frozenset(line.rstrip('\n') for line in f if line.strip())
    except FileNotFoundError:
        return frozenset()
    except OSError as e:
        print(f'[local_rotation] Could not read {path}: {e}; starting a fresh cycle')
        return frozenset()


def save_shown(path: str, shown: Iterable[str]) -> None:
    """Atomically persist the shown filenames. Failures are logged, never raised."""
    tmp_path = f'{path}.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.writelines(f'{name}\n' for name in sorted(shown))
        os.replace(tmp_path, path)
    except OSError as e:
        print(f'[local_rotation] Could not write {path}: {e}; images may repeat early')


def pick_next(
    candidates: Iterable[str], shown: FrozenSet[str], rng: Optional[random.Random] = None
) -> Tuple[str, FrozenSet[str]]:
    """Pick a random not-yet-shown image and return it with the updated shown set.

    When every candidate has been shown, a new cycle starts.
    """
    available_all = frozenset(candidates)
    if not available_all:
        raise ValueError('pick_next requires at least one candidate')

    still_present = shown & available_all
    remaining = available_all - still_present
    if not remaining:
        still_present, remaining = frozenset(), available_all

    chosen = (rng or random).choice(sorted(remaining))
    return chosen, still_present | {chosen}
