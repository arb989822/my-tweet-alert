from flask import Flask, request, render_template_string
import tweepy
import requests
import threading
import time
import os

app = Flask(__name__)

# ========== 配置 ==========
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAB5g5AEAAAAAa9H9o5gOs7Qjea5ool6%2B2wwJREo%3DHqu1al01I2n9g0kUajHUG4FjDv6rBhyYQpW9zw1oecaFGd9aRI"  # ← 替换你的 X API Bearer Token
BARK_URL = ""  # iOS Bark: https://api.day.app/你的key
PUSHOVER_USER = ""  # Android Pushover: 你的 User Key
PUSHOVER_TOKEN = ""  # Android Pushover: 你的 API Token

# 监控列表文件
USERS_FILE = "users.txt"
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        f.write("xfourbnb\n")  # 默认监控 @xfourbnb

# =========================

client = tweepy.Client(bearer_token=BEARER_TOKEN)
user_ids = {}
last_ids = {}

def load_users():
    if not os.path.exists(USERS_FILE):
        return ["xfourbnb"]
    with open(USERS_FILE, "r") as f:
        return [line.strip().lstrip('@') for line in f if line.strip()]

def save_user(username):
    with open(USERS_FILE, "a") as f:
        f.write(username.lstrip('@') + "\n")

def send_alert(username, text):
    title = f"🚨 @{username} 发推了！"
    msg = text.replace("\n", " ").replace("\r", " ")
    if BARK_URL:
        # iOS Bark
        url = f"{BARK_URL}/{title}/{msg}?sound=alarm&level=10&group=TweetAlert&icon=https://abs.twimg.com/responsive/twitter-bird-dark-bgs.png"
        try:
            requests.get(url, timeout=5)
        except Exception as e:
            print(f"Bark 推送失败: {e}")
    if PUSHOVER_USER and PUSHOVER_TOKEN:
        # Android Pushover
        data = {
            "token": PUSHOVER_TOKEN,
            "user": PUSHOVER_USER,
            "title": title,
            "message": msg,
            "sound": "siren",
            "priority": 2,
            "retry": 30,
            "expire": 300,
            "url": "https://twitter.com/" + username,
            "attachment": "https://abs.twimg.com/responsive/twitter-bird-dark-bgs.png"
        }
        try:
            requests.post("https://api.pushover.net/1/messages.json", data=data, timeout=5)
        except Exception as e:
            print(f"Pushover 推送失败: {e}")

def monitor():
    global user_ids, last_ids
    users = load_users()
    for username in users:
        try:
            user = client.get_user(username=username)
            user_ids[username] = user.data.id
            last_ids[username] = None
            print(f"已添加监控: @{username}")
        except Exception as e:
            print(f"添加 @{username} 失败: {e}")

    while True:
        try:
            for username in list(user_ids.keys()):
                uid = user_ids.get(username)
                if not uid: continue
                tweets = client.get_users_tweets(
                    uid,
                    max_results=5,
                    tweet_fields=["created_at"],
                    exclude=["retweets", "replies"],
                    since_id=last_ids.get(username)
                )
                if tweets.data:
                    for tweet in reversed(tweets.data):
                        if last_ids[username] is None or tweet.id > last_ids.get(username, 0):
                            send_alert(username, tweet.text)
                            print(f"[{time.strftime('%H:%M:%S')}] 推送: @{username} - {tweet.text[:50]}...")
                    last_ids[username] = tweets.data[0].id
        except Exception as e:
            print(f"监控错误: {e}")
        time.sleep(3)  # 每 3 秒检查一次

# 启动监控线程
threading.Thread(target=monitor, daemon=True).start()
print("🚨 推特实时警报系统启动...")

# 网页面板 HTML 模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>推特实时警报系统</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f0f0f0; }
        .container { max-width: 600px; background: white; padding: 20px; border-radius: 10px; }
        input { padding: 10px; width: 200px; }
        button { padding: 10px 20px; background: #1da1f2; color: white; border: none; border-radius: 5px; }
        ul { list-style: none; padding: 0; }
        li { padding: 10px; background: #e8f4fd; margin: 5px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 推特实时警报系统</h1>
        <p>当前监控账号：</p>
        <ul>
            {% for user in users %}
            <li>@{{ user }}</li>
            {% endfor %}
        </ul>
        <form method="post">
            <input type="text" name="username" placeholder="@username" required>
            <button type="submit">添加监控</button>
        </form>
        <p><small>系统每 3 秒检查一次，支持 iOS Bark / Android Pushover 推送。</small></p>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    users = load_users()
    if request.method == "POST":
        username = request.form["username"].lstrip('@').lower().strip()
        if username and username not in [u.lower() for u in users]:
            save_user(username)
            # 重新加载
            users = load_users()
            return f"<script>alert('✅ 已添加 @{username}！'); window.location='/';</script>"
    return render_template_string(HTML_TEMPLATE, users=users)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
