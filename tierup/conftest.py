# content of conftest.py
import pytest
from configparser import ConfigParser


def read_config(ini_path):
    config = ConfigParser()
    config.read(ini_path)
    return config


def pytest_addoption(parser):
    parser.addoption(
        "--jpconfig", action="store", type=read_config, help="JellyPy config ini file"
    )


@pytest.fixture
def jpconfig(request):
    return request.config.getoption("--jpconfig")
