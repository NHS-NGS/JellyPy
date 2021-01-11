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

from get_gnomad_freq import gnomad_query
from get_json_variants import ReadJSON
from clinvar_query import clinvar_vcf_to_df, get_clinvar_ids, get_clinvar_data
from hgmd_query import hgmd_vcf_to_df, hgmd_variants
from paper_scraper import scrapePubmed
from variants_to_db import SQLQueries
from variant_validator_query import query_variantvalidator


class SampleAnalysis():

    def __init__(self):
        self.json_data = ReadJSON()
        self.scrape_pubmed = scrapePubmed()


    def get_json_data(self, json_file, all_panels, hgnc_df):
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

        ir_panel = self.json_data.get_panels(ir_json)
        print("ir_panels", ir_panel)

        # get info on each member of pedigree in JSON
        ir_members = self.json_data.get_members(ir_json)

        # get total no. variants in JSON
        total_variants = len(variant_list)

        # get genes of panels from PanelApp used to filter variants
        print("checking panelapp panels")

        analysis_panels = []
        panel_dicts = []

        for panel in ir_panel:
            # for each panel from JSON, get green genes from entry in PA
            # and latest version used
            for pa_panel in all_panels.keys():
                if all_panels[pa_panel].get_name() == panel[0]:
                    # panel name still a valid panel

                    # get latest version of panel
                    panel_name = all_panels[pa_panel].get_name()
                    ver = all_panels[pa_panel].get_version()
                    analysis_panels.append((panel_name, ver))

                    # returns list of dicts for each gene with symbol,
                    # hgnc id and ensembl ID
                    panel_dict = {}
                    panel_dict[panel_name] = all_panels[pa_panel].get_genes()
                    panel_dicts.append(panel_dict)

            if panel[0] not in analysis_panels:
                print("Panel not in keys")
                # panel not in names, try getting from disorders, used
                # in cases where panel names changed / panels merge etc.
                for pa_panel in all_panels.keys():
                    disorders = all_panels[pa_panel].get_relevant_disorders()
                    rel_disorder = [x for x in disorders if x == panel[0]]
                    if len(rel_disorder) != 0:
                        # panel found in relevant disorder list
                        # get latest version of panel
                        panel_name = all_panels[pa_panel].get_name()
                        ver = all_panels[pa_panel].get_version()
                        analysis_panels.append((
                            panel_name, ver
                        ))
                        panel_dict = {}
                        panel_dict[panel_name] = all_panels[pa_panel].get_genes()
                        panel_dicts.append(panel_dict)

        print("analysis panels: ", analysis_panels)
        print("Number of variants before: {}".format(len(position_list)))

        # build simple lists for variant matching
        ensembl_ids = []
        hgnc_ids = []
        gene_symbols = []

        for panel in panel_dicts:
            for k, v in panel.items():
                ensembl_ids.extend([x["ensembl_id"]["GRCh38"] for x in v])
                gene_symbols.extend([x["symbol"] for x in v])
                hgnc_ids.extend([x["hgnc_id"] for x in v])

        # keep variants only in panel genes
        panel_variants = []

        for var in variant_list:
            # check if variant is in gene by ensembl id, gene symbol,
            # hgnc id
            if var["ensemblId"] in ensembl_ids:
                panel_variants.append(var)
            elif var["gene"] in gene_symbols:
                panel_variants.append(var)
            else:
                # hgnc not in JSONs, get from hgnc txt file to match
                # against panel hgnc ids
                hgnc_id = hgnc_df[hgnc_df["symbol"] == var["gene"]]

                if hgnc_id.empty:
                    # hgnc id not identified from symbol, check in prev
                    # symbols
                    hgnc_id = hgnc_df[hgnc_df[
                        "prev_symbol"].astype(str).str.contains(var["gene"])]

                if not hgnc_id.empty:
                    # found hgnc id from current or porevious symbol
                    hgnc_id = hgnc_id.iloc[0]["hgnc_id"].split(':')[1]

                    if hgnc_id in hgnc_ids:
                        # id found, check against panel gene ids
                        panel_variants.append(var)

        variant_list = panel_variants

        # build simple list of chrom & pos for analysis
        position_list = []
        for var in variant_list:
            position_list.append((var["chromosome"], var["position"]))

        print("Number of variants after: ", len(position_list))

        analysis_variants = len(variant_list)

        return ir_id, ir_panel, hpo_terms, disorder_list, variant_list,\
            position_list, analysis_panels, total_variants, analysis_variants,\
            ir_members


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
            return None, None, None, None

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
        pubmed_columns = [
            "chromosome", "pos", "ref", "alt", "pmid", "title", "associated",
            "term", "url"
        ]
        pubmed_df = pd.DataFrame(columns=pubmed_columns)

        gnomad_columns = [
            "chromosome", "pos", "ref", "alt", "af", "cadd", "revel",
            "splice_ai", "splice_ai_cons", "primate_ai"
        ]

        gnomad_dtypes = {
            "chromosome": str, "pos": int, "ref": str, "alt": str, "af": str,
            "cadd": float, "revel": float, "splice_ai": float,
            "splice_ai_cons": str, "primate_ai": float
        }
        # create empty df for adding gnomad entries to
        gnomad_df = pd.DataFrame(columns=gnomad_columns)
        gnomad_df = gnomad_df.astype(gnomad_dtypes)

        print("Querying gnomAD & LitVar")

        for var in variant_list:
            query = "{}-{}-{}-{}".format(
                var["chromosome"], var["position"], var["ref"], var["alt"]
            )
            # get allele frequencies & in-silico predictions from gnomad
            gnomad = gnomad_query(query)

            if gnomad is not None:
                af = float(gnomad["af"])
                # check if cadd & splice_ai included in the predictions
                keys = [x["id"] for x in gnomad["in_silico_predictors"]]
                if "cadd" in keys:
                    cadd = [
                        x["value"] for x in gnomad["in_silico_predictors"]
                        if x["id"] == "cadd"
                    ][0]
                else:
                    cadd = None

                if "revel" in keys:
                    revel = [
                        x["value"] for x in gnomad["in_silico_predictors"]
                        if x["id"] == "revel"
                    ][0]
                else:
                    revel = None

                if "splice_ai" in keys:
                    sa = [x["value"] for x in gnomad["in_silico_predictors"]
                          if x["id"] == "splice_ai"][0]
                    sa = sa.split(" ", 1)

                    splice_ai = float(sa[0])
                    splice_ai_cons = sa[1].strip("()")
                else:
                    splice_ai = None
                    splice_ai_cons = None

                if "primate_ai" in keys:
                    primate_ai = [
                        x["value"] for x in gnomad["in_silico_predictors"]
                        if x["id"] == "primate_ai"
                    ][0]
                    primate_ai = float(primate_ai)
                else:
                    primate_ai = None
            else:
                # gnomAD response returned None
                af = None
                cadd = None
                revel = None
                splice_ai = None
                splice_ai_cons = None
                primate_ai = None

            # add to gnomad df
            data = {
                "chromosome": var["chromosome"],
                "pos": var["position"],
                "ref": var["ref"],
                "alt": var["alt"],
                "af": af,
                "cadd": cadd,
                "revel": revel,
                "splice_ai": splice_ai,
                "splice_ai_cons": splice_ai_cons,
                "primate_ai": primate_ai
            }

            gnomad_df = gnomad_df.append(data, ignore_index=True)

            if var["c_change"] is None:
                continue
                # c_change missing from json, use variant validator
                # to populate
                query_var = "{}:{}:{}:{}".format(
                    var["chromosome"], var["position"],
                    var["ref"], var["alt"]
                )

                response = query_variantvalidator(
                    "GRCh38", query_var, "all"
                )

                if response is not None:
                    # get just key with transcript & c_change
                    tx_key = [x for x in response.keys() if "_" in x]

                    for key in tx_key:
                        try:
                            var["c_change"] = key[0].split(":")[1]
                        except (IndexError, KeyError):
                            continue

            if var["c_change"]:
                print("Searching PubMed for papers")
                papers = None
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

        # remove any duplciate rows
        gnomad_df = gnomad_df.drop_duplicates()

        return clinvar_summary_df, hgmd_match_df, pubmed_df, gnomad_df


    def update_db(self, sql, ir_id, ir_panel, analysis_panels, total_variants,
                  analysis_variants, analysis_id, hpo_terms, variant_list,
                  clinvar_summary_df, hgmd_match_df, pubmed_df, gnomad_df,
                  ir_members):
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

        # save members for sample to member table
        sql.save_members(sql.cursor, sample_id, ir_members)

        # save original sample panels from JSON, passes if already saved
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

            if not gnomad_df.empty:
                # get gnomad results for current variant
                gnomad_entries = gnomad_df.loc[(
                    gnomad_df["pos"] == var["position"]
                ) & (
                    gnomad_df["chromosome"] == var["chromosome"]
                ) & (
                    gnomad_df["ref"] == var["ref"]
                ) & (
                    gnomad_df["alt"] == var["alt"]
                )]
            else:
                gnomad_entries = pd.DataFrame

            if not all(x.empty for x in [
                hgmd_entries, clinvar_entries, pubmed_entries, gnomad_entries
            ]):
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
                            "mol_cons": row["mol_cons"],
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
                            "hgmd_id": row["ID"], "chrom": row["chrom"],
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

                if not gnomad_entries.empty:
                    # should just be one entry, take first row
                    entry = gnomad_entries.iloc[0]

                    # save af to database
                    allele_freq_id = sql.save_af(sql.cursor, entry["af"])

                    # save in-silico predictions
                    in_silico_predictions_id = sql.save_in_silico(
                        sql.cursor, entry
                    )
                else:
                    allele_freq_id = None
                    in_silico_predictions_id = None


                # annotation added, add variant and link to annotation
                variant = {
                    "chrom": var["chromosome"], "pos": var["position"],
                    "tier": var["tier"], "ref": var["ref"], "alt": var["alt"],
                    "consequence": var["consequence"], "gene": var["gene"],
                    "transcript": var["transcript"],
                    "c_change": var["c_change"], "p_change": var["p_change"],
                    "ensemblId": var["ensemblId"],
                    "segregationPattern": var["segregationPattern"],
                    "modeOfInheritance": var["modeOfInheritance"]
                }

                variant_id = sql.save_variant(sql.cursor, variant)

                # save variant tier to tier table
                tier_id = sql.save_tier(sql.cursor, variant)

                # save variant to current sample analysis
                analysis_variant_id = sql.save_analysis_variant(
                    sql.cursor, analysis_sample_id, variant_id
                )

                # save variant attributes
                variant_attributes_id = sql.save_variant_attributes(
                    sql.cursor, variant
                )

                # link annotation to variant
                variant_annotation_id = sql.save_variant_annotation(
                    sql.cursor, tier_id, clinvar_id, hgmd_id,
                    analysis_variant_id, allele_freq_id,
                    in_silico_predictions_id, variant_attributes_id
                )

                # save zygosity of variant calls for var in each member
                for call in var["variantCalls"]:
                    zygosity_id = sql.save_zygosity(sql.cursor, call)
                    sql.save_zygosity_list(
                        sql.cursor, variant_annotation_id, zygosity_id
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
