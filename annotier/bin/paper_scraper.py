"""
Functions to find relevant papers for a variant.
Calls litvar API to get PMIDs for given variants in a
sample, then uses eUtils to return paper title and abstracts to
scrape for phenotype keywords from JSON to identify if relevant
to case.

Requires variant information, list of HPO terms
Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200916
"""
import ahocorasick
import entrezpy.conduit
import entrezpy.base.result
import entrezpy.base.analyzer
import json
import os
import pandas as pd
import pprint
import requests
import sys
import urllib
import xml.etree.ElementTree

try:
    from ncbi_credentials import ncbi_credentials
except ImportError:
    print("NCBI email and api_key must be defined in ncbi_credentials.py for\
        querying ClinVar")
    sys.exit(-1)


class PubmedRecord:
    """Simple data class to store individual Pubmed records. Individual
    authors will be stored as dict('lname':last_name, 'fname':
    first_name) in authors.
    Citations as string elements in the list citations. """

    def __init__(self):
        self.pmid = None
        self.title = None
        self.abstract = None
        self.authors = []
        self.references = []


class PubmedResult(entrezpy.base.result.EutilsResult):
    """Derive class entrezpy.base.result.EutilsResult to store Pubmed queries.
    Individual Pubmed records are implemented in :class:`PubmedRecord` and
    stored in :ivar:`pubmed_records`.

    :param response: inspected response from :class:`PubmedAnalyzer`
    :param request: the request for the current response
    :ivar dict pubmed_records: storing PubmedRecord instances"""

    def __init__(self, response, request):
        super().__init__(request.eutil, request.query_id, request.db)
        self.pubmed_records = {}

    def size(self):
        """Implement virtual method :meth:
        `entrezpy.base.result.EutilsResult.size`
        returning the number of stored data records."""
        return len(self.pubmed_records)

    def isEmpty(self):
        """Implement virtual method :meth:
        entrezpy.base.result.EutilsResult.isEmpty`
        to query if any records have been stored at all."""
        if not self.pubmed_records:
            return True
        return False

    def get_link_parameter(self, reqnum=0):
        """Implement virtual method :meth:
        `entrezpy.base.result.EutilsResult.get_link_parameter`.
        Fetching a pubmed record has no intrinsic elink capabilities and
        therefore should inform users about this."""
        print("{} has no elink capability".format(self))
        return {}

    def dump(self):
        """Implement virtual method :meth:
        `entrezpy.base.result.EutilsResult.dump`.

        :return: instance attributes
        :rtype: dict
        """
        return {self: {'dump': {
            'pubmed_records': [x for x in self.pubmed_records],
            'query_id': self.query_id, 'db': self.db,
            'eutil': self.function
        }}}

    def add_pubmed_record(self, pubmed_record):
        """The only non-virtual and therefore PubmedResult-specific
        method to handle adding new data records"""
        self.pubmed_records[pubmed_record.pmid] = pubmed_record


class PubmedAnalyzer(entrezpy.base.analyzer.EutilsAnalyzer):
    """Derived class of :class:`entrezpy.base.analyzer.EutilsAnalyzer`
    to analyze and parse PubMed responses and requests."""

    def __init__(self):
        super().__init__()

    def init_result(self, response, request):
        """Implemented virtual method :meth:
        `entrezpy.base.analyzer.init_result`.
        This method initiate a result instance when analyzing the first
        response"""
        if self.result is None:
            self.result = PubmedResult(response, request)

    def analyze_error(self, response, request):
        """Implement virtual method :meth:
        `entrezpy.base.analyzer.analyze_error`.
        Since we expect XML errors, just print the error to STDOUT for
        logging/debugging."""
        print(json.dumps({__name__: {'Response': {
            'dump': request.dump(),
            'error': response.getvalue()
        }}}))

    def analyze_result(self, response, request):
        """Implement virtual method :meth:
        `entrezpy.base.analyzer.analyze_result`.
        Parse PubMed  XML line by line to extract authors and citations.
        xml.etree.ElementTree.iterparse reads the XML file
        incrementally. Each pubmed entry is cleared after processing.

        Can be adjusted to include more/different tags to extract.
        Remember to adjust :class:`.PubmedRecord` as well."""
        self.init_result(response, request)
        isAuthorList = False
        isAuthor = False
        isRefList = False
        isRef = False
        isArticle = False
        medrec = None
        for event, elem in xml.etree.ElementTree.iterparse(
            response, events=["start", "end"]
        ):
            if event == 'start':
                if elem.tag == 'PubmedArticle':
                    medrec = PubmedRecord()
                if elem.tag == 'AuthorList':
                    isAuthorList = True
                if isAuthorList and elem.tag == 'Author':
                    isAuthor = True
                    medrec.authors.append({'fname': None, 'lname': None})
                if elem.tag == 'ReferenceList':
                    isRefList = True
                if isRefList and elem.tag == 'Reference':
                    isRef = True
                if elem.tag == 'Article':
                    isArticle = True
            else:
                if elem.tag == 'PubmedArticle':
                    self.result.add_pubmed_record(medrec)
                    elem.clear()
                if elem.tag == 'AuthorList':
                    isAuthorList = False
                if isAuthorList and elem.tag == 'Author':
                    isAuthor = False
                if elem.tag == 'ReferenceList':
                    isRefList = False
                if elem.tag == 'Reference':
                    isRef = False
                if elem.tag == 'Article':
                    isArticle = False
                if elem.tag == 'PMID':
                    if elem.text is not None:
                        medrec.pmid = elem.text.strip()
                    else:
                        medrec.pmid = None
                if isAuthor and elem.tag == 'LastName':
                    if elem.text is not None:
                        medrec.authors[-1]['lname'] = elem.text.strip()
                    else:
                        medrec.authors[-1]['lname'] = None
                if isAuthor and elem.tag == 'ForeName':
                    if elem.text is not None:
                        medrec.authors[-1]['fname'] = elem.text.strip()
                    else:
                        medrec.authors[-1]['fname'] = None
                if isRef and elem.tag == 'Citation':
                    if elem.text is not None:
                        medrec.references.append(elem.text.strip())
                if isArticle and elem.tag == 'AbstractText':
                    if not medrec.abstract:
                        if elem.text is not None:
                            medrec.abstract = elem.text.strip()
                        else:
                            medrec.abstract = None
                    else:
                        if elem.text is not None:
                            medrec.abstract += elem.text.strip()
                        else:
                            medrec.abstract = None
                if isArticle and elem.tag == 'ArticleTitle':
                    if elem.text is not None:
                        medrec.title = elem.text.strip()
                    else:
                        medrec.title = None


