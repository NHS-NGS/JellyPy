"""
Functions for handling interpretation requestions to variants data in 
JSON format.
Requiures JSONs to be in v6 schema format.
"""

import json
import os
import pprint
import re
import sys

# need to do json schema validation 
from protocols.reports_6_0_1 import InterpretedGenome

sample_id="44543-1"

def get_json(sample_id):
    """
    Read in json file

    Args:
        sample_id (str): input sample id
    
    Returns:
        ir_json (dict): input json file
    """

    json_file = os.path.join(os.path.dirname(__file__), 
                "../data/ir_jsons/{}.json").format(sample_id)

    with open(json_file) as file:
        ir_json = json.load(file)

    print(InterpretedGenome.validate(ir_json["interpreted_genome"][0]["interpreted_genome_data"]))

    return ir_json


def get_hpo_terms(ir_json):
    """
    Get hpo terms from ir json. 
    Should only be called on initial analysis of a sample.

    Args:
        ir_json (dict): input json file

    Returns:
        hpo_terms (list): list of hpo terms from json
    """
    
    # set none initially if hpoTermList has not been filled
    hpo_terms = None

    members = ir_json["interpretation_request_data"]["json_request"]\
                     ["pedigree"]["members"]

    for member in members:
        if member["isProband"] == True:

            hpo_terms = member["hpoTermList"]

            if not hpo_terms:
                # hpoTermsList not filled
                break
            else:
                for term in hpo_terms:
                    #removed unneeded fields
                    term.pop('modifiers', None)
                    term.pop('ageOfOnset', None)
                    term.pop('hpoBuildNumber', None)

    if not hpo_terms:
        print("hpoTermList not found, continuing")

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

    for interpretation in ir_json["interpreted_genome"]:
        if "interpreted_genome_data" in interpretation:            
            if "variants" in interpretation["interpreted_genome_data"]:

                print(len(interpretation["interpreted_genome_data"]["variants"]))
                
                for variant in interpretation["interpreted_genome_data"]["variants"]:

                    position = variant["variantCoordinates"]["position"]
                    chrom = variant["variantCoordinates"]["chromosome"]
                    ref = variant["variantCoordinates"]["reference"]
                    alt = variant["variantCoordinates"]["alternate"]
                    tier = variant["reportEvents"][0]["tier"]    

                    if not variant["reportEvents"][0]["variantConsequences"]:
                        var_type = None
                    else:
                        var_type = variant["reportEvents"][0]["variantConsequences"][0]["name"]
                    
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
    
    print("Number of variants in JSON: {}".format(len(variant_list)))
    print("length of position list {}".format(len(position_list)))
    print("length of variant list {}".format(len(variant_list)))

    return variant_list, position_list


if __name__ == "__main__":

    ir_json = get_json(sample_id)

    hpo_terms = get_hpo_terms(ir_json)

    variant_list = get_tiered_variants(ir_json)
