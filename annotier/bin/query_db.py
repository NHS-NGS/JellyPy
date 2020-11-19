"""
Functions to query variants from analysis run.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
201118
"""

import argparse
import os
import pandas as pd
import sys
import mysql.connector as mysql

try:
    from db_credentials import db_credentials
except ImportError:
    print("Database credentials must be first defined. Exiting.")
    sys.exit()


class dbQueries(object):

    def __init__(self, db_credentials):
        """
        Open connection to database
        Initialises self.cursor object to perform queries in other functions

        Args:
            - db_credentials (dict): credentials to connect to MySQL DB

        Returns: None
        """

        self.db = mysql.connect(
            host=db_credentials["host"],
            user=db_credentials["user"],
            passwd=db_credentials["passwd"],
            database=db_credentials["database"],
            autocommit=True
        )
        self.cursor = self.db.cursor(buffered=True)


    def analysis_variants(self, cursor, run):
        """
        """
        cursor.execute("SELECT * FROM select_all_34")
        vars = cursor.fetchall()

        header = [
            "ir_id", "chr", "position", "ref", "alt", "tier", "clinvar_id",
            "clinvar_sig", "hgmd_id", "hgmd_rs", "pmid", "pmid_rel", "af",
            "zygosity", "participant_id", "cadd", "revel", "splice_ai",
            "splice_ai_cons", "primate_ai"
        ]

        # create df with returned database object
        run_vars = pd.DataFrame(vars, columns=header)

        # set pmid to int to remove .0
        run_vars["pmid"] = run_vars["pmid"].fillna(0.0).astype(int)

        run_vars.astype('str').dtypes

        vals = [
            "tier", "clinvar_id", "clinvar_sig", "hgmd_id", "hgmd_rs", "pmid",
            "pmid_rel", "af", "cadd", "revel", "splice_ai", "splice_ai_cons",
            "primate_ai"
        ]

        # beautiful excel formatting for readability
        new = pd.pivot_table(
            run_vars, index=[
                "ir_id", "chr", "position", "ref",
                "alt", "participant_id", "zygosity"
            ], values=vals,
            aggfunc=lambda x: ' / '.join([str(v) for v in x]))

        # change column order
        new = new[[
            "tier", "clinvar_id", "clinvar_sig", "hgmd_id", "hgmd_rs", "pmid",
            "pmid_rel", "af", "cadd", "revel", "splice_ai", "splice_ai_cons",
            "primate_ai"
        ]]

        dup_cols = [
            "tier", "clinvar_id", "clinvar_sig", "hgmd_id", "hgmd_rs", "af",
            "cadd", "revel", "splice_ai", "splice_ai_cons", "primate_ai"
        ]

        # remove duplicate entries for each column except pmid
        for col in dup_cols:
            new[col] = new[col].apply(lambda row: " / ".join(
                (list(set([x.strip() for x in row.split("/")]))))
            )
        
        new["pmid_rel"] = new["pmid_rel"].apply(lambda row: " / ".join(
            (list(set([x.strip() ])))
        ))

        with pd.option_context('display.max_rows', None):
            print(new)

        # write to file
        new.to_excel("100k_variants.xlsx")


def parse_args():
    """
    """
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_1 = subparsers.add_parser(
        'get_variants', help='Get total and analysed variants for all cases on\
        an analysis run.'
    )
    parser_1.add_argument(
        '--run', type=str, help='Analysis run to retrieve variants from.\
            Default: most recent.', default=None
    )
    parser_1.set_defaults(query='variants')

    args = parser.parse_args()

    return args


def main():
    sql = dbQueries(db_credentials)

    args = parse_args()
    query = args.query


    if query == "variants":
        if not args.run:
            run = None
        else:
            run = args.run

        sql.analysis_variants(sql.cursor, run)


if __name__ == "__main__":
    main()