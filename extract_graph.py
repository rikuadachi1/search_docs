import pypdf
import csv
import re
import glob


def extract_tables_from_pdf(pdf_path, output_csv_path):
    # PDFファイルを開く
    with open(pdf_path, 'rb') as file:
        reader = pypdf.PdfReader(file)

        # 全ページのテキストを抽出
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"

    # 表を抽出（この例では表1と表2を抽出）
    tables = re.findall(r'表(\d+)(.*?)(?=表\d+|\Z)', text, re.DOTALL)

    # CSVファイルに書き込む
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        for table_num, table_content in tables:
            writer.writerow([f"表{table_num}"])

            # 行ごとに分割
            rows = table_content.strip().split('\n')
            for row in rows:
                # スペースで分割し、空の要素を除去
                cells = [cell.strip() for cell in row.split() if cell.strip()]
                writer.writerow(cells)

            writer.writerow([])  # 表の間に空行を挿入


if __name__ == "__main__":
    folder = glob.glob("kwh_pdf/*.pdf")
    print(folder)
    for file in folder:
        output_csv_path = "output/{}.csv".format(file)
        extract_tables_from_pdf(file, output_csv_path)