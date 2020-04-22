# tierup

`tierup` finds Tier 3 variants in GeL cases with PanelApp Green genes.

## Installation

```bash
pip install jellypy-tierup
```

## Guides

### Reanalyse Tier 3 variants in a GeL rare disease case

1. Create a configuration file with CIPAPI details. For example:
    ```
    # config.ini
    [pyCIPAPI]
    client_id = YOUR-GEL-CLIENT-ID
    client_secret = YOUR-GEL-CLIENT-SECRET
    ```
    
    Please note: jellypy-tierup authenticates users using their LDAP credentials and is not yet compatible with the GeL active directory authentication.

1. Run tierup
    For example, interpretation request 1234 version 2 could be analysed with:
    ```bash
    tierup --irid 1234 --irversion 1 --config config.ini
    ```

1. View results
    * \*.tierup.summary.csv - A list of any tierup (PanelApp Green) variants found. This is file is *blank* if no variants are found.
    * \*.tierup.csv - Complete data from all Tier 3 variants anlaysed

## TierUp output fields (\*.tierup.csv) 

| Field | Description
|-------|------------
|justification| GeL eventJustification field which describes why the variant was tiered 
|consequences| String representation of the GeL variantConsequences field which contains sequence ontology terms
|penetrance|Penetrace used for scoring the variant
|denovo_score|GeL likelihood of being a de novo variant
|score|GeL likelihood of explaining phenotype 
|event_id|Unique identifier for the report event
|interpretation_request_id|Case interpretation request ID
|created_at|Creation date for the GeL interpreted genome was created
|tier|Variant initial tiering value. All expected Tier3
|segregation|Pattern calculated using genotypes from family members
|inheritance|Mode of inehritance
|group|GeL unique number to group variants together
|zygosity|Zygosity in the proband
|position|Genomic coordinate
|chromosome|Chromosome number
|assembly|Reference genome
|reference|Reference allele
|alternate|Proband Alternate allele
|re_panel_id|Report event panel id
|re_panel_version|Report event panel version
|re_panel_source|Report event panel source. All expected to be panelapp
|re_panel_name|Report event panel name
|re_gene|Report event gene symbol
|tu_panel_hash|Panel unique hash id used in TierUp analysis
|tu_panel_name|Panel name used in TierUp analysis
|tu_panel_version|Panel version used in TierUp analysis
|tu_panel_number|Panel id used in TierUp analysis
|tu_panel_created|The date the panel version used in TierUp analysis was created
|pa_hgnc_id|HGNCID from the panelapp panel
|pa_gene|Gene symbol from the panel app panel
|**pa_confidence**|**Current gene confidence level from the latest version of the panel app panel; 4 or 3 = Green; 2 = Amber; 1 or 0 = Red; Green genes indicate TieredUp variant.**
|software_versions|Software versions used in the GeL analysis
|reference_db_versions|Reference database versions used int he GeL analysis
|extra_panels|Panel ID pointers updated via TierUp check for depreciated Panels in GeL directory
|tu_run_time|Time TierUp was initiaed
|tier1_count|Tier 1 report events in the initial case
|tier2_count|Tier 2 report events in the initial case
|tier3_count|Tier 3 report events in the initial case
|tu_version|jellypy-tierup version used to generate results

## Constraints

* `tierup` is designed for undiagnosed rare disease cases. The tool therefore raises an error if users attempt to process a solved case.
* Access to case data from GeL is only possible on the [HSCN](https://digital.nhs.uk/services/health-and-social-care-network)
* Case data must comply with the GeL v6 interpretation request model

## Support

Please [raise issues](https://github.com/NHS-NGS/JellyPy), message the [#jellypy slack](https://binfx.slack.com/messages) channel or [send an email](mailto:nana.mensah1@nhs.net).