import os
import time
import subprocess
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf

TICKER_LIST_CSV = "tickers_list.csv"
DATA_DIR = "stock_data"
os.makedirs(DATA_DIR, exist_ok=True)

JST = ZoneInfo("Asia/Tokyo")


# -----------------------------
# 市場時間の 30 分刻みチェック
# -----------------------------
TARGET_TIMES = {
    "09:00", "09:30",
    "10:00", "10:30",
    "11:00", "11:30",
    "12:30",
    "13:00", "13:30",
    "14:00", "14:30",
    "15:00", "15:30",
}


def is_target_time():
    """現在が取得対象の 30 分時刻かどうか判定"""
    now = datetime.now(JST)
    hhmm = now.strftime("%H:%M")
    return hhmm in TARGET_TIMES


# -----------------------------
# 銘柄リスト読み込み
# -----------------------------
def load_ticker_list():
    if not os.path.exists(TICKER_LIST_CSV):
        print(f"{TICKER_LIST_CSV} が見つかりません。")
        return []

    df = pd.read_csv(TICKER_LIST_CSV)

    if not {"銘柄コード", "銘柄名"}.issubset(df.columns):
        raise KeyError("CSV に '銘柄コード' '銘柄名' の列が必要です。")

    df["Ticker"] = df["銘柄コード"].astype(str) + ".T"
    return df


# -----------------------------
# 現在値取得
# -----------------------------
def fetch_current_price(ticker, name):
    try:
        stock = yf.Ticker(ticker)
        price = stock.fast_info.last_price

        if price is None:
            return None

        now = datetime.now(JST)

        return {
            "銘柄コード": ticker.replace(".T", ""),
            "銘柄名": name,
            "株価": price,
            "取得時間(JST)": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        print(f"{ticker} エラー: {e}")
        return None


# -----------------------------
# 全銘柄取得
# -----------------------------
def fetch_all_prices():
    df_list = load_ticker_list()
    if len(df_list) == 0:
        print("銘柄リストが読込不可")
        return pd.DataFrame()

    results = []
    for _, row in df_list.iterrows():
        res = fetch_current_price(row["Ticker"], row["銘柄名"])
        if res:
            results.append(res)
        time.sleep(0.2)

    return pd.DataFrame(results)


# -----------------------------
# CSV 保存
# -----------------------------
def save_prices(df):
    if df.empty:
        print("データなし（保存しない）")
        return None

    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    file_name = f"stock_prices_{now_str}.csv"
    file_path = os.path.join(DATA_DIR, file_name)
    df.to_csv(file_path, index=False, encoding="utf-8-sig")

    print(f"保存完了: {file_path}")
    return file_name


# -----------------------------
# GitHub コミット
# -----------------------------
def git_commit_push(file_name):
    try:
        subprocess.run(["git", "add", os.path.join(DATA_DIR, file_name)], check=True)
        subprocess.run(
            ["git", "commit", "-m", f"Add stock data {file_name}", "--allow-empty"],
            check=True
        )
        subprocess.run(["git", "push"], check=True)
        print("GitHub へプッシュ完了")
    except Exception as e:
        print(f"Git エラー: {e}")


# -----------------------------
# main
# -----------------------------
def main():
    # ★ ここが重要（30 分刻みの時だけ実行）
    if not is_target_time():
        print("対象時刻ではないためスキップします")
        return

    df = fetch_all_prices()
    file_name = save_prices(df)

    if file_name:
        git_commit_push(file_name)


if __name__ == "__main__":
    main()
