"""
Functions to take a json of GEL variants, query against ClinVar VCF
if present, and then return full ClinVar entry for those that are.

To do more than 3 requests per second to ClinVar this requires an NCBI
account, and the email and api key passing to entrezpy.
These are stored in ncbi_credentials.py in /bin.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200303
"""

import json
import sys
import time
import re
import os
import pandas as pd
import pprint
import entrezpy.esummary.esummarizer
import entrezpy.efetch.efetcher


try:
    from ncbi_credentials import ncbi_credentials
except ImportError:
    print("NCBI email and api_key must be defined in ncbi_credentials.py for\
        querying ClinVar")
    sys.exit(-1)

data_dir = os.path.join(os.path.dirname(__file__), "../data/")
clinvar_dir = os.path.join(os.path.dirname(__file__), "../data/clinvar/")


def clinvar_vcf_to_df():
    """
    Read in clinvar vcf to df for querying

    Args: None

    Returns:
        clinvar_df (dataframe): df of all ClinVar variants in vcf
        local_clinvar_ver (str): latest version of ClinVar vcf downloaded
    """
    # set paths to dirs
    data_dir = os.path.join(os.path.dirname(__file__), "../data/")
    clinvar_dir = os.path.join(os.path.dirname(__file__), "../data/clinvar/")

    local_clinvar_ver = 0

    for (dirpath, dirnames, filenames) in os.walk(clinvar_dir):
        for filename in filenames:
            if re.match("^clinvar_[0-9]+\.vcf$", filename):
                # get just the clinvar vcf
                vcf_ver = int(filename.split("_")[1].split(".")[0])
                if vcf_ver > local_clinvar_ver:
                    # if multiple vcfs in data select just the latest
                    local_clinvar_ver = vcf_ver
                    vcf = os.path.join(clinvar_dir, filename)
                else:
                    continue

    if 'vcf' not in locals():
        # ClinVar vcf not found
        print("ClinVar VCF not found in clinvar dir. Exiting.")
        sys.exit(-1)

    clinvar_df = pd.read_csv(vcf, header=[27], sep='\t', low_memory=False)

    return clinvar_df, local_clinvar_ver


def get_clinvar_ids(clinvar_df, position_list):
    """
    Function to query all variants in JSON against ClinVar df, returns
    ids of those pathogenic and likely pathogenic

    Args:
        clinvar_df (dataframe): dataframe built from ClinVar vcf
        position_list (list): list of all variant GRCh38 positions and
                              chromosome numbers from JSON

    Returns:
        clinvar_list (list): list of ClinVar IDs where position is in
                            the input JSON
    """

    # list to pass clinvar ids with ref and alt as these are not
    # returned in esummary from clinvar
    clinvar_id_list = []

    match_df = clinvar_df[
        clinvar_df[['#CHROM', 'POS']].apply(tuple, axis=1).isin(position_list)
    ]
    print("Matching ClinVar entries: ", match_df)
    for i, row in match_df.iterrows():
        print(row["INFO"])

    clinsig = ["CLNSIG=Pathogenic", "CLNSIG=Likely_pathogenic"]

    for row in match_df.itertuples():
        try:
            # get molecular consequence from VCF INFO field as it is not
            # in the API reponse
            mol_cons = [x for x in row.INFO.split(';') if x.startswith('MC')][0]
            mol_cons = mol_cons.split('|')[1].split(',')[0]
        except Exception:
            # molecular consequence field probably missing
            mol_cons = None

        if any(x in row.INFO for x in clinsig):
            # add variant ID if classified as pathogenic or
            # likely pathogenic
            clinvar_id_list.append({
                "clinvar_id": row.ID,
                "ref": row.REF,
                "alt": row.ALT,
                "mol_cons": mol_cons
            })

        if "CLNSIG=Conflicting_interpretations_of_pathogenicity" in row.INFO:
            clnsigconf = [
                i for i in row.INFO.split(";") if i.startswith("CLNSIGCONF")
            ]
            # add variant ID if classified as pathogenic or likely
            # pathogenic but with conflicts

            if "pathogenic" in clnsigconf[0].casefold():
                clinvar_id_list.append({
                    "clinvar_id": row.ID,
                    "ref": row.REF,
                    "alt": row.ALT,
                    "mol_cons": mol_cons
                })

    if len(clinvar_id_list) == 0:
        print("No matching variants identified in ClinVar")

    return clinvar_id_list


def get_clinvar_data(clinvar_id_list):
    """
    Take list of variants with pathogenic / likely pathogenic
    clinvar entries and return full clinvar information through
    NCBI eutils
    Requires NCBI email and api_key adding to ncbi_credentials.py to do
    more than 3 requests per second

    Args:
        clinvar_id_list (list): list of ClinVar IDs where position is
                             in the input JSON

    Returns:
        clinvar_summaries (dict): summary output for each
                                  clinvar variant
    """

    e = entrezpy.esummary.esummarizer.Esummarizer(
        "clinvar_summary",
        ncbi_credentials["email"],
        apikey=ncbi_credentials["api_key"],
        apikey_var=ncbi_credentials["api_key"],
        threads=4,
        qid=None
    )

    # get clinvar ids from list to search with
    clinvar_ids = [d['clinvar_id'] for d in clinvar_id_list]

    if len(clinvar_ids) < 20:
        clinvar_ids = [clinvar_ids]
    else:
        # split id's into smaller lists
        clinvar_ids = [
            clinvar_ids[i:i + 20] for i in range(0, len(clinvar_ids), 20)
        ]

    clinvar_summaries = {}

    for ids in clinvar_ids:
        for i in range(1, 5):
            # call to eutils API
            try:
                a = e.inquire({'db': 'clinvar', 'id': ids})
                summaries = a.get_result().summaries
                clinvar_summaries.update(summaries)
                break
            except Exception as e:
                print("Error in entrezpy, try: {}/5".format(i))
                print("Error: {}".format(e))
                time.sleep(2)
                continue

    rows_list = []

    for key, value in clinvar_summaries.items():

        # ref and alt not returned in summary, so get from previously
        # generated clinvar_ids_list
        id_match = next(
            (item for item in clinvar_id_list if item["clinvar_id"] == key),
            None
        )

        if id_match is not None:
            # check in case ref and alt were missing
            ref = id_match["ref"]
            alt = id_match["alt"]
            mol_cons = id_match["mol_cons"]
        else:
            ref, alt, mol_cons = None, None, None

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

                "protein_change": value["protein_change"],

                "mol_cons": mol_cons
            }
        )

        rows_list.append(row_dict)

    # build df from rows of ClinVar entries
    clinvar_summary_df = pd.DataFrame(rows_list)

    dtypes = {
        'start_pos': int, 'end_pos': int, 'supporting_subs': str
    }
    clinvar_summary_df = clinvar_summary_df.astype(dtypes)

    return clinvar_summary_df


if __name__ == "__main__":

    clinvar_df, local_clinvar_ver = clinvar_vcf_to_df()

    position_list = [('11', 64758458)]

    clinvar_id_list = get_clinvar_ids(clinvar_df, position_list)

    if len(clinvar_id_list) != 0:
        get_clinvar_data(clinvar_id_list)
