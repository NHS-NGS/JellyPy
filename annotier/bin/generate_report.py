"""
Functions to query variants from analysis run.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
201118
"""
import argparse
from datetime import datetime
import os
import sys

from functools import reduce
import mysql.connector as mysql
import numpy as np
from openpyxl import Workbook
from operator import mul
import pandas as pd
from string import Template


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


    def filter_tier_df(self, query_df, filter_df):
        """
        Filters df of tiered variants for also being a higher tier, req.
        as variant may have been reporcessed and tiered differently i.e.
        tier 3 -> tier 2; need to remove from tier 3 df

        Args:
            - query_df (df): df of 'lower' tier variants to filter
            - filter_df (df): df of 'higher' tier variants to filter
            with

        Returns:
            - filtered_df (df): df of filtered query df
        """
        filter_cols = ["ir_id", "chr", "pos", "ref", "alt"]

        # get variants unique to just the df being filtered
        query_vars = query_df[filter_cols].drop_duplicates()
        filter_vars = filter_df[filter_cols].drop_duplicates()
        filtered_vars = pd.concat([query_vars, filter_vars]).drop_duplicates(
            keep=False
        )

        # select full row from original df of unique, filtered variants
        filtered_df = pd.merge(
            filtered_vars, query_df, how='inner', on=filter_cols
        )

        return filtered_df


    def get_members(self):
        """
        Get all members from db members table, used to identify proband
        """
        self.cursor.execute(
            "SELECT participantID, isProband, affectionStatus, "
            "relation_to_proband FROM member"
        )

        members = self.cursor.fetchall()

        members_df = pd.DataFrame(members, columns=[
            "participantId", "isProband", "affectionStatus", "probandRelation"
        ])

        return members_df


    def get_analysis_runs(self):
        """
        Query analysis table to get most recent analyses
        """
        self.cursor.execute("SELECT * FROM analysis")
        runs = self.cursor.fetchall()

        runs_df = pd.DataFrame(
            runs, columns=["id", "date", "clinvar_ver", "hgmd_ver"]
        )

        return runs_df


    def get_run_stats(self, run):
        """
        Get totals of variants analysed
        """
        self.cursor.execute(
            "SELECT sample.ir_id, sample.total_variants, analysis_sample."
            "variants FROM sample LEFT JOIN analysis_sample ON analysis_sample"
            ".sample_id = sample.sample_id LEFT JOIN analysis ON analysis."
            "analysis_id = analysis_sample.analysis_id WHERE analysis."
            f"analysis_id={run};"
        )
        vars = self.cursor.fetchall()

        # returns list of tuples with id, total variants, analysed
        # variants
        total_samples = len(vars)
        total_vars = sum([x[1] for x in vars])
        analysis_variants = sum([x[2] for x in vars])
        total_no_vars = len([x[2] for x in vars if x[2] == 0])

        return total_samples, total_vars, total_no_vars


    def get_run_variants(self, run):
        """
        Get all unfiltered variants for a run and split into tiered df's

        Args:
            - cursor (obj): mysql db connector object
            - run (int): run number to return variants for

        Returns:
            - tier1_df (df): df of tier 1 variants
            - tier2_df (df): df of tier 2 variants
            - tier3_df (df): df of tier 3 variants
            - tier_none_df (df): df of variants with tier none
        """
        print("Getting all variants from run")
        self.cursor.execute(
            "SELECT sample.ir_id, analysis_sample.analysis_id, variant.chrom, "
            "variant.pos, variant.ref, variant.alt, tier.tier, sample_panel.name, "
            "sample_panel.version, analysis_panel.name, analysis_panel.version, "
            "clinvar.clinvar_id, clinvar.clin_significance, clinvar.review_status, "
            "clinvar.date_last_reviewed, "
            "hgmd.hgmd_id, hgmd.rank_score, pubmed.PMID, pubmed_list.associated, "
            "pubmed_list.term, allele_freq.gnomad_af, var_zygosity.zygosity, "
            "var_zygosity.participantId,variant_attributes.segregationPattern, "
            "variant_attributes.gene, "
            "variant_attributes.modeOfInheritance, in_silico_predictions.cadd, "
            "in_silico_predictions.revel, in_silico_predictions.splice_ai, "
            "in_silico_predictions.splice_ai_cons, "
            "in_silico_predictions.primate_ai "
            "FROM "
            "variant_annotation "
            "LEFT JOIN analysis_variant ON "
            "variant_annotation.analysis_variant_id = "
            "analysis_variant.analysis_variant_id LEFT JOIN analysis_sample "
            "ON analysis_variant.analysis_sample_id = "
            "analysis_sample.analysis_sample_id LEFT JOIN sample ON "
            "analysis_sample.sample_id = sample.sample_id LEFT JOIN "
            "sample_panel ON sample.sample_id = sample_panel.sample_id "
            "LEFT JOIN analysis_panel ON analysis_sample.analysis_sample_id = "
            "analysis_panel.analysis_sample_id "
            "LEFT JOIN variant "
            "ON analysis_variant.variant_id = variant.variant_id LEFT JOIN "
            "variant_attributes ON variant_annotation.variant_attributes_id = "
            "variant_attributes.variant_attributes_id "
            "LEFT JOIN "
            "tier ON variant_annotation.tier_id = tier.tier_id LEFT JOIN "
            "clinvar on variant_annotation.clinvar_id = clinvar.clinvar_id "
            "LEFT JOIN allele_freq ON variant_annotation.allele_freq_id = "
            "allele_freq.allele_freq_id LEFT JOIN hgmd ON "
            "variant_annotation.hgmd_id = hgmd.hgmd_id LEFT JOIN pubmed_list "
            "ON variant_annotation.annotation_id = pubmed_list.annotation_id "
            "LEFT JOIN pubmed ON pubmed.pubmed_id = pubmed_list.pubmed_id "
            "LEFT JOIN var_zygosity_list ON variant_annotation.annotation_id "
            "= var_zygosity_list.annotation_id LEFT JOIN var_zygosity ON "
            "var_zygosity_list.var_zygosity_id = var_zygosity.var_zygosity_id "
            "LEFT JOIN in_silico_predictions ON "
            "variant_annotation.in_silico_predictions_id = "
            "in_silico_predictions.in_silico_predictions_id "
            "WHERE analysis_sample.analysis_id=46;"
        )

        vars = self.cursor.fetchall()

        cols = [
            "ir_id", "analysis_id", "chr", "pos", "ref", "alt", "tier",
            "sp_name", "sp_ver", "ap_name", "ap_ver", "clinvar_id", "clin_sig",
            "review_status", "last_reviewed", "hgmd_id", "hgmd_score", "PMID",
            "pubmed_associated", "term", "gnomad_af", "zygosity",
            "participantId", "segregationPattern", "gene", "MoI", "CADD", "REVEL",
            "splice_ai", "splice_ai_cons", "primate_ai"
        ]

        run_variants_df = pd.DataFrame(vars, columns=cols)

        object_cols = [
            "review_status", "chr", "ref", "alt", "tier", "sp_name", "sp_ver",
            "ap_name", "ap_ver", "clin_sig", "hgmd_id", "PMID",
            "pubmed_associated", "term", "gnomad_af", "zygosity",
            "participantId", "segregationPattern", "splice_ai_cons"
        ]

        # set more efficient dtypes to reduce memory usage
        for col in object_cols:
            run_variants_df[col] = run_variants_df[col].astype("category")
        run_variants_df["analysis_id"] = run_variants_df[
            "analysis_id"].astype('int16')
        run_variants_df["pos"] = run_variants_df["pos"].astype('int32')

        # get member info and add to variants
        members_df = self.get_members()
        run_variants_df = pd.merge(
            run_variants_df, members_df, how='inner', on='participantId'
        )

        # split dfs by tier
        tier1_df = run_variants_df[run_variants_df['tier'] == 'TIER1']
        tier2_df = run_variants_df[run_variants_df['tier'] == 'TIER2']
        tier3_df = run_variants_df[run_variants_df['tier'] == 'TIER3']
        tier_none_df = run_variants_df[run_variants_df['tier'] == 'None']

        # filter variants from each tier against presence in higher tier
        # filter tier 2
        tier2_df = self.filter_tier_df(tier2_df, tier1_df)

        # filter tier 3
        tier3_df = self.filter_tier_df(tier3_df, tier1_df)
        tier3_df = self.filter_tier_df(tier3_df, tier2_df)

        # filter tier none
        tier_none_df = self.filter_tier_df(tier_none_df, tier1_df)
        tier_none_df = self.filter_tier_df(tier_none_df, tier2_df)
        tier_none_df = self.filter_tier_df(tier_none_df, tier3_df)

        return tier1_df, tier2_df, tier3_df, tier_none_df


    def get_tier_totals(self, tier1_df, tier2_df, tier3_df, tier_none_df):
        """
        Get total variants at each tier
        """
        print("Getting tier totals")
        tier_totals = dict()

        tier1_df.name = 'tier1'
        tier2_df.name = 'tier2'
        tier3_df.name = 'tier3'
        tier_none_df.name = 'tier_none'

        for df in [tier1_df, tier2_df, tier3_df, tier_none_df]:
            tier_totals[f'{df.name}_total'] = self.return_total(df)
            tier_totals[f'{df.name}_clinvar'] = self.return_total(
                self.filter_clinvar(df)
            )
            tier_totals[f'{df.name}_clinvar_hgmd'] = self.return_total(
                self.filter_clinvar_hgmd(df)
            )

        # calculate totals at each filter level
        tier_totals['unfilter_total'] = sum([
            tier_totals['tier1_total'], tier_totals['tier2_total'],
            tier_totals['tier3_total'], tier_totals['tier_none_total']
        ])
        tier_totals['clinvar_total'] = sum([
            tier_totals['tier1_clinvar'], tier_totals['tier2_clinvar'],
            tier_totals['tier3_clinvar'], tier_totals['tier_none_clinvar']
        ])
        tier_totals['clinvar_hgmd_total'] = sum([
            tier_totals['tier1_clinvar_hgmd'],
            tier_totals['tier2_clinvar_hgmd'],
            tier_totals['tier3_clinvar_hgmd'],
            tier_totals['tier_none_clinvar_hgmd']
        ])

        return tier_totals


    @staticmethod
    def filter_clinvar(tier_df):
        """
        Filter df of variants for having clinvar entry
        """
        return tier_df[tier_df.clinvar_id.notnull()]


    @staticmethod
    def filter_clinvar_hgmd(tier_df):
        """
        Filter df of variants for having clinvar & hgmd entry
        """
        return tier_df[tier_df[['clinvar_id', 'hgmd_id']].notnull().all(1)]


    @staticmethod
    def return_total(tier_df):
        """Returns total unique variants in a df"""
        return len(tier_df[[
            'ir_id', 'chr', 'pos', 'ref', 'alt', 'tier']].drop_duplicates())


    def format_variant_table(self, variant_df):
        """
        Format df to display properly in report

        Args:
            - variant_df (df): df of tiered variants
        Returns:
            - formatted_df (df): df with formatting for displaying
        """
        # set categorical types back to objects to allow formatting
        object_cols = [
            "review_status", "chr", "ref", "alt", "tier", "sp_name", "sp_ver",
            "ap_name", "ap_ver", "clin_sig", "hgmd_id", "PMID",
            "pubmed_associated", "term", "gnomad_af", "zygosity",
            "participantId", "segregationPattern", "splice_ai_cons"
        ]

        for col in object_cols:
            variant_df[col] = variant_df[col].astype(object)

        # set pmid to int to remove .0
        variant_df["PMID"] = variant_df["PMID"].fillna(0.0).astype(int)
        variant_df.astype('str').dtypes

        # format sample and analysis panel names and versions and pmids to one
        # col
        variant_df['s_panel'] = variant_df["sp_name"] + " (" + variant_df[
            "sp_ver"].astype(str) + ")"

        variant_df['a_panel'] = variant_df["ap_name"] + " (" + variant_df[
            "ap_ver"].astype(str) + ")"

        variant_df["PMID"] = variant_df["PMID"].astype(
            str) + " (related: " + variant_df["pubmed_associated"].astype(
            str) + "; Term: " + variant_df["term"].astype(str) + ")"

        variant_df["PMID"] = variant_df["PMID"].apply(
            lambda row: row.replace("0.0", "No").replace("1.0", "Yes")
        )

        variant_df["isProband"] = variant_df["isProband"].apply(
            lambda row: str(row).replace("0", "No").replace("1", "Yes")
        )

        # format where no papers identified
        variant_df["PMID"] = variant_df["PMID"].apply(
            lambda row: "No papers identified" if
            row == "0 (related: nan; Term: None)" else row
        )

        # remove unneeded columns
        variant_df = variant_df.drop([
            "sp_name", "sp_ver", "ap_name",
            "ap_ver", "pubmed_associated", "term"
        ], axis=1)

        vals = [
            "s_panel", "a_panel", "tier", "MoI", "segregationPattern",
            "clinvar_id", "clin_sig", "review_status", "last_reviewed",
            "hgmd_id", "hgmd_score", "PMID", "gnomad_af", "CADD", "REVEL",
            "splice_ai", "splice_ai_cons", "primate_ai"
        ]

        # beautiful excel formatting for readability
        formatted_df = pd.pivot_table(
            variant_df, index=[
                "ir_id", "chr", "pos", "ref",
                "alt", "gene", "participantId", "isProband", "affectionStatus",
                "probandRelation", "zygosity"
            ], values=vals,
            aggfunc=lambda x: ' / '.join([str(v) for v in x]))

        # change column order
        formatted_df = formatted_df[[
            "MoI", "segregationPattern", "s_panel", "a_panel", "tier",
            "clinvar_id", "clin_sig", "review_status", "last_reviewed",
            "hgmd_id", "hgmd_score", "PMID", "gnomad_af", "CADD", "REVEL",
            "splice_ai", "splice_ai_cons", "primate_ai"
        ]]

        dup_cols = [
            "s_panel", "a_panel", "tier", "clinvar_id", "clin_sig",
            "review_status", "last_reviewed", "hgmd_id", "hgmd_score",
            "gnomad_af", "CADD", "REVEL", "splice_ai", "splice_ai_cons",
            "primate_ai", "MoI", "segregationPattern"
        ]

        # remove duplicate entries for each column
        for col in dup_cols:
            formatted_df[col] = formatted_df[col].apply(lambda row: " / ".join(
                (list(set([x.strip() for x in row.split("/")]))))
            )

        # add line breaks for displaying in column within cell
        for panel in ["a_panel", "s_panel", "PMID"]:
            formatted_df[panel] = formatted_df[panel].apply(lambda row: " \n ".join(
                (list(set([x.strip() for x in row.split("/")]))))
            )

        formatted_df = formatted_df.rename(columns={
            's_panel': 'Original Panel(s)', 'a_panel': 'Analysis Panel(s)',
            'tier': 'Tier', 'clinvar_id': 'ClinVar ID',
            'clin_sig': 'Clinical Significance', 'MoI': 'modeOfInheritance',
            'review_status': 'Review Status', 'hgmd_id': 'HGMD ID',
            'hgmd_score': 'HGMD Score', "last_reviewed": "Last Reviewed"
        })

        return formatted_df


