import json
import os
import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Program elindult...")

try:
    with open("feeds.json", "r", encoding="utf-8") as f:
        feeds = json.load(f)["feeds"]
    print(f"📂 feeds.json sikeresen beolvasva. Figyelt feedek száma: {len(feeds)}")
except Exception as e:
    print(f"❌ Hiba a feeds.json beolvasásakor: {e}")
    exit(1)

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    print("💾 state.json (korábbi állapot) beolvasva.")
except:
    state = {}
    print("ℹ️ state.json nem található vagy üres, új állapotot kezdünk.")

updated = False

for feed_url in feeds:
    print(f"\n🔍 Feed ellenőrzése: {feed_url}")
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print("⚠️ Ebben a feedben nincsenek bejegyzések (üres az RSS).")
        continue

    # A legfrissebb bejegyzés a feedben
    latest = feed.entries[0]
    link = latest.get("link", "")
    title = latest.get("title", "Új poszt")
    print(f"📋 Legutóbbi poszt címe a weben: {title}")
    print(f"🔗 Link: {link}")

    # Ha ezt a linket már láttuk ennél a feednél, kihagyjuk
    if state.get(feed_url) == link:
        print("😴 Ezt a posztot már láttuk legutóbb, nem küldünk újat.")
        continue

    print("🆕 ÚJ POSZT DETEKTÁLVA! Kép keresése...")

    # Kép keresése az RSS feedben
    image_url = None
    if "media_content" in latest:
        try: image_url = latest.media_content[0]["url"]
        except: pass
    elif "media_thumbnail" in latest:
        try: image_url = latest.media_thumbnail[0]["url"]
        except: pass
    elif "links" in latest:
        for l in latest.links:
            if "image" in l.get("type", ""):
                image_url = l.get("href")
                break

    if image_url:
        print(f"📸 Kép megtalálva: {image_url}")
    else:
        print("🤷‍♂️ Nem találtam képet ehhez a poszthoz.")

    feed_name = feed.feed.get("title", "Facebook Csoport")
    message = f"🆕 *Új poszt itt:* {feed_name}\n\n📝 {title}\n\n🔗 [Megtekintés Facebookon]({link})"

    # Küldés Telegramra
    if image_url:
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": message, "parse_mode": "Markdown"}
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=payload)
    else:
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

    print(f"📤 Telegram válasz státuszkód: {res.status_code}")
    if res.status_code != 200:
        print(f"❌ Telegram hibaüzenet: {res.text}")

    state[feed_url] = link
    updated = True

# Ha történt változás, kiírjuk a state.json-ba
if updated:
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("\n💾 state.json sikeresen frissítve a repositoryban.")
else:
    print("\n😴 Nem történt változás, nem kellett menteni semmit.")
