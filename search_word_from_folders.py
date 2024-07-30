import os
import re
import pandas as pd
from tqdm import tqdm
import streamlit as st
import requests
import jaconv
import io

# DOWNLOAD_BASE_DIR = 'system'

DOWNLOAD_BASE_DIRS = {
    'emsc': 'emsc',
    'system': 'system'
}

FOLDER_NAMES = {
    'emsc': '電力・ガス取引監視等委員会',
    'system': '制度設計専門会合'
}


def is_url_valid(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


def is_valid_title(line):
    return (len(line) > 10 and
            not re.match(r'^\d+$', line) and
            len(re.findall(r'[a-zA-Z]', line)) / len(line) < 0.5)


def get_title(content):
    lines = content.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line and not line.startswith('PDF URL:'):
            line = re.sub(r'\([^)]*\)', '', line).strip()
            if is_valid_title(line):
                return line
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                next_line = re.sub(r'\([^)]*\)', '', next_line).strip()
                if is_valid_title(next_line):
                    return next_line
    return "タイトルが見つかりません"


def get_category(title, content):
    content_lower = content.lower()
    if "議事" in content_lower:
        return "議事"
    elif "報告書" in content_lower:
        return "報告書"
    elif "計画" in content_lower:
        return "計画書"
    else:
        return "その他"

def extract_date(content):
    era_to_year = {
        "平成": 1988,
        "令和": 2018,
        "Ｒ": 2018,
        "R": 2018,
    }

    patterns = [
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日',
        r'(\d{4})/(\d{1,2})/(\d{1,2})',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(平成|令和|Ｒ|R)\s*([０-９\d]{1,2}|[一二三四五六七八九十]+)\s*年\s*([０-９\d]{1,2}|[一二三四五六七八九十]+)\s*月\s*([０-９\d]{1,2}|[一二三四五六七八九十]+)\s*日'
    ]

    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            if match.group(1) in era_to_year:
                year = era_to_year[match.group(1)] + convert_to_int(match.group(2))
                month = convert_to_int(match.group(3))
                day = convert_to_int(match.group(4))
                return f"{year}年{month}月{day}日"
            else:
                return f"{match.group(1)}年{match.group(2)}月{match.group(3)}日"

    return "日付不明"


def convert_to_int(string):
    # 全角数字を半角数字に変換
    string = jaconv.z2h(string, digit=True, kana=False, ascii=False)

    # 漢数字を数字に変換
    kansuji_dict = {
        "一": "1", "二": "2", "三": "3", "四": "4", "五": "5",
        "六": "6", "七": "7", "八": "8", "九": "9", "十": "10",
    }
    for key, value in kansuji_dict.items():
        string = string.replace(key, value)

    # 「十」の特別処理
    if "十" in string:
        if string == "十":
            return 10
        elif string.startswith("十"):
            string = "1" + string[1:]
        else:
            string = string.replace("十", "0")

    return int(string)

def search_text_files(directories, keywords):
    result_list = []
    keywords_lower = [keyword.lower() for keyword in keywords]

    all_files = []
    for directory in directories:
        files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".txt")]
        all_files.extend(files)

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, file_path in enumerate(all_files):
        with open(file_path, 'r', encoding='utf-8') as text_file:
            content = text_file.read()
            content_lower = content.lower()
            first_line = content.split('\n')[0].strip()
            if first_line.startswith("PDF URL:"):
                url = first_line.split("PDF URL:")[1].strip()
                if all(keyword in content_lower for keyword in keywords_lower):
                    title = get_title(content)
                    category = get_category(title, content)
                    date = extract_date(content)
                    directory_name = os.path.basename(os.path.dirname(file_path))
                    committee = FOLDER_NAMES.get(directory_name, directory_name)
                    result_list.append([category, date, title, url, committee])

        progress = (i + 1) / len(all_files)
        progress_bar.progress(progress)
        status_text.text(f"処理中... {i + 1}/{len(all_files)} ファイル")

    progress_bar.empty()
    status_text.empty()
    return result_list


def view():
    st.title("資料ワード検索")
    keyword_input = st.text_input("検索ワード（複数の場合はスペースで区切ってください）")
    st.write("※ 公開情報すべてを網羅しているとは限りません。情報の利用についてはご自身の判断で行ってください。")

    # チェックボックスを追加（表示名を変更）
    search_emsc = st.checkbox(f"{FOLDER_NAMES['emsc']}を検索", value=True)
    search_system = st.checkbox(f"{FOLDER_NAMES['system']}を検索", value=True)

    if st.button("run"):
        keywords = keyword_input.split()
        if not keywords:
            st.write("検索ワードを入力してください。")
            return

        # 選択されたフォルダーのリストを作成
        selected_dirs = []
        if search_emsc:
            selected_dirs.append(DOWNLOAD_BASE_DIRS['emsc'])
        if search_system:
            selected_dirs.append(DOWNLOAD_BASE_DIRS['system'])

        if not selected_dirs:
            st.write("少なくとも1つの委員会を選択してください。")
            return

        result_list = search_text_files(selected_dirs, keywords)
        result_df = pd.DataFrame(result_list, columns=["カテゴリ", "日付", "タイトル", "URL", "委員会"])

        if not result_df.empty:
            st.write(f"検索結果: {len(result_df)} 件見つかりました")

            result_df['date_for_sort'] = pd.to_datetime(result_df['日付'].replace('日付不明', 'NaT'),
                                                        format='%Y年%m月%d日', errors='coerce')
            result_df = result_df.sort_values('date_for_sort', ascending=False)

            categories = result_df['カテゴリ'].unique()
            for category in categories:
                st.markdown(f"### {category}")
                category_df = result_df[result_df['カテゴリ'] == category]
                for _, row in category_df.iterrows():
                    st.markdown(f"- {row['日付']} ({row['委員会']}): [{row['タイトル']}]({row['URL']})")

            csv_buffer = io.StringIO()
            result_df.drop('date_for_sort', axis=1).to_csv(csv_buffer, index=False, encoding="utf-8-sig")
            csv_str = csv_buffer.getvalue()

            st.write("リストをダウンロード可能です。")
            st.download_button(
                label="Download CSV",
                data=csv_str.encode('utf-8-sig'),  # UTF-8 with BOM
                file_name="search_results.csv",
                mime="text/csv",
            )
        else:
            st.write("該当するテキストファイルが見つかりませんでした。")

if __name__ == "__main__":
    view()