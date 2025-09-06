import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

parser = argparse.ArgumentParser(
    description="Patent search on Google Patents based on a list of patent urls.",
)


parser.add_argument(
    "--wait_time",
    "-w",
    type=int,
    default=2.5,
    help="Seconds to wait after the patent has loaded(default: 0)",
)

parser.add_argument(
    "--selenium_path",
    "-sp",
    type=str,
    default="/snap/bin/firefox.geckodriver",
    help="Path to the Selenium driver.",
)

args = parser.parse_args()
wait_time = args.wait_time
geckodriver_path = args.selenium_path


patent_urls_links_path = Path("data/urls/")

all_urls = []

with open("test_patents.txt", "r") as file:
    all_urls = [linha.strip() for linha in file]

driver_service = webdriver.FirefoxService(executable_path=geckodriver_path)
browser = webdriver.Firefox(service=driver_service)

output_dir = Path("data/patents/metadata")
output_dir.mkdir(parents=True, exist_ok=True)

has_no_tables = []

for url in tqdm(all_urls):
    file_name = url.replace("https://", "").replace(".", "_").replace("/", "_")

    output_path = output_dir / file_name
    output_file = output_path / (file_name + ".json")

    if output_file.exists():
        continue

    browser.get(url)
    #TODO: entender melhor oq é esse wait time
    wait = WebDriverWait(browser, timeout=wait_time, poll_frequency=0.5)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    def get_meta_content(selector):
        elements = browser.find_elements(By.CSS_SELECTOR, selector)
        if elements:
            result = [element.get_attribute("content").strip() for element in elements]
            if len(result) == 1:
                return result[0]
            else:
                return result
        return None

    title = get_meta_content("meta[name='DC.title']")
    patent_type = get_meta_content("meta[name='DC.type']")
    description = get_meta_content("meta[name='DC.description']")
    application_number = get_meta_content("meta[name='citation_patent_application_number']")
    publication_number = get_meta_content("meta[name='citation_patent_publication_number']")
    pdf_url = get_meta_content("meta[name='citation_pdf_url']")
    inventors = get_meta_content("meta[scheme='inventor']")
    assignee = get_meta_content("meta[scheme='assignee']")
    date = get_meta_content("meta[name='DC.date']")

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "patent-tables table")))
        patent_tables = browser.find_elements(By.CSS_SELECTOR, "patent-tables")
        html_tables = []

        for table in patent_tables:
            patent_table_html = table.get_attribute("outerHTML")
            soup = BeautifulSoup(patent_table_html, "html.parser").prettify()
            html_tables.append(soup)

        patent_data = {
            "url": url,
            "title": title,
            "type": patent_type,
            "description": description,
            "application_number": application_number,
            "publication_number": publication_number,
            "pdf_url": pdf_url,
            "inventors": inventors,
            "assignee": assignee,
            "date": date,
            "html_tables": html_tables,
        }
        output_path.mkdir(parents=True, exist_ok=True)

        with output_file.open(mode="w", encoding="utf-8") as f:
            json.dump(patent_data, f, ensure_ascii=False, indent=4)

    except TimeoutException:
        has_no_tables.append(url)

with open(output_dir / "has_no_tables.txt", "w") as output:
    output.write(str(has_no_tables))


browser.quit()

print("Operation completed successfully.")
