import requests
import json
from openai import OpenAI
import utils


def chatgpt(prompt, function_call_flag=1):
    answer_generation_function = [
        {
            "name": "answer_generation_function",
            "description": "Answer the given question based on the given context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Answer of the given question",
                    }
                }
            }

        }
    ]

    question_answer_pair_generation_function_gpt3_5 = [
        {
            "name": "question_answer_pair_generation",
            "description": "Generate a questions with an answer, where the answer is a word or set of "
                           "consecutive words in the given data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of questions generated from the given facts.",
                    },
                    "answer": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Each question respective answer. Be sure the answer is a word or set of "
                                       "consecutive words.",
                    }
                }
            }

        }
    ]
    sub_question_phrase_identification_function = [
        {
            "name": "sub_question_phrase_identification_function",
            "description": "Extract the sub-question phrases and title from the given question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sub_question_phrase": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Sub-question phrase in a given question. Be sure to follow the examples given in the prompt",
                    },
                    "title": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Publication title in a question. Be sure to follow the examples given in the prompt",
                    }
                }
            }

        }
    ]
    title_extraction_function = [
        {
            "name": "title_extraction_function",
            "description": "Extract the title from the given phrase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "Publication title in a question. Be sure to follow the examples given in the prompt",
                    }
                }
            }

        }
    ]

    if function_call_flag == 1:
        function_call = question_answer_pair_generation_function_gpt3_5
    elif function_call_flag == 4:
        function_call = answer_generation_function
    elif function_call_flag == 5:
        function_call = sub_question_phrase_identification_function
    elif function_call_flag == 6:
        function_call = title_extraction_function

    # question_answer_pair_generation_function_gpt3_5 this is for question generation
    model = "gpt-3.5-turbo" # "gpt-4o" # "gpt-4o-mini" #"gpt-4-turbo"  # "gpt-4"
    client = OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt}
        ],
        functions=function_call,
        function_call='auto'
    )
    try:
        json_response = json.loads(completion.choices[0].message.function_call.arguments)
        # print(json_response)
        return json_response
    except Exception as e:
        print(f"An error occurred: {e}")
        return ""


def llama(user_prompt, sys_prompt_string="You are an experienced..."):
    server_url = "http://localhost:11434/api/generate"
    model = "llama3:instruct"  # "instruct" # "llama3:8B"
    # model = "llama3:8B"
    # "prompt": prompt,
    # [{"role": "user", "content": prompt}],
    messages = [
        {"role": "system", "content": sys_prompt_string},
        {"role": "user", "content": user_prompt}]

    data = dict(model=model, prompt=user_prompt, stream=False)

    headers = {"content-type": "application/json"}

    response = requests.post(server_url, headers=headers, data=json.dumps(data))
    # Check for successful response
    if response.status_code == 200:
        response_data = response.json()
        # print(f"Model: {response_data["model"]}")
        # print(f"Response: {response_data["response"]}")
        return response_data["response"]
    else:
        print(f"Error: {response.status_code}")
        return None
