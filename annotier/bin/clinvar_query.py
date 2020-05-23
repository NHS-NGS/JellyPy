"""
Functions to take a json of GEL variants, query against ClinVar VCF 
if present, and then return full ClinVar entry for those that are.

To do more than 3 requests per second to ClinVar this requires an NCBI 
account, and the email and api key passing to entrezpy. 
These are stored in ncbi_credentials.py in /bin.
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
    print("NCBI email and api_key must be defined in ncbi_credentials.py for "
        "querying ClinVar")
    sys.exit(-1)

# list to temporarialy store data in
clinvar_list = []

data_dir = os.path.join(os.path.dirname(__file__), "../data/")
clinvar_dir = os.path.join(os.path.dirname(__file__), "../data/clinvar/")

def clinvar_vcf_to_df():
    """
    Read in clinvar vcf to df for querying

    Args: None

    Returns:
        clinvar_df (dataframe): df of all ClinVar variants in vcf
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

    print("Reading HGMD Pro VCF")

    clinvar_df = pd.read_csv(vcf, header = [27], sep='\t', low_memory=False)

    return clinvar_df


def get_clinvar_ids(clinvar_df, position_list):
    """
    Function to query all variants in JSON against ClinVar df, returns 
    ids of those pathogenic and likely pathogenic

    Args:
        clinvar_df (dataframe): dataframe built from ClinVar vcf
        position_list (list): list of all variant GRCh38 positions and 
                              chromosome numbers from JSON

    Returns:
        clinvar_list (list): list of ClinVar IDs where position is in the 
                             input JSON
    """

    match_df = clinvar_df[clinvar_df[['#CHROM', 'POS']].apply(tuple, axis = 1
                ).isin(position_list)]

    for row in match_df.itertuples():
                
        if "CLNSIG=Pathogenic" in row.INFO or \
            "CLNSIG=Likely_pathogenic" in row.INFO:
            # add variant ID if classified as pathogenic or likely pathogenic
            clinvar_list.append(int(row.ID))
        
        if "CLNSIG=Conflicting_interpretations_of_pathogenicity" in row.INFO:
            clnsigconf = [i for i in row.INFO.split(";") if \
                            i.startswith("CLNSIGCONF")]
            # add variant ID if classified as pathogenic or likely 
            # pathogenic but with conflicts

            if "pathogenic" in clnsigconf[0].casefold():
                clinvar_list.append(int(row.ID))
    
    if len(clinvar_list) == 0:
        print("No matching variants identified in ClinVar")

    return clinvar_list


def get_clinvar_data(clinvar_list):
    """
    Take list of variants with pathogenic / likely pathogenic 
    clinvar entries and return full clinvar information through 
    NCBI eutils
    Requires NCBI email and api_key adding to ncbi_credentials.py to do 
    more than 3 requests per second

    Args:
        clinvar_list (list): list of ClinVar IDs where position is 
                             in the input JSON
    
    Returns:
        clinvar_summaries (dict): summary output for each 
                                  clinvar variant
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
    
    columns = ('clinvar_id', 'clinical_sig', 'date_last_rev', 'review_status',
                'var_type', 'supporting_subs', 'chrom', 'pos', 'ref', 'alt')

    rows_list = []

    for key, value in clinvar_summaries.items():

        # ref and alt not given in dict, need to pull from cdna_change field
        ref = value["variation_set"][0]["cdna_change"]
        ref = re.findall(r".*(.)&.*", ref)[0]

        alt = value["variation_set"][0]["cdna_change"].split(";")[1]

        row_dict = {}

        # select out required fields from returned eutils summary dict
        row_dict.update(
                        {
                        "clinvar_id": key,

                        "clinical_sig": value["clinical_significance"]
                                             ["description"],

                        "date_last_rev": value["clinical_significance"]
                                              ["last_evaluated"],

                        "review_status": value["clinical_significance"]
                                              ["review_status"],

                        "var_type": value["variation_set"][0]["variant_type"],

                        "supporting_subs": value["supporting_submissions"],

                        "start_pos": value["variation_set"][0]["variation_loc"]
                                          [0]["start"],

                        "end_pos": value["variation_set"][0]["variation_loc"]
                                        [0]["stop"],

                        "chrom": value["chr_sort"],

                        "ref": ref,

                        "alt": alt,

                        "protein_change": value["protein_change"]
                        }
                    ) 

        rows_list.append(row_dict)

    # build df from rows of ClinVar entries
    clinvar_summary_df = pd.DataFrame(rows_list) 
    
    return clinvar_summary_df


if __name__ == "__main__":

    clinvar_df = clinvar_vcf_to_df()

    clinvar_list = get_clinvar_ids(clinvar_df, position_list)

    if len(clinvar_list) != 0:
        get_clinvar_data(clinvar_list)
