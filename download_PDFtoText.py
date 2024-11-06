import os
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import PyPDF2
import io

BASE_URL = 'https://www.occto.or.jp/iinkai/youryou/kentoukai/2023/'
DOWNLOAD_BASE_DIR = 'youryou'


def get_soup_from_url(url):
    response = requests.get(url)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, 'html.parser')


def extract_content_between_comments(soup, start_comment, end_comment):
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    start_marker = next((c for c in comments if start_comment in c), None)
    end_marker = next((c for c in comments if end_comment in c), None)

    if not start_marker or not end_marker:
        return None

    content = ""
    for element in start_marker.find_all_next():
        if element == end_marker:
            break
        content += str(element)
    return content


def get_initial_links(url):
    soup = get_soup_from_url(url)
    # content = extract_content_between_comments(soup, '見出し', '▼▼フッターここから▼▼')
    content = extract_content_between_comments(soup, 'コンテンツここから', 'msearch')
    if not content:
        return []

    content_soup = BeautifulSoup(content, 'html.parser')
    links = [urljoin(BASE_URL, a['href']) for a in content_soup.find_all('a', href=True)]
    return [link for link in links if "youryou" in link and "#" not in link]


def extract_pdf_text(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        pdf_content = io.BytesIO(response.content)
        reader = PyPDF2.PdfReader(pdf_content)
        text = f"PDF URL: {url}\n\n"
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Failed to extract text from {url}: {e}")
        return None


def save_pdf_as_text(url, parent_dir):
    pdf_name = os.path.basename(urlparse(url).path)
    txt_name = os.path.splitext(pdf_name)[0] + ".txt"
    txt_path = os.path.join(parent_dir, txt_name)

    if os.path.exists(txt_path):
        return False

    text = extract_pdf_text(url)
    if text:
        os.makedirs(parent_dir, exist_ok=True)
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(text)
        return True
    return False


def get_all_links(url, max_depth=2):
    visited_links = set()
    all_links = set()
    to_visit = [(url, 0)]

    while to_visit:
        current_url, depth = to_visit.pop(0)
        if depth > max_depth or current_url in visited_links:
            continue

        visited_links.add(current_url)

        try:
            soup = get_soup_from_url(current_url)
            # content = extract_content_between_comments(soup, '本文開始', '▼▼フッターここから▼▼')
            content = extract_content_between_comments(soup, 'コンテンツここから', 'msearch')
            if not content:
                continue

            content_soup = BeautifulSoup(content, 'html.parser')
            page_links = [urljoin(current_url, a['href']) for a in content_soup.find_all('a', href=True)]
            page_links = [a for a in page_links if "index_emsc.html" not in a and "#" not in a]

            for link in page_links:
                if link.startswith(('http', 'https')):
                    all_links.add(link)
                    if not link.endswith('.pdf'):
                        to_visit.append((link, depth + 1))

        except Exception as e:
            print(f"An error occurred while processing {current_url}: {e}")

    return all_links


def crawl_and_save():
    url = urljoin(BASE_URL, 'index.html')
    initial_links = get_initial_links(url)
    all_links = set()
    print(initial_links)

    for link in tqdm(initial_links):
        if link.startswith(('http', 'https')):
            all_links.update(get_all_links(link))

    print(f"Total links found: {len(all_links)}")

    with tqdm(total=len(all_links), desc="Processing links") as pbar:
        for link in all_links:
            parsed_url = urlparse(link)
            relative_path = parsed_url.path.strip('/').replace('/', '_')
            dir_name = os.path.join(DOWNLOAD_BASE_DIR, relative_path)

            if link.endswith('.pdf'):
                print("test")
                save_pdf_as_text(link, os.path.dirname(dir_name))

            pbar.update(1)


if __name__ == "__main__":
    crawl_and_save()