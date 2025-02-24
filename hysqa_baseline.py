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
    examples = utils.get_examples(key="identify_title", file_path="examples.json")
    prompt = f"""Task: Your task is extracting a publication title from the given phrase. 
                Example
                    {examples}                    
                Do not add anything else.
                Please provide your result in JSON format only. Please do not include the Example in your response.

                phrase: {phrase}
            """
    title = llms.chatgpt(prompt, 6)
    return title


def identify_sub_question_phrase(question, q_type='bridge'):
    if q_type == 'bridge':
        examples = utils.get_examples(key="identify_sub_question_phrase_bridge",file_path="examples.json")
    else:
        examples = utils.get_examples(key="identify_sub_question_phrase_comparison",file_path="examples.json")
    prompt = f"""[INST]Task: Your task is extracting the sub-question phrases and publication titles in a given QUESTION.
            Example:
             {examples}                    
            Do not add anything else.
            [/INST]          
            [{{sub_question_phrase: sub question phrase}},
            {{title: title}}
            ]
            [INST]
            Please provide your result in JSON format only. Please do not include the Example in your response.
            [/INST] 

            question: {question}

        """
    # return test_chatAI.test_chat_ai(prompt)#llms.chatgpt(prompt, 5)  # .llama(decomposition_prompt)
    sub_questions = llms.chatgpt(prompt, 5)
    utils.write_to_json(sub_questions, "sub_questions.json")
    formatted_sub_questions = utils.load_json_data("sub_questions.json")
    return formatted_sub_questions


def answer_retrieval(question, author_name, context, prompt=''):
    if prompt == '':
        prompt = f"""[INST]Task: You are an experienced assistant.
                   Your task is answering in the question using the given in the CONTEXT.
                   Do not modify the answer. If you do not find an answer in the CONTEXT say 'answer not found'.
                   For your information, the author of the publication stated in question is {author_name}.
                   Please do not add any text, only display the answer!
                   [/INST]
                   Question:{question}
                   CONTEXT: {context}
                   ANSWER:
                """
    model_answer = llms.chatgpt(prompt) # llama(prompt)
    return model_answer