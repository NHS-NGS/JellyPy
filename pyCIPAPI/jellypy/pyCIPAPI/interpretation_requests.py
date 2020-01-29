"""Functions for getting and manipulating interpretation requests."""
from __future__ import print_function

import datetime
import json
import os
from time import strptime

from .auth import AuthenticatedCIPAPISession
from .config import beta_testing_base_url, live_100k_data_base_url

def get_interpretation_request_json(ir_id, ir_version, reports_v6=True, testing_on=False, token=None, session=None):
    """Get an interpretation request as a json."""
    s = session if session else AuthenticatedCIPAPISession(testing_on=testing_on, token=token)
    payload = {
        'reports_v6': reports_v6
    }
    # Use the correct url if using beta dataset for testing (imported form config.py):
    if testing_on == False:
        request_url = (live_100k_data_base_url + 'interpretation-request/{}/{}/'.format(ir_id, ir_version))
    else:
        request_url = (beta_testing_base_url + 'interpretation-request/{}/{}/'.format(ir_id, ir_version))

    return s.get(request_url, params=payload).json()


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
                                    search=None,
                                    testing_on=False,
                                    token=None,
                                    minimize=True):
    """Get a list of interpretation requests."""
    s = AuthenticatedCIPAPISession(testing_on=testing_on, token=token)
    interpretation_request_list = []

    # Use the correct url if using beta dataset for testing (imported form config.py):
    if testing_on == False:
        # Live data
        base_url = (live_100k_data_base_url + 'interpretation-request')
    else:
        # Beta test data
        base_url = (beta_testing_base_url + 'interpretation-request')

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
        'search': search,
        'minimize': minimize
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


def access_date_summary_content(date1, date2, testing_on=False, token=None):
    """
    method for accessing the JSON response from the date summary endpoint
    :param date1: '%d-%m-%Y' format date string
    :param date2: '%d-%m-%Y' format date string, exclusive of this date
    :return:
    """

    # check that the dates provided are in the correct order
    try:
        assert strptime(date1, '%d-%m-%Y') < strptime(date2, '%d-%m-%Y'), 'Dates provided in wrong order'
    except ValueError as v:
        print('Date Values provided couldn\'t be converted:', v)
        quit()

    date_summary_ext = 'interpretation-request/date-summary/{start}/{fin}/'.format(start=date1, fin=date2)

    s = AuthenticatedCIPAPISession(testing_on=testing_on, token=token)

    # switch based on test arg - currently a single results page
    if testing_on:
        return s.get(beta_testing_base_url + date_summary_ext).json()
    else:
        return s.get(live_100k_data_base_url + date_summary_ext).json()


def get_interpreted_genome_for_case(ir, version, tiering_service, testing_on=False, token=None):
    """

    :param ir: case ID, e.g. X in GEL-XXXX-y
    :param version: case Version, e.g. Y in GEL-xxxx-Y
    :param tiering_service: name of the interpreted genome service to check for
    :param testing_on:
    :param token:
    :return: an interpreted genome JSON, or None
    """

    s = AuthenticatedCIPAPISession(testing_on=testing_on, token=token)

    endpoint_suffix = 'interpreted-genome/{ir}/{ver}/{service}/last/?reports_v6=true'.format(ir=ir, ver=version,
                                                                                             service=tiering_service)

    # switch based on test arg - currently a single results page
    try:
        if testing_on:
            return s.get(beta_testing_base_url + endpoint_suffix).json()
        else:
            return s.get(live_100k_data_base_url + endpoint_suffix).json()
    except ValueError:
        print('No {service} analysis for {ir}-{ver}'.format(service=tiering_service,
                                                            ir=ir,
                                                            ver=version))
        return None


def get_workspace_mapping(token=None):
    """
    Currently 100k only, no need for a test mode
    Returns a lookup dictionary of short LDP code to GMC name
    :param: token: a pre-authorised CIP API token
    :return:
    """

    s = AuthenticatedCIPAPISession(token=token)

    workspaces = dict()
    url = live_100k_data_base_url + "/api/2/workspace-groups"

    # parse out all the endpoint results
    while True:
        json_returned = s.get(url=url).json()

        for ws in json_returned['results']:
            workspaces[ws['short_name']] = ws['gmc_name']

        # more to loop through?
        if json_returned['next']:
            url = json_returned['next']
        else:
            break

    return workspaces