class generateReport():

    @staticmethod
    def read_template():
        """
        Read in HTML template for report

        Args: None

        Returns:
            - html_template (str): report template
        """
        bin_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(bin_dir, "../data/templates/")
        single_template = os.path.join(template_dir, "report_template.html")

        with open(single_template, 'r') as template:
            html_template = template.read()

        return html_template


    @staticmethod
    def read_bootstrap():
        """
        Read in bootstrap for styling report

        Args: None
        Returns:
            - bootstrap (str): str of bootstrap file to store in report
        """
        bs = str(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "../data/css/bootstrap.min.css"
        ))
        with open(bs) as bs:
            bootstrap = bs.read()

        return bootstrap


    def generate(self, tier3_df):
        """
        Format data, pass to build to combine with template then write
        file

        Args:
            -

        Returns:
            - 
        """
        html_template = self.read_template()
        bootstrap = self.read_bootstrap()

        tier3_df = tier3_df.style\
            .set_table_attributes(
                'class="dataframe table table-striped"')\
            .set_properties(**{
                'font-size': '0.40vw', 'table-layout': 'auto', 'max-width': '100%'
            })

        tier3_table = tier3_df.render()

        report = self.build(html_template, bootstrap, tier3_table)
        self.write(report)


    def build(self, html_template, bootstrap, tier3_table):
        """
        """
        t = Template(html_template)

        date = datetime.today().strftime('%Y-%m-%d')

        report = t.safe_substitute(
            bootstrap=bootstrap,
            tier3_table=tier3_table
        )

        return report


    def write(self, report):
        """
        """
        # write report
        bin_dir = os.path.dirname(os.path.abspath(__file__))
        out_dir = os.path.join(bin_dir, "../")
        outfile = os.path.join(out_dir, "annotier_report.html")

        file = open(outfile, 'w')
        file.write(report)
        file.close()


