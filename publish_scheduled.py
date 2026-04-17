import json, os, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
USER_ID = os.environ["THREADS_USER_ID"]
BASE_URL = f"https://graph.threads.net/v1.0/{USER_ID}/threads_publish"

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")


def line_notify(text: str):
    """LINE Messaging API でプッシュ通知。失敗しても処理は続行。"""
    if not (LINE_TOKEN and LINE_USER_ID):
        print("[LINE] skipped: token or user_id not set")
        return
    try:
        payload = json.dumps({
            "to": LINE_USER_ID,
            "messages": [{"type": "text", "text": text[:4500]}]
        }).encode()
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=payload, method="POST",
            headers={
                "Authorization": f"Bearer {LINE_TOKEN}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[LINE] notified ({resp.status})")
    except Exception as e:
        print(f"[LINE] error: {e}")


def publish(container_id):
    params = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": TOKEN
    }).encode()
    req = urllib.request.Request(BASE_URL, params, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    with open("scheduled_posts.json", encoding="utf-8") as f:
        data = json.load(f)

    now = datetime.now(timezone.utc)
    changed = False
    published_list = []
    expired_list = []
    error_list = []

    for post in data["posts"]:
        if post["status"] != "pending":
            continue

        scheduled = datetime.fromisoformat(post["scheduled_time"])
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=JST)

        diff_minutes = (now - scheduled).total_seconds() / 60
        scheduled_jst_str = scheduled.astimezone(JST).strftime("%m/%d %H:%M")
        theme = post.get("theme", "(no theme)")

        if 0 <= diff_minutes <= 120:
            print(f"Publishing: {theme} (container: {post['container_id']})")
            try:
                result = publish(post["container_id"])
                post["status"] = "published"
                post["post_id"] = result.get("id")
                print(f"  -> Success! post_id: {post['post_id']}")
                published_list.append((scheduled_jst_str, theme, post["post_id"]))
            except Exception as e:
                print(f"  -> Error: {e}")
                post["status"] = "error"
                post["error"] = str(e)
                error_list.append((scheduled_jst_str, theme, str(e)))
            changed = True
        elif diff_minutes > 120:
            print(f"Expired: {theme}")
            post["status"] = "expired"
            expired_list.append((scheduled_jst_str, theme))
            changed = True

    if changed:
        with open("scheduled_posts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("scheduled_posts.json updated.")
    else:
        print("No posts to publish at this time.")

    # ---- LINE通知 ----
    messages = []
    if published_list:
        lines = ["✅ 投稿完了 ({}本)".format(len(published_list))]
        for t, theme, pid in published_list:
            lines.append(f"・{t} {theme}")
        messages.append("\n".join(lines))
    if expired_list:
        lines = ["⚠️ expired ({}本)".format(len(expired_list))]
        for t, theme in expired_list:
            lines.append(f"・{t} {theme}")
        lines.append("\n※ 予定時刻から2時間以上経過したため破棄されました")
        messages.append("\n".join(lines))
    if error_list:
        lines = ["❌ エラー ({}本)".format(len(error_list))]
        for t, theme, err in error_list:
            lines.append(f"・{t} {theme}\n  {err[:200]}")
        messages.append("\n".join(lines))

    if messages:
        line_notify("\n\n".join(messages))


if __name__ == "__main__":
    main()
