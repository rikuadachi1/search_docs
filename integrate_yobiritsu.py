import os
import csv
import pandas as pd
from datetime import datetime

import locale
from datetime import datetime

# 日本語ロケールを設定
locale.setlocale(locale.LC_TIME, 'ja_JP.UTF-8')


def extract_table2(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # 表2の開始位置を見つける
    table2_start = content.find('表２')
    if table2_start == -1:
        return None  # 表2が見つからない場合

    # 表2の内容を抽出
    table2_content = content[table2_start:].split('\n')

    # 日付行を見つける
    date_row = None
    for i, row in enumerate(table2_content):
        if '月' in row and '(' in row and ')' in row:
            date_row = row
            break

    if date_row is None:
        return None  # 日付行が見つからない場合

    # 日付を解析
    date_str = date_row.split(',')[0]
    try:
        date = datetime.strptime(date_str, '%m/%d(%a)')
    except ValueError:
        # 日本語の曜日表記の場合
        date = datetime.strptime(date_str, '%m/%d(%A)')

    # データ行を抽出
    data_row = table2_content[i].split(',')[1:]

    return [date] + data_row


def process_folder(folder_path, output_file):
    all_data = []

    # フォルダ内の全CSVファイルを処理
    for filename in os.listdir(folder_path):
        if filename.endswith('.csv'):
            file_path = os.path.join(folder_path, filename)
            data = extract_table2(file_path)
            if data:
                all_data.append(data)

    # データをDataFrameに変換
    df = pd.DataFrame(all_data, columns=['日付', '沖縄', '九州', '四国', '中国', '関西', '北陸', '中部', '東京', '東北',
                                         '北海道'])

    # 日付でソート
    df = df.sort_values('日付')

    # CSVファイルとして保存
    df.to_csv(output_file, index=False, encoding='utf-8')


# 使用例
folder_path = 'output/kwh_pdf'
output_file = 'combined_table2.csv'
process_folder(folder_path, output_file)