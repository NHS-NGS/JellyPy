
"""

Tests for jellypy pyCIPAPI package.

"""
import pytest

import jellypy.pyCIPAPI.config as config


def test_import():
    """pyCIPAPI modules can be imported. Config string is readable from module."""
    assert bool(config.live_100k_data_base_url)
