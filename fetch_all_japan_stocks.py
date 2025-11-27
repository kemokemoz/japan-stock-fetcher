import os
import time
import subprocess
from datetime import datetime
import pandas as pd
import yfinance as yf

# ---------------------------
# 設定
# ---------------------------
TICKER_LIST_CSV = "tickers_list.csv"   # ← 銘柄リスト（60銘柄）
DATA_DIR = "stock_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------
# 銘柄リストを読み込む
# ---------------------------
def load_ticker_list():
    if not os.path.exists(TICKER_LIST_CSV):
        print(f"{TICKER_LIST_CSV} が見つかりません。")
        return []

    df = pd.read_csv(TICKER_LIST_CSV)

    if not {"銘柄コード", "銘柄名"}.issubset(df.columns):
        raise KeyError("CSV に '銘柄コード' '銘柄名' の列が必要です。")

    df["Ticker"] = df["銘柄コード"].astype(str) + ".T"
    return df

# ---------------------------
# 1銘柄の現在値を取得
# ---------------------------
def fetch_current_price(ticker, name):
    try:
        stock = yf.Ticker(ticker)
        price = stock.fast_info.last_price

        if price is None:
            return None

        return {
            "銘柄コード": ticker.replace(".T", ""),
            "銘柄名": name,
            "株価": price,
            "取得時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    except Exception as e:
        print(f"{ticker} エラー: {e}")
        return None

# ---------------------------
# 指定した60銘柄を一気に取得
# ---------------------------
def fetch_all_prices():
    df_list = load_ticker_list()
    if df_list is None or len(df_list) == 0:
        print("銘柄リストが読み込めません")
        return pd.DataFrame()

    results = []
    for _, row in df_list.iterrows():
        ticker = row["Ticker"]
        name = row["銘柄名"]
        result = fetch_current_price(ticker, name)

        if result is not None:
            results.append(result)

        time.sleep(0.2)  # Yahoo の負荷対策

    if len(results) == 0:
        return pd.DataFrame()

    return pd.DataFrame(results)

# ---------------------------
# CSV 保存
# ---------------------------
def save_prices(df):
    if df.empty:
        print("取得データなし")
        return None

    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"stock_prices_{now_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)

    df.to_csv(file_path, index=False, encoding="utf-8-sig")
    print(f"保存完了: {file_path}")
    return file_name

# ---------------------------
# GitHub 自動コミット＆プッシュ
# ---------------------------
def git_commit_push(file_name):
    try:
        subprocess.run(["git", "add", os.path.join(DATA_DIR, file_name)], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add stock data {file_name}", "--allow-empty"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
        print("GitHub にプッシュ完了")
    except Exception as e:
        print(f"Git エラー: {e}")

# ---------------------------
# 実行メイン
# ---------------------------
def main():
    df = fetch_all_prices()

    file_name = save_prices(df)
    if file_name:
        git_commit_push(file_name)

if __name__ == "__main__":
    main()