def generate_report(total_samples, total_vars, runs_df, tier_totals,
                    tier1_df, tier2_df, tier3_df, tier_none_df):
    """
    Generate xlsx report

    Args:
        - 
    """ 
    xlsx = Workbook()
    sheet = xlsx.active

    date = datetime.today().strftime('%Y-%m-%d')
    outfile = f'annotier_report_{date}.xlsx'

    # build summary sheet and add formatting
    sheet['A1'] = f'Reanalysis report generated with annoTier ({date})'
    sheet['A3'] = f'Total samples analysed: {total_samples}'
    sheet['A4'] = f'Date of analysis: {runs_df.iloc[-1]["date"]}'
    sheet['A5'] = f'Total variants: {total_vars}'
    sheet['A6'] = ('Total variants in panel regions: '
                   f'{tier_totals["unfilter_total"]}')
    sheet['A7'] = ('Total variants with entry in ClinVar: '
                   f'{tier_totals["clinvar_total"]}')
    sheet['A8'] = ('Total variants with entry in ClinVar & HGMD: '
                   f'{tier_totals["clinvar_hgmd_total"]}')
    sheet['A10'] = 'Tier 1 totals:'
    sheet['B11'] = f'Unfiltered: {tier_totals["tier1_total"]}'
    sheet['B12'] = f'ClinVar: {tier_totals["tier1_clinvar"]}'
    sheet['B13'] = f'ClinVar & HGMD: {tier_totals["tier1_clinvar_hgmd"]}'
    sheet['A15'] = 'Tier 2 totals:'
    sheet['B16'] = f'Unfiltered: {tier_totals["tier2_total"]}'
    sheet['B17'] = f'ClinVar: {tier_totals["tier2_clinvar"]}'
    sheet['B18'] = f'ClinVar & HGMD: {tier_totals["tier2_clinvar_hgmd"]}'
    sheet['A20'] = 'Tier 3 totals:'
    sheet['B21'] = f'Unfiltered: {tier_totals["tier3_total"]}'
    sheet['B22'] = f'ClinVar: {tier_totals["tier3_clinvar"]}'
    sheet['B23'] = f'ClinVar & HGMD: {tier_totals["tier3_clinvar_hgmd"]}'
    sheet['A25'] = 'Tier None totals:'
    sheet['B26'] = f'Unfiltered: {tier_totals["tier_none_total"]}'
    sheet['B27'] = f'ClinVar: {tier_totals["tier_none_clinvar"]}'
    sheet['B28'] = f'ClinVar & HGMD: {tier_totals["tier_none_clinvar_hgmd"]}'

    for i in range(1, 8):
        sheet.merge_cells(f'A{i}:F{i}')

    sheet.column_dimensions['B'].auto_size = True

    xlsx.save(filename=outfile)

    # add tables of tiered variants to separate sheets
    with pd.ExcelWriter(outfile, mode='a') as w:
        tier3_df.to_excel(w, sheet_name='tier3')
        tier2_df.to_excel(w, sheet_name='tier2')
        tier1_df.to_excel(w, sheet_name='tier1')
        tier_none_df.to_excel(w, sheet_name='tierNone')

    print("Report generated: ", '/'.join([os.getcwd(), outfile]))


