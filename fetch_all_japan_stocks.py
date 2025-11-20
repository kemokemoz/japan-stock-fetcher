import os
import json
import time
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import subprocess

# ---------------------------
# 設定
# ---------------------------
TICKER_FILE = "tickers.json"
DATA_DIR = "stock_data"
EXCEL_FILE = "data_j.xls"  # 手動で更新される Excel ファイル
MAX_WORKERS = 10
RETRY_DELAY = 5

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------
# 日本株ティッカー取得（Excel ファイル）
# ---------------------------
def get_all_japanese_tickers():
    if not os.path.exists(EXCEL_FILE):
        print(f"{EXCEL_FILE} が見つかりません。先にアップロードしてください。")
        return []

    df = pd.read_excel(EXCEL_FILE, skiprows=0)  # Excel の形式に応じて調整
    if "コード" not in df.columns:
        raise KeyError("'コード' 列が Excel に存在しません。")
    tickers = df["コード"].astype(str) + ".T"
    return tickers.tolist()

# ---------------------------
# ティッカー読み込み or 更新
# ---------------------------
def load_or_update_tickers():
    update_needed = True
    if os.path.exists(TICKER_FILE):
        with open(TICKER_FILE, "r") as f:
            data = json.load(f)
            last_update = datetime.fromisoformat(data["last_update"])
            if datetime.now() - last_update < timedelta(days=30):
                update_needed = False
                return data["tickers"]

    if update_needed:
        tickers = get_all_japanese_tickers()
        with open(TICKER_FILE, "w") as f:
            json.dump({"last_update": datetime.now().isoformat(), "tickers": tickers}, f)
        print(f"ティッカーを更新しました ({len(tickers)} 件)")
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
            print(f"{ticker} 取得エラー: {e} (試行 {attempt+1})")
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
        print("取得データなし")
        return None
    now_str = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"stock_prices_{now_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    df.to_csv(file_path, index=False)
    print(f"保存完了: {file_path}")
    return file_name

# ---------------------------
# GitHub 自動コミット＆プッシュ
# ---------------------------
def git_commit_push(file_name):
    try:
        # 変更をステージング
        subprocess.run(["git", "add", os.path.join(DATA_DIR, file_name)], check=True)

        # コミット（既に同じコミットがあっても空コミット許可）
        subprocess.run(
            ["git", "commit", "-m", f"Add stock data {file_name}", "--allow-empty"], 
            check=True
        )

        # push（GitHub Actions 内では GITHUB_TOKEN による認証で安全）
        subprocess.run(["git", "push"], check=True)
        print(f"{file_name} を GitHub にコミット＆プッシュしました")
    except subprocess.CalledProcessError as e:
        print(f"Git エラー: {e}")

# ---------------------------
# メイン処理
# ---------------------------
def main():
    tickers = load_or_update_tickers()
    if not tickers:
        print("ティッカーが取得できません。処理を終了します。")
        return

    print(f"{len(tickers)} 銘柄の株価を取得中...")
    df = fetch_all_prices(tickers)

    file_name = save_prices(df)
    if file_name:
        git_commit_push(file_name)

if __name__ == "__main__":
    main()