class litVar():
    """Functions to query LitVar API"""
    def __init__(self):
        self.session = requests.Session()

    def build_url(self, end_point, query):
        """
        Builds url from given query, returns list of dicts

        Args:
            - query (str): litvar query (i.e. c. change)

        Returns:
            - query_url (str): URL with query
        """
        url = "https://www.ncbi.nlm.nih.gov/research/bionlp/litvar/api/v1/{}{}"
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

        for i in range(1, 5):
            try:
                request = self.session.get(url, headers={
                    "Accept": "application/json"
                })
                break
            except Exception as e:
                print("Something went wrong: {}".format(e))
                print("Attempt {}/5, trying again".format(i))
                continue

        if request.ok:
            data = json.loads(request.content.decode("utf-8"))
            return data
        else:
            print("Error {} for URL: {}".format(request.status_code, url))
            return None


    def query_search(self, query):
        """
        Retrieves RSIDs for given query from LitVar API.

        Args:
            - query (str): query to search

        Returns:
            - rsid_data (dict): dict in JSON format of returned data
        """
        end_point = "entity/search/"

        query_url = self.build_url(end_point, query)
        rsid_data = self.call_api(query_url)

        return rsid_data


    def filter_rsids(self, rsid_data, variant):
        """
        Takes dict of RSID data and matches entries against correct
        variant from variant_info dict.

        Args:
            - rsid_data (dict): RSID entries returned fromquery_search()
            - variant (dict): dict of variant info to match against

        Returns:
            - rsids (list): list of RSIDs to return PMIDs from
        """
        rsids = ""

        if not rsid_data:
            return None
        for entry in rsid_data:
            if "genes" in entry["data"]:
                for gene in entry["data"]["genes"]:
                    if gene["name"] == variant["gene"]:
                        rsid = entry["id"].strip("#")
                        rsids += rsid
                        rsids += ","
            else:
                return None

        return rsids


    def get_pmids(self, rsid):
        """
        Get PMIDs for given RSIDs for variant from LitVar API.

        Args:
            - rsid (str): rsid of variant, returned in data dict from
                          query_search()

        Returns:
            - pmids (list): list of dicts of pmids
        """
        end_point = "public/rsids2pmids?"

        query = {"rsids": rsid}
        query = urllib.parse.urlencode(query)

        query_url = self.build_url(end_point, query)
        pmids = self.call_api(query_url)

        return pmids


