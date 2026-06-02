import json
import os
import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

with open("feeds.json", "r", encoding="utf-8") as f:
    feeds = json.load(f)["feeds"]

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
except:
    state = {}

updated = False

for feed_url in feeds:

    feed = feedparser.parse(feed_url)

    if not feed.entries:
        continue

    latest = feed.entries[0]

    link = latest.get("link", "")
    title = latest.get("title", "Új poszt")

    if state.get(feed_url) == link:
        continue

    image_url = None

    if "media_content" in latest:
        try:
            image_url = latest.media_content[0]["url"]
        except:
            pass

    if not image_url and "media_thumbnail" in latest:
        try:
            image_url = latest.media_thumbnail[0]["url"]
        except:
            pass

    message = f"🆕 Új poszt\n\n{title}\n\n🔗 {link}"

    if image_url:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "caption": message
            },
            files={}
        )
    else:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            }
        )

    state[feed_url] = link
    updated = True

if updated:
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
