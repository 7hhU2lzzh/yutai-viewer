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

LOGIN_PHP = '''<?php
session_start();
if (isset($_SESSION['user'])) { header('Location: index.php'); exit; }
$error = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $id = trim($_POST['id'] ?? '');
    $pass = $_POST['pass'] ?? '';
    $users = json_decode(file_get_contents(__DIR__ . '/users.json'), true) ?? [];
    if (isset($users[$id]) && password_verify($pass, $users[$id]['password'])) {
        $u = $users[$id];
        if ($u['role'] !== 'admin' && !empty($u['expires'])) {
            $exp = new DateTime($u['expires']);
            if (new DateTime() > $exp) { $error = '閲覧期限が切れています。'; goto show; }
        }
        $_SESSION['user'] = $id;
        $_SESSION['role'] = $u['role'];
        header('Location: index.php'); exit;
    }
    $error = 'IDまたはパスワードが違います';
}
show:
?><!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ログイン</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f7f6f2;font-family:-apple-system,sans-serif;font-size:14px;color:#333;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border:1px solid #e8e6e0;border-radius:12px;padding:40px;width:100%;max-width:360px}
h1{font-size:20px;font-weight:600;margin-bottom:8px}
.sub{font-size:13px;color:#888;margin-bottom:24px}
.fg{margin-bottom:16px}
label{font-size:12px;font-weight:600;color:#555;margin-bottom:6px;display:block}
input{width:100%;border:1px solid #e0ddd6;border-radius:6px;padding:10px 12px;font-size:14px;outline:none}
input:focus{border-color:#aaa}
.btn{width:100%;background:#333;color:#fff;border:none;border-radius:6px;padding:12px;font-size:14px;font-weight:600;cursor:pointer}
.btn:hover{background:#555}
.error{color:#9b2335;font-size:12px;margin-top:12px}
</style></head>
<body><div class="card">
<h1>🎁 優待在庫ビューワー</h1>
<p class="sub">ログインしてください</p>
<form method="POST">
<div class="fg"><label>ユーザーID</label><input type="text" name="id" autofocus></div>
<div class="fg"><label>パスワード</label><input type="password" name="pass"></div>
<button type="submit" class="btn">ログイン</button>
<?php if($error): ?><p class="error"><?=htmlspecialchars($error)?></p><?php endif; ?>
</form></div></body></html>
'''

LOGOUT_PHP = '''<?php
session_start();
session_destroy();
header('Location: login.php');
exit;
'''

