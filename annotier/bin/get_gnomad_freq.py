"""
Functions to query gnomAD API endpoint to get allele frequencies for variants.
Returns dict of in-silico predictions and total af.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
201103
"""
import requests


def fetch(jsonquery):
    """
    Query API and returns response
    """
    url = "https://gnomad.broadinstitute.org/api"
    headers = {"Content-Type": "application/json", "charset": "utf-8"}
    response = requests.post(url, json=jsonquery, headers=headers)
    json = response.json()

    if "errors" in json:
        return

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
