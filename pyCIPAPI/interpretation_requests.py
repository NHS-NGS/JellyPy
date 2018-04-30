"""Functions for getting and manipulating interpretation requests."""

import os
import datetime
import json
from .auth import AuthenticatedSession


def get_interpretation_request_json(ir_id, ir_version):
    """Get an interpretation request as a json."""
    s = AuthenticatedSession()
    request_url = ('https://cipapi.genomicsengland.nhs.uk/api/2/'
                   'interpretation-request/{}/{}/'.format(ir_id, ir_version))
    r = s.get(request_url)
    return r.json()


def get_interpretation_request_list(page_size=100):
    """Get a list of interpretation requests."""
    s = AuthenticatedSession()
    interpretation_request_list = []
    next = ('https://cipapi.genomicsengland.nhs.uk/api/2/'
            'interpretation-request?page_size={}'.format(page_size))
    while next:
        r = s.get(next)
        interpretation_request_list += r.json()['results']
        next = r.json().get('next', False)
    return interpretation_request_list


def get_pedigree_dict(interpretation_request):
    """Make a simple dictionary representation of the pedigree.

    Create a dictionary corresponding to relation_to_proband: gelId pairs.

    Args:
        interpretation_request: JSON representation of an
            interpretation_request (output of get_interpretation_request_json).

    Returns:
        pedigree: Dictionary of keys 'relation_to_proband' and 'gelId' pairs
            extracted from the interpretation_request object.
    """
    pedigree = {}
    for p in (interpretation_request['interpretation_request_data']
              ['interpretation_request_data']['json_request']['pedigree']
              ['participants']):
        if p['isProband']:
            pedigree['Proband'] = p['gelId']
        else:
            try:
                pedigree[p['additionalInformation']['relation_to_proband']] = (
                    p['gelId'])
            except KeyError:
                pass
    return pedigree


def get_variant_tier(variant):
    """Get the most significant tier (lowest) for a variant.

    Look through the report events for a given variant and return the most
    significant (lower is more significant) tier value.

    Args:
        variant: Variant object from the TieredVariants in an interpretation
            request.

    Returns:
        tier: Integer tier value (1, 2, or 3)

    """
    tiering = []
    for reportevent in variant['reportEvents']:
        re_tier = int(reportevent['tier'].strip('TIER'))
        tiering.append(re_tier)
    tier = min(tiering)
    return tier


def save_interpretation_request_list_json(interpretation_request_list,
                                          force_update=False):
    """Save a list of interpretation requests as a datestamped JSON."""
    output_file = ('{}_interpretation_request_audit.json'
                   .format(datetime.datetime.today().strftime('%Y%m%d')))
    output_file_path = os.path.join(os.getcwd(), 'output', output_file)
    if not (os.path.isfile(output_file_path)) or (force_update is True):
        print('Writing interprettion requests data to {}'
              .format(output_file_path))
        with open(output_file_path, 'w') as fout:
            json.dump(interpretation_request_list, fout)
