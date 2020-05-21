"""
Functions for handling interpretation requestions to variants data in JSON format.
Requiures JSONs to be in v6 schema format.
"""

import json
import os
import pprint
import re
import sys

# need to do json schema validation 
# from protocols.reports_6_0_1 import InterpretedGenome


def get_json(sample_id):

    json_file = os.path.expanduser("../data/ir_jsons/{}.json").format(sample_id)

    with open(json_file) as file:
        ir_json = json.load(file)

    return ir_json


def get_hpo_terms(ir_json):
    """
    Get hpo terms from ir json, should only be called on samples initial analysis
    """

    hpo_terms = []

    for term in (
        ir_json["interpretation_request_data"]["json_request"]
        ["pedigree"]["participants"][0]['hpoTermList']
        ):

        # removed unneeded fields
        term.pop('modifiers', None)
        term.pop('ageOfOnset', None)

        hpo_terms.append(term)

    return hpo_terms

def get_tiered_variants(ir_json):
    """
    Function to get variants from ir json for analysis
    """

    variant_list = []
    position_list =  []

    for variant in (
        ir_json["interpretation_request_data"]
        ["json_request"]["TieredVariants"]
    ):
        position = int(variant["position"])
        chrom = variant["chromosome"]
        ref = variant["reference"]
        alt = variant["alternate"]
        tier = variant["reportEvents"][0]["tier"]

        variant_list.append(
            {
            "position": position, 
            "chromosome": chrom,
            "ref": ref,
            "alt": alt, 
            "tier": tier
            }
        )

        # need simple position list for later analysis
        position_list.append((chrom, position))

    return variant_list, position_list

if __name__ == "__main__":

    ir_json = get_json(sample_id)
    hpo_terms = get_hpo_terms(ir_json)
    variant_list = get_tiered_variants(ir_json)