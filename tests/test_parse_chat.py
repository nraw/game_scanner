from game_scanner.parse_chat import *


def test_parse_chat():
    messages = [
        {
            "role": "user",
            "content": "We just finished playing a game of spirit island with Ele. She was the stone and I was the jester.",
        }
    ]
    answer = parse_chat(messages)
    assert "spirit island" in answer.lower()
