import json, os, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
USER_ID = os.environ["THREADS_USER_ID"]
BASE_URL = f"https://graph.threads.net/v1.0/{USER_ID}/threads_publish"

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

    for post in data["posts"]:
        if post["status"] != "pending":
            continue

        scheduled = datetime.fromisoformat(post["scheduled_time"])
        if scheduled.tzinfo is None:
            scheduled = scheduled.replace(tzinfo=JST)

        diff_minutes = (now - scheduled).total_seconds() / 60

        if 0 <= diff_minutes <= 120:
            print(f"Publishing: {post['theme']} (container: {post['container_id']})")
            try:
                result = publish(post["container_id"])
                post["status"] = "published"
                post["post_id"] = result.get("id")
                print(f"  -> Success! post_id: {post['post_id']}")
            except Exception as e:
                print(f"  -> Error: {e}")
                post["status"] = "error"
                post["error"] = str(e)
            changed = True
        elif diff_minutes > 120:
            print(f"Expired: {post['theme']}")
            post["status"] = "expired"
            changed = True

    if changed:
        with open("scheduled_posts.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("scheduled_posts.json updated.")
    else:
        print("No posts to publish at this time.")

if __name__ == "__main__":
    main()
