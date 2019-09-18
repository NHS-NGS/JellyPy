"""Objects for authenticating with the GEL CIP API."""

from __future__ import print_function, absolute_import
import json
import jwt
from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidTokenError
import requests
import maya
from datetime import datetime, timedelta
from .auth_credentials import auth_credentials
from .config import live_100k_data_base_url, beta_testing_base_url


# get an authenticated session
class AuthenticatedCIPAPISession(requests.Session):
    """Subclass of requests Session for authenticating against GEL CIPAPI."""

    def __init__(self, testing_on=False, token=None):
        """Init AuthenticatedCIPAPISession and run authenticate function.

        Authentication credentials are stored in auth_credentials.py and are in
        dictionary format:

        auth_credentials = {"username": "username", "password": "password"}

        """
        requests.Session.__init__(self)

        if token:
            self.update_token(token)
        else:
            self.authenticate(testing_on=testing_on)

    def update_token(self, token):
        """Update session token with a user supplied one.

        Stores the JWT token and updates creation and expiration time from payload.

        Returns:
            The current instance of AuthenticatedCIPAPISession with the headers
            set to include token, the auth_time and auth_expires time.
        """

        try:
            decoded_token = jwt.decode(token, verify=False)
            self.headers.update({"Authorization": "JWT " + token})
            self.auth_time = datetime.fromtimestamp(decoded_token['orig_iat'])
            self.auth_expires = datetime.fromtimestamp(decoded_token['exp'])
        except (InvalidTokenError, DecodeError, ExpiredSignatureError, KeyError):
            self.auth_time = False
            raise Exception('Invalid or expired JWT token')
        except:
            raise

        # Check whether the token has expired
        if datetime.now() > self.auth_expires - timedelta(minutes=10):
            raise Exception('JWT token has expired')
        else:
            pass

        return self

    def authenticate(self, testing_on=False):
        """Use auth_credentials to generate an authenticated session.

        Uses the cip_auth_url hard coded in and credentials in the
        auth_credentials.py file to retrieve an authentication token from the CIP
        API.

        Returns:
            The current instance of AuthenticatedCIPAPISession with the headers
            set to include token, the auth_time and auth_expires time.
        """

        # Use the correct url if using beta dataset for testing:
        if testing_on == False:
            # Live data
            cip_auth_url = (live_100k_data_base_url + 'get-token/')
        else:
            # Beta test data
            cip_auth_url = (beta_testing_base_url + 'get-token/')

        try:
            token = (self.post(
                        cip_auth_url, data=(auth_credentials))
                     .json()['token'])
            decoded_token = jwt.decode(token, verify=False)
            self.headers.update({"Authorization": "JWT " + token})
            self.auth_time = datetime.fromtimestamp(decoded_token['orig_iat'])
            self.auth_expires = datetime.fromtimestamp(decoded_token['exp'])
        except KeyError:
            self.auth_time = False
            raise Exception('Authentication Error')
        except:
            raise

        return self


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
        auth_credentials.py file to retrieve an authentication token from the CIP
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
            self.auth_time = maya.now()
            self.auth_expires = self.auth_time.add(minutes=30)
        except KeyError:
            self.auth_time = False
            print('Authentication Error')
        return self

    def check_auth(self, testing_on=False):
        """Check whether the session is still authenticated."""
        if maya.now() > self.auth_expires():
            self.authenticate(testing_on=testing_on)
        else:
            pass
