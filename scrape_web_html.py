from prefect import flow, task
from datetime import datetime
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

class WebScrapedHtml(BaseModel):
    url: str
    page_content: str
    http_status_code: int
    content_type: str
    scraped_at: datetime
    headers: dict
    metadata: dict

@task(persist_result=False)
def save_to_db(data: WebScrapedHtml):
    pass

@task(persist_result=False)
def scrape_html_response(url: str) -> str:
    service = Service(executable_path='chromedriver')
    driver = webdriver.Chrome(
        service=service, options=ChromeOptions(headless=True))
    driver.get(url)
    page_content = driver.find_element(By.TAG_NAME, 'body').text
