import requests
import pandas as pd
import time
import os
import ftplib
import json
from io import BytesIO

# --- 設定エリア ---
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR = "www"

API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Referer": "https://gokigen-life.tokyo/20201yutai-all-list/",
}

def main():
    all_data = []
    print("🚀 取得開始...")

    for month in range(1, 13):
        try:
            res = requests.post(API_URL, headers=HEADERS, data={"month": month}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, list):
                    for r in data:
                        if r.get("code") and r.get("code") != "0000":
                            r["target_month"] = f"{month}月"
                            all_data.append(r)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error at {month}月: {e}")

    if not all_data:
        print("データなし")
        return

    update_time = time.strftime('%Y-%m-%d %H:%M')
    
    # --- HTML生成（デザイン版） ---
    html_start = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>優待在庫監視</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f0f2f5; font-family: sans-serif; }}
        .container {{ max-width: 1100px; margin-top: 20px; }}
        .header-section {{ background: linear-gradient(135deg, #0062E6, #33AEFF); color: white; padding: 20px; border-radius: 10px 10px 0 0; }}
        .stock-val {{ font-weight: bold; color: #dc3545; }}
        .zero-val {{ color: #adb5bd; }}
    </style>
</head>
<body>
<div class="container">
    <div class="card shadow-sm">
        <div class="header-section d-flex justify-content-between align-items-center">
            <h1 class="h5 mb-0">🎁 優待在庫ビューワー</h1>
            <span class="badge bg-light text-primary">更新: {update_time}</span>
        </div>
        <div class="p-3 bg-white border-bottom">
            <input type="text" id="search" class="form-control" placeholder="銘柄名やコードで検索...">
        </div>
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0" id="stockTable">
                <thead class="table-light">
                    <tr>
                        <th>月</th><th>コード</th><th>銘柄名</th>
                        <th class="text-center">日興</th><th class="text-center">カブ</th>
                        <th class="text-center">楽天</th><th class="text-center">SBI</th><th class="text-center">GMO</th>
                    </tr>
                </thead>
                <tbody>"""

    rows = ""
    for r in all_data:
        def f(v):
            if not v or v in ["0", "-", "None"]: return '<span class="zero-val">-</span>'
            return f'<span class="stock-val">{v}</span>'
        
        rows += f"""
                    <tr>
                        <td>{r.get('target_month','')}</td>
                        <td><span class="badge border text-dark">{r.get('code','')}</span></td>
                        <td><strong>{r.get('name','')}</strong></td>
                        <td class="text-center">{f(r.get('nikko_zaiko'))}</td>
                        <td class="text-center">{f(r.get('kabu_zaiko'))}</td>
                        <td class="text-center">{f(r.get('rakuten_zaiko'))}</td>
                        <td class="text-center">{f(r.get('sbi_zaiko'))}</td>
                        <td class="text-center">{f(r.get('gmo_zaiko'))}</td>
                    </tr>"""

    html_end = """
                </tbody>
            </table>
        </div>
    </div>
</div>
<script>
document.getElementById('search').addEventListener('input', function(e) {
    const term = e.target.value.toLowerCase();
    const rows = document.querySelectorAll('#stockTable tbody tr');
    rows.forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
    });
});
</script>
</body>
</html>"""

    full_html = html_start + rows + html_end

    # --- FTP転送 ---
    print(f"📡 転送中: {FTP_HOST}")
    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)
            bio = BytesIO(full_html.encode('utf-8'))
            ftp.storbinary("STOR index.html", bio)
            print("✨ 完了！")
    except Exception as e:
        print(f"❌ FTPエラー: {e}")

if __name__ == "__main__":
    main()
