"""
Main script to start new analysis run of annotier.
Outline of analysis steps:
    - Checks database is available and connection can be made
    - Checks /data/ir_jsons contains JSONs
    - Checks for newer ClinVar VCF from NCBI FTP site.
    - Reads both ClinVar and HGMD VCF into memory
    - Creates new entry in analysis table, this ID is used for all
      samples in one analysis run
    - Begins analysis, this is done from by sample_analysis.py.
      Each sample is analysed then if variants with some pathogenic
      annotation are found they are saved to the database.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200522
"""

import json
import os
import sys
import mysql.connector as mysql

from panelapp import queries

from clinvar_query import clinvar_vcf_to_df
from get_clinvar_vcf import local_vcf, get_ftp_files, get_vcf,\
    check_current_vcf
from hgmd_query import hgmd_vcf_to_df
from get_json_variants import ReadJSON
from sample_analysis import SampleAnalysis
from variants_to_db import SQLQueries

try:
    from db_credentials import db_credentials
except ImportError:
    print("Database credentials must be first defined. Exiting.")
    sys.exit(-1)

try:
    from ncbi_credentials import ncbi_credentials
except ImportError:
    print("NCBI email and api_key must be defined in ncbi_credentials.py for\
        querying ClinVar")
    sys.exit(-1)


def connect_db():
    """
    Establishes connection to database.

    Args: None

    Returns:
        - sql: MySQL database connection object
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

    json_dir = os.path.join(
        os.path.dirname(__file__), "../data/ir_jsons/passJSON/")
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

    Args: None

    Returns:
        - clinvar_df (df): df of all ClinVar variants in VCF
        - clinvar_ver (int): version of ClinVar VCF used for analysis
    """
    clinvar_df, clinvar_ver = clinvar_vcf_to_df()

    print("ClinVar VCF loaded")

    return clinvar_df, clinvar_ver


def read_hgmd():
    """
    Reads in HGMD vcf to df for analysis.

    Args: None

    Returns:
        - hgmd_df (df): df of all HGMD variants in VCF
        - hgmd_ver (int): version of HGMD VCF used for analysis
    """
    hgmd_df, hgmd_ver = hgmd_vcf_to_df()

    print("HGMD VCF loaded")

    return hgmd_df, hgmd_ver


def get_panels():
    """
    Use panelapp package to query PanelApp for all panels, used to
    filter variants against those just in panel genes

    Args: None

    Returns:
        - all_panels (dict): all PanelApp panels
    """
    print("Getting panels from PanelApp")
    all_panels = queries.get_all_panels()

    return all_panels


def read_hpo():
    """
    Reads in HPO phenotype file to df for analysis.

    Args: None

    Returns:
        - hpo_df (df): df of all hpo terms from hpo file
    """
    pubmed = scrapePubmed()

    hpo_df = pubmed.import_hpo()

    return hpo_df


def new_analysis(sql, clinvar_ver, hgmd_ver):
    """
    Create new analysis run entry in database.

    Args:
        - sql: MySQL database connection object
        - clinvar_ver (int): version of ClinVar VCF used for analysis
        - hgmd_ver (int): version of HGMD VCF used for analysis

    Returns:
        - analysis_id (int): current analysis row ID in analysis table
    """
    # check previous run ID
    analysis_id = sql.get_analysis_run(sql.cursor)

    # add new analysis to database table
    sql.save_analysis(sql.cursor, analysis_id, clinvar_ver, hgmd_ver)

    return analysis_id


def run_analysis(sql, all_panels, analysis_id, json_dir, json_total,
                 clinvar_df, hgmd_df, hpo_df):
    """
    Go through each JSON in /data/ir_json and perform analysis,
    then save to database

    Args:
        - sql: MySQL database connection object
        - analysis_id (int): current analysis row ID in analysis table
        - jsoin_dir (str): path to dir of JSONs
        - clinvar_df (df): df of all ClinVar variants in VCF
        - hgmd_df (df): df of all HGMD variants in VCF
        - hpo_df (df): df of all hpo terms from hpo file

    Returns: None
    """
    sample = SampleAnalysis()
    # read JSON, get df of variants and other required variables

    # loop over data in dir, read json in, run analysis, then save to database
    file_counter = 1

    for filename in os.listdir(json_dir):
        if filename.endswith(".json"):
            print("Analysing sample {}/{}".format(file_counter, json_total))
            json_file = os.path.join(json_dir, filename)

            ir_id, hpo_terms, disorder_list,\
                variant_list, position_list = sample.get_json_data(
                    json_file, all_panels
                )

            clinvar_summary_df, hgmd_match_df, pubmed_df = sample.run_analysis(
                clinvar_df, hgmd_df, position_list, variant_list, hpo_terms,
                disorder_list, hpo_df
            )

            print("Analysis of sample ", ir_id, "finished, saving to database")

            sample.update_db(
                sql, ir_id, analysis_id, hpo_terms, variant_list,
                clinvar_summary_df, hgmd_match_df, pubmed_df
            )

            print("sample ", ir_id, "successfully saved to database")


if __name__ == "__main__":

    # do initial set up for analysis run (check database connection etc.)
    print("Performing initial set up checks for analysis\n")

    json_dir, json_total = check_json()
    sql = connect_db()
    # check_clinvar_ver()
    clinvar_df, clinvar_ver = read_clinvar()
    hgmd_df, hgmd_ver = read_hgmd()
    all_panels = get_panels()
    # hpo_df = read_hpo()
    hpo_df = None
    analysis_id = new_analysis(sql, clinvar_ver, hgmd_ver)

    # begin analysis on each sample and save to db
    print("Starting sample analysis")
    run_analysis(sql, all_panels, analysis_id, json_dir, json_total,
                 clinvar_df, hgmd_df, hpo_df)
