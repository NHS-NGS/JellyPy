"""Objects for authenticating with the GEL CIP API."""

import json
from datetime import datetime, timedelta

import jwt
import maya
import requests
from jwt.exceptions import (DecodeError, ExpiredSignatureError,
                            InvalidTokenError)

from .auth_credentials import auth_credentials
from .config import beta_testing_auth_url, live_100K_auth_url, live_100k_data_base_url, use_active_directory


# get an authenticated session
class AuthenticatedCIPAPISession(requests.Session):
    """Subclass of requests Session for authenticating against GEL CIPAPI."""

    def __init__(self, testing_on=False, token=None, auth_credentials=auth_credentials):
        """Init AuthenticatedCIPAPISession and run authenticate function.

        Authentication credentials are stored in auth_credentials.py and are in
        dictionary format:

        auth_credentials = {"username": "username", "password": "password"}

        """
        requests.Session.__init__(self)
        self.auth_credentials = auth_credentials
        self.set_auth_url(testing_on=testing_on)
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

    def set_auth_url(self, testing_on=False):
        """
        Sets the URL to use for retrieving JWT token.
        """
        # Update which URL to use for auth depending on
        if testing_on == False and use_active_directory == True:
            # If using AD and not testing, use live AD tenant
            self.cip_auth_url = live_100K_auth_url
        elif testing_on == True and use_active_directory == True:
            # If using AD and testing, use beta AD tenant
            self.cip_auth_url = beta_testing_auth_url
        elif testing_on == False and use_active_directory == False:
            # If using LDAP and not testing, use live CIPAPI get-token url
            self.cip_auth_url = live_100k_data_base_url + 'get-token/'
        elif testing_on == True and use_active_directory == False:
            raise ValueError(
                "LDAP login no longer supported for testing. Please set use_active_directory to True in config.py"
            )

    def authenticate_ad(self, testing_on=False):
        """
        Authenticate using Active Directory client ID and client secret
        """
        if testing_on == False:
            auth=(self.auth_credentials['client_id'], self.auth_credentials['client_secret'])
        else:
            auth=(self.auth_credentials['beta_client_id'], self.auth_credentials['beta_client_secret'])
        try:
            auth_response = self.post(
                self.cip_auth_url,
                data="grant_type=client_credentials",
                auth=auth
            ).json()
            self.headers.update({"Authorization": "JWT " + auth_response['access_token']})
            self.auth_time = datetime.fromtimestamp(int(auth_response['not_before']))
            self.auth_expires = datetime.fromtimestamp(int(auth_response['expires_on']))
        except KeyError:
            self.auth_time = False
            raise Exception('Authentication Error')
        except:
            raise

    def authenticate_ldap(self):
        """
        Authenticate using legacy LDAP (to be deprecated at AD switchover)
        """
        try:
            token = (self.post(
                self.cip_auth_url, data=({
                            "username": self.auth_credentials['username'],
                            "password": self.auth_credentials['password'],
                        }
                )
            ).json()['token'])
            decoded_token = jwt.decode(token, verify=False)
            self.headers.update({"Authorization": "JWT " + token})
            self.auth_time = datetime.fromtimestamp(decoded_token['orig_iat'])
            self.auth_expires = datetime.fromtimestamp(decoded_token['exp'])
        except KeyError:
            self.auth_time = False
            raise Exception('Authentication Error')
        except:
            raise


    def authenticate(self, testing_on=False):
        """Use auth_credentials to generate an authenticated session.

        Uses the cip_auth_url and credentials in the
        auth_credentials.py file to retrieve an authentication token from AD or the CIP
        API.

        Returns:
            The current instance of AuthenticatedCIPAPISession with the headers
            set to include token, the auth_time and auth_expires time.
        """
        if use_active_directory:
            self.authenticate_ad(testing_on=testing_on)
        else:
            self.authenticate_ldap()
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
