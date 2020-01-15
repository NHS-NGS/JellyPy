# pyCIPAPI developer guide

`jellypy.pyCIPAPI` provides helper functions for interacting with GeL APIs.

## Installation

```python
pip install ./pyCIPAPI
```

## Guides

### Download interpretation request json by id and version

A GeL interpretation request can be downloaded using pyCIPAPI.

```python
import jellypy.pyCIPAPI.auth as auth
import jellypy.pyCIPAPI.interpretation_requests as irs

session = auth.AuthenticatedCIPAPISession(
        auth_credentials={
        'username': 'your_username',
        'password': 'your_password'
    }
)

# Download interpretation request 12345-1 data in json format.
irjson = irs.get_interpretation_request_json(12345, 1, session=session, reports_v6=True)
```

## Contributing

Setup a development environment on your machine with the following packages:
* pytest == 5.2.2

### Testing

Tests are writting using the `pytest` framework and kept in the JellyPy package's **/test** directory.

A configuration file may be required to authenticate API access to and pass additional parameters.

### pyCIPAPI test config

Required fields:
- username: A GeL CIP API user name
- password: A GeL CIP API password
- test_irid: An interpretation request ID for request tests
- test_irversion: A version number corresponding to `test_irid` for request tests

Create a configuration file with the following required fields

```bash
[pyCIPAPI]
username = YOURUSERNAME
password = YOURPASS
test_irid = 12345
test_irversion = 3
```
