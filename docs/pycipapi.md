# pyCIPAPI

`jellypy.pyCIPAPI` provides helper functions for interacting with GeL APIs.

## Installation

```bash
pip install jellypy-pyCIPAPI
```

## Guides

### Download interpretation request json by id and version

A GeL interpretation request can be downloaded using pyCIPAPI.

```python
import jellypy.pyCIPAPI.auth as auth
import jellypy.pyCIPAPI.interpretation_requests as irs

session = auth.AuthenticatedCIPAPISession(
    auth_credentials={
        'client_id': "YOUR_CLIENT_ID",
        'client_secret': "YOUR_CLIENT_SECRET"
        },
    testing_on=False # Switch flag for beta testing endpoints
)

# Download interpretation request 12345-1 data in json format.
irjson = irs.get_interpretation_request_json(
    ir_id=12345, ir_version=1, session=session, reports_v6=True, testing_on=False
)
```

