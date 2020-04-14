
"""
Tests for jellypy-pyCIPAPI package. 

Ensure you have installed jellypy-pyCIPAPI from the repository: 
    $ pip install ./pyCIPAPI

Usage:
    pytest pyCIPAPI/test/test_pyCIPAPI.py --jpconfig=config.ini

Example config.ini format:
    [pyCIPAPI]
    client_id = YOUR_CLIENT_ID
    client_secret = YOUR_CLIENT_SECRET
    test_irid = VALID_INTERPRETATION_REQUEST_ID
    test_irversion = VALID_INTERPRETATION_REQUEST_VERSION
"""
import pytest

import jellypy.pyCIPAPI.config as config
import jellypy.pyCIPAPI.auth as auth
import jellypy.pyCIPAPI.interpretation_requests as irs


def test_import():
    """Objects in pyCIPAPI modules can be imported from the jellypy namespace."""
    assert bool(config.live_100k_data_base_url)

def test_config(jpconfig):
    """Test that a valid config.ini file has been parsed by pytest"""
    assert jpconfig is not None, \
        "ERROR: Jellypy tests require config file. Please pass --jpconfig <yourfile.ini>"
    try:
        assert bool(jpconfig['pyCIPAPI']['client_id'])
        assert bool(jpconfig['pyCIPAPI']['client_secret'])
    except KeyError:
        raise ValueError("ERROR: Could not read expected key from jpconfig. See example in docs.")

@pytest.fixture()
def authenticated_session(jpconfig):
    session = auth.AuthenticatedCIPAPISession(
            auth_credentials={
            'client_id': jpconfig.get('pyCIPAPI', 'client_id'),
            'client_secret': jpconfig.get('pyCIPAPI', 'client_secret')
        }
    )
    return session

def test_authentication(authenticated_session):
    """Session fixture returns an authentaicated session for active directory login."""
    assert authenticated_session.headers['Authorization']

def test_get_irjson(jpconfig, authenticated_session):
    irid = jpconfig.get('pyCIPAPI', 'test_irid')
    irversion = jpconfig.get('pyCIPAPI', 'test_irversion')
    """Interpretation request data can be downloaded from the CIPAPI with an authenticated session"""
    data = irs.get_interpretation_request_json(irid, irversion, reports_v6=True, session=authenticated_session)
    assert 'interpretation_request_id' in data.keys()
