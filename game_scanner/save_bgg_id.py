from datetime import datetime

from game_scanner.db import save_document


def save_bgg_id(query, bgg_id, extra={}):
    now = datetime.now().isoformat()
    #  data = {"bgg_id": "161417", "query": "8034055580738", "added_at": now}
    data = {"bgg_id": str(bgg_id), "query": str(query), "added_at": now}
    data.update(extra)
    save_document(data)
    return None
