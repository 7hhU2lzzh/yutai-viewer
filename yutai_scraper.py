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
    return f'<td class="text-center" data-value="{v}"><span class="stock-val">{v}</span></td>'

def gyaku_class(days):
    try:
        d = int(days)
        if d >= 5: return "table-danger"
        if d >= 3: return "table-warning"
        if d >= 1: return "table-success"
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
            return f'<span class="badge bg-danger">あと{diff}日</span>'
        elif diff <= 30:
            return f'<span class="badge bg-warning text-dark">あと{diff}日</span>'
        else:
            return f'<span class="text-muted small">あと{diff}日</span>'
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
                <td data-value="0"><span class="badge border text-dark">{r.get('code','')}</span></td>
                <td data-value="0">
                    <strong>{r.get('name','')}</strong><br>
                    <small class="text-muted">{r.get('yutai','')}</small><br>
                    <small>権利日: {kenri} {countdown}</small>
                </td>
                <td class="text-center small" data-value="{r.get('gyaku_days','0')}">逆日歩<br><strong>{r.get('gyaku_days','0')}日</strong></td>
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
        tabs_html += f'<li class="nav-item"><a class="nav-link {active}" href="#" data-month="{m}">{m}月</a></li>'
        panels_html += f"""
        <div id="month-{m}" class="month-panel" style="display:{display}">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0 sortable-table">
                    <thead class="table-light">
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
            </div>
        </div>"""

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
        .zero-val  {{ color: #adb5bd; }}
        .nav-link  {{ color: #495057; }}
        .nav-link.active {{ background: #0062E6 !important; color: white !important; border-radius: 6px; }}
        th {{ cursor: pointer; user-select: none; white-space: nowrap; }}
        th:hover {{ background-color: #e9ecef; }}
        .no-stock {{ opacity: 0.4; }}
    </style>
</head>
<body>
<div class="container mt-3" style="max-width:1300px">
    <div class="card shadow-sm">
        <div class="p-3 text-white" style="background:linear-gradient(135deg,#0062E6,#33AEFF);border-radius:8px 8px 0 0">
            <h1 class="h5 mb-0">🎁 優待在庫ビューワー
                <span class="badge bg-light text-primary float-end">更新: {update_time}</span>
            </h1>
        </div>
        <div class="p-3 bg-white border-bottom d-flex gap-3 align-items-center">
            <input type="text" id="search" class="form-control" placeholder="銘柄名・コードで検索...">
            <div class="form-check form-switch mb-0 text-nowrap">
                <input class="form-check-input" type="checkbox" id="stockOnly" checked>
                <label class="form-check-label" for="stockOnly">在庫ありのみ</label>
            </div>
        </div>
        <div class="px-3 pt-2 bg-white border-bottom">
            <ul class="nav nav-pills gap-1 flex-wrap" id="monthTabs">
                {tabs_html}
            </ul>
        </div>
        <div class="bg-white">
            {panels_html}
        </div>
    </div>
</div>

<script>
document.querySelectorAll('#monthTabs a').forEach(tab => {{
    tab.addEventListener('click', function(e) {{
        e.preventDefault();
        document.querySelectorAll('#monthTabs a').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        document.querySelectorAll('.month-panel').forEach(p => p.style.display = 'none');
        document.getElementById('month-' + this.dataset.month).style.display = 'block';
        applyFilters();
    }});
}});

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

let sortState = {{}};
document.querySelectorAll('.sortable-table thead th').forEach((th, colIndex) => {{
    th.addEventListener('click', () => {{
        const table   = th.closest('table');
        const tableId = table.closest('.month-panel').id;
        if (!sortState[tableId]) sortState[tableId] = {{ col: -1, asc: true }};
        const state   = sortState[tableId];

        state.asc = (state.col === colIndex) ? !state.asc : false;
        state.col = colIndex;

        const tbody = table.querySelector('tbody');
        const rows  = Array.from(tbody.querySelectorAll('tr'));

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
