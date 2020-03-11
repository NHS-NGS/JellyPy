import json
import sys
import os
import pandas as pd
import pprint
import entrezpy.esummary.esummarizer

from ncbi_credentials import ncbi_credentials

# lists to temporarialy store data in
variant_list = []
position_list = []
clinvar_list = []

def get_json_data():
    # temporary test json until using cipapi
    sample_json = os.path.expanduser("~/annoTier_local_data/sample_ir.json")

    with open(sample_json) as json_file:
        ir_json = json.load(json_file)
    
    return ir_json

def vcf_to_df():
    # Read in clinvar vcf to df for querying
    vcf = os.path.expanduser("../data/annoTier_local_data/clinvar.vcf")
    clinvar_df = pd.read_csv(vcf, header = [27], sep='\t')

    return clinvar_df

def json_variants():
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

def get_clinvar_ids():
    """
    Function to query all variants in JSON against ClinVar VCF
    """
    for pos in position_list:
        if len(clinvar_df[clinvar_df['POS'].isin([pos])]) != 0:
            match = clinvar_df[clinvar_df['POS'].isin([pos])]
            print(match)

            if match["INFO"].str.contains("pathogenic").bool():
                clinvar_list.append(int(match.iloc[0]["ID"]))
                          
    return clinvar_list

def get_clinvar_data(clinvar_list):
    """
    Take list of variants with clinvar entries and return full clinvar entry
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
       
if __name__ == "__main__":

    json_variants()
    get_clinvar_ids()
    get_clinvar_data(clinvar_list)