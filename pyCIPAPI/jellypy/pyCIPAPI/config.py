#!/usr/bin/env python

# Configuration file for setting common variables to avoid hard-coding them in code:

# Set to true to use Active Directory authentication, or false to use legacy LDAP authentication
use_active_directory = True

# CIP-API AD authentication URLs
live_100K_auth_url = 'https://login.microsoftonline.com/0a99a061-37d0-475e-aa91-f497b83269b2/oauth2/token'
beta_testing_auth_url = 'https://login.microsoftonline.com/99515578-fda0-444c-8f5a-2005038880f2/oauth2/token'

# CIP-API base URLs for live data and beta testing:
live_100k_data_base_url = 'https://cipapi.gel.zone/api/2/'
beta_testing_base_url = 'https://cipapi-beta.genomicsengland.co.uk/api/2/'
