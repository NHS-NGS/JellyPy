"""
Functions for handling interpretation requestions to variants data in
JSON format.
Requiures JSONs to be in v6 schema format.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200521
"""

import json
import os
import pprint
import re
import sys

from pandas.io.json import json_normalize


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
            print("Reading file: ", json_file)
            ir_json = json.load(file)

        return ir_json

    def get_irid(self, ir_json):
        """
        Get ir id from within JSON, required for saving to db and more
        robust than using filename

        Args:
            - ir_json (dict): input json file

        Returns:
            - irid (str): ir id of current file
        """

        ir_id = ir_json["interpretation_request_id"]

        return ir_id

    def get_members(self, ir_json):
        """
        Get members and associated details

        Args:
            - ir_json (dict): input json file

        Returns:
            - ir_members (list): list of dicts with each member details
        """
        members = ir_json["interpretation_request_data"]["json_request"][
            "pedigree"]["members"]

        ir_members = []

        for member in members:
            cur_mem = {}
            cur_mem["fatherID"] = member["fatherId"]
            cur_mem["motherID"] = member["motherId"]
            cur_mem["sex"] = member["sex"]
            cur_mem["participantID"] = member["participantId"]
            cur_mem["affectionStatus"] = member["affectionStatus"]
            cur_mem["yearOfBirth"] = member["additionalInformation"][
                "yearOfBirth"]
            cur_mem["relation_to_proband"] = member["additionalInformation"][
                "relation_to_proband"]
            cur_mem["isProband"] = member["isProband"]

            ir_members.append(cur_mem)

        return ir_members

    def get_panels(self, ir_json):
        """
        Gets PanelApp panel(s) and versions used for case from each var.

        Args:
            - variant_list (list): list od dicts for each variant

        Returns:
            - ir_panel (list): list of tuples of panel(s) used for case
        """
        ir_panel = []

        # get panels & versions from every JSON in variant
        for interpretation in ir_json["interpreted_genome"]:
            if "interpreted_genome_data" in interpretation:
                if "variants" in interpretation["interpreted_genome_data"]:
                    for variant in interpretation["interpreted_genome_data"][
                        "variants"
                    ]:
                        for event in variant["reportEvents"]:
                            if not event["genePanel"]:
                                continue
                            else:
                                panel = (
                                    event["genePanel"]["panelName"],
                                    event["genePanel"]["panelVersion"]
                                )
                                ir_panel.append(panel)

        # get unique list of panels and version
        ir_panel = list(set(ir_panel))

        return ir_panel

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

        members = ir_json["interpretation_request_data"]["json_request"][
            "pedigree"]["members"]

        for member in members:
            if member["isProband"] is True:

                hpo_terms = member["hpoTermList"]
                disorder_list = member["disorderList"]

                if not hpo_terms:
                    # hpoTermsList not filled
                    hpo_terms = None
                else:
                    for term in hpo_terms:
                        # remove unneeded fields
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
        position_list = []

        for interpretation in ir_json["interpreted_genome"]:
            if "interpreted_genome_data" in interpretation:
                if "variants" in interpretation["interpreted_genome_data"]:
                    for variant in interpretation["interpreted_genome_data"][
                        "variants"
                    ]:
                        position = variant["variantCoordinates"]["position"]
                        chrom = variant["variantCoordinates"]["chromosome"]
                        ref = variant["variantCoordinates"]["reference"]
                        alt = variant["variantCoordinates"]["alternate"]
                        tier = variant["reportEvents"][0]["tier"]
                        gene = variant["reportEvents"][0][
                            "genomicEntities"][0]["geneSymbol"]
                        build = variant["variantCoordinates"]["assembly"]
                        penetrance = variant["reportEvents"][0]["penetrance"]
                        denovoQScore = variant["reportEvents"][0][
                            "deNovoQualityScore"]
                        variantCalls = variant["variantCalls"]

                        for call in variantCalls:
                            for key in list(call.keys()):
                                # drop all but zygosity and ID for each call
                                if key not in ["zygosity", "participantId"]:
                                    del call[key]

                        try:
                            var_type = variant["variantAttributes"][
                                "additionalTextualVariantAnnotations"
                                ]["consequence"]
                        except Exception:
                            var_type = None

                        # get transcript and cDNA change
                        try:
                            hgvs = variant["variantAttributes"][
                                "additionalTextualVariantAnnotations"
                            ]["hgvs"]
                            hgvs = hgvs.split(":")

                            transcript = hgvs[1]
                            c_change = hgvs[2]
                            p_change = hgvs[3]
                        except Exception:
                            transcript = None
                            c_change = None
                            p_change = None

                        variant_list.append({
                            "position": position,
                            "chromosome": chrom,
                            "ref": ref,
                            "alt": alt,
                            "tier": tier,
                            "gene": gene,
                            "consequence": var_type,
                            "c_change": c_change,
                            "p_change": p_change,
                            "transcript": transcript,
                            "build": build,
                            "penetrance": penetrance,
                            "denovoQScore": denovoQScore,
                            "variantCalls": variantCalls
                        })

                        # need simple position list for later analysis
                        position_list.append((chrom, position))

        print("Number of variants in JSON: {}".format(len(variant_list)))

        return variant_list, position_list


if __name__ == "__main__":

    pass

    # ir_json = ReadJSON.read_json(self, json_file)

    # hpo_terms, disorder_list = ReadJSON.get_hpo_terms(self, ir_json)

    # variant_list = ReadJSON.get_tiered_variants(self, ir_json)
