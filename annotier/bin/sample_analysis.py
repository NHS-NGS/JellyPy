"""
Calls functions to:
    - check if new ClinVar VCF ver. is available
        - if so, downloads and extracts to /data/clinvar
    - read in a sample json, extract hpo terms and tiered variants
    - run reanalysis (currently against ClinVar and HGMD Pro)
    - save annotation to db
"""

import json
import sys
import re
import os
import pandas as pd
import pprint
import time

from get_json_variants import ReadJSON
from clinvar_query import clinvar_vcf_to_df, get_clinvar_ids, get_clinvar_data
from hgmd_query import hgmd_vcf_to_df, hgmd_variants
from variants_to_db import SQLQueries
from pubmed_query import scrapePubmed


sample_id = "55904-1"


class SampleAnalysis():

    def __init__(self):
        self.json_data = ReadJSON()
        self.pubmed = scrapePubmed()


    def get_json_data(self, json_file):
        """
        Call functions from get_json_variants to get HPO terms and tiered 
        variants for analysis
        """
        ir_json = self.json_data.read_json(json_file)
        
        ir_id = self.json_data.get_irid(ir_json)
        hpo_terms, disorder_list = self.json_data.get_hpo_terms(ir_json)
        variant_list, position_list = self.json_data.get_tiered_variants(ir_json)

        print("Number of variants: {}".format(len(position_list)))
        
        return ir_id, hpo_terms, disorder_list, variant_list, position_list


    def run_analysis(self, clinvar_df, hgmd_df, position_list, variant_list,
                        hpo_terms, disorder_list, hpo_df):
        """
        Call analysis functions, return outputs from each to import to db

        Args:
            position_list (list): list of all variant positions in json
            clinvar_df (dataframe): df of all ClinVar variants from VCF
            clinvar_list (list): list of ClinVar ids for tiered variants
            hgmd_df (dataframe): df of all HGMD variants


        Returns:
            clinvar_df (dataframe): df of all ClinVar variants from VCF
            clinvar_list (list): list of all ClinVar ent
            hgmd_df (dataframe): df of all HGMD variants from VCF

            clinvar_summary_df (dataframe): df of ClinVar entries for 
                                            tiered variants

            hgmd_match_df (dataframe): df of HGMD entries for 
                                    tiered variants
        """

        # get list of ClinVar entries for tiered variants
        clinvar_id_list = get_clinvar_ids(clinvar_df, position_list)
        
        if len(clinvar_id_list) != 0:
        # get full ClinVar entries with NCBI eutils, return in df
            clinvar_summary_df = get_clinvar_data(clinvar_id_list)

            print("Number of pathogenic/likely pathogenic ClinVar entries: {}".\
                    format(len(clinvar_summary_df.index)))
        else:
            # no pathogenic (or likely) in ClinVar
            clinvar_summary_df = None
        
        # get HGMD entries for tiered variants
        hgmd_match_df = hgmd_variants(hgmd_df, position_list)

        
        # empty df to store pubmed records in
        columns = ["chrom", "pos", "ref", "alt", "pmid", "title", "associated"]
        pubmed_df = pd.DataFrame(columns=columns)

        # get names for hpo terms from JSON, then clean
        hpo_names = self.pubmed.get_diseaseName(hpo_terms, disorder_list, hpo_df)
        clean_names = self.pubmed.clean_hpo_names(hpo_names)

        # get abstracts of papers inlcuding the variant, then scrape for related hpo term
        # all are saved, if includes hpo term then saved to db with associated=True

        # format variant as c. notation, search for variant plus any other change at same pos
        
        # make list of all combination of every variant c. change
        changes = []
        search_slices = []

        for variant in variant_list:

            # no c. notation available => can't search pubmed
            if not variant["c_change"]:
                continue
        
            if variant["c_change"] == "c.1975A>G":
                continue
            
            pattern = re.compile('^(c.)[0-9]*[A-Z]>[A-Z]')

            if pattern.match(variant["c_change"]):
                # pattern in format c.pos/ref/>/alt, remove alt to
                # search for all 3 possible alts, with & without *
                change = variant["c_change"].replace("+", "%2B")[:-1]+"+OR+"
                change_wc = variant["c_change"][:-1]+"*"+"+OR+"

                changes.append(change)
                changes.append(change_wc)
                
            else:
                # not a SNV (i.e indel), don't check for alt changes
                change = variant["c_change"].replace("+", "%2B")+"+OR+"
            
                changes.append(change)
        
        # divide c. change list into chunks of 100 for searching
        for i in range(0, len(changes), 1):
            chunk = changes[i:i + 1]
            chunk = "".join(chunk)
            search_slices.append(chunk[:-4])
         

        pmid_list = []

        # for each change at variant position, get ids of pubmed entries
        for chunk in search_slices:
            print("CHUNK", chunk)
            ids = self.pubmed.search(chunk)
            print(ids)
            if ids:
                pmid_list.extend(ids)

        sys.exit()
        
        pmid_list = list(set(pmid_list))

        print("pmid list: ", pmid_list)
        print(len(pmid_list))

        sys.exit()

        if len(pmid_list) != 0:
            # get abstracts of papers from id list
            print("getting abstracts")
            abs_list = self.pubmed.get_abstract(pmid_list)

            # scrape title abstract for presence of key words, returned in list of ids if present
            relevant_abs = self.pubmed.scrape_abstract(abs_list, clean_names)
            
            # add papers to pubmed df
            for paper in abs_list:
                if paper["id"] in relevant_abs:
                    associated="True"
                else:
                    associated="False"
                # add to df
                pubmed_df.append([variant["chromosome"], variant["position"], variant["ref"],
                                variant["alt"], paper["id"], paper["title"], associated])
            
        print("NEXT VARIANT")

        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print(pubmed_df)

        print("pubmed df")

        return clinvar_summary_df, hgmd_match_df, pubmed_df


    def update_db(self, sql, ir_id, analysis_id, hpo_terms, variant_list, clinvar_summary_df, hgmd_match_df, pubmed_df):
        """
        Update reanalysis database with outputs of analyses
        """

        # save sample to database with ir id, if exists just get db entry of sample
        sample_id = sql.save_sample(sql.cursor, ir_id)
        
        # add entry to analysis_sample table, uses current analysis ID
        analysis_sample_id = sql.save_analysis_sample(sql.cursor, analysis_id, sample_id)

        # for each variant in variant list, check if some annotation is found for position
        # if yes, save variant, if not then it is passed
        for var in variant_list:

            clinvar_entries = clinvar_summary_df.loc[(clinvar_summary_df['start_pos'] == var["position"]) & (clinvar_summary_df['chrom'] == var["chromosome"])]

            hgmd_entries = hgmd_match_df.loc[(hgmd_match_df['pos'] == var["position"]) & (hgmd_match_df['chrom'] == var["chromosome"])]
        
            pubmed_entires = pubmed_df.loc[(pubmed_df['position'] == var["position"]) & (pubmed_df['chromosome'] == var["chromosome"])]

            if all(len(df) == 0 for df in [hgmd_entries, clinvar_entries, pubmed_entires]):
                # no annotation found, go to next variant
                continue
            else:
                # some annotation found, save to tables and get id's if ref and alt same

                clinvar_id = None
                hgmd_id = None

                # save clinvar annotation
                if len(clinvar_entries) != 0:
                    for i, row in clinvar_entries.iterrows():
                        clinvar = {
                                    "clinvar_id": row["clinvar_id"], "clin_signficance": row["clin_signficance"], 
                                    "date_last_reviewed": row["date_last_reviewed"], "review_status": row["review_status"], 
                                    "var_type": row["var_type"], "supporting_submissions": row["supporting_submissions"],
                                    "chrom": row["chrom"], "pos": row["pos"], "ref": row["ref"], "alt": row["alt"]
                                    }
                        if clinvar["ref"] == var["ref"] and clinvar["alt"] == variant["alt"]:
                            # same ref & alt, link to variant
                            clinvar_id = sql.save_clinvar(sql.cursor, clinvar)
                        else:
                            # different ref & alt, just save
                            sql.save_clinvar(sql.cursor, clinvar)
                

                # save hgmd annotation
                if len(hgmd_entries) != 0:
                    for i, row in hgmd_entries.iterrows():
                        hgmd = {
                                "hgmd_id": row["hgmd_id"], "rank_score": row["rank_score"], 
                                "chrom": row["chrom"], "pos": row["pos"], 
                                "ref": row["ref"], "alt": row["alt"], "dna_change": row["dna_change"], 
                                "prot_change": row["prot_change"], 
                                "db": row["db"], "phenotype": row["phenotype"], "rs_id": row["rs_id"]
                                }
                        if hgmd["ref"] == var["ref"] and hgmd["alt"] == var["alt"]:
                            # same ref and alt, link to variant
                            hgmd_id = sql.save_hgmd(sql.cursor, hgmd)
                        else:
                            # different ref & alt, just save
                            sql.save_hgmd(sql.cursor, hgmd)

                pubmed_list = []

                # save pubmed annotation
                if len(pubmed_entires) != 0:
                    for i, row in pubmed_entires.itterows():
                        pub = {
                                "PMID": row["pmid"], "title": row["title"]
                            }

                        pub_id = sql.save_pubmed(sql.cursor, pub)

                        pubmed_list.append(
                                        {
                                            "pub_id": pub_id,
                                            "ref": row["ref"],
                                            "alt": row["alt"],
                                            "associated": row["associated"]
                                        }
                                        )
                
                pubmed_list_id = sql.save_pubmed_list(sql.cursor, pubmed_list)

                # annotation added, add variant and link to annotation

                variant = {
                            "chrom": var["chromosome"], "pos": var["position"], "tier": var["tier"],
                            "ref": var["ref"], "alt": var["alt"], "consequence": var["consequence"]
                            }

                variant_id = sql.save_variant(sql.cursor, variant)

                # save variant tier to tier table
                tier_id = sql.save_tier(sql.cursor, variant)

                # save variant to current sample analysis
                analysis_variant_id = sql.save_analysis_variant(sql.cursor, analysis_sample_id, variant_id)

                # link annotation to variant
                sql.save_variant_annotation(sql.cursor, tier_id, clinvar_id, hgmd_id, pubmed_list_id, analysis_variant_id)


if __name__ == "__main__":

    pass
