
"""
Tests for jellypy-pyCIPAPI package

Usage:
    pytest tierup/test/test_requests.py --jpconfig=tierup/test/config.ini
"""
import pytest

import jellypy.pyCIPAPI.config as config
import jellypy.pyCIPAPI.auth as auth
import jellypy.pyCIPAPI.interpretation_requests as irs


def test_import():
    """Objects in pyCIPAPI modules can be imported from the jellypy namespace."""
    assert bool(config.live_100k_data_base_url)

def test_config(jpconfig):
    """A jellypy config.ini file has been parsed by pytest"""
    assert jpconfig is not None, \
        "ERROR: Jellypy tests require config file. Please pass --jpconfig <yourfile.ini>"
    try:
        assert bool(jpconfig['pyCIPAPI']['username'])
        assert bool(jpconfig['pyCIPAPI']['password'])
    except KeyError:
        raise ValueError("ERROR: Could not read expected key from jpconfig. See example in docs.")

def test_get_irjson(jpconfig):
    """Interpretation requests json files can be downloaded from the CIPAPI"""
    irid = jpconfig.get('pyCIPAPI', 'test_irid')
    irversion = jpconfig.get('pyCIPAPI', 'test_irversion')
    session = auth.AuthenticatedCIPAPISession(
            auth_credentials={
            'username': jpconfig.get('pyCIPAPI', 'username'),
            'password': jpconfig.get('pyCIPAPI', 'password')
        }
    )
    # Attempt to get a known interpretation request. This can be changed in the test config.
    data = irs.get_interpretation_request_json(irid, irversion, reports_v6=True, session=session)
    assert isinstance(data, dict)
