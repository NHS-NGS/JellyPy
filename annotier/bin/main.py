import json
import os
import sys
import mysql.connector as mysql

from clinvar_query import clinvar_vcf_to_df
from get_clinvar_vcf import local_vcf, get_ftp_files, get_vcf, check_current_vcf
from hgmd_query import hgmd_vcf_to_df
from get_json_variants import ReadJSON
from sample_analysis import SampleAnalysis
from variants_to_db import SQLQueries
from pubmed_query import scrapePubmed

try:
    from db_credentials import db_credentials
except ImportError:
    print("Database credentials must be first defined. Exiting.")
    sys.exit(-1)

try:
    from ncbi_credentials import ncbi_credentials
except ImportError:
    print("NCBI email and api_key must be defined in ncbi_credentials.py for "
        "querying ClinVar")
    sys.exit(-1)


# main functions to run analysis for list of samples and generate report

samples=[
    "871-1",
    "981-1",
    "982-1",
    "26181-1",
    "44543-1",
    "55904-1"
    ]

"""to do:
    - call functions to:
        - check db connection
        - check for new clinvar vcf and download
        - read in hgmd vcf -> df
        - read in clinvar vcf -> df
        - maybe generate some database stats to compare to after
    - run get_analysis_run() and save_analysis()
        - return analysis ID
    - run single sample analysis
"""

def connect_db():
    """
    Establishes connection to database.
    """
    try:
        sql = SQLQueries(db_credentials)
    except mysql.Error as err:
        print("Error connecting to reanalysis database, exiting now.")
        print("Error: ", err)
        sys.exit()
    
    print("Successfully connected to database")

    return sql


def check_json():
    """
    Checks for JSONs present in appropriate dir
    """
    
    json_dir = os.path.join(os.path.dirname(__file__), "../data/ir_jsons/")
    json_total = 0

    # check if at least 1 JSON in the dir
    for file in os.listdir(json_dir):
        if file.endswith(".json"):
            json_total += 1
            
    if json_total == 0:
        print("Directory has no JSONs, nothing to do, exiting now.")
        sys.exit(-1)
    
    print("Number of JSONs for analysis:", json_total)

    return json_dir, json_total


def check_clinvar_ver():
    """
    Checks for new version of ClinVar on NSBI FTP site
    """
    local_vcf_ver = local_vcf()
    ftp_vcf, ftp_vcf_ver = get_ftp_files()
    get_vcf(ftp_vcf)
    check_current_vcf(ftp_vcf, ftp_vcf_ver, local_vcf_ver)


def read_clinvar():
    """
    Reads in ClinVar vcf to df for analysis.
    
    """
    clinvar_df, clinvar_ver = clinvar_vcf_to_df()

    print("ClinVar VCF loaded")

    return clinvar_df, clinvar_ver


def read_hgmd():
    """
    Reads in HGMD vcf to df for analysis.
    """
    hgmd_df, hgmd_ver = hgmd_vcf_to_df()

    print("HGMD VCF loaded")

    return hgmd_df, hgmd_ver


def read_hpo():
    """
    Reads in HPO phenotype file to df for analysis.

    Args: None

    Returns:
        - 
    """
    pubmed = scrapePubmed()

    hpo_df = pubmed.import_hpo()

    return hpo_df


def new_analysis(sql, clinvar_ver, hgmd_ver):
    """
    Create new analysis run entry in database.
    """
    # check previous run ID
    analysis_id = sql.get_analysis_run(sql.cursor)

    # add new analysis to database table
    sql.save_analysis(sql.cursor, analysis_id, clinvar_ver, hgmd_ver)

    return analysis_id


def run_analysis(sql, analysis_id, json_dir, clinvar_df, hgmd_df, hpo_df):
    """
    Go through each JSON in /data/ir_json and perform analysis, then save to database
    """
    sample = SampleAnalysis()
    # read JSON, get df of variants and other required variables

    # loop over data in dir, read json in, then run analysis, then save to database

    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            json_file = os.path.join(json_dir, filename)
            ir_id, hpo_terms, disorder_list, variant_list, position_list = sample.get_json_data(json_file)

            clinvar_summary_df, hgmd_match_df, pubmed_df = sample.run_analysis(clinvar_df, hgmd_df, position_list, variant_list, hpo_terms, disorder_list, hpo_df)
            
            print("Analysis of sample ", ir_id, "finished, saving to database")

            print(pubmed_df)

            sample.update_db(sql, ir_id, analysis_id, hpo_terms, variant_list, clinvar_summary_df, hgmd_match_df, pubmed_df)

            print("sample ", ir_id, "successfully saved to database")


if __name__ == "__main__":

    # do initial set up for analysis run (check database connection etc.)
    print("Performing initial set up checks for analysis")

    json_dir, json_total = check_json()
    sql = connect_db()
    #check_clinvar_ver()
    clinvar_df, clinvar_ver = read_clinvar()
    hgmd_df, hgmd_ver = read_hgmd()
    hpo_df = read_hpo()
    analysis_id = new_analysis(sql, clinvar_ver, hgmd_ver)

    # begin analysis on each sample and save to db
    print("Starting sample analysis")
    run_analysis(sql, analysis_id, json_dir, clinvar_df, hgmd_df, hpo_df)

