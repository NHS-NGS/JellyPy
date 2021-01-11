Notes on setting up and running annoTier

Required external files:
    - HGMD Pro VCF (/data/hgmd/)
    - ClinVar VCF (/data/hgmd/) - latest version automatically downloaded from FTP site during set up
    - HGNC complete symbol file (/data/hgnc/) - ftp://ftp.ebi.ac.uk/pub/databases/genenames/hgnc/tsv/hgnc_complete_set.txt
    - HPO phenotype file (/data/hpo) -
    http://compbio.charite.de/jenkins/job/hpo.annotations.current/lastSuccessfulBuild/artifact/current/phenotype.hpoa

Requires '100k_reanalysis' MySQL database setting up, and credentials entering
into `db_credentials.py` file. Also requires an NCBI account for querying their
API's and credentials entering into `ncbi_credentials.py`.

All required Python packages are stored in `requirements.txt` (Python 3.7+).

Currently relies on JSONs being pulled from the CIP-API and stored in
`/data/ir_jsons`. `validate_json.py` is a script to filter a dir of
JSONs to ensure only unsolved, rare disease, GRCh38 JSONs are retained. Those
that are usable will be saved into `/data/ir_jsons/passJSON`, the rest will be put
in `/data/ir_jsons/failJSON`.
