import requests
import pandas as pd
import time
import os
import ftplib
import json
from io import BytesIO

# GitHub Secretsから読み込み
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR  = "www" # さくらインターネットなら通常は 'www'

API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Referer": "https://gokigen-life.tokyo/20201yutai-all-list/",
}

def main():
    all_data = []
    print("データ取得を開始します...")
    for month in range(1, 13):
        try:
            res = requests.post(API_URL, headers=HEADERS, data={"month": month}, timeout=20)
            if res.status_code == 200:
                for r in res.json():
                    if r.get("code") and r.get("code") != "0000":
                        r["target_month"] = f"{month}月"
                        all_data.append(r)
            time.sleep(0.5)
        except Exception as e:
            print(f"{month}月の取得でエラー: {e}")

    if all_data:
        json_str = json.dumps(all_data, ensure_ascii=False)
        html_content = f"<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'><title>優待在庫</title></head><body><h1>更新: {time.strftime('%Y-%m-%d %H:%M')}</h1><pre>{json_str}</pre></body></html>"
        
        print(f"FTP接続試行: {FTP_HOST}")
        try:
            with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
                print("ログイン成功")
                print(f"現在のディレクトリ: {ftp.pwd()}")
                
                # フォルダ移動
                try:
                    ftp.cwd(FTP_DIR)
                    print(f"ディレクトリ移動成功: {FTP_DIR}")
                except Exception as e:
                    print(f"ディレクトリ移動失敗 ({FTP_DIR}): {e}")
                    print(f"現在の場所にあるもの: {ftp.nlst()}")

                # ファイル書き込み
                bio = BytesIO(html_content.encode('utf-8'))
                ftp.storbinary("STOR index.html", bio)
                print("アップロード完了: index.html")
                
        except Exception as e:
            print(f"FTP操作全体でエラーが発生しました: {e}")
    else:
        print("データが取得できなかったため、アップロードを中止しました。")

if __name__ == "__main__":
    main()
