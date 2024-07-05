import os
import requests
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from tqdm import tqdm

# ターゲットURL
base_url = 'https://www.emsc.meti.go.jp/activity/'
url = urljoin(base_url, 'index_system.html')
download_base_dir = 'pdf_downloads'

# ウェブページの内容を取得
response = requests.get(url)
response.raise_for_status()  # ステータスコードが200以外の場合に例外を発生させる

# エンコーディングの設定
response.encoding = response.apparent_encoding

# BeautifulSoupを使ってHTMLをパース
soup = BeautifulSoup(response.text, 'html.parser')

# コメントノードを抽出
comments = soup.find_all(string=lambda text: isinstance(text, Comment))

# <!-- 本文開始 -->から<!-- ▼▼フッターここから▼▼ -->までのセクションを抽出
start_marker = None
end_marker = None

for comment in comments:
    if '本文開始' in comment:
        start_marker = comment
    if '▼▼フッターここから▼▼' in comment:
        end_marker = comment

if not start_marker or not end_marker:
    print("指定されたコメントがHTML内に見つかりませんでした。")
else:
    # 該当セクションの内容を抽出
    content = ""
    for element in start_marker.find_all_next():
        if element == end_marker:
            break
        content += str(element)

    # 該当セクションを再度パース
    content_soup = BeautifulSoup(content, 'html.parser')

    # 該当セクション内のすべてのhrefリンクを抽出
    initial_href_links = [urljoin(base_url, a['href']) for a in content_soup.find_all('a', href=True)]
    print(initial_href_links)
    initial_href_links = [i for i in initial_href_links if not  "#" in i]
    initial_href_links = [i for i in initial_href_links if "index_system" in i]
    print(initial_href_links)

    # 初期のリンクを表示
    print("Initial href links:")
    for link in initial_href_links:
        print(link)

    # すべてのリンク先のhrefリンクをリスト化する関数
    visited_links = set()


    def get_links_from_url(url, depth=0, max_depth=3, parent_dir=''):
        if depth > max_depth or url in visited_links:
            return set()

        if url.endswith('.pdf'):
            download_pdf(url, parent_dir)
            return set()

        visited_links.add(url)

        try:
            response = requests.get(url)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            try:
                page_soup = BeautifulSoup(response.text, 'html.parser')
            except Exception as e:
                print(f"Parsing failed for {url} with 'html.parser': {e}")
                page_soup = BeautifulSoup(response.content, 'lxml')

            # コメントノードを抽出
            comments = page_soup.find_all(string=lambda text: isinstance(text, Comment))

            start_marker = None
            end_marker = None

            for comment in comments:
                if '本文開始' in comment:
                    start_marker = comment
                if '▼▼フッターここから▼▼' in comment:
                    end_marker = comment

            if not start_marker or not end_marker:
                return set()

            content = ""
            for element in start_marker.find_all_next():
                if element == end_marker:
                    break
                content += str(element)

            content_soup = BeautifulSoup(content, 'html.parser')
            page_links = [urljoin(url, a['href']) for a in content_soup.find_all('a', href=True)]

            # システムログ.htmlを含まないようにする
            page_links = [a for a in page_links if "index_system.html" not in a]
            # #を含むものを消す
            page_links = [a for a in page_links if "#" not in a]
            # ディレクトリ名を生成
            parsed_url = urlparse(url)
            dir_name = os.path.join(parent_dir, parsed_url.path.strip('/').replace('/', '_'))

            # ディレクトリを作成
            os.makedirs(dir_name, exist_ok=True)

            # 再帰的にリンクを取得
            all_links = set(page_links)
            for link in tqdm(page_links, desc=f"Processing depth {depth}"):
                if link.startswith('http') or link.startswith('https'):
                    new_links = get_links_from_url(link, depth + 1, max_depth, dir_name)
                    all_links.update(new_links)

            return all_links
        except requests.exceptions.RequestException as e:
            print(f"Failed to retrieve {url}: {e}")
            return set()
        except Exception as e:
            print(f"An error occurred while processing {url}: {e}")
            return set()


    def download_pdf(url, parent_dir):
        try:
            response = requests.get(url)
            response.raise_for_status()
            pdf_name = os.path.basename(urlparse(url).path)
            pdf_path = os.path.join(parent_dir, pdf_name)

            with open(pdf_path, 'wb') as pdf_file:
                pdf_file.write(response.content)
            print(f"Downloaded: {pdf_path}")
        except Exception as e:
            print(f"Failed to download {url}: {e}")


    # すべてのリンク先のhrefリンクを取得
    all_links = set()
    for link in tqdm(initial_href_links, desc="Initial links"):
        if link.startswith('http') or link.startswith('https'):
            new_links = get_links_from_url(link, parent_dir=download_base_dir)
            all_links.update(new_links)

    # すべてのリンクを表示
    print("\nAll href links, including those from link destinations:")
    for link in all_links:
        print(link)
