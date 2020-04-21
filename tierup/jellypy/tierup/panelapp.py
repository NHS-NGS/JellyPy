"""Utilities for working with PanelApp"""

import requests

class GeLPanel():
    """A GeL PanelApp Panel."""
    host = "https://panelapp.genomicsengland.co.uk/api/v1/panels"
    
    def __init__(self, panel, version=None):
        self.url = f'{self.host}/{panel}'
        self.version = float(version) if version else None
        self._json = self._get_panel_json()

        # Initialise attributes
        self.name, self.id, self.hash = self._json['name'], self._json['id'], self._json['hash_id']
        self.created = self._json['version_created']
        self.version = float(self._json['version'])
        
    def get_gene_map(self):
        """Returns a list mapping gene symbols to a (hgnc id, confidence level) tuple."""
        mapping = { gene['gene_data']['hgnc_symbol']: (gene['gene_data']['hgnc_id'], gene['confidence_level'])
            for gene in self._json['genes']
        }
        return mapping

    def _get_panel_json(self):
        """Returns json response object for API request."""
        data = requests.get(self.url, params={"version" : self.version})
        data.raise_for_status() # Raise error if invalid response code
        return data.json()

    def __str__(self):
        return f"{self.name}, {self.id}"

class PanelApp():
    """Iterable container for panel data from PanelApp /panels endpoint.

    Args:
        head (int): Set a limit of PanelApp response objects to return from the head.
            Useful for testing without iterating over all panels.

    >>> pa = PanelApp()
    >>> for panel in pa:
    >>> ...  # Do something with panel
    """

    def __init__(
        self,
        endpoint="https://panelapp.genomicsengland.co.uk/api/v1/panels",
        head=None
    ):
        self.endpoint = endpoint
        # Query PanelApp API. This is a generator and will not yield until iterated
        self._panels = self._get_panels()
        self.head = head
        # Set counter for head argument
        self.counter = 0

    def _get_panels(self):
        """Get all panels from instance endpoint"""
        response = requests.get(self.endpoint)
        response.raise_for_status()
        r = response.json()
        # Yield panels from the first response
        for panel in r['results']:
            yield panel
        # API responses from the /panels endpoint are paginated.
        # While the response dictionary contains a url for the next page.
        while r['next']:
            # Get panels from the next page of API results.
            response = requests.get(r['next'])
            r = response.json()
            for panel in r['results']:
                yield panel

    def __iter__(self):
        return self

    def __next__(self):
        if self.head:
            while self.counter < self.head:
                self.counter += 1
                return next(self._panels)
            else:
                raise StopIteration()
        else:
            return next(self._panels)
