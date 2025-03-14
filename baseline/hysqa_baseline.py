import json
from urllib.parse import urlparse
import os

import rag
import utils
import llms
import re

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
        examples = utils.get_examples(key="identify_sub_question_phrase_bridge", file_path="examples.json")
    else:
        examples = utils.get_examples(key="identify_sub_question_phrase_comparison", file_path="examples.json")
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


def answer_kg_kg_questions(question, q_type, author_dblp_uri):
    subqs = (identify_sub_question_phrase(question, q_type))
    context = []
    question_decomposition_process = [question]
    updated_question = question
    sub_question_phrase = ''
    if 'sub_question_phrase' in subqs:
        visited_nodes = []
        if q_type == 'bridge':
            sub_question_phrase = subqs['sub_question_phrase'][0]
            title = get_title(subqs)
            entity = entity_resolution(title)
            author_uri = author_dblp_uri.strip('<>')
            if entity:
                for entity_item in entity:
                    if 'orcid' in entity_item:
                        if urlparse(entity_item['author']) == urlparse(author_uri):
                            updated_question = question.replace(sub_question_phrase, entity_item['primarycreatorname'])
                            question_decomposition_process.append(updated_question)
                        semoa_record = utils.search_semoa(entity_item['orcid'])
                        # print(semoa_record)
                        if entity_item['author'] not in visited_nodes:
                            visited_nodes.append(entity_item['author'])
                            context.append(semoa_record)
            if not context:
                context.append(kg_kg_search(author_dblp_uri))
        if q_type == 'comparison':
            author_uris = [author_dblp_uri[0]['author1_dblp_uri'].strip('<>'),
                           author_dblp_uri[0]['author2_dblp_uri'].strip('<>')]
            if len(subqs['sub_question_phrase']) > 1:
                # if 'title' not in subqs:
                title_1 = identify_title(subqs['sub_question_phrase'][0])
                title_2 = identify_title(subqs['sub_question_phrase'][1])
                entity_1 = entity_resolution(title_1['title'][0])
                entity_2 = entity_resolution(title_2['title'][0])
                if entity_1 and entity_2:
                    for entity_1_item in entity_1:
                        if 'orcid' in entity_1_item:
                            if entity_1_item['author'] in author_uris:
                                updated_question = question.replace(subqs['sub_question_phrase'][0],
                                                                    entity_1_item['primarycreatorname'])
                                question_decomposition_process.append(updated_question)
                            semoa_record_1 = utils.search_semoa(entity_1_item['orcid'])
                            if entity_1_item['author'] not in visited_nodes:
                                visited_nodes.append(entity_1_item['author'])
                                context.append(semoa_record_1)

                    for entity_2_item in entity_2:
                        if 'orcid' in entity_2_item:
                            if entity_2_item['author'] in author_uris:
                                updated_question = updated_question.replace(subqs['sub_question_phrase'][1],
                                                                            entity_2_item['primarycreatorname'])
                                question_decomposition_process.append(updated_question)
                            semoa_record_2 = utils.search_semoa(entity_2_item['orcid'])
                            if entity_2_item['author'] not in visited_nodes:
                                visited_nodes.append(entity_2_item['author'])
                                context.append(semoa_record_2)
                if not context:
                    context.append(kg_kg_search(author_uris[0]))
                    context.append(kg_kg_search(author_uris[1]))
    else:
        if q_type == 'bridge':
            context.append(kg_kg_search(author_dblp_uri))
        if q_type == 'comparison':
            author_uris = [author_dblp_uri[0]['author1_dblp_uri'].strip('<>'),
                           author_dblp_uri[0]['author2_dblp_uri'].strip('<>')]
            context.append(kg_kg_search(author_uris[0]))
            context.append(kg_kg_search(author_uris[1]))
    if context:
        answer = answer_extractor(updated_question, context)
        return answer, question_decomposition_process, context, sub_question_phrase
    else:
        return None, question_decomposition_process, context, sub_question_phrase


def kg_kg_search(author_dblp_uri):
    author_uri = author_dblp_uri.strip('<>')
    result = entity_resolution(f"<{author_uri}>", False)
    if result:
        for r in result:
            if 'orcid' in r:
                semoa_record = utils.search_semoa(r['orcid'])
                return semoa_record


def kg_text_search_info(question, sub_question_phrase, author_dblp_uri):
    result = entity_resolution(author_dblp_uri, False)
    out_file_path = ''
    updated_question = question
    for r in result:
        if 'wikipedia' in r:
            updated_question = question.replace(sub_question_phrase, r['primarycreatorname'])
            out_file_path, wikipedia_text = get_wikipedia_text(r['wikipedia'])
    return out_file_path, updated_question


