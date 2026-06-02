"""Tests for Phase 8: HTTP Basic Auth (AUTH-01..AUTH-08).

These tests target require_auth and APP_PASSWORD which Plan 08-02 will add to app.py.
They MUST fail (RED) until that plan lands — that is the TDD contract.

AUTH-01: require_auth passes request through when APP_PASSWORD is empty (opt-in)
AUTH-02: missing credentials -> 401 + WWW-Authenticate: Basic realm="EPF"
AUTH-02: wrong password -> 401
AUTH-03: all four routes (/, /setting, /download, /sleep) require auth
AUTH-04: APP_PASSWORD read from environment
AUTH-06: correct credentials -> route returns 200 (admin:secret)
AUTH-08: failed auth attempt logged at WARNING level
"""

import base64
import importlib
import logging

import pytest

import app as app_module


def _basic_header(user='admin', password='secret'):
    creds = base64.b64encode(f'{user}:{password}'.encode()).decode()
    return {'Authorization': f'Basic {creds}'}


@pytest.fixture
def auth_client(monkeypatch):
    """Test client with APP_PASSWORD='secret' set (auth enabled)."""
    monkeypatch.setattr(app_module, 'APP_PASSWORD', 'secret')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def open_client(monkeypatch):
    """Test client with APP_PASSWORD='' (auth disabled / opt-in off)."""
    monkeypatch.setattr(app_module, 'APP_PASSWORD', '')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def test_protected_route_no_credentials_returns_401(auth_client):
    """AUTH-02: missing credentials on a protected route returns 401."""
    resp = auth_client.get('/setting')
    assert resp.status_code == 401


def test_401_includes_www_authenticate_header(auth_client):
    """AUTH-02: 401 response includes WWW-Authenticate: Basic realm="EPF"."""
    resp = auth_client.get('/setting')
    assert 'WWW-Authenticate' in resp.headers
    assert resp.headers['WWW-Authenticate'] == 'Basic realm="EPF"'


def test_wrong_password_returns_401(auth_client):
    """AUTH-02: wrong password returns 401."""
    resp = auth_client.get('/setting', headers=_basic_header(password='wrong'))
    assert resp.status_code == 401


def test_protected_route_correct_credentials_returns_200(auth_client):
    """AUTH-06: correct credentials (admin:secret) allow access and return 200."""
    resp = auth_client.get('/setting', headers=_basic_header())
    assert resp.status_code == 200


def test_no_password_set_allows_access(open_client):
    """AUTH-01: when APP_PASSWORD is empty the route is openly accessible (opt-in)."""
    resp = open_client.get('/setting')
    assert resp.status_code == 200


@pytest.mark.parametrize('route', ['/', '/setting', '/download', '/sleep'])
def test_all_routes_require_auth(auth_client, route):
    """AUTH-03: all four routes return 401 when no credentials are supplied."""
    resp = auth_client.get(route)
    assert resp.status_code == 401


def test_app_password_loaded_from_env(monkeypatch):
    """AUTH-04: APP_PASSWORD is read from the APP_PASSWORD environment variable."""
    monkeypatch.setenv('APP_PASSWORD', 'fromenv')
    importlib.reload(app_module)
    assert app_module.APP_PASSWORD == 'fromenv'


def test_failed_auth_is_logged(auth_client, caplog):
    """AUTH-08: a failed authentication attempt is logged at WARNING level."""
    with caplog.at_level(logging.WARNING):
        auth_client.get('/setting', headers=_basic_header(password='wrong'))
    assert any(record.levelname == 'WARNING' and 'uth' in record.getMessage() for record in caplog.records)
