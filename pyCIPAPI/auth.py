"""Objects for authenticating with the GEL CIP API."""

from __future__ import print_function, absolute_import
import requests
import maya
from .auth_credentials import auth_credentials


# get an authenticated session
class AuthenticatedCIPAPISession(requests.Session):
    """Subclass of requests Session for authenticating against GEL CIPAPI."""

    def __init__(self):
        """Init AuthenticatedCIPAPISession and run authenticate function.

        Authentication credentials are stored in auth_credentials.py and are in
        dictionary format:

        auth_credentials = {"username": "username", "password": "password"}

        """
        requests.Session.__init__(self)
        self.authenticate()

    def authenticate(self):
        """Use auth_credentials to generate an authenticated session.

        Uses the cip_auth_url hard coded in and credentials in the
        auth_credentials file to retrieve an authentication token from the CIP
        API.

        Returns:
            The current instance of AuthenticatedCIPAPISession with the headers
            set to include token, the auth_time and auth_expires time.
        """
        cip_auth_url = 'https://cipapi.genomicsengland.nhs.uk/api/2/get-token/'
        try:
            token = (self.post(
                        cip_auth_url, data=(auth_credentials))
                     .json()['token'])
            self.headers.update({"Authorization": "JWT " + token})
            self.auth_time = maya.now()
            self.auth_expires = self.auth_time.add(minutes=30)
        except KeyError:
            self.auth_time = False
            print('Authentication Error')
        return self

    def check_auth(self):
        """Check whether the session is still authenticated."""
        if maya.now() > self.auth_expires():
            self.authenticate()
        else:
            pass