ADMIN_PHP = '''<?php
session_start();
if (!isset($_SESSION['user']) || $_SESSION['role'] !== 'admin') { header('Location: login.php'); exit; }
$users_file = __DIR__ . '/users.json';
$users = json_decode(file_get_contents($users_file), true) ?? [];
$message = '';
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? '';
    if ($action === 'add') {
        $id = trim($_POST['new_id'] ?? '');
        $pass = $_POST['new_pass'] ?? '';
        $role = $_POST['new_role'] ?? 'user';
        $expires = $_POST['expires'] ?? '';
        if ($id && $pass) {
            $users[$id] = ['password'=>password_hash($pass,PASSWORD_DEFAULT),'role'=>$role,'expires'=>$expires?:null];
            file_put_contents($users_file, json_encode($users, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
            $message = "✅ ユーザー「{$id}」を追加しました";
        }
    }
    if ($action === 'delete') {
        $did = $_POST['del_id'] ?? '';
        if ($did && $did !== $_SESSION['user']) {
            unset($users[$did]);
            file_put_contents($users_file, json_encode($users, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
            $message = "🗑️ 削除しました";
        }
    }
    if ($action === 'update_expires') {
        $uid = $_POST['upd_id'] ?? '';
        $expires = $_POST['expires'] ?? '';
        if ($uid && isset($users[$uid])) {
            $users[$uid]['expires'] = $expires ?: null;
            file_put_contents($users_file, json_encode($users, JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE));
            $message = "✅ 期限を更新しました";
        }
    }
}
$now = new DateTime();
?><!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ユーザー管理</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#f7f6f2;font-family:-apple-system,sans-serif;font-size:14px;color:#333}
.header{background:#fff;border-bottom:1px solid #e8e6e0;padding:16px 24px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:16px;font-weight:600}
.btn-sm{border:1px solid #e0ddd6;border-radius:6px;padding:6px 12px;font-size:12px;cursor:pointer;background:#fff;color:#555;text-decoration:none;display:inline-block;margin-left:8px}
.body{max-width:900px;margin:24px auto;padding:0 24px}
.msg{background:#f0f7f0;border:1px solid #c0e0c0;border-radius:6px;padding:10px 16px;margin-bottom:16px;font-size:13px}
.card{background:#fff;border:1px solid #e8e6e0;border-radius:8px;padding:24px;margin-bottom:24px}
.card h2{font-size:14px;font-weight:600;margin-bottom:16px;color:#555}
.form-row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.fg{display:flex;flex-direction:column;gap:4px}
label{font-size:12px;font-weight:600;color:#555}
input,select{border:1px solid #e0ddd6;border-radius:6px;padding:8px 12px;font-size:13px;outline:none}
.btn-add{background:#333;color:#fff;border:none;border-radius:6px;padding:9px 16px;font-size:13px;cursor:pointer}
.btn-danger{background:#fff;color:#9b2335;border:1px solid #f0c0c0;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer}
table{width:100%;border-collapse:collapse}
th{background:#faf9f7;border-bottom:1px solid #e8e6e0;padding:8px 12px;font-size:12px;font-weight:600;color:#888;text-align:left}
td{padding:10px 12px;border-bottom:1px solid #f0ede6;font-size:13px}
.ra{background:#333;color:#fff;border-radius:4px;padding:2px 8px;font-size:11px}
.ru{background:#f0ede6;color:#555;border-radius:4px;padding:2px 8px;font-size:11px}
.expired{color:#9b2335}
.valid{color:#2d7a2d}
</style></head>
<body>
<div class="header"><h1>⚙️ ユーザー管理</h1>
<div><a href="index.php" class="btn-sm">ビューワーへ</a><a href="logout.php" class="btn-sm">ログアウト</a></div></div>
<div class="body">
<div class="card" style="background:#fafaf8;border:1px solid #e8e6e0;border-radius:8px;padding:20px;margin-bottom:24px">
<h2 style="font-size:13px;font-weight:600;color:#555;margin-bottom:14px">🔗 管理リンク集</h2>
<table style="width:100%;border-collapse:collapse;font-size:13px">
<tr style="border-bottom:1px solid #f0ede6">
  <td style="padding:8px 12px;color:#888;white-space:nowrap;width:140px">GitHub</td>
  <td style="padding:8px 12px"><a href="https://github.com/7hhU2lzzh/yutai-viewer" target="_blank" style="color:#333">https://github.com/7hhU2lzzh/yutai-viewer</a></td>
</tr>
<tr style="border-bottom:1px solid #f0ede6">
  <td style="padding:8px 12px;color:#888">GAS: taisyaku監視</td>
  <td style="padding:8px 12px"><a href="https://script.google.com/home/projects/1INi7jnp4vD3pbu89oJ7Avr9WuV8EM0RMVCkgfk_ibo_XtIJb81tTfO6q/edit" target="_blank" style="color:#333">開く</a><span style="color:#aaa;font-size:12px;margin-left:8px">machspeeddesigners@gmail.com</span></td>
</tr>
<tr style="border-bottom:1px solid #f0ede6">
  <td style="padding:8px 12px;color:#888">GAS: 適時開示新着</td>
  <td style="padding:8px 12px"><a href="https://script.google.com/home/projects/1cG-mi_kKjt47rY7YTZQkoLKPXqesUVZFjopGPWJhR8QhHSQX-S8-aLuz/edit" target="_blank" style="color:#333">開く</a><span style="color:#aaa;font-size:12px;margin-left:8px">machspeeddesigners@gmail.com</span></td>
</tr>
<tr style="border-bottom:1px solid #f0ede6">
  <td style="padding:8px 12px;color:#888">Claude Console</td>
  <td style="padding:8px 12px"><a href="https://console.anthropic.com" target="_blank" style="color:#333">https://console.anthropic.com</a><span style="color:#aaa;font-size:12px;margin-left:8px">ttkzo.ngta@gmail.com</span></td>
</tr>
</table>
</div>
<div class="card" style="background:#fafaf8;border:1px solid #e8e6e0;border-radius:8px;padding:20px;margin-bottom:24px">
<h2 style="font-size:13px;font-weight:600;color:#555;margin-bottom:14px">📝 作業メモ（重要）</h2>
<ul style="font-size:13px;color:#555;line-height:2;padding-left:20px">
  <li><code>index.php</code> は手動FTPアップ（スクレイパーは触らない）</li>
  <li><code>hashi_data.json</code> はスクレイパーが絶対に上書きしない設計</li>
  <li>端の編集権限は管理者のみ（一般ユーザーは表示のみ）</li>
  <li>初期パスワードは <code>password</code> → ログイン後すぐ変更推奨</li>
  <li>GitHub Actionsが <code>hashi_api.php</code> を自動FTP転送する</li>
  <li><code>users.json</code> / <code>hashi_data.json</code> はサーバー上で保護（.htaccess）</li>
</ul>
</div>
<?php if($message): ?><div class="msg"><?=htmlspecialchars($message)?></div><?php endif; ?>
<div class="card"><h2>＋ ユーザー追加</h2>
<form method="POST"><input type="hidden" name="action" value="add">
<div class="form-row">
<div class="fg"><label>ID</label><input type="text" name="new_id" required></div>
<div class="fg"><label>パスワード</label><input type="password" name="new_pass" required></div>
<div class="fg"><label>権限</label><select name="new_role"><option value="user">一般</option><option value="admin">管理者</option></select></div>
<div class="fg"><label>閲覧期限</label><input type="date" name="expires"></div>
<div class="fg"><label>&nbsp;</label><button type="submit" class="btn-add">追加</button></div>
</div></form></div>
<div class="card"><h2>ユーザー一覧</h2>
<table><thead><tr><th>ID</th><th>権限</th><th>閲覧期限</th><th>期限変更</th><th>操作</th></tr></thead>
<tbody>
<?php foreach($users as $uid=>$u): ?>
<?php $exp_dt = (!empty($u['expires'])) ? new DateTime($u['expires']) : null; $expired = $exp_dt && $now > $exp_dt; ?>
<tr>
<td><strong><?=htmlspecialchars($uid)?></strong></td>
<td><?=$u['role']==='admin'?'<span class="ra">管理者</span>':'<span class="ru">一般</span>'?></td>
<td><?php if(!$exp_dt): ?><span style="color:#aaa">無期限</span>
<?php elseif($expired): ?><span class="expired">⚠️ <?=htmlspecialchars($u['expires'])?> 期限切れ</span>
<?php else: ?><span class="valid"><?=htmlspecialchars($u['expires'])?></span><?php endif; ?></td>
<td><?php if($u['role']!=='admin'): ?>
<form method="POST" style="display:flex;gap:8px;align-items:center;">
<input type="hidden" name="action" value="update_expires">
<input type="hidden" name="upd_id" value="<?=htmlspecialchars($uid)?>">
<input type="date" name="expires" value="<?=htmlspecialchars($u['expires']??'')?>" style="padding:4px 8px;font-size:12px">
<button type="submit" class="btn-sm">更新</button></form>
<?php else: ?><span style="color:#aaa">-</span><?php endif; ?></td>
<td><?php if($uid!==$_SESSION['user']): ?>
<form method="POST" onsubmit="return confirm('削除しますか？')">
<input type="hidden" name="action" value="delete">
<input type="hidden" name="del_id" value="<?=htmlspecialchars($uid)?>">
<button type="submit" class="btn-danger">削除</button></form>
<?php else: ?><span style="color:#aaa">-</span><?php endif; ?></td>
</tr><?php endforeach; ?>
</tbody></table></div></div></body></html>
'''

