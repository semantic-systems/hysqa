from SPARQLWrapper import SPARQLWrapper, JSON
import json


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

