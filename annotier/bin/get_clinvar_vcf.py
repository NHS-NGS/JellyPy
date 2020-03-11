"""
Used to check if new monthly release of ClinVar VCF is available for download. 
If so, it is downloaded and extracted into /data.
"""

import os
import re
from ftplib import FTP

f = []

dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, "../data/")

for (dirpath, dirnames, filenames) in os.walk(data_dir):
    f.extend(filenames)

print(f)
print(data_dir)

def ftp_files():

    ftp = FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pub/clinvar/vcf_GRCh38/")

    file_list = []
    ftp_vcfs = []
    ftp.retrlines('LIST', file_list.append)

    for file in file_list:
        file_name = file.split()[-1]
        if re.match("^clinvar_[0-9]+\.vcf.gz$", file_name):
            # get just the full clinvar vcfs
            ftp_vcfs.append(file_name)

    print(ftp_vcfs)

    return ftp_vcfs

def check_current_vcf(ftp_vcfs):
    for vcf in ftp_vcfs:
        ftp_vcf_date = 0

        if int(vcf.split("_")[1].split(".")[0]) > int(ftp_vcf_date):
            # get date of newest vcf from ftp site
            ftp_vcf_date = vcf.split("_")[1].split(".")[0]

            # need to add check against current vcf, and if newer is available then download
        
if __name__ == "__main__":

    ftp_vcfs = ftp_files()
    check_current_vcf(ftp_vcfs)
