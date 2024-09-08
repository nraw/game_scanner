from game_scanner.parse_chat import *


def test_parse_chat():
    messages = [
        {
            "role": "user",
            "content": "We just finished playing a game of spirit island with Ele. She was the stone and I was the jester.",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "When is the last time I played spirit island?",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "I played chess today with mom. Score was 3-0",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "Who played against whom in the last game of war chest?",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "What is the last game I played?",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "What are all the spirits I've played in spirit island? They should be marked with A:",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "There should be a game of terraforming mars in my history for today. Can you delete it?",
        }
    ]
    messages = [
        {
            "role": "user",
            "content": "Can you tell me more about the game Bestiary of Sigillum?",
        }
    ]
    #  messages = [
    #      {
    #          "role": "user",
    #          "content": "Add Gloomhaven to my wishlist",
    #      }
    #  ]

    messages.append(
        {
            "role": "user",
            "content": "That's bullocks? Did you just make all of that up? Quite impressive actually :D",
        }
    )
    answer = parse_chat(messages)
    assert "spirit island" in answer.lower()


def test_ping_gpt():
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]
    )
    system_prompt = "Hi"
    params_raw = ping_gpt(client, system_prompt)
    assert params_raw is not None
