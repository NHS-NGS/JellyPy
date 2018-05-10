"""Objects for authenticating with the GEL CIP API."""

from __future__ import print_function, absolute_import
import json
from datetime import datetime, timedelta
import requests
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
            self.auth_time = datetime.utcnow()
            self.auth_expires = self.auth_time + timedelta(minutes=30)
        except KeyError:
            self.auth_time = False
            print('Authentication Error')
        return self

    def check_auth(self):
        """Check whether the session is still authenticated."""
        if datetime.utcnow() > self.auth_expires():
            self.authenticate()
        else:
            pass


class AuthenticatedOpenCGASession(requests.Session):
    """Subclass of requests Session for accessing GEL openCGA instance."""

    def __init__(self):
        """Init AuthenticatedOpenCGASession and run authenticate function.

        Authentication credentials are stored in auth_credentials.py and are in
        dictionary format:

        auth_credentials = {"username": "username", "password": "password"}

        """
        requests.Session.__init__(self)
        self.host_url = ('https://apps.genomicsengland.nhs.uk/opencga/'
                         'webservices/rest/v1')
        self.authenticate()

    def authenticate(self):
        """Use auth_credentials to generate an authenticated session.

        Uses the cip_auth_url hard coded in and credentials in the
        auth_credentials file to retrieve an authentication token from the CIP
        API.

        Returns:
            The current instance of AuthenticatedOpenCGASession with the sid
            value as an attribute, plus the auth_time and auth_expires time.
        """
        opencga_auth_url = ('{host}/users/{username}/login'
                            .format(host=self.host_url,
                                    username=auth_credentials['username']))
        try:
            self.headers.update({"Accept": "application/json",
                                 "Content-Type": "application/json",
                                 "Authorization": "Bearer "})
            sid_response = (self.post(opencga_auth_url,
                                      data=json.dumps(auth_credentials))
                            .json())
            self.sid = sid_response['response'][0]['result'][0]['sessionId']
            self.auth_time = datetime.utcnow()
            self.auth_expires = self.auth_time + timedelta(minutes=30)
        except KeyError:
            self.auth_time = False
            print('Authentication Error')
        return self

    def check_auth(self):
        """Check whether the session is still authenticated."""
        if datetime.utcnow() > self.auth_expires():
            self.authenticate()
        else:
            pass
