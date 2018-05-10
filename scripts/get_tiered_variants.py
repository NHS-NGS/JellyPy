"""Output TSV file of tiered variants ready for Alamut Batch annotation.

Usage:
    get_tiered_variants.py [--force-update] [--site SITE ...]
    get_tiered_variants.py (-h | --help)
    get_tiered_variants.py [--version]

Options:
    -h, --help      Show this screen.
    --version       Show version.
    --force-update  Get data from API even if a cached version exists.
    --site          One or more site codes to limit output by site, eg: RR8.

"""
from __future__ import print_function, absolute_import
try:
    from exceptions import FileNotFoundError as FileError
except ImportError:
    from exceptions import IOError as FileError
import os
import datetime
import json
from docopt import docopt
from pyCIPAPI.interpretation_requests import (
    get_interpretation_request_json, get_interpretation_request_list,
    get_pedigree_dict, get_variant_tier, save_interpretation_request_list_json)


def _main(args):
    # load or get interpretation_request_list
    interpretation_request_list = (get_latest_interpretation_request_list(
                                   args['--force-update']))
    for case in interpretation_request_list:
        # Ignore cases where the site is not in the list of given sites
        # Or if no sites have been given do the case handling anyway
        if (args['--site'] and not
           set(case['sites']).intersection(set(args['SITE']))):
            pass
        else:
            handle_interpretation_request(case, args['--force-update'])
    # Save the interpretation_request_list to JSON
    save_interpretation_request_list_json(interpretation_request_list,
                                          args['--force-update'])


def get_latest_interpretation_request_list(force_update=False):
    """Get the latest version of the interpretation_request_list.

    Check if there is a up to date (using today's date) interpretation request
    list JSON saved to disk. If there is load it, if not use the helper
    functions to load it.

    Args:
        force_update (bool): If True create the interpretation request list
            using the helper function, even if an on disk version exists.

    Returns:
        interpretation_request_list: List of individual interpretation request
            objects.

    """
    if not force_update:
        try:
            input_file = ('{}_interpretation_request_audit.json'
                          .format(datetime.datetime.today()
                                  .strftime('%Y%m%d')))
            input_file_path = os.path.join(os.getcwd(), 'output', input_file)
            with open(input_file_path, 'r+') as fin:
                interpretation_request_list = json.load(fin)
            print('Using cached interpretation request list.')
        except FileError:
            print('Querying CIPAPI for interpretation request list.')
            interpretation_request_list = get_interpretation_request_list()
    else:
        print('Querying CIPAPI for interpretation request list.')
        interpretation_request_list = get_interpretation_request_list()
    return interpretation_request_list


def handle_interpretation_request(interpretation_request, force_update=False):
    """Handle an interpretation request for getting tiered variants.

    Check if the interpretation request has interpretation_request_data and get
    if from the CIPAPI if not. Make a simple_pedigree record and then pass the
    interpretation_request to output_variant_tsv for export.

    Args:
        interpretation_request: JSON representation of an
            interpretation_request (output of get_interpretation_request_json).
        force_update: Boolean switch to enforce output file overwriting.

    """
    # get_or_create interpretation_request_data
    ir_id, ir_version = (interpretation_request['interpretation_request_id']
                         .split('-'))
    try:
        interpretation_request_data = (interpretation_request
                                       ['interpretation_request_data'])
    except KeyError:
        interpretation_request_data = (get_interpretation_request_json(
                                       ir_id, ir_version))
        interpretation_request['interpretation_request_data'] = (
            interpretation_request_data)
    # make simple pedigree
    interpretation_request['simple_pedigree'] = (get_pedigree_dict(
        interpretation_request))
    output_variant_tsv(interpretation_request, force_update)


def output_variant_tsv(interpretation_request, force_update=False):
    """Output a variant TSV to match Alamut Batch format for annotation.

    If a variant TSV for the given interpretation_request (version, and genome
    build) exists then pass. If a matching file does not exist or the
    force_update boolean is True then for each of the variants in the
    interpretation_request get the zygosity for the proband, mother, and father
    (where they are known) and output into a TSV.

    Args:
        interpretation_request: JSON representation of an
            interpretation_request (output of get_interpretation_request_json).
        force_update: Boolean switch to enforce output file overwriting.

    """
    # Make the file paths for existance checking
    ir_id, ir_version = (interpretation_request['interpretation_request_id']
                         .split('-'))
    variant_tsv = '{}_{}_{}_{}_tiered_variants.tsv'.format(
        interpretation_request['family_id'], ir_id, ir_version,
        interpretation_request['assembly'])
    variant_tsv_path = os.path.join(os.getcwd(), 'output', variant_tsv)
    # Check for file existance or force_update boolean
    if not (os.path.isfile(variant_tsv_path)) or (force_update is True):
        print('Writing variants to {}'.format(variant_tsv_path))
        with open(variant_tsv_path, 'w') as fout:
            # Write header row ofr human readability
            header = ('#id\tchr\tposition\tref\talt\tTier\tproband_zygosity\t'
                      'mother_zygosity\tfather_zygosity\n')
            fout.write(header)
            # Construct the row for a given variant
            for variant in (
                 interpretation_request['interpretation_request_data']
                 ['interpretation_request_data']['json_request']
                 ['TieredVariants']):
                dbSNPid = variant['dbSNPid']
                chromosome = variant['chromosome']
                position = variant['position']
                ref = variant['reference']
                alt = variant['alternate']
                # Get variant tier
                tier = str(get_variant_tier(variant))
                # Get the zygosities where known
                proband_zygosity = (get_call_zygosity(
                                    variant,
                                    interpretation_request['simple_pedigree'],
                                    'Proband'))
                mother_zygosity = (get_call_zygosity(
                                   variant,
                                   interpretation_request['simple_pedigree'],
                                   'Mother'))
                father_zygosity = (get_call_zygosity(
                                   variant,
                                   interpretation_request['simple_pedigree'],
                                   'Father'))
                fout.write('\t'.join([dbSNPid, chromosome, str(position), ref,
                           alt, tier, proband_zygosity, mother_zygosity,
                           father_zygosity]) + '\n')


def get_call_zygosity(variant, simple_pedigree, family_member):
    """Get the zygosity for the given variant for the fiven family member.

    Using the simple_pedigree dictionary extract the genotype for the given
    variant which matches the desired type of family member. If not record is
    found for the given family member return the zygosity as 'Unknown'.

    Args:
        variant: Variant object from the TieredVariants in an interpretation
            request.
        simple_pedigree: Simple dictionary representation of the GEL pedigree.
        family_member: String denoting which family member; eg 'Proband',
            'Mother', or 'Father'.

    Returns:
        zygosity: String representing the variant zygosity for the family
            member. 'Unknown' if not present.

    """
    zygosity = 'Unknown'
    for genotype in variant['calledGenotypes']:
        if genotype['gelId'] == simple_pedigree.get(family_member, False):
            zygosity = genotype['genotype']
    return zygosity


if __name__ == '__main__':
    arguments = docopt(__doc__, version='1.1')
    _main(arguments)
