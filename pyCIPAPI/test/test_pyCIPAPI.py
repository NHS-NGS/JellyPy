
"""
Tests for jellypy pyCIPAPI package.

Usage from /JellyPy/pyCIPAPI:
    pytest --pconfig=test/pyCIPAPI_config.ini
"""
import pytest

import jellypy.pyCIPAPI.config as config
import jellypy.pyCIPAPI.auth as auth
import jellypy.pyCIPAPI.interpretation_requests as irs


def test_import():
    """pyCIPAPI modules can be imported. Config string is readable from module."""
    assert bool(config.live_100k_data_base_url)

def test_config(jellypy_config):
    """pyCIPAPI_config.ini accurately passed to pytest and readable"""
    assert bool(jellypy_config['pyCIPAPI']['username']), "ERROR: Could not read pytestconfig file"

@pytest.fixture
def cipapi_session(jellypy_config):
    auth_credentials = {
        'username': jellypy_config['pyCIPAPI']['username'],
        'password': jellypy_config['pyCIPAPI']['password']
    }
    return auth.AuthenticatedCIPAPISession(auth_credentials=auth_credentials)

def test_auth(cipapi_session):
    """auth.AuthenticatedCIPAPISession can authenticate users. Requires pre-populated config.ini
    file passed to pytest instance"""
    # Session auth time is set to false if error raised
    assert cipapi_session.auth_time != False

class TestIRTools():
    def test_get_irjson(self, cipapi_session):
        """Interpretation request jsons can be downloaded from the CIPAPI"""
        data = irs.get_ir_json(2202,2,cipapi_session,{'reports_v6':True})
        assert 'interpreted_genome' in data.keys()
    
    def test_v6_model(self, cipapi_session):
        """Returned json is GeL v6 model"""
        is_v6 = irs.get_ir_json(2202,2,cipapi_session,{'reports_v6':True})
        not_v6 = irs.get_ir_json(2202,2,cipapi_session,{'reports_v6':True})

        pass