class scrapePubmed():
    """
    Calls methods to query LitVar for PMIDs, then sets up connection to
    PubMed via eUtils conduit pipeline to retrieve titles and abstracts.
    """

    def __init__(self):
        pass

    def read_hpo(self):
        """
        Reads in HPO phenotype file to df for analysis.

        Args: None

        Returns:
            - hpo_df (df): df of all hpo terms from hpo file
        """
        print("Reading HPO file")

        try:
            hpo = os.path.join(
                os.path.dirname(__file__), "../data/hpo/phenotype.hpoa"
            )

            header = [
                "DatabaseID", "DiseaseName", "Qualifier", "HPO_ID", 
                "Reference", "Evidence", "Onset", "Frequency",
                "Sex", "Modifier", "Aspect", "Biocuration"
            ]

            hpo_df = pd.read_csv(
                hpo, sep="\t", low_memory=False, comment="#", names=header
            )

        except IOError as e:
            print("Error reading HPO phenotype file from /data/hpo/: ", e)
            print("Exiting now.")
            sys.exit(-1)

        return hpo_df


    def build_url(self, pmid):
        """Builds PubMed url from given PMID

        Args:
            - pmid (int): pmid of paper

        Returns:
            - url (str): url string from pmid
        """
        return str("https://pubmed.ncbi.nlm.nih.gov/{}/".format(pmid))


    def get_papers(self, pmids, ncbi_credentials):
        """
        For given PMIDs, returns the title and abstract of papers from
        Pubmed via eUtils.

        Args:
            - pmids (list): list of PMIDs from LitVar API
            - ncbi_credentials (dict): account credentials for using API

        Returns:
            - all_papers (list): list of dicts of paper titles and abstracts
        """

        c = entrezpy.conduit.Conduit(ncbi_credentials["email"])
        fetch_pubmed = c.new_pipeline()
        fetch_pubmed.add_fetch({
            'db': 'pubmed',
            'id': pmids,
            'retmode': 'xml',
            'retmax': 30
        },
            analyzer=PubmedAnalyzer())

        for i in range(1, 5):
            try:
                a = c.run(fetch_pubmed)
                break
            except TypeError as e:
                print("Error in entrezpy: ", e)
                print("Trying again {}/5".format(i))
                continue

        res = a.get_result()

        papers = []

        for i in res.pubmed_records:
            paper = {}
            print(res.pubmed_records[i])
            paper["pmid"] = res.pubmed_records[i].pmid
            paper["title"] = res.pubmed_records[i].title
            paper["abstract"] = res.pubmed_records[i].abstract
            paper["url"] = self.build_url(res.pubmed_records[i].pmid)
            papers.append(paper)

        return papers


    def hpo_to_phenotype(self, hpo_df, hpo_terms):
        """
        Get phenotype terms for given HPO terms.

        Args:
            - hpo_df (df): df of all hpo terms from phenotype.hpoa file
            - hpo_terms (list): list of dicts with HPO terms from JSON

        Returns:
            - phenotypes (list): list of phenotype terms from HPO terms
        """

        terms = [x["term"] for x in hpo_terms]

        phenotypes = hpo_df[hpo_df.HPO_ID.isin(terms)]["DiseaseName"].to_list()
        phenotypes = list(set(phenotypes))

        # split terms by ;, remove empty string entries
        phenotypes = [x.split(";") for x in phenotypes if x]
        phenotypes = [x.strip() for list in phenotypes for x in list if x]

        return phenotypes


    def scrape_paper(self, papers, phenotypes):
        """
        Takes returned papers from pubmed and attempts to match
        pheontype terms against abstract to ascertain
        relevance of paper to the variant in context of the phenotype.
        This uses the Aho-Corasick algoritm implemented through
        pyahocorasick.

        Args:
            - papers (dict): papers related to variant from pubmed
            - phenotypes (list): phenotype terms of case

        Returns:
            - papers (list): list of papers from input with extra
                "relevant" and "term" field if term identified, if not
                returns nulll
        """
        A = ahocorasick.Automaton()

        # build trie of phenotype terms to search with
        for idx, key in enumerate(phenotypes):
            A.add_word(key, (idx, key))

        A.make_automaton()

        counter = 0

        # for each paper, check if phenotype term is present
        for paper in papers:
            if paper["abstract"]:
                for end_index, (insert_order, original_value) in A.iter(
                    paper["abstract"]
                ):
                    print("relevant paper found")
                    papers[counter]["associated"] = True
                    papers[counter]["term"] = original_value

                if "associated" not in papers[counter]:
                    print("not relevant paper found")
                    papers[counter]["associated"] = False
                    papers[counter]["term"] = None
            else:
                # no abstract present
                papers[counter]["associated"] = False
                papers[counter]["term"] = None

            counter += 1

        return papers


    def main(self, variant, hpo_terms):
        """
        Calls LitVar API with variant to get RSIDs -> PMIDs, then calls
        eUtils API with PMIDs to return papers

        Args:
            - variant (dict): variant info in dict

        Returns:
            - papers (dict):
        """
        litvar = litVar()

        # get associated PMIDs for given variant from LitVar API
        rsid_data = litvar.query_search(variant["c_change"])
        rsids = litvar.filter_rsids(rsid_data, variant)

        if rsids:
            pmids = litvar.get_pmids(rsids)
            if len(pmids) != 0:
                # get title and abstract from PubMed via eUtils
                papers = self.get_papers(pmids, ncbi_credentials)
            else:
                return None

            # get phenotype terms for sample HPO terms
            hpo_df = self.read_hpo()

            # get relevant phenotype terms and search against papers
            phenotypes = self.hpo_to_phenotype(hpo_df, hpo_terms)
            papers = self.scrape_paper(papers, phenotypes)
        else:
            papers = None

        return papers


if __name__ == "__main__":

    scraper = scrapePubmed()
    variant = {"gene": "MAN2B1", "c_change": "c.1830+1G>C"}
    hpo_terms = [{"term": "this"}]
    scraper.main(variant, hpo_terms)
