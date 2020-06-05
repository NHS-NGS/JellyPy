import pytest

from jellypy.tierup.panelapp import GeLPanel

def test_gelpanel_query():
    # Test gel panel query for ACVRL1 (ENSG00000139567)
    #   and in Hereditary haemorrhagic telangiectasia (123)
    acvrl1_ensembl_id = 'ENSG00000139567'
    gp = GeLPanel(123)
    results = gp.query(acvrl1_ensembl_id)
    assert results == (
        'HGNC:175', 'ACVRL1', '3', 'ENSG00000139567',
        'MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted'
    )
    assert gp.query('NOT_AN_ENSEMBL_ID') == (None, None, None, None, None)
    assert gp.query('') == (None, None, None, None, None)