def main():
    report = generateReport()
    sql = dbQueries(db_credentials)

    # get data
    runs_df = sql.get_analysis_runs()
    last_run = runs_df.iloc[-1]['id']
    prev_run = runs_df.iloc[-2]['id']
    total_samples, total_vars, total_no_vars = sql.get_run_stats(last_run)
    tier1_df, tier2_df, tier3_df, tier_none_df = sql.get_run_variants(last_run)

    # format & calculate values
    tier_totals = sql.get_tier_totals(
        tier1_df, tier2_df, tier3_df, tier_none_df
    )

    # filter each df of variants for ones present in clinvar
    tier1_df = sql.filter_clinvar(tier1_df)
    tier2_df = sql.filter_clinvar(tier2_df)
    tier3_df = sql.filter_clinvar(tier3_df)
    tier_none_df = sql.filter_clinvar(tier_none_df)

    print("Formatting tables")
    tier1_df = sql.format_variant_table(tier1_df)
    tier2_df = sql.format_variant_table(tier2_df)
    tier3_df = sql.format_variant_table(tier3_df)
    tier_none_df = sql.format_variant_table(tier_none_df)

    for k, v in tier_totals.items():
        print(k, " : ", v)

    generate_report(
        total_samples, total_vars, runs_df, tier_totals, tier1_df, tier2_df,
        tier3_df, tier_none_df
    )


if __name__ == "__main__":
    main()
