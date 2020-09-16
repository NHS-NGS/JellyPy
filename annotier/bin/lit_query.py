"""
Functions to call litvar API to get PMIDs for given variants in a
sample, allows to annotate variants with new literature

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200916
"""

import json
import requests
import sys

class litVar():

    def __init__(self):
        pass
    

    def build_url(self, end_point, query):
        """
        Builds url from given query, returns list of dicts

        Args:
            - query (str): litvar query (i.e. c. change)
        
        Returns:
            - query_url (str): URL with query
        """
        url = "https://www.ncbi.nlm.nih.gov/research/bionlp/litvar/api/v1/{}/{}"
        query_url = url.format(end_point, query)

        return query_url
    

    def call_api(self, url):
        """
        Make call to API with given url including search term

        Args:
            - query_url (str): URL with query
        
        Returns:
            - data (dict): dict in JSON format of returned data
        """

        try:
            request = requests.get(url, headers={"Accept": "application/json"})
        except Exception as e:
            print("Something went wrong: {}".format(e))
            sys.exit(-1)

        if request.ok:
            data = json.loads(request.content.decode("utf-8"))
            return data
        else:
            print("Error {} for URL: {}".format(request.status_code, url))
            sys.exit(-1)
    

    def query_search(self, query):
        """
        Retrieves top variants for given query

        Args:
            - query (str): query to search
        
        Returns:
            - data (dict): dict in JSON format of returned data
        """
        end_point = "entity/search"

        query_url = self.build_url(end_point, query)
        print(query_url)
        data = self.call_api(query_url)

        return data

