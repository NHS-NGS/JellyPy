"""
Functions for handling interpretation requestions to variants data in JSON format.
"""

import json
import re
import requests

import jellypy.pyCIPAPI.interpretation_requests as irs

from jellypy.pyCIPAPI.auth import AuthenticatedCIPAPISession

def get_ir_json(irid, irsession, session: AuthenticatedCIPAPISession):
    """
    
    """
    ir_json = irs.get_interpretation_request_json(
            irid, irversion, reports_v6=True, session=session
        )

""" leaving this until later when GEL sort their mess out