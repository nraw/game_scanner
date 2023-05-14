import firebase_admin
from firebase_admin import credentials, firestore
from loguru import logger


def get_collection(collection_name="games"):
    db = get_db_connection()
    c = db.collection(collection_name)
    return c


def get_db_connection():
    cred = credentials.Certificate("nraw-key.json")

    try:
        app = firebase_admin.initialize_app(cred)
    except ValueError:
        pass

    db = firestore.client()
    return db


def save_document(data):
    c = get_collection()
    c.add(data)
    logger.info(f"Saved document: {data}")


def retrieve_document(query):
    c = get_collection()
    bgg_id = ""
    docs = (
        c.where("query", "==", query)
        .order_by("added_at", direction=firestore.Query.DESCENDING)
        .stream()
    )
    try:
        doc = next(docs)
        data = doc.to_dict()
        bgg_id = data.get("bgg_id", "")
        logger.info(f"Retrieved bgg_id: {bgg_id}")
    except StopIteration:
        logger.info(f"No bgg_id for query: {query}")
        pass
    return bgg_id
