from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from fetch_rss_articles import fetch_rss_articles

@task(persist_result=False)
def get_outdated_feeds(limit: int = 10) -> list:
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        results = session.fetch_all("SELECT id FROM rss_feeds WHERE active = TRUE AND (fetched_at < NOW() - INTERVAL '6 hours' OR fetched_at IS NULL) ORDER BY fetched_at ASC LIMIT :limit", {"limit": limit})
        return [result[0] for result in results]
    
@flow(persist_result=False)
def fetch_rss_feeds(limit: int = 10):
    feed_ids = get_outdated_feeds(limit)
    for feed_id in feed_ids:
        fetch_rss_articles(feed_id)
        
if __name__ == "__main__":
    fetch_rss_feeds()