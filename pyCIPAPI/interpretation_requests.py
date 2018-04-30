"""Functions for getting and manipulating interpretation requests."""

from auth import AuthenticatedSession


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

    Create a dictionary corresponding to gelId: relation_to_proband pairs.

    Args:
        interpretation_request: JSON representation of an
            interpretation_request (output of get_interpretation_request_json).

    Returns:
        pedigree: Dictionary of 'gelId' keys and 'relation_to_proband' pairs
            extracted from the interpretation_request object.
    """
    pedigree = {}
    for p in (interpretation_request['interpretation_request_data']
              ['json_request']['pedigree']['participants']):
        if p['additionalInformation']['relation_to_proband'] == '-':
            pedigree[p['gelId']] = 'Proband'
        else:
            pedigree[p['gelId']] = (p['additionalInformation']
                                    ['relation_to_proband'])
    return pedigree
