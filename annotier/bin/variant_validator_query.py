"""
Functions to query variant validator API to get c. nomenclature for a
variant, required for querying LitVar API to retrieve papers.

Returns str with of c. variant nomenclature.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
201104
"""
import requests

from time import sleep
import sys


def fetch(query):
    """
    Query API and returns response
    """
    url = (
        "https://rest.variantvalidator.org/VariantValidator/variantvalidator/"
        "{}/{}/{}?content-type=application%2Fjson"
    )
    query = [requests.utils.quote(x) for x in query]

    url = url.format(query[0], query[1], query[2])

    headers = {"accept": "application/json"}
    response = None

    for i in range(1, 5):
        try:
            response = requests.get(url, headers=headers)
        except Exception as e:
            print("Error in querying variant validator, try {}/5: ".format(i))
            print("Error: ", e)
            sleep(5)
            continue

    if response is not None:
        try:
            response = response.json()
        except Exception as e:
            print("Error formatting response: ", e)
            return None
    else:
        return None

    if "errors" in response:
        return None

    return response


def query_variantvalidator(build, variant, transcript):
    """
    Call fetch() to query api with given build, variant descriptor and
    transcript.
    Args:
        - build (str): reference build
        - variant (str): formatted variant descriptor
        - transcript (str): specified transcript (return everything with "all")
    Returns:
        - reposonse(dict): JSON formatted response or None
    """
    query = [build, variant, transcript]

    response = fetch(query)

    return response


if __name__ == "__main__":

    build = "GRCh38"
    variant = "chr1:114570720:CTG:C"
    variant = "chr5:139326284:G:GAAATTTCT"
    transcript = "all"

    response = query_variantvalidator(build, variant, transcript)
    print(response)

    keys = response.keys()
    print(keys)

    correct_key = [x for x in keys if "NM_" in x][0]
        
    print("correct_key", correct_key)

    print(correct_key.split(":")[1])
