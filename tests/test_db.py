from game_scanner.db import *

def test_get_db_connection():
    db = get_db_connection()
    assert db is not None

def test_get_collection():
    c = get_collection(collection_name="playrequests")
    assert c is not None

def test_save_document():
    data = {"game": "Spirit Island", "objectid": "161417"}
    save_document(data, collection_name="playrequests")
