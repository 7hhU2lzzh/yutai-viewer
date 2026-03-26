import re
import requests
import time
import os
import ftplib
import json
from io import BytesIO
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))

# --- 設定 ---
FTP_HOST   = os.getenv("FTP_HOST")
FTP_USER   = os.getenv("FTP_USER")
FTP_PASS   = os.getenv("FTP_PASS")
FTP_DIR    = "www"

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

FIRMS      = ['nvol', 'kvol', 'rvol', 'svol', 'gvol', 'mvol']
FIRM_NAMES = {'nvol':'日興', 'kvol':'カブコム', 'rvol':'楽天', 'svol':'SBI', 'gvol':'GMO', 'mvol':'松井'}

# hashi_api.php: 端データをサーバー保存するAPI（hashi_data.jsonは上書きしない）
HASHI_API_PHP = '''<?php
session_start();
if (!isset($_SESSION['user'])) { http_response_code(401); exit; }
if ($_SESSION['role'] !== 'admin') { http_response_code(403); exit; }

$file = __DIR__ . '/hashi_data.json';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit; }

header('Content-Type: application/json; charset=utf-8');

// $_POST を優先（FormData送信の場合）、なければJSON bodyを読む
if (!empty($_POST)) {
    $body = $_POST;
} else {
    $raw  = file_get_contents('php://input');
    $body = json_decode($raw, true) ?? [];
}

$key = preg_replace('/[^a-zA-Z0-9_\\-]/', '', $body['key'] ?? '');
$val = $body['value'] ?? '';

// キーが空、または値が長すぎる場合のみ拒否（自由入力対応のため許可リスト廃止）
if (!$key || mb_strlen($val, 'UTF-8') > 50) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'invalid_param', 'key' => $key]);
    exit;
}

$data = [];
if (file_exists($file)) {
    $data = json_decode(file_get_contents($file), true) ?? [];
}

if ($val === '') {
    unset($data[$key]);
} else {
    $data[$key] = $val;
}

$result = file_put_contents($file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
if ($result === false) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'write_failed']);
    exit;
}

echo json_encode(['ok' => true]);
'''


def clean(val):
    """APIがNoneや文字列"null"を返すケースを空文字に変換する"""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() == "null" else s


def strip_company_type(name: str) -> str:
    """株式会社・有限会社などの法人格表記を除去する"""
    patterns = [
        r'株式会社', r'有限会社', r'合同会社', r'合資会社', r'合名会社',
        r'（株）', r'\(株\)', r'㈱',
        r'（有）', r'\(有\)', r'㈲',
        r'（合）', r'\(合\)',
    ]
    for p in patterns:
        name = re.sub(r'\s*' + p + r'\s*', '', name)
    return name.strip()


def fetch_name_from_yahoo(code: str) -> str:
    """Yahoo!ファイナンスから銘柄名を取得する（nameがnullの場合のフォールバック）"""
    try:
        url = f"https://finance.yahoo.co.jp/quote/{code}.T"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ja,en;q=0.9",
        }
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return ""
        html = res.text

        # og:titleから「社名（コード）」を取得
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if m:
            raw = m.group(1)
            n = re.match(r'^(.+?)[\s　]*[\(（][0-9]{4}[\)）]', raw)
            name = n.group(1).strip() if n else raw.strip()
            return strip_company_type(name)

        # titleタグからフォールバック
        m2 = re.search(r'<title>\s*(.+?)[\s　（(【]', html)
        if m2:
            return strip_company_type(m2.group(1).strip())

    except Exception as e:
        print(f"    Yahoo!取得失敗 {code}: {e}")
    return ""


def is_night_snapshot_time(now: datetime) -> bool:
    """現在時刻が23:00〜23:10 JSTかどうか判定"""
    return now.hour == 23 and now.minute <= 10


