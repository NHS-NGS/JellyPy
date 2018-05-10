"""Download all the VCFs associated with the given family ID.

Usage:
    download_family_vcfs.py --family-id FAMILY_ID --download-location LOCATION
    download_family_vcfs.py (-h | --help)

Options:
    -h, --help              Show this screen.
    --family-id             ID number for desired GEL family.
    --download-location     Path to location of downloaded VCFs.

"""

from __future__ import print_function, absolute_import
import os
import sys
from docopt import docopt
from pyCIPAPI.interpretation_requests import (
    get_interpretation_request_json, get_interpretation_request_list)
from pyCIPAPI.opencga import (get_study_id, find_file_id, download_file)


def _main(args):
    for case in get_interpretation_request_list():
        if case['family_id'] == args['FAMILY_ID']:
            get_all_vcfs(case, args['LOCATION'])


def get_all_vcfs(case, download_location):
    """Download all the VCFs for a given case.

    Takes a case JSON from the CIP API searches for the study type and then
    for each VCF in the VCFs field does a lookup using the file nameto get the
    file id and performs a download to the specified download location.

    Args:
        case: JSON object from the CIP API
        download_location: File path to where the script should save the file.

    """
    ir, version = case['interpretation_request_id'].split('-')
    print('Searching for interpretation request {}-{} for family id {}'
          .format(ir, version, case['family_id']))
    case['interpretation_request_data'] = (get_interpretation_request_json(
                                          ir, version))
    study_id = get_study_id(study_type=case['sample_type'],
                            assembly=case['assembly'])
    print('Identified family {} with study id {}'
          .format(case['family_id'], study_id))
    try:
        vcf_list = (case['interpretation_request_data']
                    ['interpretation_request_data']['json_request']['VCFs'])
    except KeyError:
        print('No VCFs available for family {}'.format(case['family_id']))
        sys.exit()
    for vcf in vcf_list:
        filename = os.path.basename(vcf['URIFile'])
        print('Searching for file id for file {}'.format(filename))
        file_id = find_file_id(study_id, 'VCF', filename)
        if file_id:
            print('Downloading file {} (id: {})'.format(filename, file_id))
            download_file(file_id, study_id, filename, download_location)
        else:
            print('No file id found for file {}'.format(filename))


if __name__ == '__main__':
    arguments = docopt(__doc__)
    _main(arguments)
