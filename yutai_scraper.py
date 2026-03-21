import requests
import time
import os
import ftplib
import crypt
from io import BytesIO
from datetime import datetime

# --- 設定 ---
FTP_HOST   = os.getenv("FTP_HOST")
FTP_USER   = os.getenv("FTP_USER")
FTP_PASS   = os.getenv("FTP_PASS")
FTP_DIR    = "www"
BASIC_USER = os.getenv("BASIC_USER")
BASIC_PASS = os.getenv("BASIC_PASS")

API_URL = "https://gokigen-life.tokyo/api/00ForWeb/ForZaiko2.php"

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

def main():
    all_data = []
    print("🚀 取得開始...")

    for month in range(1, 13):
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Origin": "https://gokigen-life.tokyo",
            "Referer": REFERER_MAP[month],
        }
        try:
            res = requests.post(API_URL, headers=headers, data={"month": month}, timeout=30)
            if res.status_code == 200:
                data = res.json()
                for r in data:
                    if r.get("code") and r.get("code") != "0000":
                        all_data.append({
                            "month":  month,
                            "code":   r.get("code", ""),
                            "name":   r.get("name", "") or "",
                            "yutai":  r.get("yutai", "") or "",
                            "gyaku":  int(r.get("gyaku_days", 0) or 0),
                            "kenri":  r.get("d_kenri", "") or "",
                            "nvol":   int(r.get("nvol", 0) or 0),
                            "kvol":   int(r.get("kvol", 0) or 0),
                            "rvol":   int(r.get("rvol", 0) or 0),
                            "svol":   int(r.get("svol", 0) or 0),
                            "gvol":   int(r.get("gvol", 0) or 0),
                            "mvol":   int(r.get("mvol", 0) or 0),
                        })
            print(f"  {month}月: OK")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ {month}月 エラー: {e}")

    if not all_data:
        print("データなし")
        return

    current_month = datetime.now().month
    update_time   = datetime.now().strftime('%Y-%m-%d %H:%M')

    import json
    data_json = json.dumps(all_data, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>優待在庫ビューワー</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #f7f6f2; font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif; font-size: 14px; color: #333; }}
        .header {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ font-size: 18px; font-weight: 600; color: #333; }}
        .update-badge {{ background: #f0ede6; color: #888; font-size: 12px; padding: 4px 10px; border-radius: 20px; }}
        .toolbar {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 12px 24px; display: flex; gap: 16px; align-items: center; }}
        .search-input {{ flex: 1; border: 1px solid #e0ddd6; border-radius: 6px; padding: 8px 12px; font-size: 14px; outline: none; background: #faf9f7; }}
        .search-input:focus {{ border-color: #aaa; background: #fff; }}
        .toggle-label {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; white-space: nowrap; cursor: pointer; }}
        .tabs {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 0 24px; display: flex; gap: 4px; overflow-x: auto; }}
        .tab-btn {{ display: inline-block; padding: 12px 14px; font-size: 13px; color: #888; text-decoration: none; border-bottom: 2px solid transparent; white-space: nowrap; cursor: pointer; }}
        .tab-btn:hover {{ color: #333; }}
        .tab-btn.active {{ color: #333; border-bottom-color: #333; font-weight: 600; }}
        .table-wrap {{ overflow-x: auto; }}
        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table thead th {{ background: #faf9f7; border-bottom: 1px solid #e8e6e0; padding: 10px 16px; font-size: 12px; font-weight: 600; color: #888; text-align: center; cursor: pointer; user-select: none; white-space: nowrap; }}
        .data-table thead th:first-child, .data-table thead th:nth-child(2) {{ text-align: left; }}
        .data-table thead th:hover {{ background: #f0ede6; color: #333; }}
        .data-table tbody tr {{ border-bottom: 1px solid #f0ede6; }}
        .data-table tbody tr:hover {{ background: #faf9f7; }}
        .data-table tbody td {{ padding: 12px 16px; vertical-align: middle; }}
        .row-success {{ background: #f0f7f0; }}
        .row-warning {{ background: #fffbf0; }}
        .row-danger  {{ background: #fff5f5; }}
        .code-badge {{ display: inline-block; border: 1px solid #e0ddd6; border-radius: 4px; padding: 2px 8px; font-size: 12px; color: #555; background: #faf9f7; }}
        .yutai-text {{ color: #888; font-size: 12px; }}
        .kenri-text {{ color: #aaa; font-size: 11px; }}
        .gyaku-val  {{ font-size: 12px; color: #888; }}
        .stock-val {{ font-weight: 600; color: #9b2335; }}
        .zero-val  {{ color: #ccc; }}
        .badge-days {{ display: inline-block; border-radius: 20px; padding: 1px 8px; font-size: 11px; margin-left: 4px; }}
        .badge-days.danger  {{ background: #fde8e8; color: #9b2335; }}
        .badge-days.warning {{ background: #fef3e0; color: #a06000; }}
        .badge-days.normal  {{ background: #f0ede6; color: #888; }}
        .container {{ max-width: 1300px; margin: 0 auto; background: #fff; min-height: 100vh; box-shadow: 0 0 40px rgba(0,0,0,0.06); }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎁 優待在庫ビューワー</h1>
        <span class="update-badge">更新: {update_time}</span>
    </div>
    <div class="toolbar">
        <input type="text" id="search" class="search-input" placeholder="銘柄名・コードで検索...">
        <label class="toggle-label">
            <input type="checkbox" id="stockOnly" checked>
            在庫ありのみ
        </label>
    </div>
    <div class="tabs" id="monthTabs"></div>
    <div class="table-wrap">
        <table class="data-table">
            <thead>
                <tr>
                    <th data-label="コード">コード</th>
                    <th data-label="銘柄名・優待">銘柄名・優待</th>
                    <th data-label="逆日歩">逆日歩</th>
                    <th data-label="日興">日興</th>
                    <th data-label="カブコム">カブコム</th>
                    <th data-label="楽天">楽天</th>
                    <th data-label="SBI">SBI</th>
                    <th data-label="GMO">GMO</th>
                    <th data-label="松井">松井</th>
                </tr>
            </thead>
            <tbody id="tbody"></tbody>
        </table>
    </div>
</div>

<script>
const allData = {data_json};
let currentMonth = {current_month};
let sortCol = -1;
let sortAsc = true;

// タブ生成
const tabs = document.getElementById('monthTabs');
for (let m = 1; m <= 12; m++) {{
    const a = document.createElement('a');
    a.className = 'tab-btn' + (m === currentMonth ? ' active' : '');
    a.textContent = m + '月';
    a.dataset.month = m;
    a.addEventListener('click', () => {{
        currentMonth = m;
        document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
        a.classList.add('active');
        sortCol = -1;
        sortAsc = true;
        document.querySelectorAll('.data-table thead th').forEach(t => t.textContent = t.dataset.label);
        renderTable();
    }});
    tabs.appendChild(a);
}}

function gyakuClass(d) {{
    if (d >= 5) return 'row-danger';
    if (d >= 3) return 'row-warning';
    if (d >= 1) return 'row-success';
    return '';
}}

function daysUntil(kenri) {{
    if (!kenri) return '';
    try {{
        const now = new Date();
        const s = kenri.replace(/<br>/g, ' ').split(' ')[0];
        const parts = s.match(/(\d+)月(\d+)日/);
        if (!parts) return '';
        let target = new Date(now.getFullYear(), parseInt(parts[1]) - 1, parseInt(parts[2]));
        if (target < now) target.setFullYear(now.getFullYear() + 1);
        const diff = Math.ceil((target - now) / 86400000);
        if (diff <= 7)  return `<span class="badge-days danger">あと${{diff}}日</span>`;
        if (diff <= 30) return `<span class="badge-days warning">あと${{diff}}日</span>`;
        return `<span class="badge-days normal">あと${{diff}}日</span>`;
    }} catch(e) {{ return ''; }}
}}

function fmt(v) {{
    if (!v) return `<td class="text-center"><span class="zero-val">-</span></td>`;
    return `<td class="text-center"><span class="stock-val">${{v.toLocaleString()}}</span></td>`;
}}

function renderTable() {{
    const q         = document.getElementById('search').value.toLowerCase();
    const stockOnly = document.getElementById('stockOnly').checked;

    let rows = allData.filter(r => r.month === currentMonth);

    if (sortCol >= 0) {{
        const keys = ['code','name','gyaku','nvol','kvol','rvol','svol','gvol','mvol'];
        const key = keys[sortCol];
        rows.sort((a, b) => {{
            const aVal = typeof a[key] === 'number' ? a[key] : 0;
            const bVal = typeof b[key] === 'number' ? b[key] : 0;
            return sortAsc ? aVal - bVal : bVal - aVal;
        }});
    }}

    const tbody = document.getElementById('tbody');
    const hasStock = r => r.nvol || r.kvol || r.rvol || r.svol || r.gvol || r.mvol;

    tbody.innerHTML = rows.map(r => {{
        const matchSearch = (r.code + r.name + r.yutai).toLowerCase().includes(q);
        const matchStock  = !stockOnly || hasStock(r);
        if (!matchSearch || !matchStock) return '';
        return `
            <tr class="${{gyakuClass(r.gyaku)}}">
                <td><span class="code-badge">${{r.code}}</span></td>
                <td>
                    <strong>${{r.name}}</strong><br>
                    <small class="yutai-text">${{r.yutai}}</small><br>
                    <small class="kenri-text">権利日: ${{r.kenri}} ${{daysUntil(r.kenri)}}</small>
                </td>
                <td class="text-center"><span class="gyaku-val">${{r.gyaku}}日</span></td>
                ${{fmt(r.nvol)}}${{fmt(r.kvol)}}${{fmt(r.rvol)}}${{fmt(r.svol)}}${{fmt(r.gvol)}}${{fmt(r.mvol)}}
            </tr>`;
    }}).join('');
}}

renderTable();

document.getElementById('search').addEventListener('input', renderTable);
document.getElementById('stockOnly').addEventListener('change', renderTable);

document.querySelectorAll('.data-table thead th').forEach((th, colIndex) => {{
    th.addEventListener('click', () => {{
        sortAsc = (sortCol === colIndex) ? !sortAsc : false;
        sortCol = colIndex;
        document.querySelectorAll('.data-table thead th').forEach(t => t.textContent = t.dataset.label);
        th.textContent = th.dataset.label + (sortAsc ? ' ▲' : ' ▼');
        renderTable();
    }});
}});
</script>
</body>
</html>"""

    hashed   = crypt.crypt(BASIC_PASS, crypt.mksalt(crypt.METHOD_SHA512))
    htpasswd = f"{BASIC_USER}:{hashed}\n"
    htaccess = """AuthType Basic
AuthName "Private Area"
AuthUserFile /home/seiheki/www/.htpasswd
Require valid-user
"""

    print("📡 FTP転送中...")
    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)
            ftp.storbinary("STOR index.html", BytesIO(html.encode('utf-8')))
            ftp.storbinary("STOR .htpasswd",  BytesIO(htpasswd.encode('utf-8')))
            ftp.storbinary("STOR .htaccess",  BytesIO(htaccess.encode('utf-8')))
            print("✅ 完了！")
    except Exception as e:
        print(f"❌ FTPエラー: {e}")

if __name__ == "__main__":
    main()
