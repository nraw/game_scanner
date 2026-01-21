import json
import os

import firebase_admin
from firebase_admin import credentials, firestore
from loguru import logger

# Module-level singleton for Firestore client
_db_client = None


def get_collection(collection_name="games"):
    db = get_db_connection()
    c = db.collection(collection_name)
    return c


def get_db_connection():
    global _db_client
    if _db_client is not None:
        return _db_client

    firestore_key = os.environ.get("FIRESTORE_KEY")
    if not firestore_key:
        raise ValueError("FIRESTORE_KEY environment variable is required")
    firestore_creds = json.loads(firestore_key)
    cred = credentials.Certificate(firestore_creds)

    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        pass

    _db_client = firestore.client()
    return _db_client


def save_document(data, collection_name="games"):
    c = get_collection(collection_name=collection_name)
    c.add(data)
    logger.info(f"Saved document: {data}")


def retrieve_document(query, collection_name="games"):
    c = get_collection(collection_name=collection_name)
    bgg_id = ""
    docs = (
        c.where("query", "==", query)
        .order_by("added_at", direction=firestore.Query.DESCENDING)
        .limit(1)
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


def retrieve_play_request(message_id):
    c = get_collection(collection_name="play_requests")
    docs = c.where("message_id", "==", message_id).stream()
    try:
        doc = next(docs)
        doc_data = doc.to_dict()
        logger.info(f"Retrieved play request: {doc_data}")
    except StopIteration:
        logger.info(f"No play request for message_id: {message_id}")
        doc_data = {}
    return doc_data


def retrieve_messages(message_id):
    c = get_collection(collection_name="messages")
    docs = c.where("message_id", "==", message_id).stream()
    try:
        doc = next(docs)
        doc_data = doc.to_dict()
        previous_messages = doc_data.get("messages", [])
        logger.info(f"Retrieved play request: {doc_data}")
    except StopIteration:
        logger.info(f"No play request for message_id: {message_id}")
        previous_messages = []
    return previous_messages
