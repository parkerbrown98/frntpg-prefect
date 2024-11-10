from prefect import task, flow
from prefect.blocks.system import Secret
from prefect_sqlalchemy import SqlAlchemyConnector
from pydantic import BaseModel
from openai import OpenAI

class ArticleStatistics(BaseModel):
    word_count: int
    sentence_count: int
    readability_score: float
    sentiment_score: float

class ArticleExtraction(BaseModel):
    url: str
    title: str
    authors: list[str] | None
    summary: str
    keywords: list[str]
    publish_date: str | None
    statistics: ArticleStatistics

@task
def extract_article(url: str) -> ArticleExtraction:
    secret_block = Secret.load("openai-token")
    openai_token = secret_block.get()
    client = OpenAI(api_key=openai_token)
    compl = client.beta.chat.completions.parse(
        model='gpt-4o-2024-08-06',
        messages=[
            {'role': 'system', 'content': 'You are an expert in journalism. Given any URL, you should accurately extract key information from the article. Do not include any information that is not present in the article.'},
            {'role': 'user', 'content': url},
        ],
        response_format=ArticleExtraction,
    )
    return compl.choices[0].message.parsed

@task
def save_article_extraction(id: int, article: ArticleExtraction):
    conn = SqlAlchemyConnector.load("pg-local")
    with conn as session:
        session.execute(
            "INSERT INTO article_extractions (article_id, url, title, authors, summary, keywords, publish_date, word_count, sentence_count, readability_score, sentiment_score) VALUES (:article_id, :url, :title, :authors, :summary, :keywords, :publish_date, :word_count, :sentence_count, :readability_score, :sentiment_score)",
            {
                "article_id": id,
                "url": article.url,
                "title": article.title,
                "authors": article.authors,
                "summary": article.summary,
                "keywords": article.keywords,
                "publish_date": article.publish_date,
                "word_count": article.statistics.word_count,
                "sentence_count": article.statistics.sentence_count,
                "readability_score": article.statistics.readability_score,
                "sentiment_score": article.statistics.sentiment_score,
            },
        )
        
@task(persist_result=False)
def get_articles_for_extraction(limit: int = 10):
    conn = SqlAlchemyConnector.load("pg-local")
    with conn as session:
        return session.fetch_all("SELECT id, url FROM rss_articles WHERE NOT EXISTS (SELECT 1 FROM article_extractions WHERE article_extractions.article_id = rss_articles.id) ORDER BY published_at DESC LIMIT :limit", {"limit": limit})

@flow(persist_result=False, log_prints=True)
def extract_articles(limit: int = 10):
    articles = get_articles_for_extraction(limit)
    for article in articles:
        extraction = extract_article(article[1])
        save_article_extraction(article[0], extraction)
        print(f"Extracted {article[1]}")

if __name__ == '__main__':
    extract_articles()