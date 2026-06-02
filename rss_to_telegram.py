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
    print(f"📂 feeds.json beolvasva. Figyelt feedek száma: {len(feeds)}")
except Exception as e:
    print(f"❌ Hiba a feeds.json beolvasásakor: {e}")
    exit(1)

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
    print("💾 state.json beolvasva.")
except:
    state = {}
    print("ℹ️ state.json nem található, újat kezdünk.")

updated = False
uj_posztok_szama = 0

for feed_url in feeds:
    print(f"\n🔍 Feed ellenőrzése: {feed_url}")
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print("⚠️ Ebben a feedben nincsenek bejegyzések.")
        continue

    latest = feed.entries[0]
    link = latest.get("link", "")
    title = latest.get("title", "Új poszt")
    
    # Kézi indítás és tesztelés segítése: ha a state üres, az első futáskor 
    # elmentjük a posztot, de nem spameljük tele a Telegramot az összes csoport legutóbbi posztjával.
    if feed_url not in state:
        print(f"✨ Első alkalommal látom ezt a feedet. Regisztrálom a legfrissebb posztot, de most még nem küldöm el.")
        state[feed_url] = link
        updated = True
        continue

    # Ha ezt a linket már láttuk ennél a feednél, kihagyjuk
    if state.get(feed_url) == link:
        print("😴 Ezt a posztot már láttuk legutóbb.")
        continue

    print("🆕 ÚJ POSZT DETEKTÁLVA! Kép keresése...")
    uj_posztok_szama += 1

    # Kép keresése
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

    feed_name = feed.feed.get("title", "Facebook Csoport")
    message = f"🆕 *Új poszt itt:* {feed_name}\n\n📝 {title}\n\n🔗 [Megtekintés Facebookon]({link})"

    # Küldés Telegramra
    if image_url:
        payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": message, "parse_mode": "Markdown"}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=payload)
    else:
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

    state[feed_url] = link
    updated = True

# 🔔 ÚJ FUNKCIÓ: Ha lefutott a kör, de nem volt egyetlen új poszt sem
if uj_posztok_szama == 0 and len(state) > 0:
    print("ℹ️ Nem volt új poszt. Értesítés küldése a Telegramra...")
    status_message = "✅ *A bútorfigyelő bot sikeresen lefutott.* jelenleg nincs új elvihető tárgy a csoportokban. 💤"
    payload = {"chat_id": CHAT_ID, "text": status_message, "parse_mode": "Markdown"}
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

# Ha történt változás, kiírjuk a state.json-ba
if updated:
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("\n💾 state.json sikeresen frissítve.")
