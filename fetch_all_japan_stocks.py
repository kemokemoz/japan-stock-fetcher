import os
import json
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import subprocess
import requests
from io import BytesIO

# ---------------------------
# 設定
# ---------------------------
TICKER_FILE = "tickers.json"
DATA_DIR = "stock_data"
os.makedirs(DATA_DIR, exist_ok=True)

MAX_WORKERS = 10
RETRY_DELAY = 5

# ---------------------------
# 日本全株ティッカー取得（JPX CSV）
# ---------------------------
def get_all_japanese_tickers():
    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    r = requests.get(url)
    df = pd.read_excel(BytesIO(r.content), skiprows=2)
    tickers = df["コード"].astype(str) + ".T"
    return tickers.tolist()

def load_or_update_tickers():
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            data = json.load(f)
            last_update = datetime.fromisoformat(data["last_update"])
            if datetime.now() - last_update < timedelta(days=30):
                return data["tickers"]

    # 更新が必要な場合
    tickers = get_all_japanese_tickers()
    with open(TICKER_FILE, "w") as f:
        json.dump({"last_update": datetime.now().isoformat(), "tickers": tickers}, f)
    return tickers

# ---------------------------
# 株価取得
# ---------------------------
def fetch_price(ticker):
    for attempt in range(3):
        try:
            df = yf.download(ticker, period="1d", interval="60m", progress=False)
            df.reset_index(inplace=True)
            df["Ticker"] = ticker
            return df
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            time.sleep(RETRY_DELAY)
    return None

def fetch_all_prices(tickers):
    all_data = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_price, t): t for t in tickers}
        for future in futures:
            result = future.result()
            if result is not None:
                all_data.append(result)
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

# ---------------------------
# CSV 保存
# ---------------------------
def save_prices(df):
    if df.empty:
        print("No data fetched")
        return None
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"stock_prices_{now_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    df.to_csv(file_path, index=False)
    print(f"Saved: {file_path}")
    return file_name

# ---------------------------
# GitHub に自動コミット＆プッシュ
# ---------------------------
def git_commit_push(file_name):
    try:
        subprocess.run(["git", "config", "--global", "user.email", "you@example.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Your Name"], check=True)
        subprocess.run(["git", "add", os.path.join(DATA_DIR, file_name)], check=True)
        subprocess.run(["git", "commit", "-m", f"Add stock data {file_name}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print(f"Committed and pushed {file_name} to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"Git error: {e}")

# ---------------------------
# メイン処理
# ---------------------------
def main():
    tickers = load_or_update_tickers()
    print(f"Fetching {len(tickers)} tickers...")
    df = fetch_all_prices(tickers)
    file_name = save_prices(df)
    if file_name:
        git_commit_push(file_name)

if __name__ == "__main__":
    main()
