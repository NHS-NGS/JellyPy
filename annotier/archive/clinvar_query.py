import json
import sys
import os
import time

from Bio import Entrez

# temporary test json until use cipapi
with open("/mnt/storage/home/rainfoj/sample_ir.json") as json_file:
    sample_data = json.load(json_file)

variant_list = []
clinvar_list = []

Entrez.email="rainford1995@gmail.com"

for variant in (
    sample_data["interpretation_request_data"]
    ["json_request"]["TieredVariants"]
):
    position = variant["position"]
    chrom = variant["chromosome"]
    tier = variant["reportEvents"][0]["tier"]

    variant_list.append({"position": position, "chromosome": chrom, "tier": tier})

print(variant_list)

for variant in variant_list:

    handle = Entrez.esearch(db="clinvar", term="{}[CPOS] {}[chr]".format(position, chrom))
    record = Entrez.read(handle)
    handle.close()

    clinvar_id = record["IdList"]

    print(clinvar_id)

    if clinvar_id:
        #clinvar_list.append(clinvar_id)
        variant_list["clinvar_id"] = "clinvar_id"

    time.sleep(0.5)

print(variant_list)

# handle = Entrez.esummary(db="clinvar", id="157906")
#  record = Entrez.read(handle)
#  handle.close()
#  print(record)



print(clinvar_list)

