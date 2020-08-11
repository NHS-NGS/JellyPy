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

    def query(self, ensembl_id):
        """Query the panel app panel for gene data.

        Args:
            ensembl_id (str): An ensembl gene identifier. E.g. "ENSG00000196411"
        Returns:
            query_result (tuple): Returns metadata for the first gene matching the input ensembl ID.
            query_result lists the hgnc id, hgnc symbol, panelapp confidence level and ensembl id:
                (
                    'HGNC:3395',
                    'EPHB4',
                    '3',
                    'ENSG00000196411',
                    'MONOALLELIC, autosomal or pseudoautosomal, imprinted status unknown'
                )
                If a matching gene is not found, query_result is (None, None, None, None, None).
        """
        # Iterate over genes in this panel
        for panel_gene in self._json['genes']:
            # Get ensembl ids for the current gene. An ensembl id is present for each reference
            #   genome. For example, p_ensembl_ids = ['ENSG00000139567',  'ENSG00000139567'].
            p_ensembl_ids = [
                ensembl_version['ensembl_id'] 
                for reference, ensembl_dict in panel_gene['gene_data']['ensembl_genes'].items()
                for ensembl_version in ensembl_dict.values() 
            ]
            # If the gene's ensembl id matches the function input, return gene metadata and exit.
            if ensembl_id in p_ensembl_ids:
                hgnc_id = panel_gene['gene_data']['hgnc_id']
                hgnc_symbol = panel_gene['gene_data']['hgnc_symbol']
                confidence_level = panel_gene['confidence_level']
                p_ensembl_id = ensembl_id
                mode_of_inheritance = panel_gene['mode_of_inheritance']
                return (hgnc_id, hgnc_symbol, confidence_level, p_ensembl_id, mode_of_inheritance)
        # Here, we have iterated over all genes and could not find ensemblID, hence the gene is not
        #   not present in the panel. Return a tuple containing None.
        else:
            return (None,None,None,None,None)

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
