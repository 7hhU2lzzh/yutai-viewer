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
FTP_DIR  = "/www/"

API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Referer": "https://gokigen-life.tokyo/20201yutai-all-list/",
}

def main():
    all_data = []
    # 12ヶ月分のデータを取得
    for month in range(1, 13):
        print(f"{month}月 取得中...")
        try:
            res = requests.post(API_URL, headers=HEADERS, data={"month": month}, timeout=20)
            if res.status_code == 200:
                for r in res.json():
                    if r.get("code") and r.get("code") != "0000":
                        # 月情報を追加して保存
                        r["target_month"] = f"{month}月"
                        all_data.append(r)
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")

    if all_data:
        # ビューワーHTMLを生成
        json_str = json.dumps(all_data, ensure_ascii=False)
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>優待在庫リアルタイム</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                .stock-active {{ background-color: #dcfce7; font-weight: bold; color: #166534; }}
                th {{ position: sticky; top: 0; background: #f3f4f6; z-index: 10; }}
            </style>
        </head>
        <body class="bg-gray-100 p-4">
            <div class="max-w-6xl mx-auto">
                <h1 class="text-xl font-bold mb-4">優待在庫状況 (更新: {time.strftime('%Y-%m-%d %H:%M')})</h1>
                <div class="bg-white rounded shadow overflow-hidden h-[800px] overflow-y-auto">
                    <table class="w-full text-sm text-left">
                        <thead>
                            <tr class="bg-gray-100 border-b">
                                <th class="p-2">月</th><th class="p-2">コード</th><th class="p-2">銘柄名</th>
                                <th class="p-2 text-center">日興</th><th class="p-2 text-center">カブ</th>
                                <th class="p-2 text-center">楽天</th><th class="p-2 text-center">SBI</th>
                                <th class="p-2 text-center">GMO</th><th class="p-2 text-center">松井</th>
                            </tr>
                        </thead>
                        <tbody id="out"></tbody>
                    </table>
                </div>
            </div>
            <script>
                const data = {json_str};
                const out = document.getElementById('out');
                data.forEach(d => {{
                    const tr = document.createElement('tr');
                    tr.className = "border-b hover:bg-gray-50";
                    tr.innerHTML = `
                        <td class="p-2 text-gray-500">${{d.target_month}}</td>
                        <td class="p-2 font-mono">${{d.code}}</td>
                        <td class="p-2 font-bold">${{d.name || ""}}</td>
                        <td class="p-2 text-center ${{d.nvol > 0 ? 'stock-active':''}}">${{d.nvol || 0}}</td>
                        <td class="p-2 text-center ${{d.kvol > 0 ? 'stock-active':''}}">${{d.kvol || 0}}</td>
                        <td class="p-2 text-center ${{d.rvol > 0 ? 'stock-active':''}}">${{d.rvol || 0}}</td>
                        <td class="p-2 text-center ${{d.svol > 0 ? 'stock-active':''}}">${{d.svol || 0}}</td>
                        <td class="p-2 text-center ${{d.gvol > 0 ? 'stock-active':''}}">${{d.gvol || 0}}</td>
                        <td class="p-2 text-center ${{d.mvol > 0 ? 'stock-active':''}}">${{d.mvol || 0}}</td>
                    `;
                    out.appendChild(tr);
                }});
            </script>
        </body>
        </html>
        """
        
        # FTPでアップロード
        try:
            with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
                ftp.cwd(FTP_DIR)
                bio = BytesIO(html_content.encode('utf-8'))
                ftp.storbinary("STOR index.html", bio)
                print("FTPアップロード成功！")
        except Exception as e:
            print(f"FTPエラー: {e}")

if __name__ == "__main__":
    main()
