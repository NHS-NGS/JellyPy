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

from pandas.io.json import json_normalize
# need to do json schema validation 
#from protocols.reports_6_0_1 import InterpretedGenome


class ReadJSON():

    def __init__(self):
        pass


    def read_json(self, json_file):
        """
        Read in json file

        Args:
            ir_json (file): input json file
        
        Returns:
            ir_json (dict): out json file as a var
        """

        with open(json_file) as file:
            ir_json = json.load(file)

        #print(InterpretedGenome.validate(ir_json["interpreted_genome"][0]["interpreted_genome_data"]))

        return ir_json


    def get_irid(self, ir_json):
        """
        Get ir id from within JSON, required for saving to db and more robust than using filename
        
        Args:
            - ir_json (dict): input json file

        Returns:
            - irid (str): ir id of current file
        """

        ir_id = ir_json["interpretation_request_id"]

        return ir_id


    def get_hpo_terms(self, ir_json):
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
                disorder_list = member["disorderList"]

                if not hpo_terms:
                    # hpoTermsList not filled
                    hpo_terms = None
                else:
                    for term in hpo_terms:
                        #removed unneeded fields
                        term.pop('modifiers', None)
                        term.pop('ageOfOnset', None)
                        term.pop('hpoBuildNumber', None)
                
                if not disorder_list:
                    # disorder list not filled
                    disorder_list = None

        if not hpo_terms:
            print("hpoTermList not found, continuing")

        return hpo_terms, disorder_list


    def get_tiered_variants(self, ir_json):
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
                        
                        # check cdna field has been filled
                        if not variant["variantAttributes"]["cdnaChanges"]:
                            c_change = None
                        else:
                            c_change = variant["variantAttributes"]["cdnaChanges"][0].split(":")[1]  

                        variant_list.append(
                            {
                            "position": position, 
                            "chromosome": chrom,
                            "ref": ref,
                            "alt": alt, 
                            "tier": tier,
                            "consequence": var_type,
                            "c_change": c_change
                            }
                        )

                        # need simple position list for later analysis
                        position_list.append((chrom, position))
        
        print("Number of variants in JSON: {}".format(len(variant_list)))


        return variant_list, position_list


if __name__ == "__main__":

    ir_json = ReadJSON.read_json(self, json_file)

    hpo_terms, disorder_list = ReadJSON.get_hpo_terms(self, ir_json)

    variant_list = ReadJSON.get_tiered_variants(self, ir_json)
