from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from rss_parser import RSSParser

import requests

@task
def get_feed_url(id: int) -> str:
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        feed = session.fetch_one("SELECT url FROM rss_feeds WHERE id = :id", {"id": id})
        return feed[0]

@task
def get_feed_articles(url: str) -> list:
    response = requests.get(url)
    parser = RSSParser()
    content = parser.parse(response.text).dict_plain()
    return [{"title": item["title"], "url": item["links"][0], "author": item["author"], "published_at": item["pub_date"]} for item in content["channel"]["items"]]

@task(persist_result=False)
def save_articles(feed_id: int, articles: list):
    db_context = SqlAlchemyConnector.load("pg-local")
    with db_context as session:
        session.execute_many("INSERT INTO rss_articles (feed_id, title, url, author, published_at) VALUES (:feed_id, :title, :url, :author, :published_at)", [{"feed_id": feed_id, **article} for article in articles])

@flow(persist_result=False)
def fetch_rss_articles(id: int):
    url = get_feed_url(id)
    articles = get_feed_articles(url)
    save_articles(id, articles)