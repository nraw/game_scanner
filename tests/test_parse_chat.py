from game_scanner.parse_chat import *


def test_parse_chat():
    messages = [
        {
            "role": "user",
            "content": "We just finished playing a game of spirit island with Ele. She was the stone and I was the jester.",
        }
    ]
    #  messages = [
    #      {
    #          "role": "user",
    #          "content": "Add Gloomhaven to my wishlist",
    #      }
    #  ]
    answer = parse_chat(messages)
    assert "spirit island" in answer.lower()


def test_ping_gpt():
    client = openai.OpenAI(
        api_key=os.environ["OPENAI_API_KEY"], base_url=os.environ["OPENAI_BASE_URL"]
    )
    system_prompt = "Hi"
    params_raw = ping_gpt(client, system_prompt)
