# SAFETY POLICY:
# GitHub ActionsからFTPするのは自動生成データJSONだけ。
# .htaccess / PHP / users.json / hashi_data.json など、
# サーバー設定・アプリ本体・手入力データは一切変更しない。
#
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


    # --- stock_data.json を生成 ---
    stock_data = {
        "update_time": update_time,
        "data": all_data
    }
    with open("stock_data.json", "w", encoding="utf-8") as f:
        json.dump(stock_data, f, ensure_ascii=False)

    with open("kokuzetsu_data.json", "w", encoding="utf-8") as f:
        json.dump(kokuzetsu, f, ensure_ascii=False)

    # --- FTP転送（データJSONのみ） ---
    # 重要:
    #   PHP / .htaccess / users.json / hashi_data.json は絶対にアップロードしない。
    #   自動処理がサーバー設定やアプリ本体を上書きしないよう、許可リスト方式にする。
    print("📡 FTP転送中（データのみ）...")

    if not FTP_HOST or not FTP_USER or not FTP_PASS:
        raise RuntimeError("FTP_HOST / FTP_USER / FTP_PASS が設定されていません")

    uploads = {
        "stock_data.json": stock_data,
        "kokuzetsu_data.json": kokuzetsu,
    }

    # 将来コードを変更したときも、ここに明示したJSON以外は送信させない
    allowed_remote_files = {
        "stock_data.json",
        "kokuzetsu_data.json",
    }

    try:
        with ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS, timeout=30) as ftp:
            ftp.cwd(FTP_DIR)

            for remote_name, data in uploads.items():
                if remote_name not in allowed_remote_files:
                    raise RuntimeError(f"許可されていないFTP送信を拒否: {remote_name}")

                payload = json.dumps(
                    data,
                    ensure_ascii=False,
                    separators=(",", ":")
                ).encode("utf-8")

                ftp.storbinary(
                    f"STOR {remote_name}",
                    BytesIO(payload)
                )
                print(f"  ✅ {remote_name} ({len(payload)} bytes)")

            print("✅ FTP転送完了（データJSONのみ）")

    except Exception as e:
        print(f"❌ FTPエラー: {e}")
        raise



if __name__ == "__main__":
    main()
