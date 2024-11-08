from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from rss_parser import RSSParser
from datetime import datetime

import requests


@task
def validate_feed(url: str) -> bool:
    try:
        response = requests.get(url, timeout=10)
        parser = RSSParser()
        parser.parse(response.text)
        return True
    except Exception as e:
        return False


@task(persist_result=False)
def save_audit_result(id: int, valid: bool):
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        session.execute("UPDATE rss_feeds SET audited_at = :audited_at, active = :active WHERE id = :id", {
                        "id": id, "audited_at": datetime.now(), "active": valid})


@flow(persist_result=False, log_prints=True)
def audit_rss_feeds(limit: int = 10):
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        feeds = session.fetch_all(
            "SELECT id, url FROM rss_feeds ORDER BY audited_at ASC LIMIT :limit", {"limit": limit})
        print(f"Found {len(feeds)} feeds to audit")
        count = 0
        for feed in feeds:
            valid = validate_feed(feed[1])
            save_audit_result(feed[0], valid)
            if not valid:
                count += 1
        print(f"Disabled {count} feeds due to errors")


if __name__ == "__main__":
    audit_rss_feeds()
