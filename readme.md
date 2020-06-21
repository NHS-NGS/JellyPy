# JellyPy

![jellypy_logo](assets/jellypy_logo_v2.png)

## Python packages for working with GeL data

JellyPy documentation is available at https://acgs.gitbook.io/jellypy

Packages:

* `jellypy-pyCIPAPI` : Client library for the Clinical Interpretation Portal
* `jellypy-tierup` : Reanalyse Tier 3 variants 

## Contributing

Please raise an issue to request new functions or features: https://github.com/NHS-NGS/JellyPy/issues

To develop a new function or feature, please take a look at the issues raised. If there's something that you would like to code up, then (you are awesome and) start a discussion in the #jellypy channel at https://binfx.slack.com/messages

## Changelog

### jellypy-pyCIPAPI

* 0.1.0 - Make JellyPy a namespace package
* 0.2.0 - Update pyCIPAPI to work with GeL client token/secret GMS authentication
* 0.2.1 - Support legacy authentication by allowing AD to be toggled on/off in config file
* 0.2.2 - Add sub-heading to README changelog
* 0.2.3 - Update live 100K url. Display response on API errors. Add tests for auth api calls.

### jellypy-tierup

* 0.2.0 - TierUp development release with pyCIPAPI 0.2.3
* 0.3.0 - Use ensembl identifiers to query panel app. Implement mode of inheritance check.
