"""
Used to check if new monthly release of ClinVar VCF is available for download. 
If so, it is downloaded and extracted into /data.
"""

import os
import re
import gzip
import zipfile
from ftplib import FTP

dirname = os.path.dirname(__file__)
data_dir = os.path.join(dirname, "../data/")

def local_vcf():
    """
    Check for local ClinVar vcf, and return version (date)
    """
    data_files = []
    local_vcf_ver = 0

    for (dirpath, dirnames, filenames) in os.walk(data_dir):
        data_files.extend(filenames)

    for file in data_files:
        if re.match("^clinvar_[0-9]+\.vcf$", file):
            # get just the clinvar vcf
            local_vcf_ver = int(file.split("_")[1].split(".")[0])
            print("Current version of ClinVar downloaded: {}".format(local_vcf_ver))

    if local_vcf_ver == 0:
        # no vcf downloaded
        print("No vcf found locally")

    return local_vcf_ver

def get_ftp_files():
    """
    Get latest available vcf from NCBI FTP site
    """

    ftp = FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pub/clinvar/vcf_GRCh38/")

    file_list = []
    ftp.retrlines('LIST', file_list.append)

    for file in file_list:
        file_name = file.split()[-1]
        if re.match("^clinvar_[0-9]+\.vcf.gz$", file_name):
            # get just the full clinvar vcf
            ftp_vcf = file_name
    
    ftp_vcf_ver = int(ftp_vcf.split("_")[1].split(".")[0])
    
    print("Latest available ClinVar version available: {}".format(ftp_vcf_ver))

    return ftp_vcf, ftp_vcf_ver

def get_vcf(filename):
    """
    Downloads file from NCBI FTP site to /data
    """

    ftp = FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pub/clinvar/vcf_GRCh38/")

    file_to_download = os.path.join(data_dir, filename)
    localfile = open(file_to_download, 'wb')

    ftp.retrbinary('RETR ' + filename, localfile.write, 1024)

    ftp.quit()
    localfile.close()

def check_current_vcf(ftp_vcf, ftp_vcf_ver, local_vcf_ver):
    """
    Check if local ClinVar vcf is latest, if not download from FTP site and decompress
    """

    if ftp_vcf_ver > local_vcf_ver:
        
        print("New ClinVar vcf available, downloading now ({})".format(ftp_vcf))
        get_vcf(ftp_vcf) # downloads latest vcf
        
        vcf_to_unzip = os.path.join(data_dir, ftp_vcf)
        decompressed_vcf = os.path.join(data_dir, str(ftp_vcf).strip(".gz"))

        with gzip.open(vcf_to_unzip, 'rb') as f:
            print("Decompressing {}".format(ftp_vcf))
            # unzip vcf
            vcf_data = f.read()
            f.close()

        with open(decompressed_vcf, "wb") as f:
            # write data from decompressed vcf to new vcf
            f.write(vcf_data)
            f.close
        
        os.unlink(vcf_to_unzip) # delete original vcf.gz

    else:
        print("Latest ClinVar vcf already downloaded")
 
if __name__ == "__main__":

    local_vcf_ver = local_vcf()
    ftp_vcf, ftp_vcf_ver = get_ftp_files()
    check_current_vcf(ftp_vcf, ftp_vcf_ver, local_vcf_ver)
