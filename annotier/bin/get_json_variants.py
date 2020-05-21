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

sample_id="55904-1"

def get_json(sample_id):
    """
    Read in json file

    Args:
        sample_id (str): input sample id
    
    Returns:
        ir_json (dict): input json file
    """

    json_file = os.path.expanduser("../data/ir_jsons/{}.json").format(sample_id)

    with open(json_file) as file:
        ir_json = json.load(file)

    return ir_json


def get_hpo_terms(ir_json):
    """
    Get hpo terms from ir json, should only be called on initial analysis of a sample

    Args:
        ir_json (dict): input json file

    Returns:
        hpo_terms (list): list of hpo terms from json
    """

    hpo_terms = []

    for term in (ir_json["interpretation_request_data"]["json_request"]
                        ["pedigree"]["members"][0]['hpoTermList']
        ):

        # removed unneeded fields
        term.pop('modifiers', None)
        term.pop('ageOfOnset', None)
        term.pop('hpoBuildNumber', None)

        hpo_terms.append(term)

    return hpo_terms


def get_tiered_variants(ir_json):
    """
    Function to get variants from ir json for analysis

    Args:
        ir_json (dict): input json file

    Returns:
        variant_list (list): list of tiered variants from json
        position_list (list): list of tiered varaints with only chrom & pos
    """

    variant_list = []
    position_list =  []

    for variant in (
        ir_json["interpreted_genome"][0]["interpreted_genome_data"]["variants"]
    ):

        position = variant["variantCoordinates"]["position"]
        chrom = variant["variantCoordinates"]["chromosome"]
        ref = variant["variantCoordinates"]["reference"]
        alt = variant["variantCoordinates"]["alternate"]
        var_type = variant["reportEvents"][0]["variantConsequences"][0]["name"]
        tier = variant["reportEvents"][0]["tier"]    

        variant_list.append(
            {
            "position": position, 
            "chromosome": chrom,
            "ref": ref,
            "alt": alt, 
            "tier": tier,
            "type": var_type
            }
        )

        # need simple position list for later analysis
        position_list.append((chrom, position))

    return variant_list, position_list


if __name__ == "__main__":

    ir_json = get_json(sample_id)
    hpo_terms = get_hpo_terms(ir_json)
    variant_list = get_tiered_variants(ir_json)