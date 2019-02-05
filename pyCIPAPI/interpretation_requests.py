"""Functions for getting and manipulating interpretation requests."""

import os
import datetime
import json
from .auth import AuthenticatedCIPAPISession


def get_interpretation_request_json(ir_id, ir_version, reports_v6=None):
    """Get an interpretation request as a json."""
    s = AuthenticatedCIPAPISession()
    payload = {
        'reports_v6': reports_v6
    }
    request_url = ('https://cipapi.genomicsengland.nhs.uk/api/2/'
                   'interpretation-request/{}/{}/'.format(ir_id, ir_version))
    r = s.get(request_url, params=payload)
    return r.json()


def get_interpretation_request_list(page_size=100,
                                    cip=None,
                                    group_id=None,
                                    version=None,
                                    interpretation_request_id=None,
                                    workspace=None,
                                    status=None,
                                    last_status=None,
                                    members=None,
                                    cohort_id=None,
                                    workflow_status=None,
                                    update_date=None,
                                    case_id=None,
                                    sample_type=None,
                                    assembly=None,
                                    case_priority=None,
                                    family_id=None,
                                    proband_id=None,
                                    long_name=None,
                                    tags=None,
                                    search=None):
    """Get a list of interpretation requests."""
    s = AuthenticatedCIPAPISession()
    interpretation_request_list = []
    base_url = ('https://cipapi.genomicsengland.nhs.uk/api/2/'
                'interpretation-request')
    payload = {
            'page_size': page_size,
            'cip': cip,
            'group_id': group_id,
            'version': version,
            'interpretation_request_id': interpretation_request_id,
            'workspace': workspace,
            'status': status,
            'last_status': last_status,
            'members': members,
            'cohort_id': cohort_id,
            'workflow_status': workflow_status,
            'update_date': update_date,
            'case_id': case_id,
            'sample_type': sample_type,
            'assembly': assembly,
            'case_priority': case_priority,
            'family_id': family_id,
            'proband_id': proband_id,
            'long_name': long_name,
            'tags': tags,
            'search': search
            }
    r = s.get(base_url, params=payload)
    interpretation_request_list += r.json()['results']
    next = r.json().get('next', False)
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
