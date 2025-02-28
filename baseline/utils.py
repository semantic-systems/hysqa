from SPARQLWrapper import SPARQLWrapper, JSON
from urllib.parse import urlparse
from bs4 import BeautifulSoup, SoupStrainer
import urllib
from urllib.request import urlopen
from urllib.parse import quote
import json
import re
import importlib


def get_examples(key, file_path="./examples.json"):
    with open(file_path, 'r', encoding='utf-8') as file:
        examples = json.load(file)
    return examples.get(key, None)


def extruct_values(results):
    return_result = []
    for result in results["results"]["bindings"]:
        converted_result = {}
        for key, value_info in result.items():
            value = value_info.get('value')
            if value:
                converted_result[key] = value
        return_result.append(converted_result)
    return return_result


def run_sparql_query(sparql_endpoint, sparql_query, param='', flag=False):
    if flag:
        sparql_query = sparql_query % param
    try:
        sparql = SPARQLWrapper(sparql_endpoint)
        sparql.setQuery(sparql_query)
        sparql.setReturnFormat(JSON)
        result = sparql.query().convert()
        return result
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    return


def query_sparql_endpoint(endpoint_url, sparql_query, search_key, flag=False):
    sparql = SPARQLWrapper(endpoint_url)
    if flag:
        sparql.setQuery(sparql_query % (search_key, search_key, search_key.strip("<>").strip()))
    else:
        sparql.setQuery(sparql_query % search_key)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return_result = []
    for result in results["results"]["bindings"]:
        converted_result = {}
        for key, value_info in result.items():
            value = value_info.get('value')
            if value:
                converted_result[key] = value
        return_result.append(converted_result)
    return return_result


def search_semoa(author_dblp_orcid):
    sparql_endpoint = "http://localhost:3030/sopena/sparql"
    orcid_query = """PREFIX ns2: <https://semopenalex.org/ontology/>
               PREFIX ns3: <http://purl.org/spar/bido/>
               PREFIX ns4: <https://dbpedia.org/ontology/>
               PREFIX ns5: <https://dbpedia.org/property/>

               SELECT * WHERE
               {
               GRAPH <https://semopenalex.org/authors/context> {
                 {
                   OPTIONAL {?author_uri ns2:orcidId ?orcid . }
                   OPTIONAL {?author_uri ns3:orcidId ?orcid . }
                   OPTIONAL { ?author_uri ns4:orcidId ?orcid . }
                   OPTIONAL { ?author_uri ns5:orcidId ?orcid . }
                   FILTER (?orcid = "%s")
                   }
                   }
               } 
           """
    orcid_query_result = query_sparql_endpoint(sparql_endpoint, orcid_query, author_dblp_orcid)
    if orcid_query_result:
        author_semoa_uri = orcid_query_result[0]['author_uri']
        return author_semoa_uri
    else:
        return None


def extract_text_from_wikipedia(url):
    try:
        decoded_url = urllib.parse.unquote(url)
        wikipedia_url = decoded_url.replace(" ", "_")
        encoded_url = quote(wikipedia_url, safe=':/')
        source = urlopen(encoded_url).read()
        soup = BeautifulSoup(source, 'lxml')
        title = soup.title.string.strip()
        title = title.rstrip('- Wikipedia')
        text = ''
        for paragraph in soup.find(id="bodyContent").find_all('p'):
            text += paragraph.text
        pattern = r'\[\d+\]'
        cleaned_wikipedia_text = re.sub(pattern, '', text)
        cleaned_wikipedia_text = cleaned_wikipedia_text.strip()
        return cleaned_wikipedia_text
    except Exception as e:
        print(f"General Exception: {e}")
        print(f"Failed to retrieve: {url}")
        return None