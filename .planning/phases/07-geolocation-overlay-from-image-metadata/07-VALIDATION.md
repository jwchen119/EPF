---
phase: 7
slug: geolocation-overlay-from-image-metadata
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-01
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (installed, no version pin) |
| **Config file** | none — pytest discovers `tests/` automatically |
| **Quick run command** | `pytest tests/test_geo_overlay.py -x` |
| **Full suite command** | `pytest tests/ -x` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_geo_overlay.py -x`
- **After every plan wave:** Run `pytest tests/ -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-??-01 | 01 | 0 | GEO-01..12 | unit/integration | `pytest tests/test_geo_overlay.py -x` | ❌ W0 | ⬜ pending |
| 7-??-02 | 01 | 1 | GEO-01,02,03 | unit | `pytest tests/test_geo_overlay.py::test_extract_gps_from_exif tests/test_geo_overlay.py::test_extract_gps_no_gps_tag tests/test_geo_overlay.py::test_extract_gps_no_exif_method -x` | ❌ W0 | ⬜ pending |
| 7-??-03 | 01 | 1 | GEO-07,08 | unit | `pytest tests/test_geo_overlay.py::test_geocache_hit_no_network_call tests/test_geo_overlay.py::test_geocache_stores_null_on_error -x` | ❌ W0 | ⬜ pending |
| 7-??-04 | 01 | 1 | GEO-04,05,06 | unit | `pytest tests/test_geo_overlay.py::test_location_from_immich_exif tests/test_geo_overlay.py::test_location_immich_empty_fields tests/test_geo_overlay.py::test_location_from_local_gps -x` | ❌ W0 | ⬜ pending |
| 7-??-05 | 01 | 2 | GEO-09,10,11,12 | integration | `pytest tests/test_geo_overlay.py::test_scale_img_geo_plus_date_overlay tests/test_geo_overlay.py::test_scale_img_date_fallback tests/test_geo_overlay.py::test_scale_img_location_only tests/test_geo_overlay.py::test_scale_img_no_overlay -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_geo_overlay.py` — stubs for GEO-01 through GEO-12 (entire new test file)
- [ ] `tests/conftest.py` additions — `synthetic_gps_image` fixture (PIL Image with embedded GPSInfo EXIF), `mock_geo_cache_dir` fixture (tmp_path-based cache dir)

*Existing `conftest.py` fixtures `blank_rgb_image`, `large_rgb_image`, `dejavu_or_default_font` are reusable for integration tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Nominatim network call returns city+country | D-03, D-09 | Requires network; would hit real OSM API at 1 req/sec | Run `python -c "from app import reverse_geocode_cached; print(reverse_geocode_cached(48.1351, 11.5820))"` and verify `"Munich, Germany"` (or similar) |
| geo_cache.json written to IMMICH_PHOTO_DEST | D-10 | Requires env var and real file system setup | Set `IMMICH_PHOTO_DEST=/tmp/test_photos`, run geocode call, verify `ls /tmp/test_photos/geo_cache.json` |
| Combined overlay renders correctly in browser | D-04, D-19 | Visual check — pixel content | Serve app, open image endpoint, verify `"Munich, Germany • 05.01.2022"` text appears on photo |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
