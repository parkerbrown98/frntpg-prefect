from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from rss_parser import RSSParser
from datetime import datetime

import requests

@task(timeout_seconds=10)
def validate_feed(id: int) -> bool:
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        try:
            feed = session.fetch_one("SELECT url FROM rss_feeds WHERE id = :id", {"id": id})
            response = requests.get(feed[0])
            parser = RSSParser()
            parser.parse(response.text)
            return True
        except Exception as e:
            return False
 
@task(persist_result=False)
def save_audit_result(id: int, valid: bool):
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        session.execute("UPDATE rss_feeds SET audited_at = :audited_at, active = :active WHERE id = :id", {"id": id, "audited_at": datetime.now(), "active": valid})
        
@flow
def audit_rss_feeds(limit: int = 10):
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        feeds = session.fetch_all("SELECT id FROM rss_feeds ORDER BY audited_at ASC LIMIT :limit", {"limit": limit})
        for feed in feeds:
            valid = validate_feed(feed[0])
            save_audit_result(feed[0], valid)
            
if __name__ == "__main__":
    audit_rss_feeds()