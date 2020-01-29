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
    username = your_username
    password = your_password
    ```

1. Run tierup
    For example, interpretation request 1234 version 2 could be analysed with:
    ```bash
    tierup --irid 1234 --irversion 1 --config config.ini
    ```

1. View results
    * \*.tierup.summary.csv - A list of any tierup (PanelApp Green) variants found
    * \*.tierup.csv - Complete data from all Tier 3 variants anlaysed

## Constraints

* `tierup` analyses undiagnosed rare disease cases
* Access to case data from GeL is only possible on the [HSCN](https://digital.nhs.uk/services/health-and-social-care-network)
* Case data must comply with the GeL v6 interpretation request model

## Support

Please [raise issues](https://github.com/NHS-NGS/JellyPy), message the [#jellypy slack](https://binfx.slack.com/messages) channel or [send an email](mailto:nana.mensah1@nhs.net).