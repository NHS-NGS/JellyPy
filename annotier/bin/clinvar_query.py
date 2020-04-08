"""
Functions to take a json of GEL variants, query against ClinVar VCF 
if present, and then return full ClinVar entry for those that are.

To do more than 3 requests per second to ClinVar this requires an NCBI account,
and the email and api key passing to entrezpy. These are stored in ncbi_credentials.py
in /bin.
"""

import json
import sys
import re
import os
import pandas as pd
import pprint
import entrezpy.esummary.esummarizer

from ncbi_credentials import ncbi_credentials

# lists to temporarialy store data in
variant_list = []
position_list = []
clinvar_list = []

dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, "../data/")

def get_json_data():
    # temporary test json until using cipapi
    sample_json = os.path.expanduser("~/annoTier_local_data/sample_ir.json")

    with open(sample_json) as json_file:
        ir_json = json.load(json_file)

    return ir_json

def vcf_to_df():
    """
    Read in clinvar vcf to df for querying
    """
    
    data_files = []

    for (dirpath, dirnames, filenames) in os.walk(data_dir):
        data_files.extend(filenames)

    for file in data_files:
        if re.match("^clinvar_[0-9]+\.vcf$", file):
            # get just the clinvar vcf
            vcf = os.path.join(data_dir, file)

    clinvar_df = pd.read_csv(vcf, header = [27], sep='\t', low_memory=False)
    
    return clinvar_df

def json_variants(ir_json):
    """
    Function to pull out variant positions from JSON
    """

    for variant in (
        ir_json["interpretation_request_data"]
        ["json_request"]["TieredVariants"]
    ):
        position = int(variant["position"])
        chrom = variant["chromosome"]
        tier = variant["reportEvents"][0]["tier"]

        variant_list.append({"position": position, "chromosome": chrom, "tier": tier})
        position_list.append(position)
    
    return variant_list

def get_clinvar_ids(clinvar_df):
    """
    Function to query all variants in JSON against ClinVar df, returns ids of those pathogenic and likely pathogenic
    """
    for position in position_list:
        # check if variant position is in clinvar df
        if len(clinvar_df[clinvar_df['POS'].isin([position])]) != 0:
            
            match = clinvar_df[clinvar_df['POS'].isin([position])]
            match_info = match.iloc[0]["INFO"] # get info field with pathogenicity

            if "CLNSIG=Pathogenic" in match_info or "CLNSIG=Likely_pathogenic" in match_info:
                # add variant if classified as pathogenic or likely pathogenic
                clinvar_list.append(int(match.iloc[0]["ID"]))
            
            if "CLNSIG=Conflicting_interpretations_of_pathogenicity" in match_info:
                clnsigconf = [i for i in match_info.split(";") if i.startswith("CLNSIGCONF")]

                if "pathogenic" in clnsigconf[0].casefold():
                    # add variant if classified as pathogenic or likely pathogenic but with conflicts
                    clinvar_list.append(int(match.iloc[0]["ID"]))
    
    return clinvar_list

def get_clinvar_data(clinvar_list):
    """
    Take list of variants with pathogenic / likely pathogenic 
    clinvar entries and return full clinvar information
    Requires NCBI email and api_key adding to ncbi_credentials.py to do more than 3 requests per second
    """
    e = entrezpy.esummary.esummarizer.Esummarizer("clinvar_summary",
                ncbi_credentials["email"],
                apikey = ncbi_credentials["api_key"],
                apikey_var=ncbi_credentials["api_key"],
                threads = 4,
                qid = None
                )
    
    a = e.inquire({'db': 'clinvar', 'id': clinvar_list})
    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(a.get_result().summaries)

    # need to decide what needs returning from .summaries, probably clinvar_id and clinsig
       
if __name__ == "__main__":

    ir_json = get_json_data()
    clinvar_df = vcf_to_df()
    json_variants(ir_json)
    get_clinvar_ids(clinvar_df)
    get_clinvar_data(clinvar_list)