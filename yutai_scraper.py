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

def fmt_vol(v):
    if not v or str(v) in ["0", "-", "None", ""]:
        return '<td class="text-center" data-value="0"><span class="zero-val">-</span></td>'
    num = int(v)
    return f'<td class="text-center" data-value="{num}"><span class="stock-val">{num:,}</span></td>'

def gyaku_class(days):
    try:
        d = int(days)
        if d >= 5: return "row-danger"
        if d >= 3: return "row-warning"
        if d >= 1: return "row-success"
    except:
        pass
    return ""

def days_until(kenri_date_str):
    try:
        now = datetime.now()
        s = kenri_date_str.replace("月", "/").replace("日", "").replace("<br>", " ").split()[0]
        parts = s.split("/")
        month = int(parts[0])
        day   = int(parts[1])
        target = datetime(now.year, month, day)
        if target < now:
            target = datetime(now.year + 1, month, day)
        diff = (target - now).days
        if diff <= 7:
            return f'<span class="badge-days danger">あと{diff}日</span>'
        elif diff <= 30:
            return f'<span class="badge-days warning">あと{diff}日</span>'
        else:
            return f'<span class="badge-days normal">あと{diff}日</span>'
    except:
        return ""

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
                        r["target_month"] = month
                        all_data.append(r)
            print(f"  {month}月: OK")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ {month}月 エラー: {e}")

    if not all_data:
        print("データなし")
        return

    current_month = datetime.now().month
    update_time   = datetime.now().strftime('%Y-%m-%d %H:%M')

    rows_by_month = {m: "" for m in range(1, 13)}
    for r in all_data:
        m         = r["target_month"]
        gc        = gyaku_class(r.get("gyaku_days", 0))
        kenri     = r.get("d_kenri") or ""
        countdown = days_until(kenri) if kenri else ""
        has_stock = any([
            r.get('nvol') and str(r.get('nvol')) not in ["0", ""],
            r.get('kvol') and str(r.get('kvol')) not in ["0", ""],
            r.get('rvol') and str(r.get('rvol')) not in ["0", ""],
            r.get('svol') and str(r.get('svol')) not in ["0", ""],
            r.get('gvol') and str(r.get('gvol')) not in ["0", ""],
            r.get('mvol') and str(r.get('mvol')) not in ["0", ""],
        ])
        stock_flag = "has-stock" if has_stock else "no-stock"

        rows_by_month[m] += f"""
            <tr class="{gc} {stock_flag}">
                <td data-value="0"><span class="code-badge">{r.get('code','')}</span></td>
                <td data-value="0">
                    <strong>{r.get('name','')}</strong><br>
                    <small class="yutai-text">{r.get('yutai','')}</small><br>
                    <small class="kenri-text">権利日: {kenri} {countdown}</small>
                </td>
                <td class="text-center" data-value="{r.get('gyaku_days','0')}">
                    <span class="gyaku-val">{r.get('gyaku_days','0')}日</span>
                </td>
                {fmt_vol(r.get('nvol'))}
                {fmt_vol(r.get('kvol'))}
                {fmt_vol(r.get('rvol'))}
                {fmt_vol(r.get('svol'))}
                {fmt_vol(r.get('gvol'))}
                {fmt_vol(r.get('mvol'))}
            </tr>"""

    tabs_html   = ""
    panels_html = ""
    for m in range(1, 13):
        active  = "active" if m == current_month else ""
        display = "block"  if m == current_month else "none"
        tabs_html += f'<a class="tab-btn {active}" href="#" data-month="{m}">{m}月</a>'
        panels_html += f"""
        <div id="month-{m}" class="month-panel" style="display:{display}">
            <table class="data-table" id="tbl-{m}">
                <thead>
                    <tr>
                        <th data-label="コード">コード</th>
                        <th data-label="銘柄名・優待">銘柄名・優待</th>
                        <th class="text-center" data-label="逆日歩">逆日歩</th>
                        <th class="text-center" data-label="日興">日興</th>
                        <th class="text-center" data-label="カブコム">カブコム</th>
                        <th class="text-center" data-label="楽天">楽天</th>
                        <th class="text-center" data-label="SBI">SBI</th>
                        <th class="text-center" data-label="GMO">GMO</th>
                        <th class="text-center" data-label="松井">松井</th>
                    </tr>
                </thead>
                <tbody>{rows_by_month[m]}</tbody>
            </table>
        </div>"""

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
        .tab-btn {{ display: inline-block; padding: 12px 14px; font-size: 13px; color: #888; text-decoration: none; border-bottom: 2px solid transparent; white-space: nowrap; }}
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
        .no-stock {{ opacity: 0.35; }}
        .text-center {{ text-align: center; }}
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
    <div class="tabs" id="monthTabs">
        {tabs_html}
    </div>
    <div class="table-wrap">
        {panels_html}
    </div>
</div>

<script>
// 月タブ切り替え
document.querySelectorAll('.tab-btn').forEach(tab => {{
    tab.addEventListener('click', function(e) {{
        e.preventDefault();
        document.querySelectorAll('.tab-btn').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        document.querySelectorAll('.month-panel').forEach(p => p.style.display = 'none');
        document.getElementById('month-' + this.dataset.month).style.display = 'block';
        applyFilters();
    }});
}});

// フィルター
function applyFilters() {{
    const q         = document.getElementById('search').value.toLowerCase();
    const stockOnly = document.getElementById('stockOnly').checked;
    document.querySelectorAll('.month-panel').forEach(panel => {{
        if (panel.style.display === 'none') return;
        panel.querySelectorAll('tbody tr').forEach(row => {{
            const matchSearch = row.textContent.toLowerCase().includes(q);
            const matchStock  = !stockOnly || row.classList.contains('has-stock');
            row.style.display = (matchSearch && matchStock) ? '' : 'none';
        }});
    }});
}}

document.getElementById('search').addEventListener('input', applyFilters);
document.getElementById('stockOnly').addEventListener('change', applyFilters);
applyFilters();

// ソート
let sortState = {{}};
document.querySelectorAll('.data-table thead th').forEach((th, colIndex) => {{
    th.addEventListener('click', () => {{
        const table   = th.closest('table');
        const tableId = table.closest('.month-panel').id;
        if (!sortState[tableId]) sortState[tableId] = {{ col: -1, asc: true }};
        const state   = sortState[tableId];

        state.asc = (state.col === colIndex) ? !state.asc : false;
        state.col = colIndex;

        const tbody = table.querySelector('tbody');
        const rows  = Array.from(tbody.querySelectorAll('tr'));

        // 一旦全行表示してからソート
        rows.forEach(r => r.style.display = '');

        rows.sort((a, b) => {{
            const aVal = parseInt(a.cells[colIndex]?.dataset.value || '0') || 0;
            const bVal = parseInt(b.cells[colIndex]?.dataset.value || '0') || 0;
            return state.asc ? aVal - bVal : bVal - aVal;
        }});

        table.querySelectorAll('thead th').forEach(t => {{
            t.textContent = t.dataset.label;
        }});
        th.textContent = th.dataset.label + (state.asc ? ' ▲' : ' ▼');
        rows.forEach(r => tbody.appendChild(r));

        // フィルター再適用
        applyFilters();
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
