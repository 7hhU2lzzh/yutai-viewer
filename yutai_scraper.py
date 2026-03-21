import requests
import time
import os
import ftplib
import crypt
import json
from io import BytesIO
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))

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

FIRMS     = ['nvol', 'kvol', 'rvol', 'svol', 'gvol', 'mvol']
FIRM_NAMES = {'nvol':'日興', 'kvol':'カブコム', 'rvol':'楽天', 'svol':'SBI', 'gvol':'GMO', 'mvol':'松井'}

def main():
    now = datetime.now(JST)
    today_str    = now.strftime('%Y/%m/%d')
    update_time  = now.strftime('%Y-%m-%d %H:%M')
    current_year = now.year

    # --- prev.json と kokuzetsu.json を読む ---
    prev_data = {}
    if os.path.exists("prev.json"):
        with open("prev.json", "r", encoding="utf-8") as f:
            prev_data = json.load(f)

    kokuzetsu = {}
    if os.path.exists("kokuzetsu.json"):
        with open("kokuzetsu.json", "r", encoding="utf-8") as f:
            kokuzetsu = json.load(f)

    # --- クロール ---
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
                            "month": month,
                            "code":  r.get("code", ""),
                            "name":  r.get("name", "") or "",
                            "yutai": r.get("yutai", "") or "",
                            "gyaku": int(r.get("gyaku_days", 0) or 0),
                            "kenri": r.get("d_kenri", "") or "",
                            "nvol":  int(r.get("nvol", 0) or 0),
                            "kvol":  int(r.get("kvol", 0) or 0),
                            "rvol":  int(r.get("rvol", 0) or 0),
                            "svol":  int(r.get("svol", 0) or 0),
                            "gvol":  int(r.get("gvol", 0) or 0),
                            "mvol":  int(r.get("mvol", 0) or 0),
                        })
            print(f"  {month}月: OK")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️ {month}月 エラー: {e}")

    if not all_data:
        print("データなし")
        return

    # --- 枯渇検出 ---
    print("🔍 枯渇検出中...")
    for r in all_data:
        code     = r["code"]
        month    = r["month"]
        # 権利年の判定：権利月が現在月より前なら翌年の権利
        kenri_year = current_year
        key      = f"{kenri_year}_{month}_{code}"
        prev_key = f"{month}_{code}"
        prev     = prev_data.get(prev_key, {})

        if key not in kokuzetsu:
            kokuzetsu[key] = {
                "code":        code,
                "name":        r["name"],
                "kenri_year":  kenri_year,
                "kenri_month": month,
                "firms":       {}
            }

        for f in FIRMS:
            prev_vol = prev.get(f, 0)
            curr_vol = r[f]
            if prev_vol > 0 and curr_vol == 0:
                if f not in kokuzetsu[key]["firms"]:
                    kokuzetsu[key]["firms"][f] = today_str
                    print(f"  枯渇検出: {r['name']} {FIRM_NAMES[f]} {today_str}")

    # --- prev.json を更新 ---
    new_prev = {}
    for r in all_data:
        key = f"{r['month']}_{r['code']}"
        new_prev[key] = {f: r[f] for f in FIRMS}

    with open("prev.json", "w", encoding="utf-8") as f:
        json.dump(new_prev, f, ensure_ascii=False, indent=2)

    with open("kokuzetsu.json", "w", encoding="utf-8") as f:
        json.dump(kokuzetsu, f, ensure_ascii=False, indent=2)

    print("✅ kokuzetsu.json 更新完了")

    # --- HTML生成 ---
    data_json      = json.dumps(all_data,  ensure_ascii=False)
    kokuzetsu_json = json.dumps(kokuzetsu, ensure_ascii=False)

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
        .header h1 {{ font-size: 18px; font-weight: 600; }}
        .update-badge {{ background: #f0ede6; color: #888; font-size: 12px; padding: 4px 10px; border-radius: 20px; }}
        .toolbar {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 12px 24px; display: flex; gap: 16px; align-items: center; }}
        .search-input {{ flex: 1; border: 1px solid #e0ddd6; border-radius: 6px; padding: 8px 12px; font-size: 14px; outline: none; background: #faf9f7; }}
        .search-input:focus {{ border-color: #aaa; background: #fff; }}
        .toggle-label {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; white-space: nowrap; cursor: pointer; }}
        .main-tabs {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 0 24px; display: flex; gap: 4px; }}
        .main-tab {{ padding: 12px 16px; font-size: 13px; color: #888; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }}
        .main-tab:hover {{ color: #333; }}
        .main-tab.active {{ color: #333; border-bottom-color: #333; font-weight: 600; }}
        .sub-tabs {{ background: #faf9f7; border-bottom: 1px solid #e8e6e0; padding: 0 24px; display: flex; gap: 4px; overflow-x: auto; }}
        .sub-tab {{ padding: 8px 12px; font-size: 12px; color: #888; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }}
        .sub-tab:hover {{ color: #333; }}
        .sub-tab.active {{ color: #333; border-bottom-color: #555; font-weight: 600; }}
        .panel {{ display: none; }}
        .panel.active {{ display: block; }}
        .table-wrap {{ overflow-x: auto; }}
        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table thead th {{ background: #faf9f7; border-bottom: 1px solid #e8e6e0; padding: 10px 16px; font-size: 12px; font-weight: 600; color: #888; text-align: center; cursor: pointer; user-select: none; white-space: nowrap; }}
        .data-table thead th:first-child, .data-table thead th:nth-child(2) {{ text-align: left; }}
        .data-table thead th:hover {{ background: #f0ede6; color: #333; }}
        .data-table tbody tr {{ border-bottom: 1px solid #f0ede6; }}
        .data-table tbody tr:hover {{ background: #faf9f7; }}
        .data-table tbody td {{ padding: 12px 16px; vertical-align: middle; text-align: center; }}
        .data-table tbody td:first-child, .data-table tbody td:nth-child(2) {{ text-align: left; }}
        .row-success {{ background: #f0f7f0; }}
        .row-warning {{ background: #fffbf0; }}
        .row-danger  {{ background: #fff5f5; }}
        .code-badge {{ display: inline-block; border: 1px solid #e0ddd6; border-radius: 4px; padding: 2px 8px; font-size: 12px; color: #555; background: #faf9f7; }}
        .yutai-text {{ color: #888; font-size: 12px; }}
        .kenri-text {{ color: #aaa; font-size: 11px; }}
        .gyaku-val  {{ font-size: 12px; color: #888; }}
        .stock-val {{ font-weight: 600; color: #9b2335; }}
        .zero-val  {{ color: #ccc; }}
        .ok-val {{ color: #2d7a2d; font-weight: 600; font-size: 12px; }}
        .ng-val {{ color: #9b2335; font-size: 12px; }}
        .badge-days {{ display: inline-block; border-radius: 20px; padding: 1px 8px; font-size: 11px; margin-left: 4px; }}
        .badge-days.danger  {{ background: #fde8e8; color: #9b2335; }}
        .badge-days.warning {{ background: #fef3e0; color: #a06000; }}
        .badge-days.normal  {{ background: #f0ede6; color: #888; }}
        .tweet-box {{ background: #f7f6f2; border: 1px solid #e0ddd6; border-radius: 8px; padding: 16px; font-size: 13px; line-height: 1.8; white-space: pre-wrap; font-family: monospace; margin: 16px 24px; }}
        .copy-btn {{ margin: 0 24px 16px; border: 1px solid #e0ddd6; border-radius: 6px; padding: 8px 16px; font-size: 13px; cursor: pointer; background: #fff; color: #555; }}
        .copy-btn:hover {{ background: #f0ede6; }}
        .section-title {{ padding: 16px 24px 8px; font-size: 13px; font-weight: 600; color: #555; }}
        .year-tabs {{ background: #fff; border-bottom: 1px solid #e8e6e0; padding: 0 24px; display: flex; gap: 4px; }}
        .year-tab {{ padding: 10px 14px; font-size: 13px; color: #888; cursor: pointer; border-bottom: 2px solid transparent; white-space: nowrap; }}
        .year-tab:hover {{ color: #333; }}
        .year-tab.active {{ color: #333; border-bottom-color: #333; font-weight: 600; }}
        .container {{ max-width: 1300px; margin: 0 auto; background: #fff; min-height: 100vh; box-shadow: 0 0 40px rgba(0,0,0,0.06); }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎁 優待在庫ビューワー</h1>
        <span class="update-badge">更新: {update_time}</span>
    </div>

    <!-- メインタブ -->
    <div class="main-tabs">
        <div class="main-tab active" data-tab="zaiko">在庫状況</div>
        <div class="main-tab" data-tab="kokuzetsu">枯渇情報</div>
        <div class="main-tab" data-tab="tweet">ツイート原稿</div>
    </div>

    <!-- 在庫状況 -->
    <div id="zaiko" class="panel active">
        <div class="toolbar">
            <input type="text" id="search" class="search-input" placeholder="銘柄名・コードで検索...">
            <label class="toggle-label">
                <input type="checkbox" id="stockOnly" checked>在庫ありのみ
            </label>
        </div>
        <div class="sub-tabs" id="monthTabs"></div>
        <div class="table-wrap">
            <table class="data-table" id="stockTable">
                <thead><tr>
                    <th data-label="コード">コード</th>
                    <th data-label="銘柄名・優待">銘柄名・優待</th>
                    <th data-label="逆日歩">逆日歩</th>
                    <th data-label="日興">日興</th>
                    <th data-label="カブコム">カブコム</th>
                    <th data-label="楽天">楽天</th>
                    <th data-label="SBI">SBI</th>
                    <th data-label="GMO">GMO</th>
                    <th data-label="松井">松井</th>
                </tr></thead>
                <tbody id="stockTbody"></tbody>
            </table>
        </div>
    </div>

    <!-- 枯渇情報 -->
    <div id="kokuzetsu" class="panel">
        <div class="year-tabs" id="kokuzetsuYearTabs"></div>
        <div class="sub-tabs" id="kokuzetsuMonthTabs"></div>
        <div class="table-wrap">
            <table class="data-table">
                <thead><tr>
                    <th>コード</th><th>銘柄名</th>
                    <th>日興</th><th>カブコム</th><th>楽天</th><th>SBI</th><th>GMO</th><th>松井</th>
                </tr></thead>
                <tbody id="kokuzetsuTbody"></tbody>
            </table>
        </div>
    </div>

    <!-- ツイート原稿 -->
    <div id="tweet" class="panel">
        <div class="year-tabs" id="tweetYearTabs"></div>
        <div class="sub-tabs" id="tweetMonthTabs"></div>
        <div class="section-title">📋 ツイート原稿①：完全枯渇リスト（来年用）</div>
        <div class="tweet-box" id="tweet1"></div>
        <button class="copy-btn" onclick="copyText('tweet1')">コピー</button>
        <div class="section-title">📋 ツイート原稿②：まだ建てられる銘柄（リアルタイム）</div>
        <div class="tweet-box" id="tweet2"></div>
        <button class="copy-btn" onclick="copyText('tweet2')">コピー</button>
    </div>
</div>

<script>
const allData   = {data_json};
const kokuzetsu = {kokuzetsu_json};
const firms     = ['nvol','kvol','rvol','svol','gvol','mvol'];
const firmNames = {{'nvol':'日興','kvol':'カブコム','rvol':'楽天','svol':'SBI','gvol':'GMO','mvol':'松井'}};

let currentMonth  = {now.month};
let currentYear   = {now.year};
let currentKYear  = {now.year};
let currentKMonth = {now.month};
let currentTYear  = {now.year};
let currentTMonth = {now.month};
let sortCol = -1;
let sortAsc = true;

// 年一覧をkokuzetsuから取得
function getYears() {{
    const years = [...new Set(Object.values(kokuzetsu).map(v => v.kenri_year))].sort((a,b) => b-a);
    return years.length ? years : [{now.year}];
}}

// 月タブ生成
function buildMonthTabs(containerId, activeMonth, onClick) {{
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    for (let m = 1; m <= 12; m++) {{
        const a = document.createElement('a');
        a.className   = 'sub-tab' + (m === activeMonth ? ' active' : '');
        a.textContent = m + '月';
        a.addEventListener('click', () => {{
            container.querySelectorAll('.sub-tab').forEach(t => t.classList.remove('active'));
            a.classList.add('active');
            onClick(m);
        }});
        container.appendChild(a);
    }}
}}

// 年タブ生成
function buildYearTabs(containerId, activeYear, onClick) {{
    const container = document.getElementById(containerId);
    container.innerHTML = '';
    getYears().forEach(y => {{
        const a = document.createElement('a');
        a.className   = 'year-tab' + (y === activeYear ? ' active' : '');
        a.textContent = y + '年';
        a.addEventListener('click', () => {{
            container.querySelectorAll('.year-tab').forEach(t => t.classList.remove('active'));
            a.classList.add('active');
            onClick(y);
        }});
        container.appendChild(a);
    }});
}}

// 在庫状況タブ
buildMonthTabs('monthTabs', currentMonth, m => {{
    currentMonth = m;
    sortCol = -1; sortAsc = true;
    document.querySelectorAll('#stockTable thead th').forEach(t => t.textContent = t.dataset.label);
    renderStock();
}});

// 枯渇情報タブ
buildYearTabs('kokuzetsuYearTabs', currentKYear, y => {{
    currentKYear = y;
    buildMonthTabs('kokuzetsuMonthTabs', currentKMonth, m => {{ currentKMonth = m; renderKokuzetsu(); }});
    renderKokuzetsu();
}});
buildMonthTabs('kokuzetsuMonthTabs', currentKMonth, m => {{ currentKMonth = m; renderKokuzetsu(); }});

// ツイート原稿タブ
buildYearTabs('tweetYearTabs', currentTYear, y => {{
    currentTYear = y;
    buildMonthTabs('tweetMonthTabs', currentTMonth, m => {{ currentTMonth = m; renderTweet(); }});
    renderTweet();
}});
buildMonthTabs('tweetMonthTabs', currentTMonth, m => {{ currentTMonth = m; renderTweet(); }});

function gyakuClass(d) {{
    if (d >= 5) return 'row-danger';
    if (d >= 3) return 'row-warning';
    if (d >= 1) return 'row-success';
    return '';
}}

function daysUntil(kenri) {{
    if (!kenri) return '';
    try {{
        const now   = new Date();
        const parts = kenri.match(/(\d+)月(\d+)日/);
        if (!parts) return '';
        let target = new Date(now.getFullYear(), parseInt(parts[1])-1, parseInt(parts[2]));
        if (target < now) target.setFullYear(now.getFullYear()+1);
        const diff = Math.ceil((target - now) / 86400000);
        if (diff <= 7)  return `<span class="badge-days danger">あと${{diff}}日</span>`;
        if (diff <= 30) return `<span class="badge-days warning">あと${{diff}}日</span>`;
        return `<span class="badge-days normal">あと${{diff}}日</span>`;
    }} catch(e) {{ return ''; }}
}}

function renderStock() {{
    const q         = document.getElementById('search').value.toLowerCase();
    const stockOnly = document.getElementById('stockOnly').checked;
    let rows = allData.filter(r => r.month === currentMonth);
    if (sortCol >= 0) {{
        const keys = ['code','name','gyaku','nvol','kvol','rvol','svol','gvol','mvol'];
        const key  = keys[sortCol];
        rows.sort((a,b) => {{
            const av = typeof a[key]==='number' ? a[key] : 0;
            const bv = typeof b[key]==='number' ? b[key] : 0;
            return sortAsc ? av-bv : bv-av;
        }});
    }}
    const hasStock = r => firms.some(f => r[f] > 0);
    document.getElementById('stockTbody').innerHTML = rows.map(r => {{
        if (!(r.code+r.name+r.yutai).toLowerCase().includes(q)) return '';
        if (stockOnly && !hasStock(r)) return '';
        const vols = firms.map(f => r[f] > 0
            ? `<td><span class="stock-val">${{r[f].toLocaleString()}}</span></td>`
            : `<td><span class="zero-val">-</span></td>`).join('');
        return `<tr class="${{gyakuClass(r.gyaku)}}">
            <td><span class="code-badge">${{r.code}}</span></td>
            <td><strong>${{r.name}}</strong><br>
                <small class="yutai-text">${{r.yutai}}</small><br>
                <small class="kenri-text">権利日: ${{r.kenri}} ${{daysUntil(r.kenri)}}</small></td>
            <td><span class="gyaku-val">${{r.gyaku}}日</span></td>
            ${{vols}}</tr>`;
    }}).join('');
}}

function renderKokuzetsu() {{
    const stocks = allData.filter(r => r.month === currentKMonth);
    document.getElementById('kokuzetsuTbody').innerHTML = stocks.map(r => {{
        const key = `${{currentKYear}}_${{currentKMonth}}_${{r.code}}`;
        const k   = kokuzetsu[key] || {{}};
        const kf  = k.firms || {{}};
        const hasK = firms.some(f => kf[f]);
        if (!hasK) return '';
        const cells = firms.map(f => {{
            if (kf[f])    return `<td class="ng-val">~${{kf[f]}}</td>`;
            if (r[f] > 0) return `<td class="ok-val">✅在庫あり</td>`;
            return `<td class="zero-val">-</td>`;
        }}).join('');
        return `<tr>
            <td><span class="code-badge">${{r.code}}</span></td>
            <td><strong>${{r.name}}</strong></td>
            ${{cells}}</tr>`;
    }}).join('');
}}

function renderTweet() {{
    const stocks   = allData.filter(r => r.month === currentTMonth);
    const hasStock = r => firms.some(f => r[f] > 0);

    const dead = stocks.filter(r => {{
        const key = `${{currentTYear}}_${{currentTMonth}}_${{r.code}}`;
        const kf  = (kokuzetsu[key] || {{}}).firms || {{}};
        return !hasStock(r) && firms.some(f => kf[f]);
    }});
    let t1 = `◇ ${{currentTYear}}年${{currentTMonth}}月末権利【枯渇日】\n\n`;
    dead.forEach(r => {{
        const key  = `${{currentTYear}}_${{currentTMonth}}_${{r.code}}`;
        const kf   = (kokuzetsu[key] || {{}}).firms || {{}};
        const dates = firms.map(f => kf[f]).filter(Boolean).sort();
        t1 += `${{r.code}} ${{r.name}} ~${{dates[dates.length-1]}}\n`;
    }});
    document.getElementById('tweet1').textContent = t1 || '（まだデータがありません）';

    const partial = stocks.filter(r => {{
        const key = `${{currentTYear}}_${{currentTMonth}}_${{r.code}}`;
        const kf  = (kokuzetsu[key] || {{}}).firms || {{}};
        return hasStock(r) && firms.some(f => kf[f]);
    }});
    let t2 = `◇ ${{currentTYear}}年${{currentTMonth}}月末 まだ建てられる銘柄\n\n`;
    partial.forEach(r => {{
        const key    = `${{currentTYear}}_${{currentTMonth}}_${{r.code}}`;
        const kf     = (kokuzetsu[key] || {{}}).firms || {{}};
        const okList = firms.map((f,i) => r[f]>0 ? `✅${{firmNames[f]}}` : null).filter(Boolean);
        const ngList = firms.map((f,i) => kf[f]   ? `${{firmNames[f]}}~${{kf[f]}}` : null).filter(Boolean);
        t2 += `${{r.code}} ${{r.name}}\n${{okList.join(' ')}} ${{ngList.join(' ')}}\n\n`;
    }});
    document.getElementById('tweet2').textContent = t2 || '（まだデータがありません）';
}}

// 初期描画
renderStock();
renderKokuzetsu();
renderTweet();

// 検索・フィルター
document.getElementById('search').addEventListener('input', renderStock);
document.getElementById('stockOnly').addEventListener('change', renderStock);

// ソート
document.querySelectorAll('#stockTable thead th').forEach((th, colIndex) => {{
    th.addEventListener('click', () => {{
        sortAsc = (sortCol === colIndex) ? !sortAsc : false;
        sortCol = colIndex;
        document.querySelectorAll('#stockTable thead th').forEach(t => t.textContent = t.dataset.label);
        th.textContent = th.dataset.label + (sortAsc ? ' ▲' : ' ▼');
        renderStock();
    }});
}});

// メインタブ切り替え
document.querySelectorAll('.main-tab').forEach(tab => {{
    tab.addEventListener('click', () => {{
        document.querySelectorAll('.main-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(tab.dataset.tab).classList.add('active');
    }});
}});

function copyText(id) {{
    navigator.clipboard.writeText(document.getElementById(id).textContent)
        .then(() => alert('コピーしました！'));
}}
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
