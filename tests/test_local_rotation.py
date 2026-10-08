"""Tests for no-repeat rotation of the local photo source.

Every image in the local folder is shown once before any image repeats.
Shown filenames are persisted so the cycle survives server restarts.
"""

import random

import pytest
from PIL import Image

import app as app_module
from local_rotation import load_shown, pick_next, save_shown

# ---------------------------------------------------------------------------
# pick_next: pure selection logic
# ---------------------------------------------------------------------------


def test_pick_next_never_picks_already_shown():
    candidates = ['a.jpg', 'b.jpg', 'c.jpg']
    for seed in range(50):
        chosen, _ = pick_next(candidates, frozenset({'a.jpg', 'b.jpg'}), random.Random(seed))
        assert chosen == 'c.jpg'


def test_pick_next_adds_choice_to_shown():
    chosen, shown = pick_next(['a.jpg', 'b.jpg'], frozenset({'a.jpg'}), random.Random(0))
    assert chosen == 'b.jpg'
    assert shown == frozenset({'a.jpg', 'b.jpg'})


def test_pick_next_does_not_mutate_input():
    original = frozenset({'a.jpg'})
    pick_next(['a.jpg', 'b.jpg'], original, random.Random(0))
    assert original == frozenset({'a.jpg'})


def test_full_cycle_shows_every_image_exactly_once():
    candidates = [f'img_{i}.jpg' for i in range(20)]
    rng = random.Random(42)
    shown = frozenset()
    seen = []
    for _ in candidates:
        chosen, shown = pick_next(candidates, shown, rng)
        seen.append(chosen)
    assert sorted(seen) == sorted(candidates)


def test_cycle_restarts_when_everything_was_shown():
    candidates = ['a.jpg', 'b.jpg']
    chosen, shown = pick_next(candidates, frozenset(candidates), random.Random(0))
    assert chosen in candidates
    assert shown == frozenset({chosen})


def test_new_images_join_the_current_cycle():
    chosen, _ = pick_next(['a.jpg', 'b.jpg', 'new.jpg'], frozenset({'a.jpg', 'b.jpg'}), random.Random(0))
    assert chosen == 'new.jpg'


def test_deleted_images_are_dropped_from_shown():
    _, shown = pick_next(['a.jpg', 'b.jpg'], frozenset({'a.jpg', 'gone.jpg'}), random.Random(0))
    assert shown == frozenset({'a.jpg', 'b.jpg'})


def test_pick_next_rejects_empty_candidates():
    with pytest.raises(ValueError):
        pick_next([], frozenset(), random.Random(0))


# ---------------------------------------------------------------------------
# load_shown / save_shown: persistence
# ---------------------------------------------------------------------------


def test_load_shown_missing_file_returns_empty(tmp_path):
    assert load_shown(str(tmp_path / 'nope.txt')) == frozenset()


def test_save_then_load_roundtrip(tmp_path):
    path = str(tmp_path / 'local_tracking.txt')
    names = frozenset({'a.jpg', 'IMG_0060 (1).JPG', '2015 Legoland Aaron.jpg'})
    save_shown(path, names)
    assert load_shown(path) == names


def test_load_shown_ignores_blank_lines(tmp_path):
    path = tmp_path / 'local_tracking.txt'
    path.write_text('a.jpg\n\n  \nb.jpg\n')
    assert load_shown(str(path)) == frozenset({'a.jpg', 'b.jpg'})


def test_save_shown_unwritable_path_does_not_raise(tmp_path):
    save_shown(str(tmp_path / 'missing_dir' / 'local_tracking.txt'), frozenset({'a.jpg'}))


# ---------------------------------------------------------------------------
# /download integration: local mode cycles without repeats
# ---------------------------------------------------------------------------


@pytest.fixture
def multi_image_client(tmp_path, monkeypatch):
    photos = tmp_path / 'local'
    photos.mkdir()
    for i in range(3):
        Image.new('RGB', (120, 160), (255, 255, 255)).save(str(photos / f'img_{i}.jpg'), 'JPEG')

    tracking = tmp_path / 'local_tracking.txt'
    monkeypatch.setattr(app_module, 'localdir', str(photos))
    monkeypatch.setattr(app_module, 'local_tracking_file', str(tracking))
    monkeypatch.setattr(app_module, 'APP_PASSWORD', '')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c, tracking


def _served_name(response):
    disposition = response.headers['Content-Disposition']
    return disposition.split('image_')[1].split('.bin')[0]


def test_download_cycles_through_all_local_images(multi_image_client):
    client, tracking = multi_image_client
    served = [_served_name(client.get('/download')) for _ in range(3)]
    assert sorted(served) == ['img_0', 'img_1', 'img_2']
    assert load_shown(str(tracking)) == frozenset({'img_0.jpg', 'img_1.jpg', 'img_2.jpg'})


def test_download_starts_new_cycle_after_all_shown(multi_image_client):
    client, tracking = multi_image_client
    for _ in range(3):
        client.get('/download')
    response = client.get('/download')
    assert response.status_code == 200
    assert len(load_shown(str(tracking))) == 1
