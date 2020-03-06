"""
Functions to query ClinVar for tiered variants

NCBI don't like lots of requests so will take too long to use eutils, sadness :(
Keeping in archive incase eutils is useful in future for anything

"""

import json
import sys
import os
import time
import entrezpy.esearch.esearcher
#import entrezpy.esummary.esummarizer


from ncbi_credentials import ncbi_credentials

# temporary test json until using cipapi
sample_json = os.path.expanduser("~/annoTier_local_data/sample_ir.json")
with open(sample_json) as json_file:
    sample_data = json.load(json_file)

# lists to temporarialy store data in
variant_list = []
clinvar_list = []

def json_variants():

    for variant in (
        sample_data["interpretation_request_data"]
        ["json_request"]["TieredVariants"]
    ):
        position = variant["position"]
        chrom = variant["chromosome"]
        tier = variant["reportEvents"][0]["tier"]

        variant_list.append({"position": position, "chromosome": chrom, "tier": tier})
    
    return variant_list

def check_uid_uniqeness(result):
    """This function tests if using multiple requests per query continue
    properly"""
    uniq = {}
    dupl_count = {}
    for i in result.uids:
      if i not in uniq:
        uniq[i] = 0
      uniq[i] += 1
      if uniq[i] > 1:
        dupl_count[i] = uniq[i]
    if len(uniq) !=  result.size():
      print("!: ERROR: Found  {} duplicate uids. Not expected. Duplicated UIDs:".format(len(dupl_count)))
      for i in dupl_count:
        print("{}\t{}".format(i, dupl_count[i]))
      return False
    return True



def get_clinvar_ids(variant_list):
   
    clinvar_ids = []

    for variant in variant_list:
        print("variant info:", variant)

        e = entrezpy.esearch.esearcher.Esearcher("get_clinvar_ids",
                ncbi_credentials["email"],
                apikey = ncbi_credentials["api_key"],
                apikey_var=ncbi_credentials["api_key"],
                threads=4
                )

        analyser = e.inquire({'db': 'clinvar',
                            'term' : '{}[CPOS] {}[chr]'.format(
                                variant["position"], variant["chromosome"]),
                            })
     
        if analyser.isEmpty():
            print("Nothing found")

        if check_uid_uniqeness(analyser.get_result()):
            if analyser.get_result().retmax == analyser.result.size():
                print("ok")
            else:
                print("failed")                 
            print(analyser.get_result().uids)
            clinvar_ids.append(analyser.get_result().uids)


def get_clinvar_data(clinvar_ids):
    e = entrezpy.esummary.esummarizer.Esummarizer(clinvar_summary,
                ncbi_credentials.email,
                apikey = ncbi_credentials.api_key,
                apikey_var=None,
                threads = 4,
                qid = None
                )
    
    analyser = e.inquire({'db': 'clinvar', 'id': clinvar_ids})

if __name__ == "__main__":

    json_variants()
    get_clinvar_ids(variant_list)
    # get_clinvar_data()


