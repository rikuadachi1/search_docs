import os
import PyPDF2
import pandas as pd
from tqdm import tqdm
import streamlit as st
from urllib.parse import urljoin
import requests

BASE_URL = 'https://www.emsc.meti.go.jp/activity/'


def is_url_valid(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def search_pdfs(directory, keyword):
    path_list = []
    for root, dirs, files in os.walk(directory):
        for file in tqdm(files):
            if file.endswith(".pdf"):
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as pdf_file:
                    try:
                        reader = PyPDF2.PdfReader(pdf_file)
                        for page in reader.pages:
                            text = page.extract_text()
                            if keyword in text:
                                relative_path = os.path.relpath(file_path, directory)
                                url = urljoin(BASE_URL, relative_path.replace('\\', '/'))
                                if is_url_valid(url):
                                    path_list.append([root, file, url])
                                break
                    except:
                        pass
    return path_list


def view():
    directory = "./pdf_downloads/"
    st.title("OCCTOワード検索")
    keyword = st.text_input("検索ワード")
    if st.button("run"):
        path_list = search_pdfs(directory, keyword)
        path_df = pd.DataFrame(path_list, columns=["ディレクトリ", "pdfファイル", "URL"])

        if not path_df.empty:
            st.write("検索結果:")
            df = st.data_editor(path_df)

            # URLをクリック可能にする
            st.markdown("### クリック可能なURL")
            for _, row in df.iterrows():
                st.markdown(f"[{row['pdfファイル']}]({row['URL']})")

            # CSVダウンロードボタン
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="search_results.csv",
                mime="text/csv",
            )
        else:
            st.write("該当するPDFが見つかりませんでした。")


if __name__ == "__main__":
    view()