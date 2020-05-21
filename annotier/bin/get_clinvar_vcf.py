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
clinvar_dir = os.path.join(dirname, "../data/clinvar/")

# compile required regex 
clinvar_vcf_regex = re.compile("^clinvar_([0-9]+)\.vcf$")
clinvar_gz_regex = re.compile("^clinvar_[0-9]+\.vcf.gz$")

def local_vcf():
    """
    Check for local ClinVar vcf, and return version (date)

    Args: None

    Returns:
        local_vcf_ver (int): latest version no. of local ClinVar VCF  
    """
    local_vcf_ver = 0

    for (dirpath, dirnames, filenames) in os.walk(clinvar_dir):
        for filename in filenames:
            match = clinvar_vcf_regex.match(filename)
            if match:
                # get just the clinvar vcf
                vcf_ver = int(filename.split("_")[1].split(".")[0])
                if vcf_ver > local_vcf_ver:
                    # if multiple vcfs in data select just the latest
                    local_vcf_ver = vcf_ver
                else:
                    continue

    if local_vcf_ver == 0:
        # no vcf downloaded
        print("No vcf found locally, latest will be downloaded")
    else:
        print("Current version of ClinVar downloaded: {}".format(local_vcf_ver))

    return local_vcf_ver


def get_ftp_files():
    """
    Get latest available vcf from NCBI FTP site

    Args: None

    Returns:
        ftp_vcf (string): filename of latest available VCF from FTP site
        ftp_vcf_ver (int): version no. of latest available VCF from FTP site 
    """

    ftp = FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pub/clinvar/vcf_GRCh38/")

    file_list = []
    ftp.retrlines('LIST', file_list.append)

    for file_name in file_list:

        file_name = file_name.split()[-1]

        if clinvar_gz_regex.match(file_name):
            # get just the full clinvar vcf
            ftp_vcf = file_name
            ftp_vcf_ver = int(ftp_vcf.split("_")[1].split(".")[0])

            break
    
    print("Latest available ClinVar version available: {}".format(ftp_vcf_ver))

    return ftp_vcf, ftp_vcf_ver

def get_vcf(filename):
    """
    Downloads file from NCBI FTP site to /data/clinvar, called by check_current_vcf()
    
    Args:
        filename (string): name of VCF to be downloaded from FTP site
    
    Outputs:
        localfile (file): downloaded VCF into /data/clinvar/

    Returns: None
    """

    ftp = FTP("ftp.ncbi.nlm.nih.gov")
    ftp.login()
    ftp.cwd("/pub/clinvar/vcf_GRCh38/")

    file_to_download = os.path.join(clinvar_dir, filename)
    
    with open(file_to_download, 'wb') as localfile:
        ftp.retrbinary('RETR ' + filename, localfile.write, 1024)

    ftp.quit()

def check_current_vcf(ftp_vcf, ftp_vcf_ver, local_vcf_ver):
    """
    Check if local ClinVar vcf is latest, if not download from FTP site and decompress

    Args:
        ftp_vcf (string): filename of latest available VCF from FTP site
        ftp_vcf_ver (int): version no. of latest available VCF from FTP site 
        local_vcf_ver (int): version no. of latest localy available VCF
    
    Outputs:
        localfile (file): downloaded VCF into /data/clinvar/ (from get_vcf())
    
    Returns: None
    """

    if ftp_vcf_ver > local_vcf_ver:
        
        print("New ClinVar vcf available, downloading now ({})".format(ftp_vcf))
        get_vcf(ftp_vcf) # downloads latest vcf
        
        vcf_to_unzip = os.path.join(clinvar_dir, ftp_vcf)
        decompressed_vcf = os.path.join(clinvar_dir, str(ftp_vcf)[:-3]) # removes .gz extension

        with gzip.open(vcf_to_unzip, 'rb') as f:
            print("Decompressing {}".format(ftp_vcf))
            # unzip vcf
            vcf_data = f.read()
            f.close()

        with open(decompressed_vcf, "wb") as f:
            # write data from decompressed vcf to new vcf
            f.write(vcf_data)
            f.close
        
        os. remove(vcf_to_unzip) # delete original vcf.gz

    else:
        print("Latest ClinVar vcf already downloaded")
 
if __name__ == "__main__":
    local_vcf_ver = local_vcf()
    ftp_vcf, ftp_vcf_ver = get_ftp_files()
    check_current_vcf(ftp_vcf, ftp_vcf_ver, local_vcf_ver)
