import json
import os
from distutils import dir_util
from pathlib import Path

import pytest
from jellypy.tierup.lib import TieringLite, ReportEvent
from jellypy.tierup.panelapp import GeLPanel


# Read test data from a file
@pytest.fixture
def tdata(tmpdir, request):
    test_dir = Path(request.module.__file__).parent / "test_data"
    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, str(tmpdir))
    with open(Path(tmpdir / "test_tierup_data.json")) as f:
        tdata = json.load(f)
    return tdata

def test_gelpanel_query(tdata):
    panel_id = tdata["test_gel_panel"][0]["panel_id"]
    gp = GeLPanel(panel_id)
    for query, result in tdata["test_gel_panel"][0]["queries"].items():
        assert gp.query(query) == tuple(result)

def test_mode_of_inheritance(tdata):
    tl = TieringLite()
    for test_data in tdata["test_mode_of_inheritance"]:
        tiering, panelapp, result = test_data
        assert tl._moi_match(tiering, panelapp) == result

def test_high_impact(tdata):
    tl = TieringLite()
    for test_data in tdata["test_high_impact"]:
        segregation, consequence, result = test_data
        assert tl._is_high_impact(segregation, consequence) == result

def test_tiering_lite(tdata):
    tl = TieringLite()
    for td in tdata["test_tiering_lite"]:
        event = ReportEvent(td['report_event'], td['variant'], td['proband_call'])
        panel = GeLPanel(td['panel_id'])
        assert tl.retier(event, panel)[0] == td['result']