# tierup

`tierup` reanalyses Tier 3 variants in undiagnosed GeL rare disease cases.

`tierup` answers the following questions derived from the GeL tiering rules:
- Is the variant in a green gene in a panel app panel assigned to the case?
- Does the variant mode of inheritance match the gene's in the panel app panel?

Tier 3 variants that meet these criteria are labelled 'tier\_1' or 'tier\_2' in the tier\_tierup field of the `tierup` output CSV.

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

2. Run tierup
    For example, interpretation request 1234 version 2 could be analysed with:
    ```bash
    tierup --irid 1234 --irversion 1 --config config.ini
    ```
    If the intepretation request data is available locally in json format, then you can pass the file directly:
    ```bash
    tierup -j interpretation_request.json --config config.ini
    ```

3. View results
    * \*.tierup.csv - The `tier_tierup` column in the results file contains the new variant tier determined by tierup. Each row is a report event for a variant in the proband. Note: The same variant may have multiple report events depending on the number of assigned gene panels, mode of inheritance and penetrance models analysed.

## TierUp output fields (\*.tierup.csv)

| Field | Description
|-------|------------
|interpretation_request_id| Identifier for GeL case
|tier_tierup| Tiering result from tierup: tier_3_not_in_panel, tier_3_red_or_amber, tier_3_green_moi_mismatch, tier_2, tier_1
|tier_gel| Initial GeL tier. Previously *tier* field in tierup 0.2.0
|assembly|Reference genome
|chromosome|Chromosome number
|position|Genomic coordinate
|reference|Reference allele
|alternate|Proband Alternate allele
|consequences| Sequence ontology terms for the variant consequences in all relevant transcripts
|zygosity|Zygosity in the proband
|segregation|Pattern calculated using genotypes from family members
|penetrance| Penetrance model used to assess the variant
|tiering_moi| Mode of inheritance for the variant in the proband. Previously *inheritance* field in tierup 0.2.0
|tu_panel_hash|Panel unique hash id used in TierUp analysis
|tu_panel_name|Panel name used in TierUp analysis
|tu_panel_version|Panel version used in TierUp analysis
|tu_panel_number|Panel id used in TierUp analysis
|tu_panel_created|The date the panel version used in TierUp analysis was created
|tu_run_time|Time TierUp was initiated
|pa_ensembl| Ensembl identifier for the gene in panelapp panel
|pa_hgnc_id|HGNC ID from the panel app panel
|pa_gene|Gene symbol from the panel app panel
|pa_moi| Mode of inheritance for the gene in the panelapp panel version
|pa_confidence|Current gene confidence level from the latest version of the panel app panel: 4 or 3 = Green; 2 = Amber; 1 or 0 = Red; Green genes indicate TieredUp variant.
|extra_panels|Panel ID pointers updated via TierUp check for depreciated Panels in GeL directory
|re_id|Unique identifier for the report event. Previously *event_id* field in tierup 0.2.0
|re_panel_id|Report event panel id
|re_panel_version|Report event panel version
|re_panel_source|Report event panel source. All expected to be panelapp
|re_panel_name|Report event panel name
|re_gene|Report event gene symbol
|justification| GeL eventJustification field which describes why the variant was tiered
|created_at|Creation date for the GeL interpreted genome was created
|software_versions|Software versions used in the GeL analysis
|reference_db_versions|Reference database versions used int he GeL analysis
|tu_version|jellypy-tierup version used to generate results

## Constraints

* `tierup` input is limited to undiagnosed rare disease cases. The tool therefore raises an error if users attempt to process a solved case.
* Access to case data from GeL is only possible on the [HSCN](https://digital.nhs.uk/services/health-and-social-care-network)
* Interpretation request data must comply with the GeL v6 interpretation request model
* `tierup` does not analyse CNVs
* `tierup` does not account for information on variant penetrance

## Support

Please [raise issues](https://github.com/NHS-NGS/JellyPy), message the [#jellypy slack](https://binfx.slack.com/messages) channel or [send an email](mailto:nana.mensah1@nhs.net).