def answer_kg_text_questions(docs_embedding_generator, question, author_dblp_uri):
    sub_question = identify_sub_question_phrase(question)
    question_decomposition_process = [question]
    out_file_path = ''
    sub_question_phrase = ''
    if 'sub_question_phrase' in sub_question:
        sub_question_phrase = sub_question['sub_question_phrase'][0]
        title = get_title(sub_question)
        entity = entity_resolution(title)
        author_uri = author_dblp_uri.strip('<>')
        updated_question = question
        if entity:
            for entity_item in entity:
                if urlparse(entity_item['author']) == urlparse(author_uri):
                    updated_question = question.replace(sub_question_phrase, entity_item['primarycreatorname'])
                    out_file_path, wikipedia_text = get_wikipedia_text(entity_item['wikipedia'])
                    question_decomposition_process.append(updated_question)
            if out_file_path == '':
                out_file_path, updated_question = kg_text_search_info(question, sub_question_phrase, author_dblp_uri)
        else:
            out_file_path, updated_question = kg_text_search_info(question, sub_question_phrase, author_dblp_uri)
    else:
        result = entity_resolution(author_dblp_uri, False)
        # print(result)
        for r in result:
            if 'wikipedia' in r:
                out_file_path, wikipedia_text = get_wikipedia_text(r['wikipedia'])
    if os.path.exists(out_file_path):
        response = rag.rag_answer_generator(docs_embedding_generator, out_file_path, updated_question)
        return response
    else:
        return None


