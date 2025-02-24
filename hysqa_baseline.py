import utils
import llms

def get_title(sub_question):
    title = ''
    if 'title' in sub_question:
        if isinstance(sub_question['title'], list):
            if len(sub_question['title']) > 0:
                title = sub_question['title'][0]
    else:
        title_dict = identify_title(sub_question['sub_question_phrase'][0])
        utils.write_to_json(title_dict, "title_updated.json")
        title_new = utils.load_json_data("title_updated.json")
        if 'title' in title_new:
            if len(title_new['title']) > 0:
                title = title_new['title'][0]
    return title


def entity_resolution(entity='', flag=True):
    sparql_end_point = "https://dblp-april24.skynet.coypu.org/sparql"
    if flag:
        entity = entity.rstrip("'")
        entity = entity.lstrip("'")
        entity = entity.rstrip('"')
        entity = entity.lstrip('"')
        if not entity.endswith('.'):
            entity += '.'
        query = """PREFIX dblp: <https://dblp.org/rdf/schema#>
                SELECT *
                  WHERE {
                  ?paper dblp:title "%s" .
                  ?author ^dblp:authoredBy ?paper ;
                          dblp:primaryCreatorName ?primarycreatorname ;
                          dblp:orcid ?orcid ;
                          dblp:wikipedia ?wikipedia .
                  FILTER (CONTAINS(STR(?wikipedia), "en.wikipedia.org"))
                }"""
    else:
        query = """PREFIX dblp: <https://dblp.org/rdf/schema#>
                SELECT *
                  WHERE {
                  %s dblp:primaryCreatorName ?primarycreatorname ;
                     dblp:orcid ?orcid ;
                     dblp:wikipedia ?wikipedia .
                  FILTER (CONTAINS(STR(?wikipedia), "en.wikipedia.org"))
                }"""

    sparql_result = utils.run_sparql_query(sparql_end_point, query, entity, True)
    search_result = []
    if sparql_result:
        for result in sparql_result["results"]["bindings"]:
            temp = {}
            for key, value_info in result.items():
                temp[key] = value_info.get('value')
            search_result.append(temp)
    # print(search_result)
    return search_result


def identify_title(phrase):
    examples = utils.get_examples(key="identify_title", file_path="./examples.json")
    prompt = f"""Task: Your task is extracting a publication title from the given phrase. 
                Example
                    {examples}                    
                Do not add anything else.
                Please provide your result in JSON format only. Please do not include the Example in your response.

                phrase: {phrase}
            """
    title = llms.chatgpt(prompt, 6)
    return title
