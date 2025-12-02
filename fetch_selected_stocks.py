import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
import jpholiday

# ------------------------------
# 定数
# ------------------------------
TICKER_LIST_CSV = "tickers_list.csv"
DATA_DIR = "stock_data"
JST = ZoneInfo("Asia/Tokyo")

# 日本市場の取得対象時刻（JST）
TARGET_TIMES = [
    "09:00", "09:30",
    "10:00", "10:30",
    "11:00", "11:30",
    "12:30",
    "13:00", "13:30",
    "14:00", "14:30",
    "15:00", "15:30",
]

os.makedirs(DATA_DIR, exist_ok=True)

# ------------------------------
# 日本営業日判定（平日かつ祝日・年末年始除外）
# ------------------------------
def is_business_day():
    now = datetime.now(JST)
    today = now.date()

    # 平日判定
    if now.weekday() >= 5:  # 5=土曜, 6=日曜
        print(f"⛔ 土日: {today}")
        return False

    # 日本の祝日
    if jpholiday.is_holiday(today):
        print(f"⛔ 祝日: {today}")
        return False

    # 年末年始（12/29〜1/3）
    if (today.month == 12 and today.day >= 29) or (today.month == 1 and today.day <= 3):
        print(f"⛔ 年末年始: {today}")
        return False

    return True

# ------------------------------
# 現在時刻が対象時刻か判定（±5分）
# ------------------------------
def is_target_time():
    now = datetime.now(JST)
    for t in TARGET_TIMES:
        h, m = map(int, t.split(":"))
        target = datetime(now.year, now.month, now.day, h, m, tzinfo=JST)
        diff = abs((now - target).total_seconds())
        if diff <= 300:  # ±5分
            print(f"⭐ 取得時刻一致: {now.strftime('%H:%M:%S')} ≈ {t}")
            return True
    print(f"⏸ 対象外時刻: {now.strftime('%H:%M:%S')}")
    return False

# ------------------------------
# 銘柄リスト読み込み
# ------------------------------
def load_ticker_list():
    if not os.path.exists(TICKER_LIST_CSV):
        print(f"⚠ {TICKER_LIST_CSV} が見つかりません")
        return []

    df = pd.read_csv(TICKER_LIST_CSV)
    if not {"銘柄コード", "銘柄名"}.issubset(df.columns):
        raise KeyError("CSV に '銘柄コード' '銘柄名' が必要です")

    df["Ticker"] = df["銘柄コード"].astype(str) + ".T"
    return df

# ------------------------------
# 株価取得
# ------------------------------
def fetch_current_price(ticker, name):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1d", interval="1m")
        if df.empty:
            print(f"⚠ データ取得不可: {ticker}")
            return None

        price = df["Close"].iloc[-1]
        now = datetime.now(JST)

        return {
            "銘柄コード": ticker.replace(".T", ""),
            "銘柄名": name,
            "株価": float(price),
            "取得時間(JST)": now.strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        print(f"❌ {ticker} エラー: {e}")
        return None

# ------------------------------
# 全銘柄取得
# ------------------------------
def fetch_all_prices():
    df_list = load_ticker_list()
    if len(df_list) == 0:
        print("❌ 銘柄リスト読込不可")
        return pd.DataFrame()

    results = []
    for _, row in df_list.iterrows():
        data = fetch_current_price(row["Ticker"], row["銘柄名"])
        if data:
            results.append(data)
        time.sleep(0.3)  # API負荷軽減
    return pd.DataFrame(results)

# ------------------------------
# CSV 保存
# ------------------------------
def save_prices(df):
    if df.empty:
        print("⚠ データなし → CSV保存しません")
        return None

    now_str = datetime.now(JST).strftime("%Y%m%d_%H%M")
    file_name = f"stock_prices_{now_str}.csv"
    path = os.path.join(DATA_DIR, file_name)

    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"💾 保存完了: {path}")
    return file_name

# ------------------------------
# main
# ------------------------------
def main():
    # 1. 営業日か確認
    if not is_business_day():
        return

    # 2. 対象時刻か確認
    if not is_target_time():
        return

    # 3. 株価取得
    df = fetch_all_prices()

    # 4. CSV 保存
    save_prices(df)

if __name__ == "__main__":
    main()
