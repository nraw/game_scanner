import json
import os
from datetime import date

import openai
from loguru import logger

from game_scanner.db import  save_document
from game_scanner.play_payload_management import (get_extra_info,
                                                  play_request_to_md)
from game_scanner.schemas import PlayRequest


def parse_chat(messages: list[dict], message_id: int = 0):
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]
    )
    system_prompt = get_processing_prompt(messages)
    try:
        params_raw = ping_gpt(client, system_prompt)
    except openai.RateLimitError as e:
        logger.error(e)
        answer = "Rate limit exceeded. Am I in trouble? (•̪ o •̪)"
        return answer
    params = json.loads(params_raw)
    play_request = PlayRequest(**params)
    data = play_request.model_dump()
    extra_info = get_extra_info(play_request)
    data.update(extra_info)
    play_request_md = play_request_to_md(data)
    data["message_id"] = message_id
    save_document(data, collection_name="play_requests")
    answer = play_request_md

    #  r = register_to_bgg(play_payload.model_dump())
    #  print(payload_to_md(play_payload))
    return answer


def get_processing_prompt(messages: list[dict]):
    user_name = "andrej"
    today = date.today().isoformat()
    conversation = [f"{message['role']}: {message['content']}" for message in messages]
    conversation_string = "\n".join(conversation)

    system_prompt = f"""you are an information retriever.
today is the {today}. 
the user is one of the players, {user_name}.
retrieve the parameters needed for the playrequest from the following conversation:
{conversation_string}

focus on the information provided by the user, as it might provide changes to the ones from the assistant.
"""
    return system_prompt


def ping_gpt(client, system_prompt):
    gpt_messages = [
        {
            "role": "system",
            "content": system_prompt,
        }
    ]

    tools, tool_choice = get_parameters_tool()
    # Create a chat completion
    chat_completion = client.chat.completions.create(
        messages=gpt_messages,
        #  model="gpt-3.5-turbo",
        model="gpt-3.5-turbo-0125",
        tools=tools,
        tool_choice=tool_choice,
    )
    params_raw = chat_completion.choices[0].message.tool_calls[0].function.arguments
    return params_raw


def get_parameters_tool():
    tool_name = "parse_play_info"
    tools = [
        {
            "type": "function",
            "function": {
                "description": "Parse the parameters needed to log a play",
                "name": tool_name,
                "parameters": PlayRequest.model_json_schema(),
            },
        }
    ]
    tool_choice = {"type": "function", "function": {"name": tool_name}}
    return tools, tool_choice