def get_wikipedia_text(wikipedia_uri):
    write_to_path = "entity.txt"
    directory = os.path.dirname(write_to_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    parsed_url, title, wikipedia_text = utils.extract_text_from_wikipedia(wikipedia_uri)
    if wikipedia_text is None:
        return None, None
    pattern = r'\[\d+\]'
    cleaned_wikipedia_text = re.sub(pattern, '', wikipedia_text)
    cleaned_wikipedia_text = cleaned_wikipedia_text.strip()
    with open(write_to_path, "w", encoding="utf-8") as txt_file:
        txt_file.write(cleaned_wikipedia_text)
    return "entity_text", cleaned_wikipedia_text


def entity_semoa_facts(semoa_record):
    records = []
    if 'institute' in semoa_record:
        for institute_info in semoa_record['institute']:
            records.append({'institute_name': institute_info['name'],
                            'wikipedia_uri': institute_info['wikipedia_url']})
    return records


def kg_kg_text_search_info(author_dblp_uri):
    kg_context = []
    out_file_path = ''
    result = entity_resolution(author_dblp_uri, False)
    if result:
        for r in result:
            temp = ''
            semoa_record = utils.search_semoa(r['orcid'])
            if semoa_record:
                entity_semoa_info = entity_semoa_facts(semoa_record)
                if 'wikipedia_uri' in entity_semoa_info[0]:
                    # print(True)
                    out_file_path, wikipedia_text = get_wikipedia_text(entity_semoa_info[0]['wikipedia_uri'])
                    temp = entity_semoa_info[0]['institute_name']
            kg_context.append({'author_name': r['primarycreatorname'], 'institute_name': temp})
            # print(kg_context)
    return out_file_path, kg_context


def answer_kg_kg_text_questions(docs_embedding_generator, question, author_dblp_uri):
    sub_question = identify_sub_question_phrase(question)
    question_decomposition_process = [question]
    kg_context = []
    visited_nodes = []
    sub_question_phrase = ''
    out_file_path = ''
    updated_question = question
    if 'sub_question_phrase' in sub_question:
        sub_question_phrase = sub_question['sub_question_phrase'][0]
        title = get_title(sub_question)
        if title != '':
            entity = entity_resolution(title)
            author_uri = author_dblp_uri.strip('<>')
            if entity:
                for entity_item in entity:
                    if urlparse(entity_item['author']) == urlparse(author_uri):
                        updated_question = question.replace(sub_question_phrase, entity_item['primarycreatorname'])
                        question_decomposition_process.append(updated_question)
                    # print(entity_item['orcid'])
                    # parsed_url = urlparse(entity_item['orcid'])
                    # url_string = parsed_url.geturl().strip()
                    semoa_record = utils.search_semoa(entity_item['orcid'])
                    # print(semoa_record)
                    if semoa_record:
                        entity_semoa_info = entity_semoa_facts(semoa_record)
                        if entity_semoa_info:
                            if 'wikipedia_uri' in entity_semoa_info[0]:
                                out_file_path, wikipedia_text = get_wikipedia_text(
                                    entity_semoa_info[0]['wikipedia_uri'])

                                if entity_item['author'] not in visited_nodes:
                                    visited_nodes.append(entity_item['author'])
                                    kg_context.append({'author_name': entity_item['primarycreatorname'],
                                                       'institute_name': entity_semoa_info[0]['institute_name']})
            else:
                out_file_path, kg_context = kg_kg_text_search_info(author_dblp_uri)
        else:
            out_file_path, kg_context = kg_kg_text_search_info(author_dblp_uri)
    else:
        out_file_path, kg_context = kg_kg_text_search_info(author_dblp_uri)
    if os.path.exists(out_file_path):
        response = rag.rag_answer_generator(docs_embedding_generator, out_file_path, updated_question, kg_context, True)
        # print(response)
        return response
    else:
        return None


def answer_extractor(question, context):
    prompt = f"""Task: Your task is answering the question based on the given context.
                 Do not add anything else.
                 Please provide your result in JSON format only. Please do not include the Example in your response.

                 context: {context}
                 question:{question}
                 answer: 
            """
    answer = llms.chatgpt(prompt, 4)  # test_chatAI.test_chat_ai(prompt) # llms.chatgpt(prompt, 4)  #   #
    return answer


def process_rag_result(q_id, rag_result, q_type, source_type, reasoning_path):
    model_answer = rag_result[0]['answer'] if rag_result else ''
    input_to_rag = rag_result[0]['input'] if rag_result else ''
    rag_context = rag_result[0]['context'] if rag_result else ''
    return {
        "id": q_id,
        "answer": model_answer,
        "input_question_to_rag": input_to_rag,
        "context": rag_context,
        "type": q_type,
        "source_type": source_type,
        "reasoning_path": reasoning_path
    }


def run_answer_extraction(file_name):
    test_data = utils.load_json_data(file_name)
    answer_predictions = utils.load_json_data("data/experiment/answer_predictions.json")
    utils.write_to_json(answer_predictions, "answer_predictions_backup.json")
    docs_embedding_generator = rag.DocsEmbeddingsGenerator()
    for item in test_data:  # [3000:3003]:
        question = item['question']
        q_type = item['type']
        author_dblp_uri = item['author_dblp_uri']
        # print(identify_bridging_entity(question))
        source_type = " ".join(item['source_types'])
        if source_type == 'KG KG':
            answer, question_decomposition_history, context, sqp = answer_kg_kg_questions(question, q_type,
                                                                                          author_dblp_uri)
            answer_predictions.append({"id": item["id"],
                                       "answer": answer,
                                       "sub_question_phrase": sqp,
                                       "question_decomposition_history": question_decomposition_history,
                                       "context": context,
                                       "type": q_type,
                                       "source_type": source_type,
                                       "reasoning_path": "dblp semoa"
                                       })
        else:
            reasoning_path = " ".join(item["reasoning_path"])
            if reasoning_path == "dblp author wikipedia text":
                rag_result = answer_kg_text_questions(docs_embedding_generator, question, author_dblp_uri)
                answer_predictions.append(
                    process_rag_result(item["id"], rag_result, q_type, source_type, reasoning_path))
            else:
                rag_result = answer_kg_kg_text_questions(docs_embedding_generator, question, author_dblp_uri)
                answer_predictions.append(
                    process_rag_result(item["id"], rag_result, q_type, source_type, reasoning_path))

        utils.write_to_json(answer_predictions, "data/experiment/answer_predictions.json")


def parse_nested_json(json_obj):
    if isinstance(json_obj, str):
        try:
            nested_data = json.loads(json_obj)
            return nested_data
        except json.JSONDecodeError:
            return json_obj
    return json_obj


def extract_data(json_input):
    # Ensure the input is always a string before parsing
    if isinstance(json_input, dict):
        data = json_input
    else:
        try:
            data = json.loads(json_input)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return

    if not isinstance(data, dict):
        print("JSON data is not a dictionary.")
        return

    id_value = data.get("id", "No ID")
    answer_data = data.get("answer")

    if answer_data:
        answer_data = parse_nested_json(answer_data)

    return id_value, answer_data


def parse_answer_predictions():
    clean_prediction = utils.load_json_data("cleaned_answer_predictions.json")
    final_predictions = []
    for item in clean_prediction:
        _id, answer = extract_data(item)
        final_predictions.append({"id": _id, "answer": answer})
    utils.write_to_json(final_predictions, "answer_predictions.json")
    predictions = utils.load_json_data("answer_predictions.json")
    model_predictions = []
    for item in predictions:
        try:
            if isinstance(item['answer'], dict):
                values = list(item['answer'].values())
                answer = values[0]
            else:
                ans_json = parse_nested_json(item['answer'])
                answer = list(ans_json.values())[0]
        except Exception as e:
            answer = ""
            print(f"An error occurred while converting to list: {e}")

        model_predictions.append({"id": item["id"], "answer": answer})
    utils.write_to_json(model_predictions, "answer_prediction.json")


if __name__ == "__main__":
    run_answer_extraction("data/hysqa_test_set.json")