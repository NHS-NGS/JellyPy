"""Functions for interacting with GEL instance of openCGA."""
from __future__ import print_function

import os

from .auth import AuthenticatedOpenCGASession


def get_study_id(study_type, assembly=None, sample_type=None):
    """Return study_id for the given study_type, sample_type and assembly.

    Given a study type, assembly, and possibly a sample type return the
    corresponding GEL ID for the following possibilities:
        - Rare Disease GRCh37 = 1000000024
        - Rare Disease GRCh38 = 1000000032
        - Cancer Germline (GRCh38) = 1000000034
        - Cancer Somatic (GRCh38) = 1000000038

    Args:
        study_type (str): raredisease or cancer.
        assembly (str): GRCh37 or GRCh38 (for rare disease samples).
        sample_type (str): germline or somatic (for cancer samples).

    Returns:
        study_id (int): ID for appropriate study within the CIPAPI.

    """
    study_id = None
    if study_type.lower() == 'raredisease':
        if assembly.lower() == 'grch37':
            study_id = 1000000024
        elif assembly.lower() == 'grch38':
            study_id = 1000000032
        else:
            study_id = None
    elif study_type.lower() == 'cancer':
        if sample_type.lower() == 'germline':
            study_id = 1000000034
        elif sample_type.lower() == 'somatic':
            study_id = 1000000038
        else:
            study_id = None
    else:
        study_id = None
    return study_id


def find_file_id(study_id, file_format, file_name):
    """Find the file ID for the given filename, format, and study ID.

    Use the openCGA file search endpoint to get the file_id for the given
    study_id, file_format, and file_name.

    Args:
        study_id (int): ID for appropriate study within the CIPAPI.
        file_format (str): Format of file to search for (eg VCF).
        file_name (str): Name of file to search for.

    Returns:
        file_id (int): ID for given file in openCGA. Will be None if failed
            search or no search results are found.
    """
    s = AuthenticatedOpenCGASession()
    # Construct search url
    search_url = ("{host}/files/search?format=VCF&sid={sid}&study={study_id}"
                  "&name={file_name}&exclude=meta&limit=1&sort=creationDate"
                  .format(host=s.host_url, sid=s.sid, study_id=study_id,
                          file_name=file_name))
    r = s.get(search_url)
    file_id = None
    if r.status_code == 200:
        try:
            file_id = r.json()['response'][0]['result'][0]['id']
        except (KeyError, IndexError):
            print('Unable to find file {file_idname}'
                  .format(filename=file_name))
    else:
        print('Search for file {file_name} failed'.format(filename=file_name))
    return file_id


def download_file(file_id, study_id, file_name, download_folder=None):
    """Download a file from the GEL openCGA instance.

    Args:
        file_id (int): ID for given file in openCGA.
        study_id (int): ID for appropriate study within the CIPAPI.
        file_name (str): Name of file to create with download.
        download_folder (str): Path to download location. Defaults to current
            working directory.

    """
    s = AuthenticatedOpenCGASession()
    # Construct download url
    download_url = ("{host}/files/{file_id}/download?sid={sid}&"
                    "study={study_id}"
                    .format(host=s.host_url, file_id=file_id, sid=s.sid,
                            study_id=study_id))
    r = s.get(download_url, stream=True)
    if r.status_code == 200:
        if not download_folder:
            download_folder = os.getcwd()
        download_path = os.path.join(download_folder, file_name)
        print('Downloading to {download_path}'
              .format(download_path=download_path))
        with open(download_path, 'wb') as fout:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    fout.write(chunk)
                    fout.flush()
    else:
        print('Unable to download file {file_id} for study {study_id}'
              .format(file_id=file_id, study_id=study_id))
