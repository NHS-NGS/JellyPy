import pytest

from jellypy.tierup.panelapp import GeLPanel
from jellypy.tierup.lib import TieringLite

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

TEST_MODE_OF_INHERITANCE = [
    ("biallelic", "BOTH monoallelic and biallelic, autosomal or pseudoautosomal", True),
    ("biallelic", "BIALLELIC, autosomal or pseudoautosomal", True),
    ("mitochondrial", "MITOCHONDRIAL", True),
    ("DENOVO",  "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown", True),
    ("monoallelic_maternally_imprinted", "MONOALLELIC, autosomal or pseudoautosomal, maternally imprinted (paternal allele expressed)", True),
    ("xlinked_biallelic", "X-LINKED: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)", False),
    ("xlinked_biallelic", "X linked: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)", False),
    ("monoallelic", "MONOALLELIC, autosomal or pseudoautosomal", True),
    ("monoallelic", "Other - please specify in evaluation comments", True),
    ("monoallelic", "Unknown", True),
    ("xlinked_biallelic", "X-LINKED: hemizygous mutation in males, biallelic mutations in females", True),
    ("xlinked_monoallelic", "X-LINKED: hemizygous mutation in males, biallelic mutations in females", True),
    ("xlinked_monoallelic", "X linked: hemizygous mutation in males, monoallelic mutations in females may cause disease (may be less severe, later onset than males)", True),
    ("monoallelic_not_imprinted", "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted", True),
    ("monoallelic_not_imprinted", "MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown", True),
    ("DOMINANT", "", True),
    (None, "", True),
    (None, None, True),
    ("mitochondrial", "BIALLELIC, autosomal or pseudoautosomal", False),
    ("DENOVO",  "BIALLELIC, autosomal or pseudoautosomal", False),
    ("biallelic", "MITOCHONDRIAL", False),
    ("monoallelic_maternally_imprinted", "BIALLELIC, autosomal or pseudoautosomal", False),
    ("monoallelic", "BIALLELIC, autosomal or pseudoautosomal", False),
]

@pytest.mark.parametrize('tiering,panelapp,result', TEST_MODE_OF_INHERITANCE)
def test_mode_of_inheritance(tiering, panelapp, result):
    tl = TieringLite()
    assert tl.moi_match(tiering, panelapp) == result