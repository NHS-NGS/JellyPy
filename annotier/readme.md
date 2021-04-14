### annoTier

annoTier is a tool for the reanalysis and reannotation of unsolved 100,000 Genome Project cases.


#### General Workflow

- tiered variants and required case metadata parsed from JSON file
- latest version of original PanelApp panels retrieved with current green gene list
- variants filtered against PanelApp panel green genes
- presence of variant queried against CLinVar & HGMD
- gnomAD queried for pop.frequency, as well as extra in-silico predictions if available (REVEL, CADD, SpliceAI, PrimateAI)
- LitVar / PubMed queried to identify literature describing the variant, HPO terms used along with text scraping to identify if relevant to case phenotype
- results stored in MySQL database
- once analysis of all samples is complete, an .xlsx report may be generated with the level of pathogenicity


#### Requirements
- Python 3.7+
- Python packages (defined inr requirements.txt)
- MySQL
- HGMD Pro
- NCBI credentials


#### To do
- store all variants regardless of annotation, useful to identify if more tiered variants present in gene for cases heterzygous variants in AR disorders
- improve retrieval of literature
- add more annotation sources to allow more granular filtering
- adapt to reanalyse GRCh37 aligned cases