def load_night_snapshot() -> dict:
    """night_snapshot.json を読み込む（銘柄ごとの夜23時データ）"""
    if os.path.exists("night_snapshot.json"):
        with open("night_snapshot.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_night_snapshot(snapshot: dict):
    """night_snapshot.json を保存"""
    with open("night_snapshot.json", "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def main():
    now          = datetime.now(JST)
    today_str    = now.strftime('%Y/%m/%d')
    update_time  = now.strftime('%Y-%m-%d %H:%M')
    current_year = now.year

    # --- 夜23時スナップショット判定 ---
    is_night = is_night_snapshot_time(now)
    if is_night:
        print("🌙 夜23時スナップショットモード")

    # --- prev.json と kokuzetsu.json を読む ---
    prev_data = {}
    if os.path.exists("prev.json"):
        with open("prev.json", "r", encoding="utf-8") as f:
            prev_data = json.load(f)

    kokuzetsu = {}
    if os.path.exists("kokuzetsu.json"):
        with open("kokuzetsu.json", "r", encoding="utf-8") as f:
            kokuzetsu = json.load(f)

    # --- night_snapshot.json を読む ---
    night_snapshot = load_night_snapshot()

    # --- name_cache.json を読む（一度取得した社名はキャッシュ済み） ---
    name_cache = {}
    if os.path.exists("name_cache.json"):
        with open("name_cache.json", "r", encoding="utf-8") as f:
            name_cache = json.load(f)
        name_cache_updated = False
    else:
        # 初回：空ファイルを作成しておく（git addで存在しないエラーを防ぐ）
        with open("name_cache.json", "w", encoding="utf-8") as f:
            json.dump({}, f)
        name_cache_updated = True  # 初回作成もコミット対象に

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
                        code = r.get("code", "")
                        name = clean(r.get("name"))

                        # nameが空の場合：キャッシュ確認→なければYahoo!取得
                        if not name and code:
                            if code in name_cache:
                                name = name_cache[code]
                                print(f"    📦 キャッシュ使用: {code} → {name}")
                            else:
                                print(f"    ⚠️ name=null: {code} → Yahoo!から取得中...")
                                name = fetch_name_from_yahoo(code)
                                if name:
                                    print(f"    ✅ 取得成功: {code} → {name}")
                                    name_cache[code] = name
                                    name_cache_updated = True
                                else:
                                    print(f"    ❌ 取得失敗: {code} → 空のまま（キャッシュに記録）")
                                    name_cache[code] = ""  # 次回以降Yahoo!を叩かない
                                    name_cache_updated = True
                                time.sleep(1)

                        all_data.append({
                            "month": month,
                            "code":  code,
                            "name":  name,
                            "yutai": clean(r.get("yutai")),
                            "gyaku": int(r.get("gyaku_days", 0) or 0),
                            "kenri": clean(r.get("d_kenri")),
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

    # --- name_cache.json を更新（新規取得があった場合のみ） ---
    if name_cache_updated:
        with open("name_cache.json", "w", encoding="utf-8") as f:
            json.dump(name_cache, f, ensure_ascii=False, indent=2)
        print(f"📦 name_cache.json 更新完了（{len(name_cache)}件）")

    if not all_data:
        print("データなし")
        return

    # --- 夜23時スナップショット更新 ---
    if is_night:
        print("🌙 夜23時スナップショット保存中...")
        snapshot_date = now.strftime('%Y-%m-%d')
        snapshot_time = now.strftime('%H:%M')
        for r in all_data:
            snap_key = f"{r['month']}_{r['code']}"
            night_snapshot[snap_key] = {
                "date": snapshot_date,
                "time": snapshot_time,
                "nvol": r["nvol"],
                "kvol": r["kvol"],
                "rvol": r["rvol"],
                "svol": r["svol"],
                "gvol": r["gvol"],
                "mvol": r["mvol"],
            }
        save_night_snapshot(night_snapshot)
        print(f"🌙 night_snapshot.json 更新完了（{len(night_snapshot)}件）")

    # --- 枯渇検出 ---
    print("🔍 枯渇検出中...")
    for r in all_data:
        code  = r["code"]
        month = r["month"]
        key   = f"{current_year}_{month}_{code}"
        prev  = prev_data.get(f"{month}_{code}", {})

        if key not in kokuzetsu:
            kokuzetsu[key] = {
                "code":        code,
                "name":        r["name"],
                "kenri_year":  current_year,
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

    # --- users.json が存在しなければ初期ファイルを作成 ---
    if not os.path.exists("users.json"):
        initial_users = {
            "admin": {
                "password": "$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi",
                "role": "admin",
                "expires": None
            }
        }
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(initial_users, f, ensure_ascii=False, indent=2)

    # --- stock_data.json を生成（night_snapshot_latest を埋め込む） ---
    for r in all_data:
        snap_key = f"{r['month']}_{r['code']}"
        if snap_key in night_snapshot:
            r["night_snapshot_latest"] = night_snapshot[snap_key]

    stock_data = {
        "update_time": update_time,
        "data": all_data
    }
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(stock_data, f, ensure_ascii=False)

    with open("kokuzetsu_data.json", "w", encoding="utf-8") as f:
        json.dump(kokuzetsu, f, ensure_ascii=False)

    # .htaccess
    htaccess = """# users.json / prev.json / kokuzetsu.json は直接アクセス禁止
<Files "users.json">
    <IfVersion < 2.4>
        Deny from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all denied
    </IfVersion>
</Files>
<Files "prev.json">
    <IfVersion < 2.4>
        Deny from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all denied
    </IfVersion>
</Files>
<Files "kokuzetsu.json">
    <IfVersion < 2.4>
        Deny from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all denied
    </IfVersion>
</Files>
# stock_data.json / kokuzetsu_data.json / hashi_data.json はJSから読むため許可
<Files "stock_data.json">
    <IfVersion < 2.4>
        Allow from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all granted
    </IfVersion>
</Files>
<Files "kokuzetsu_data.json">
    <IfVersion < 2.4>
        Allow from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all granted
    </IfVersion>
</Files>
<Files "hashi_data.json">
    <IfVersion < 2.4>
        Allow from all
    </IfVersion>
    <IfVersion >= 2.4>
        Require all granted
    </IfVersion>
</Files>
"""

    # --- FTP転送 ---
    print("📡 FTP転送中...")
    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)

            # PHPファイル
            ftp.storbinary("STOR hashi_api.php", BytesIO(HASHI_API_PHP.encode('utf-8')))

            # データJSON
            ftp.storbinary("STOR stock_data.json",     BytesIO(json.dumps(stock_data, ensure_ascii=False).encode('utf-8')))
            ftp.storbinary("STOR kokuzetsu_data.json",  BytesIO(json.dumps(kokuzetsu, ensure_ascii=False).encode('utf-8')))

            # users.json は既存なら上書きしない
            try:
                ftp.size("users.json")
                print("  users.json は既存のためスキップ")
            except Exception:
                with open("users.json", "rb") as f:
                    ftp.storbinary("STOR users.json", f)
                print("  users.json を初期作成")

            # hashi_data.json は既存なら上書きしない（端データを守る）
            try:
                ftp.size("hashi_data.json")
                print("  hashi_data.json は既存のためスキップ")
            except Exception:
                ftp.storbinary("STOR hashi_data.json", BytesIO(b'{}'))
                print("  hashi_data.json を初期作成")

            # .htaccess
            ftp.storbinary("STOR .htaccess", BytesIO(htaccess.encode('utf-8')))

            print("✅ 完了！")
    except Exception as e:
        print(f"❌ FTPエラー: {e}")


if __name__ == "__main__":
    main()
