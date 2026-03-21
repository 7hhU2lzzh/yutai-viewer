import requests
import pandas as pd
import time
import os
import ftplib
import json
from io import BytesIO

# --- 設定エリア（GitHub Secretsから読み込み） ---
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR  = "www"  # さくらインターネットの公開ディレクトリ名

# 在庫データの取得先URL
API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Referer": "https://gokigen-life.tokyo/20201yutai-all-list/",
}

def main():
    all_data = []
    print("🚀 在庫データの取得を開始します...")

    # 1月から12月までのデータを順次取得
    for month in range(1, 13):
        try:
            res = requests.post(API_URL, headers=HEADERS, data={"month": month}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    for r in data:
                        # 無効なコード（0000など）を除外
                        if r.get("code") and r.get("code") != "0000":
                            r["target_month"] = f"{month}月"
                            all_data.append(r)
                print(f"✅ {month}月のデータを取得しました")
            time.sleep(0.5) # サーバー負荷軽減のための待機
        except Exception as e:
            print(f"❌ {month}月の取得でエラーが発生しました: {e}")

    if not all_data:
        print("⚠️ データが取得できなかったため、終了します。")
        return

    # --- HTMLの生成（Bootstrap 5 を使用したデザイン） ---
    update_time = time.strftime('%Y-%m-%d %H:%M')
    
    html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>優待在庫リアルタイム監視</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f0f2f5; font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif; }}
        .container {{ max-width: 1100px; margin-top: 30px; margin-bottom: 50px; }}
        .card {{ border: none; border-radius: 15px; box-shadow: 0 8px 30px rgba(0,0,0,0.05); overflow: hidden; }}
        .header-section {{ background: linear-gradient(135deg, #0062E6, #33AEFF); color: white; padding: 25px; }}
        .table thead {{ background-color: #f8f9fa; color: #444; border-bottom: 2px solid #dee2e6; }}
        .stock-val {{ font-weight: 700; color: #dc3545; font-size: 1.1rem; }}
        .zero-val {{ color: #adb5bd; font-weight: 400; }}
        .search-container {{ padding: 20px; background: white; border-bottom: 1px solid #eee; }}
        .update-badge {{ background: rgba(255,255,255,0.2); padding: 5px 12px; border-radius: 20px; font-size: 0.85rem; }}
        tr:hover {{ background-color: #fdfdfe !important; }}
        @media (max-width: 768px) {{ .table {{ font-size: 0.85rem; }} }}
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <div class="header-section d-flex justify-content-between align-items-center">
            <h1 class="h4 mb-0">🎁 優待在庫ビューワー</h1>
            <span class="update-badge">最終更新: {update_time}</span>
        </div>
        
        <div class="search-container">
            <input type="text" id="search" class="form-control form-control-lg" placeholder="銘柄名・コード・月で絞り込み...">
        </div>

        <div class="table-responsive">
            <table class="table align-middle mb-0" id="stockTable">
                <thead>
                    <tr>
                        <th>月</th>
                        <th>コード</th>
                        <th>銘柄名</th>
