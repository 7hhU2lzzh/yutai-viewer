import requests
import pandas as pd
import time
import os
import ftplib
import json
from io import BytesIO

FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
FTP_DIR  = "www"

API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"

# ✅ 月ごとのReferer
REFERER_MAP = {
    1:  "https://gokigen-life.tokyo/20201yutai-all-list/",
    2:  "https://gokigen-life.tokyo/20202yutai-all-list/",
    3:  "https://gokigen-life.tokyo/03yutai-all-list/",
    4:  "https://gokigen-life.tokyo/04yutai-all-list/",
    5:  "https://gokigen-life.tokyo/201905yutai-all-list/",
    6:  "https://gokigen-life.tokyo/201906yutai-all-list/",
    7:  "https://gokigen-life.tokyo/201907yutai-all-list/",
    8:  "https://gokigen-life.tokyo/201908yutai-all-list/",
    9:  "https://gokigen-life.tokyo/201909yutai-all-list/",
    10: "https://gokigen-life.tokyo/201910yutai-all-list/",
    11: "https://gokigen-life.tokyo/201911yutai-all-list/",
    12: "https://gokigen-life.tokyo/201912yutai-all-list/",
}

def fmt_vol(v):
    """在庫数のフォーマット"""
    if not v or str(v) in ["0", "-", "None", ""]:
        return '<span class="zero-val">-</span>'
    return f'<span class="stock-val">{v}</span>'

def main():
    all_data = []
    print("🚀 取得開始...")

    for month in range(1, 13):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://gokigen-life.tokyo",
            "Referer": REFERER_MAP[month],  # ✅ 月ごとに切り替え
        }
        try:
            res = requests.post(API_URL, headers=headers, data={"month": month}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for r in data:
                    if r.get("code") and r.get("code") != "0000":
                        r["target_month"] = f"{month}月"
                        all_data.append(r)
            print(f"  {month}月: {len([r for r in all_data if r.get('target_month')==f'{month}月'])}件")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ {month}月 エラー: {e}")

    if not all_data:
        print("データなし")
        return

    update_time = time.strftime('%Y-%m-%d %H:%M')

    rows = ""
    for r in all_data:
        rows += f"""
            <tr>
                <td>{r.get('target_month','')}</td>
                <td><span class="badge border text-dark">{r.get('code','')}</span></td>
                <td><strong>{r.get('name','')}</strong><br>
                    <small class="text-muted">{r.get('yutai','')}</small></td>
                <td class="text-center">{fmt_vol(r.get('nvol'))}</td>
                <td class="text-center">{fmt_vol(r.get('kvol'))}</td>
                <td class="text-center">{fmt_vol(r.get('rvol'))}</td>
                <td class="text-center">{fmt_vol(r.get('svol'))}</td>
                <td class="text-center">{fmt_vol(r.get('gvol'))}</td>
                <td class="text-center">{fmt_vol(r.get('mvol'))}</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>優待在庫ビューワー</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f0f2f5; }}
        .stock-val {{ font-weight: bold; color: #dc3545; }}
        .zero-val {{ color: #adb5bd; }}
    </style>
</head>
<body>
<div class="container mt-3" style="max-width:1200px">
    <div class="card shadow-sm">
        <div class="p-3 text-white" style="background:linear-gradient(135deg,#0062E6,#33AEFF);border-radius:8px 8px 0 0">
            <h1 class="h5 mb-0">🎁 優待在庫ビューワー
                <span class="badge bg-light text-primary float-end">更新: {update_time}</span>
            </h1>
        </div>
        <div class="p-3 bg-white border-bottom">
            <input type="text" id="search" class="form-control" placeholder="銘柄名・コードで検索...">
        </div>
        <div class="table-responsive">
            <table class="table table-hover align-middle mb-0" id="tbl">
                <thead class="table-light">
                    <tr>
                        <th>月</th><th>コード</th><th>銘柄名・優待</th>
                        <th class="text-center">日興</th><th class="text-center">カブコム</th>
                        <th class="text-center">楽天</th><th class="text-center">SBI</th>
                        <th class="text-center">GMO</th><th class="text-center">松井</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
    </div>
</div>
<script>
document.getElementById('search').addEventListener('input', function() {{
    const q = this.value.toLowerCase();
    document.querySelectorAll('#tbl tbody tr').forEach(r => {{
        r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none';
    }});
}});
</script>
</body>
</html>"""

    # FTP転送
    print(f"📡 FTP転送中...")
    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)
            ftp.storbinary("STOR index.html", BytesIO(html.encode('utf-8')))
            print("✅ 完了！")
    except Exception as e:
        print(f"❌ FTPエラー: {e}")

if __name__ == "__main__":
    main()