# hashi_api.php: 端データをサーバー保存するAPI（hashi_data.jsonは上書きしない）
HASHI_API_PHP = '''<?php
session_start();
if (!isset($_SESSION['user'])) { http_response_code(401); exit; }

$file = __DIR__ . '/hashi_data.json';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit; }

$body = json_decode(file_get_contents('php://input'), true);
$key  = preg_replace('/[^a-zA-Z0-9_\\-]/', '', $body['key'] ?? '');
$val  = $body['value'] ?? '';

$allowed = ['', '端のみ', '端+空', '本+端+本', '本+端+空+本', '不明(調査中)'];
if (!$key || !in_array($val, $allowed, true)) { http_response_code(400); exit; }

$data = [];
if (file_exists($file)) {
    $data = json_decode(file_get_contents($file), true) ?? [];
}
if ($val === '') {
    unset($data[$key]);
} else {
    $data[$key] = $val;
}
file_put_contents($file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
header('Content-Type: application/json');
echo json_encode(['ok' => true]);
'''


def clean(val):
    """APIが文字列"null"を返すケースを空文字に変換する"""
    if val is None:
        return ""
    s = str(val).strip()
    return "" if s.lower() == "null" else s


def strip_company_type(name: str) -> str:
    """株式会社・有限会社などの法人格表記を除去する"""
    import re
    # 前後のスペース系も含めて除去
    patterns = [
        r'株式会社',
        r'有限会社',
        r'合同会社',
        r'合資会社',
        r'合名会社',
        r'（株）',
        r'\(株\)',
        r'㈱',
        r'（有）',
        r'\(有\)',
        r'㈲',
        r'（合）',
        r'\(合\)',
    ]
    for p in patterns:
        name = re.sub(r'\s*' + p + r'\s*', '', name)
    return name.strip()


