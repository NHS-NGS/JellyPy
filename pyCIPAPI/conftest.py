# content of conftest.py
import pytest
from configparser import ConfigParser

def read_config(ini_path):
    config = ConfigParser()
    config.read(ini_path)
    return config
    

def pytest_addoption(parser):
    parser.addoption(
        "--pconfig", action="store", type=read_config, help="pyCIPAPI_config"
    )

@pytest.fixture
def pycipapi_config(request):
    return request.config.getoption("--pconfig")