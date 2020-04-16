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

try:
    from ncbi_credentials import ncbi_credentials
except ImportError:
    print("NCBI email and api_key must be first defined in ncbi_credentials.py for querying ClinVar")
    sys.exit(-1)

# lists to temporarialy store data in
variant_list = []
position_list = []
clinvar_list = []

dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, "../data/")
clinvar_dir = os.path.join(dirname, "../data/clinvar/")

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
    local_vcf_ver = 0

    for (dirpath, dirnames, filenames) in os.walk(clinvar_dir):
        for filename in filenames:
            if re.match("^clinvar_[0-9]+\.vcf$", filename):
                # get just the clinvar vcf
                vcf_ver = int(filename.split("_")[1].split(".")[0])
                if vcf_ver > local_vcf_ver:
                    # if multiple vcfs in data select just the latest
                    local_vcf_ver = vcf_ver
                    vcf = os.path.join(clinvar_dir, filename)
                else:
                    continue

    clinvar_df = pd.read_csv(vcf, header = [27], sep='\t', low_memory=False)
    print(clinvar_df)
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
        position_list.append((chrom, position))
    
    return variant_list, position_list

def get_clinvar_ids(clinvar_df, position_list):
    """
    Function to query all variants in JSON against ClinVar df, returns ids of those pathogenic and likely pathogenic

    Args:
        clinvar_df (dataframe): dataframe built from ClinVar vcf
        position_list (list): list of all variant GRCh38 positions and chromosome numbers from JSON

    Returns:
        clinvar_list (list): list of ClinVar IDs where position is in the input JSON
    """

    match_df = clinvar_df[clinvar_df[['#CHROM', 'POS']].apply(tuple, axis = 1).isin(position_list)]

    for row in match_df.itertuples():
                
        if "CLNSIG=Pathogenic" in row.INFO or "CLNSIG=Likely_pathogenic" in row.INFO:
            # add variant ID if classified as pathogenic or likely pathogenic
            clinvar_list.append(int(row.ID))
        
        if "CLNSIG=Conflicting_interpretations_of_pathogenicity" in row.INFO:
            clnsigconf = [i for i in row.INFO.split(";") if i.startswith("CLNSIGCONF")]

            if "pathogenic" in clnsigconf[0].casefold():
                # add variant ID if classified as pathogenic or likely pathogenic but with conflicts
                clinvar_list.append(int(row.ID))
    
    if len(clinvar_list) == 0:
        print("No matching variants identified in ClinVar")
        
    return clinvar_list

def get_clinvar_data(clinvar_list):
    """
    Take list of variants with pathogenic / likely pathogenic 
    clinvar entries and return full clinvar information through NCBI eutils
    Requires NCBI email and api_key adding to ncbi_credentials.py to do more than 3 requests per second

    Args:
        clinvar_list (list): list of ClinVar IDs where position is in the input JSON
    
    Returns:
        clinvar_summaries (dict): summary output for each clinvar variant
    """
    
    e = entrezpy.esummary.esummarizer.Esummarizer("clinvar_summary",
                ncbi_credentials["email"],
                apikey = ncbi_credentials["api_key"],
                apikey_var=ncbi_credentials["api_key"],
                threads = 4,
                qid = None
                )
    
    a = e.inquire({'db': 'clinvar', 'id': clinvar_list})
    clinvar_summaries = a.get_result().summaries

    pp = pprint.PrettyPrinter(indent=1)
    pp.pprint(clinvar_summaries)

    # need to decide what needs returning from .summaries, probably clinvar_id and clinsig
    
    return clinvar_summaries

if __name__ == "__main__":

    ir_json = get_json_data()
    clinvar_df = vcf_to_df()
    json_variants(ir_json)
    get_clinvar_ids(clinvar_df, position_list)
    if len(clinvar_list) != 0:
        get_clinvar_data(clinvar_list)