def fetch_name_from_yahoo(code: str) -> str:
    """Yahoo!ファイナンスから銘柄名を取得する（nullの場合のフォールバック）"""
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

        # og:title から「社名（コード）」を取得
        import re
        m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
        if m:
            raw = m.group(1)
            # 「北浜キャピタル&コンサルティング(2134)」→ 社名だけ
            n = re.match(r'^(.+?)[\s　]*[\(（][0-9]{4}[\)）]', raw)
            name = n.group(1).strip() if n else raw.strip()
            return strip_company_type(name)

        # title タグからフォールバック
        m2 = re.search(r'<title>\s*(.+?)[\s　（(【]', html)
        if m2:
            return strip_company_type(m2.group(1).strip())

    except Exception as e:
        print(f"    Yahoo!取得失敗 {code}: {e}")
    return ""


def main():
    now          = datetime.now(JST)
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
                        name = clean(r.get("name"))
                        code = r.get("code", "")

                        # nameが空ならYahoo!ファイナンスから取得
                        if not name and code:
                            print(f"    ⚠️ name=null: {code} → Yahoo!から取得中...")
                            name = fetch_name_from_yahoo(code)
                            if name:
                                print(f"    ✅ 取得成功: {code} → {name}")
                            else:
                                print(f"    ❌ 取得失敗: {code} → 空のまま")
                            time.sleep(1)  # Yahoo!への連続アクセス対策

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

    if not all_data:
        print("データなし")
        return

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

    # --- stock_data.json を生成 ---
    stock_data = {
        "update_time": update_time,
        "data": all_data
    }
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(stock_data, f, ensure_ascii=False)

    with open("kokuzetsu_data.json", "w", encoding="utf-8") as f:
        json.dump(kokuzetsu, f, ensure_ascii=False)

    # .htaccess: 機密ファイルへの直接アクセスを禁止
    htaccess = """# 機密ファイルへの直接アクセス禁止
<Files "users.json">
    Deny from all
</Files>
<Files "prev.json">
    Deny from all
</Files>
<Files "kokuzetsu.json">
    Deny from all
</Files>
<Files "hashi_data.json">
    Deny from all
</Files>
"""

    # --- FTP転送 ---
    print("📡 FTP転送中...")
    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS) as ftp:
            ftp.cwd(FTP_DIR)

            # PHPファイル
            ftp.storbinary("STOR login.php",     BytesIO(LOGIN_PHP.encode('utf-8')))
            ftp.storbinary("STOR logout.php",    BytesIO(LOGOUT_PHP.encode('utf-8')))
            ftp.storbinary("STOR admin.php",     BytesIO(ADMIN_PHP.encode('utf-8')))
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
