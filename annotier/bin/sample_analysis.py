"""
Calls functions to:
    - check if new ClinVar VCF ver. is available
        - if so, downloads and extracts to /data/clinvar
    - read in a sample json, extract hpo terms and tiered variants
    - run reanalysis (currently against ClinVar and HGMD Pro)
    - save annotation to db

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200506
"""

import json
import sys
import re
import os
import pandas as pd
import pprint
import time

from panelapp import api, Panelapp, queries

from get_json_variants import ReadJSON
from clinvar_query import clinvar_vcf_to_df, get_clinvar_ids, get_clinvar_data
from hgmd_query import hgmd_vcf_to_df, hgmd_variants
from paper_scraper import scrapePubmed
from variants_to_db import SQLQueries


class SampleAnalysis():

    def __init__(self):
        self.json_data = ReadJSON()
        self.scrape_pubmed = scrapePubmed()


    def get_json_data(self, json_file, all_panels):
        """
        Call functions from get_json_variants to get HPO terms and
        tiered variants for analysis

        Args:
            - json_file (file): input IR JSON
            - all_panels (dict): all PanelApp panels (from main.get_panels())

        Returns:
            - ir_id (int): ID of IR sample
            - hpo_terms (list): list of HPO terms from JSON
            - disorder_list (list): list of disorder terms from JSON
            - variant_list (list): list of dicts with variant info
            - position list (list): list of tuples with variant positons
            - analysis_panels (list): list of tuples for each panel and
                version used for reanalysis (panel_name, version)
        """
        ir_json = self.json_data.read_json(json_file)

        # get sample and variant data from json
        ir_id = self.json_data.get_irid(ir_json)
        hpo_terms, disorder_list = self.json_data.get_hpo_terms(ir_json)
        variant_list, position_list = self.json_data.get_tiered_variants(
            ir_json)
        ir_panel = self.json_data.get_disease(variant_list)

        # get total no. variants in JSON
        total_variants = len(variant_list)

        # get genes of panels from PanelApp used to filter variants
        panel_genes = []
        all_panel_hashes = {}
        analysis_panels = []

        print("checking panelapp panels")
        # build dict of all PanelApp panel hashes -> panel ids
        for id, panel in all_panels.items():
            if panel.get_data()["hash_id"] is not None:
                all_panel_hashes[panel.get_data()["hash_id"]] = id

        print("ir panels")
        print(ir_panel)

        # get panel genes for each panel in JSON
        for panel in ir_panel:
            if panel[1] in all_panel_hashes or panel[1].isdigit():
                # JSON panel hash in PA hash dict or panel ID in hash
                # field, get panel genes
                if panel[1].isdigit():
                    panel_id = int(panel[1])
                else:
                    panel_id = all_panel_hashes[panel[1]]

                panel = all_panels[panel_id]
                name = panel.get_data()["name"]
                ver = panel.get_data()["version"]

                for gene in all_panels[panel_id].get_data()["genes"]:
                    if gene["confidence_level"] == "3":
                        # check each gene in panel is green
                        panel_genes.append(gene["entity_name"])
                        # panel_genes.extend(all_panels[panel_id].get_genes())

                if name and ver:
                    analysis_panels.append((name, ver))
            else:
                # JSON panel hash not in PA hash dict, check panel name
                # against relevenat disorder list and disease groups as
                # not "specificDisease" from JSON can be either
                print("no hash match")
                fields = [
                    "relevant_disorders",
                    "disease_group",
                    "disease_sub_group"
                ]

                for pa_panel in all_panels.values():
                    # check ir_panel name against each field, break if found
                    for field in fields:
                        if panel[0] in pa_panel.get_data()[field]:
                            print(panel[0], field)
                            # match panel
                            for gene in pa_panel.get_data()["genes"]:
                                if gene["confidence_level"] == "3":
                                    # check each gene in panel is green
                                    panel_genes.append(
                                        gene["gene_data"]["gene_symbol"]
                                    )
                                    # panel_genes.extend(pa_panel.get_genes())
                                # get panel name and version to record
                                name = pa_panel.name
                                ver = pa_panel.version
                            if name and ver:
                                analysis_panels.append((name, ver))
                            break

        print("Number of variants before: {}".format(len(position_list)))

        # keep variants only in panel genes
        variant_list = [x for x in variant_list if x['gene'] in panel_genes]

        # build simple list of chrom & pos for analysis
        position_list = []
        for var in variant_list:
            position_list.append((var["chromosome"], var["position"]))

        print("Number of variants after: ", len(position_list))

        analysis_variants = len(variant_list)

        return ir_id, ir_panel, hpo_terms, disorder_list, variant_list,\
            position_list, analysis_panels, total_variants, analysis_variants


    def run_analysis(self, clinvar_df, hgmd_df, position_list, variant_list,
                     hpo_terms, disorder_list, hpo_df):
        """
        Call analysis functions, return outputs from each to import to db

        Args:
            - clinvar_df (dataframe): df of all ClinVar variants
              from VCF
            - hgmd_df (dataframe): df of all HGMD variants from VCF
            - position list (list): list of tuples with variant positons
            - variant list (list): list of dicts with variant info
            - hpo_terms (list): list of HPO terms from JSON
            - disorder_list (list): list of disorder terms from JSON
            - hpo_df (df): df of HPO term info

        Returns:
            - clinvar_summary_df (dataframe): df of ClinVar entries for
                                            tiered variants
            - hgmd_match_df (dataframe): df of HGMD entries for
                                    tiered variants
        """
        # if no variants found in panel regions, return none to skip
        if len(position_list) == 0:
            print("No variants in panel regions, skipping analysis")
            return None, None, None

        # get list of ClinVar entries for tiered variants
        clinvar_id_list = get_clinvar_ids(clinvar_df, position_list)
        print("Clinvar ID list: ", clinvar_id_list)

        if len(clinvar_id_list) != 0:
            # get full ClinVar entries with NCBI eutils, return in df
            clinvar_summary_df = get_clinvar_data(clinvar_id_list)

            print("Number of pathogenic/likely pathogenic ClinVar entries:\
                {}". format(len(clinvar_summary_df.index)))
        else:
            # no pathogenic (or likely) in ClinVar
            clinvar_summary_df = None

        # get HGMD entries for tiered variants
        hgmd_match_df = hgmd_variants(hgmd_df, position_list)

        # empty df to store pubmed records in
        columns = [
            "chromosome", "pos", "ref", "alt", "pmid", "title","associated",
            "term", "url"
        ]
        pubmed_df = pd.DataFrame(columns=columns)

        for var in variant_list:
            if var["c_change"]:
                # if c. notation available, search for papers
                papers = self.scrape_pubmed.main(var, hpo_terms)
                if papers:
                    for paper in papers:
                        dict = {
                            "chromosome": var["chromosome"],
                            "pos": var["position"],
                            "ref": var["ref"],
                            "alt": var["alt"],
                            "pmid": paper["pmid"],
                            "title": paper["title"],
                            "associated": paper["associated"],
                            "term": paper["term"],
                            "url": paper["url"]
                        }
                        pubmed_df = pubmed_df.append(dict, ignore_index=True)
                
                dtypes = {
                    'chromosome': str, 'pos': int, 'ref': str, 'alt': str,
                    'pmid': int, 'title': str, 'associated': bool,
                    'term': str, 'url': str
                }

                pubmed_df = pubmed_df.astype(dtypes)

        return clinvar_summary_df, hgmd_match_df, pubmed_df


    def update_db(self, sql, ir_id, ir_panel, analysis_panels, total_variants,
                  analysis_variants, analysis_id, hpo_terms, variant_list,
                  clinvar_summary_df, hgmd_match_df, pubmed_df):
        """
        Update reanalysis database with outputs of analyses.

        Args:
            - ir_id (int): id of IR sample
            - analysis_id (int): row ID of sample in analysis table
              from VCF
            - hpo_terms (list): list of HPO terms from JSON
            - variant list (list): list of dicts with variant info
            - clinvar_summary_df (dataframe): df of ClinVar entries for
                                            tiered variants
            - hgmd_match_df (dataframe): df of HGMD entries for
                                    tiered variants

        Returns: None
        """
        # save sample to database with ir id, if exists just get db
        # entry of sample
        sample_id = sql.save_sample(sql.cursor, ir_id, total_variants)

        # save sample original panels from JSON, passes if already saved
        sql.save_sample_panel(sql.cursor, sample_id, ir_panel)

        # add entry to analysis_sample table, uses current analysis ID
        analysis_sample_id = sql.save_analysis_sample(
            sql.cursor, analysis_id, sample_id, analysis_variants)

        # save record of versions used for reanalysis of each panel
        sql.save_analysis_panel(
            sql.cursor, analysis_sample_id, analysis_panels
        )

        # for each variant in variant list, check if some annotation
        # is found for position if yes, save variant, if not then it
        # is passed
        for var in variant_list:
            print("variant")
            print(var)
            print("pubmed dataframe")
            print(pubmed_df)

            if clinvar_summary_df is not None:
                clinvar_entries = clinvar_summary_df.loc[(
                    clinvar_summary_df['start_pos'] == var["position"]
                ) & (
                    clinvar_summary_df['chrom'] == var["chromosome"]
                )]
            else:
                clinvar_entries = pd.DataFrame

            if hgmd_match_df is not None:
                hgmd_entries = hgmd_match_df.loc[(
                    hgmd_match_df['pos'] == var["position"]
                ) & (
                    hgmd_match_df['chrom'] == var["chromosome"]
                )]
            else:
                hgmd_entries = pd.DataFrame

            if pubmed_df is not None:
                # get papers for current variant
                pubmed_entries = pubmed_df.loc[(
                    pubmed_df["pos"] == var["position"]
                ) & (
                    pubmed_df["chromosome"] == var["chromosome"]
                ) & (
                    pubmed_df["ref"] == var["ref"]
                ) & (
                    pubmed_df["alt"] == var["alt"]
                )]
            else:
                pubmed_entries = pd.DataFrame

            if not all(x.empty for x in [
                hgmd_entries, clinvar_entries, pubmed_entries]
            ):
                # some annotation found, save to tables and get id's if
                # ref and alt same save clinvar annotation
                if not clinvar_entries.empty:
                    for i, row in clinvar_entries.iterrows():
                        clinvar = {
                            "clinvar_id": row["clinvar_id"],
                            "clin_signficance": row["clinical_sig"],
                            "date_last_reviewed": row["date_last_rev"],
                            "review_status": row["review_status"],
                            "var_type": row["var_type"],
                            "supporting_submissions": row["supporting_subs"],
                            "chrom": row["chrom"], "pos": row["start_pos"],
                            "ref": row["ref"], "alt": row["alt"]
                        }

                        if clinvar["ref"] == var["ref"] and clinvar["alt"] == var["alt"]:
                            # same ref & alt, link to variant
                            clinvar_id = sql.save_clinvar(sql.cursor, clinvar)
                        else:
                            # different ref & alt, just save
                            sql.save_clinvar(sql.cursor, clinvar)
                            clinvar_id = None
                else:
                    clinvar_id = None

                # save hgmd annotation
                if not hgmd_entries.empty:
                    for i, row in hgmd_entries.iterrows():
                        hgmd = {
                            "hgmd_id": row["ID"],"chrom": row["chrom"],
                            "pos": row["pos"], "ref": row["REF"],
                            "alt": row["ALT"], "dna_change": row["DNA"],
                            "prot_change": row["PROT"], "db": row["DB"],
                            "phenotype": row["PHEN"],
                            "rankscore": row["RANKSCORE"]
                        }
                        if hgmd["ref"] == var["ref"] and hgmd["alt"] == var["alt"]:
                            # same ref and alt, link to variant
                            hgmd_id = sql.save_hgmd(sql.cursor, hgmd)
                        else:
                            # different ref & alt, just save
                            sql.save_hgmd(sql.cursor, hgmd)
                            hgmd_id = None
                else:
                    hgmd_id = None

                # annotation added, add variant and link to annotation

                variant = {
                    "chrom": var["chromosome"], "pos": var["position"],
                    "tier": var["tier"], "ref": var["ref"], "alt": var["alt"],
                    "consequence": var["consequence"], "gene": var["gene"]
                }

                variant_id = sql.save_variant(sql.cursor, variant)

                # save variant tier to tier table
                tier_id = sql.save_tier(sql.cursor, variant)

                # save variant to current sample analysis
                analysis_variant_id = sql.save_analysis_variant(
                    sql.cursor, analysis_sample_id, variant_id
                )

                # link annotation to variant
                variant_annotation_id = sql.save_variant_annotation(
                    sql.cursor, tier_id, clinvar_id, hgmd_id,
                    analysis_variant_id
                )

                # save pubmed annotation, has to be last as requires
                # annotation ID
                if not pubmed_entries.empty:
                    for i, row in pubmed_entries.iterrows():
                        # save pubmed entry
                        pub = {
                            "pmid": row["pmid"], "title": row["title"],
                            "url": row["url"]
                        }
                        pubmed_id = sql.save_pubmed(sql.cursor, pub)

                        # link pubmed entry to variant annotation
                        pub_list = {
                            "annotation_id": variant_annotation_id,
                            "pubmed_id": pubmed_id,
                            "associated": row["associated"],
                            "term": row["term"]
                        }
                        sql.save_pubmed_list(sql.cursor, pub_list)
            else:
                # no annotation found, go to next variant
                continue


if __name__ == "__main__":

    pass
