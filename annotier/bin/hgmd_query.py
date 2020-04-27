"""
Functions to take a json of GEL variants, query against HGMD Pro VCF 
and return any identified variants.

Requires downloading of HGMD pro in to data/hgmd
"""

import json
import sys
import re
import os
import pandas as pd
from clinvar_query import get_json_data, json_variants

dirname = os.path.dirname(__file__)
hgmd_dir = os.path.join(dirname, "../data/hgmd/")

def hgmd_vcf_to_df():
    """
    Read in HGMD vcf to df for querying
    """
    vcf = None

    for (dirpath, dirnames, filenames) in os.walk(hgmd_dir):
        for filename in filenames:
            if re.match("^hgmd_pro_[0-9\.]+_hg38.vcf$", filename):
                vcf = os.path.join(hgmd_dir, filename)
            else:
                continue

    if not vcf:
        print("HGMD hg38 vcf not found, please ensure it is in data/hgmd")
        sys.exit(-1)

    hgmd_df = pd.read_csv(vcf, header = [19], sep='\t', low_memory=False)

    return hgmd_df

def hgmd_variants(hgmd_df, position_list):
    """
    Query variant positions from JSON against HGMD vcf
    """

    hgmd_match_df = hgmd_df[hgmd_df[['#CHROM', 'POS']].apply(tuple, axis = 1).isin(position_list)]

    print(hgmd_match_df)

    for i, row in hgmd_match_df.iterrows():
        print(row["INFO"])

    return hgmd_match_df

if __name__ == "__main__":

    ir_json = get_json_data()
    variant_list, position_list = json_variants(ir_json)
    hgmd_df = hgmd_vcf_to_df()
    hgmd_variants(hgmd_df, position_list)

