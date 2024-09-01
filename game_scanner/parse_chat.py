import json
import os
from datetime import date

import openai
from loguru import logger

from game_scanner.add_wishlist import add_wishlist
from game_scanner.db import save_document
from game_scanner.play_payload_management import (get_bgg_id, get_extra_info,
                                                  play_request_to_md)
from game_scanner.register_play import log_play_to_bgg, register_to_bgg
from game_scanner.schemas import (BGGIdReuqest, LogRequest, PlayRequest,
                                  WishlistRequest)

func_map = {
    "log_game": log_play_to_bgg,
    "wishlist_game": add_wishlist,
    "get_bgg_id": get_bgg_id,
}


def parse_chat(messages: list[dict], message_id: int = 0):
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]
    )
    text = None
    params_raw = None
    while text is None:
        gpt_messages = get_processing_prompt(messages)
        try:
            text, params_raw = ping_gpt(client, gpt_messages)
        except openai.RateLimitError as e:
            logger.error(e)
            answer = "Rate limit exceeded. Am I in trouble? (•̪ o •̪)"
            return answer
        if params_raw is not None:
            messages.append(
                {
                    "role": "assistant",
                    "content": f"Function call: {params_raw}",
                }
            )
            params = json.loads(params_raw.arguments)
            func_name = params_raw.name
            func = func_map[func_name]
            output = func(**params)
            messages.append(
                {
                    "role": "system",
                    "content": f"Function output: {output}",
                }
            )
    messages.append(
        {
            "role": "assistant",
            "content": text,
        }
    )
    save_document(
        {"message_id": message_id, "messages": messages}, collection_name="messages"
    )
    return text

    #  play_request = PlayRequest(**params)
    #  data = play_request.model_dump()
    #  extra_info = get_extra_info(play_request)
    #  data.update(extra_info)
    #  play_request_md = play_request_to_md(data)
    #  data["message_id"] = message_id
    #  save_document(data, collection_name="play_requests")
    #  answer = play_request_md

    #  r = register_to_bgg(play_payload.model_dump())
    #  print(payload_to_md(play_payload))
    return answer


def get_processing_prompt(messages: list[dict]):
    user_name = "andrej"
    today = date.today().isoformat()

    system_prompt = f"""You are a personal board game assistant.
Today is the {today}. 
The user is one of the players, {user_name}.
You have the ability to log plays and add games to wishlists.
Those actions require the BoardGameGeek ID of the game. You have a function available to you to identify the id from the game.
When referring to a game back to the user, make a markdown hyperlink like so 
[<game>](https://boardgamegeek.com/boardgame/<game_id>)
where you replace <game> and <game_id> with the name of the game and the id of the game respectively.
"""
    gpt_messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        *messages,
    ]

    return gpt_messages


def ping_gpt(client, gpt_messages):
    #  gpt_messages = [
    #      {
    #          "role": "system",
    #          "content": system_prompt,
    #      }
    #  ]

    #  tools, tool_choice = get_parameters_tool()
    tools, tool_choice = get_all_tools()
    # Create a chat completion
    chat_completion = client.chat.completions.create(
        messages=gpt_messages,
        #  model="gpt-3.5-turbo",
        model="gpt-4o",
        tools=tools,
        tool_choice=tool_choice,
    )
    first_choice = chat_completion.choices[0].message
    text = first_choice.content
    if first_choice.tool_calls:
        params_raw = first_choice.tool_calls[0].function
    else:
        params_raw = None
    return text, params_raw


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


def get_all_tools():
    tool_choice = "auto"
    #  tool_choice = "required"
    tools = [
        {
            "type": "function",
            "function": {
                "description": "Add a log of a play",
                "name": "log_game",
                "parameters": LogRequest.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "description": "Add the game to the wishlist",
                "name": "wishlist_game",
                "parameters": WishlistRequest.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "description": "Get the BoardGameGeek ID of a game",
                "name": "get_bgg_id",
                "parameters": BGGIdReuqest.model_json_schema(),
            },
        },
    ]
    return tools, tool_choice
