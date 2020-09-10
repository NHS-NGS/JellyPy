"""
Functions to take a json of GEL variants, query against HGMD Pro VCF 
and return any identified variants in formatted dataframe.

Requires downloading of HGMD pro in to data/hgmd
"""

import json
import sys
import re
import os
import pandas as pd

def hgmd_vcf_to_df():
    """
    Read in HGMD vcf to df for querying

    Args: None

    Returns:
        hgmd_df (dataframe): df of all variants in HGMD Pro vcf
    """
    
    hgmd_dir = os.path.join(os.path.dirname(__file__), "../data/hgmd/")

    vcf = None

    for (dirpath, dirnames, filenames) in os.walk(hgmd_dir):
        for filename in filenames:
            if re.match("^hgmd_pro_[0-9\.]+_hg38.vcf$", filename):
                vcf = os.path.join(hgmd_dir, filename)
                hgmd_ver = filename.strip(".vcf")
                print("HGMD ver: ", hgmd_ver)
            else:
                continue

    if not 'vcf' in locals():
        print("HGMD hg38 vcf not found, please ensure it is in data/hgmd")
        sys.exit(-1)
    
    # read VCF into df
    hgmd_df = pd.read_csv(vcf, header = [19], sep='\t', low_memory=False)

    return hgmd_df, hgmd_ver


def hgmd_variants(hgmd_df, position_list):
    """
    Query variant positions from JSON against HGMD vcf

    Args:
        hgmd_df (dataframe): df of all variants in HGMD Pro vcf
        position_list (list): list of all  variant positions in json

    Returns:
        hgmd_df_match (dataframe): df of all HGMD variants in json
    """

    hgmd_match_df = hgmd_df[hgmd_df[['#CHROM', 'POS']].apply(tuple, axis = 1
                    ).isin(position_list)]
    
    hgmd_match_df = hgmd_match_df.rename(columns={'#CHROM': 'chrom',
                                            'POS': 'pos'})
    
    # create empty columns to split required INFO fields to
    split_info = ['CLASS','DNA','PROT','DB','PHEN','RANKSCORE']
    

    hgmd_match_df = hgmd_match_df.reindex(columns=[
            *hgmd_match_df.columns.tolist(), *split_info], fill_value="None")
 
    for i, row in hgmd_match_df.iterrows():

        info = row["INFO"].split(";")        
        
        # fields in INFO aren't consistently present so
        # check for existence then update df field if present
        CLSS = [s for s in info if "CLASS" in s]
        DNA = [s for s in info if "DNA" in s]
        PROT = [s for s in info if "PROT" in s]        
        DB = [s for s in info if "DB" in s]
        PHEN = [s for s in info if "PHEN" in s]
        RS = [s for s in info if "RANKSCORE" in s]

        if CLSS:
            hgmd_match_df.at[i, 'CLASS'] = CLSS[0].split("=")[1]
        if DNA:
            hgmd_match_df.at[i, 'DNA'] = DNA[0].split("=")[1]
        if PROT:
            hgmd_match_df.at[i, 'PROT'] = PROT[0].split("=")[1]
        if DB:
            hgmd_match_df.at[i, 'DB'] = DB[0].split("=")[1]
        if PHEN:
            hgmd_match_df.at[i, 'PHEN'] = PHEN[0].split("=")[1].strip('"')
        if RS:
            hgmd_match_df.at[i, 'RANKSCORE'] = RS[0].split("=")[1]

    # drop unndeed info field
    hgmd_match_df = hgmd_match_df.drop("INFO", 1)

    return hgmd_match_df


if __name__ == "__main__":

    ir_json = get_json_data()
    variant_list, position_list = json_variants(ir_json)
    hgmd_df = hgmd_vcf_to_df()
    hgmd_variants(hgmd_df, position_list)

