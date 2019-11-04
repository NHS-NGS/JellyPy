
"""
Tests for jellypy pyCIPAPI package.

Usage from /JellyPy/pyCIPAPI:
    pytest --pconfig=test/pyCIPAPI_config.ini
"""
import pytest

import jellypy.pyCIPAPI.config as config
import jellypy.pyCIPAPI.auth as auth


def test_import():
    """pyCIPAPI modules can be imported. Config string is readable from module."""
    assert bool(config.live_100k_data_base_url)

def test_config(pycipapi_config):
    """pyCIPAPI_config.ini accurately passed to pytest and readable"""
    assert bool(pycipapi_config['DEFAULT']['username']), "ERROR: Could not read pytestconfig file"

@pytest.fixture
def cipapi_session(pycipapi_config):
    auth_credentials = {
        'username': pycipapi_config['DEFAULT']['username'],
        'password': pycipapi_config['DEFAULT']['password']
    }
    return auth.AuthenticatedCIPAPISession(auth_credentials=auth_credentials)

def test_auth(cipapi_session):
    """auth.AuthenticatedCIPAPISession can authenticate users. Requires pre-populated config.ini
    file passed to pytest instance"""
    # Session auth time is set to false if error raised
    assert cipapi_session.auth_time != False
