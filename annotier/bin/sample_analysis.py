"""
Calls functions to:
    - check if new ClinVar VCF ver. is available
        - if so, downloads and extracts to /data/clinvar
    - read in a sample json, extract hpo terms and tiered variants
    - run reanalysis (currently against ClinVar and HGMD Pro)
    - save annotation to db
"""

import json
import sys
import re
import os
import pandas as pd
import pprint
import sqlite3

from get_json_variants import get_hpo_terms, get_json, get_tiered_variants
from clinvar_query import clinvar_vcf_to_df, get_clinvar_ids, get_clinvar_data
from hgmd_query import hgmd_vcf_to_df, hgmd_variants

sample_id="55904-1"

def find_json(sample_id):
    """
    For given ir_id, check if json is available locally, if not get 
    from cipAPI
    """

    try:
        ir_json = get_json(sample_id)

        print("Analysing sample {}".format(sample_id))
        
        return ir_json
    except:
        # local file not found, retrieve via cipAPI
        print("json not found locally")
        # code for doing cipapi ir to do
        sys.exit()


def get_json_data(ir_json):
    """
    Call functions from gel_requests to get HPO terms and tiered 
    variants for analysis
    """

    hpo_terms = get_hpo_terms(ir_json)
    variant_list, position_list = get_tiered_variants(ir_json)
    print("Number of variants: {}".format(len(position_list)))
    
    return hpo_terms, variant_list, position_list


def run_analysis(position_list):
    """
    Call analysis functions, return outputs from each to import to db

    Args:
        position_list (list): list of all variant positions in json
        clinvar_df (dataframe): df of all ClinVar variants from VCF
        clinvar_list (list): list of ClinVar ids for tiered variants
        hgmd_df (dataframe): df of all HGMD variants


    Returns:
        clinvar_df (dataframe): df of all ClinVar variants from VCF
        clinvar_list (list): list of all ClinVar ent
        hgmd_df (dataframe): df of all HGMD variants from VCF

        clinvar_summary_df (dataframe): df of ClinVar entries for 
                                        tiered variants

        hgmd_match_df (dataframe): df of HGMD entries for 
                                   tiered variants
    """

    # read ClinVar vcf in
    clinvar_df = clinvar_vcf_to_df()

    # get list of ClinVar entries for tiered variants
    clinvar_list = get_clinvar_ids(clinvar_df, position_list)

    # get full ClinVar entries with NCBI eutils, return in df
    clinvar_summary_df = get_clinvar_data(clinvar_list)

    print("Number of pathogenic/likely pathogenic ClinVar entries: {}".format(
        len(clinvar_summary_df.index)))

    # read HGMD Pro vcf in
    hgmd_df = hgmd_vcf_to_df()
    
    # get HGMD entries for tiered variants
    hgmd_match_df = hgmd_variants(hgmd_df, position_list)

    print("Number of HGMD entries: {}".format(len(hgmd_match_df.index)))

    return clinvar_summary_df, hgmd_match_df


def update_db():
    """
    Update reanalysis database with outputs of analyses
    """

    # to do

if __name__ == "__main__":

    ir_json = find_json(sample_id)
    hpo_terms, variant_list, position_list = get_json_data(ir_json)
    run_analysis(position_list)
