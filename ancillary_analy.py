import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime


def analyze_balancing_prices(file_path):
    """
    三次調整力2の平均落札価格を時系列で分析する
    """
    # データ読み込み
    df = pd.read_csv(file_path, encoding="shift-jis", skiprows=2)

    # 平均落札価格の行のみを抽出（取引情報カラムで検索）
    mask = df['取引情報'].str.contains('最高落札価格（電源属地別）', na=False)
    df_prices = df[mask].copy()  # .copy()で警告を解消

    # ブロック番号とdateを抽出してカラムとして追加
    df_prices.loc[:, 'block'] = df_prices['TT'].str[-2:].astype(int)
    df_prices.loc[:, 'date'] = pd.to_datetime(df_prices['TT'].str[:8], format='%Y%m%d')

    # インデックスを設定
    df_prices = df_prices.set_index(['date', 'block'])

    # 必要なカラムのみを抽出
    areas = ['北海道', '東北', '東京', '中部', '北陸', '関西', '中国', '四国', '九州']
    df_prices = df_prices[areas].astype(float)

    return df_prices


def compare_prices(df_40, df_32):
    """価格の比較分析を行う"""
    areas = ['北海道', '東北', '東京', '中部', '北陸', '関西', '中国', '四国', '九州']
    results = {}
    all_comparisons = []

    # 各エリアについて分析
    for area in areas:
        block_comparisons = []

        # 各ブロック(1-8)について分析
        for block in range(1, 9):
            try:
                # 各日付のブロックごとの価格を比較
                df_40_block = df_40.xs(block, level='block')[area]
                df_32_block = df_32.xs(block, level='block')[area]

                # 価格差の計算
                price_diff = df_40_block - df_32_block

                # 統計情報の計算
                comparison = {
                    'area': area,
                    'block': block,
                    'avg_price_40': df_40_block.mean(),
                    'avg_price_32': df_32_block.mean(),
                    'times_40_higher': (price_diff > 0).sum(),
                    'times_32_higher': (price_diff < 0).sum(),
                    'times_equal': (price_diff == 0).sum(),
                    'avg_diff': price_diff.mean()
                }
                block_comparisons.append(comparison)
                all_comparisons.append(comparison)
            except Exception as e:
                print(f"Error processing {area} block {block}: {str(e)}")

        results[area] = pd.DataFrame(block_comparisons)

    # 全ての結果をまとめたDataFrameを作成
    all_results_df = pd.DataFrame(all_comparisons)

    return results, all_results_df


def save_results(results, all_results_df, output_dir="output"):
    """結果をCSVファイルとして保存"""
    # 出力ディレクトリが存在しない場合は作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # タイムスタンプを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 各エリアの結果を個別のCSVファイルとして保存
    for area, df_result in results.items():
        filename = f"{output_dir}/comparison_results_{area}_{timestamp}.csv"
        df_result.to_csv(filename, index=False, encoding='utf-8-sig')

    # 全体の結果を1つのCSVファイルとして保存
    summary_filename = f"{output_dir}/comparison_results_all_{timestamp}.csv"
    all_results_df.to_csv(summary_filename, index=False, encoding='utf-8-sig')

    return summary_filename


# メイン処理
files_40 = glob.glob("input/4-0/*")
files_32 = glob.glob("input/3-2/*")
df_40_out = None
df_32_out = None

# 4.0版のファイル処理
for file in files_40:
    df_40 = analyze_balancing_prices(file)
    df_40_out = df_40 if df_40_out is None else pd.concat([df_40_out, df_40])

# 3.2版のファイル処理
for file in files_32:
    df_32 = analyze_balancing_prices(file)
    df_32_out = df_32 if df_32_out is None else pd.concat([df_32_out, df_32])

# 重複を除去してソート
if df_40_out is not None:
    df_40_out = df_40_out[~df_40_out.index.duplicated(keep='last')].sort_index()
if df_32_out is not None:
    df_32_out = df_32_out[~df_32_out.index.duplicated(keep='last')].sort_index()

# 比較分析の実行
results, all_results_df = compare_prices(df_40_out, df_32_out)

# 結果をCSVファイルとして保存
summary_file = save_results(results, all_results_df)
print(f"\n結果は以下のファイルに保存されました：{summary_file}")

# 結果の表示（オプション）
for area, df_result in results.items():
    print(f"\n{area}の分析結果:")
    total_40_higher = df_result['times_40_higher'].sum()
    total_32_higher = df_result['times_32_higher'].sum()
    avg_diff = df_result['avg_diff'].mean()
    print(f"4.0の方が高かった回数: {total_40_higher}")
    print(f"3.2の方が高かった回数: {total_32_higher}")
    print(f"平均価格差: {avg_diff:.2f}円")