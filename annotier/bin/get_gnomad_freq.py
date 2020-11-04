"""
Functions to query gnomAD API endpoint to get allele frequencies for variants.
Returns dict of in-silico predictions and total af.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
201103
"""
import requests

from time import sleep


def fetch(jsonquery):
    """
    Query API and returns response
    """
    url = "https://gnomad.broadinstitute.org/api"
    headers = {"Content-Type": "application/json", "charset": "utf-8"}
    response = None

    for i in range(1, 5):
        try:
            response = requests.post(url, json=jsonquery, headers=headers)
        except Exception as e:
            print("Error in querying gnomAD, try {}/5: ".format(i))
            print("Error: ", e)
            sleep(5)
            continue

    if response is not None:
        try:
            json = response.json()
        except Exception as e:
            print("Error formatting response: ", e)
            return None
    else:
        return None

    if "errors" in json:
        return None

    return json


def gnomad_query(variant):
    """
    Format query for GraphQL query to gnomAD API.

    Args: variant (str): variant to query
    """

    query = """
    {{
        variant(variantId:"{}", dataset: gnomad_r3) {{
          in_silico_predictors {{
            value
            id
          }}
        genome {{
          ac
          an
        }}
        }}
    }}
    """.format(variant)

    response = fetch({"query": query})
    print("response: ", response)
    if response is not None:
        response = response["data"]["variant"]

        # calculate freq. from ac / an
        freq = response["genome"]["ac"] / response["genome"]["an"]
        freq = f"{freq:.9f}"

        # add af to response
        del response["genome"]
        response["af"] = freq

    return response


if __name__ == "__main__":
    variant = "1-114570720-CTG-C"
    gnomad_query(variant)
