import json
import os
import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Program elindult (Összes új poszt gyűjtése)...")

try:
    with open("feeds.json", "r", encoding="utf-8") as f:
        feeds = json.load(f)["feeds"]
except Exception as e:
    print(f"❌ Hiba a feeds.json beolvasásakor: {e}")
    exit(1)

try:
    with open("state.json", "r", encoding="utf-8") as f:
        state = json.load(f)
except:
    state = {}

total_uj_posztok = 0

for feed_url in feeds:
    print(f"\n🔍 Feed ellenőrzése: {feed_url}")
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        print("⚠️ Ebben a feedben nincsenek bejegyzések.")
        continue

    # Elmentjük, mi volt az eddigi utolsó látott link ebben a csoportban
    utolso_mentett_link = state.get(feed_url)
    
    # Kigyűjtjük azokat a posztokat, amiket most találtunk és még NEM láttunk
    uj_bejegyzesek = []
    for entry in feed.entries:
        jelenlegi_link = entry.get("link", "")
        
        # Ha elértünk a legutóbb mentett linkhez, megállunk (a többi már régi)
        if jelenlegi_link == utolso_mentett_link:
            break
            
        uj_bejegyzesek.append(entry)

    # Biztonsági kör: Ha a feed még SOHA nem szerepelt a state.json-ban,
    # akkor csak a legfrissebbet regisztráljuk, hogy ne spamelje tele a csatornát az összes régi poszttal
    if utolso_mentett_link is None:
        print(f"✨ Új feed regisztrálva a rendszerbe: {feed_url}")
        state[feed_url] = feed.entries[0].get("link", "")
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        continue

    if not uj_bejegyzesek:
        print("😴 Nincs új poszt ebben a csoportban.")
        continue

    print(f"🆕 {len(uj_bejegyzesek)} db ÚJ POSZT TALÁLHATÓ! Küldés folyamatban...")
    
    # Időrendben fordítva (a régebbitől az újabb felé) küldjük el őket, hogy jól jelenjen meg a chatedben
    for latest in reversed(uj_bejegyzesek):
        link = latest.get("link", "")
        title = latest.get("title", "Új poszt")
        total_uj_posztok += 1

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

    # A legfrissebb poszt linkjét mentjük el a legvégén állapottnak
    state[feed_url] = feed.entries[0].get("link", "")
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# Státuszjelentés, ha semmi új nem volt sehol
if total_uj_posztok == 0:
    print("ℹ️ Nem volt új poszt egyik csoportban sem.")
    status_message = "✅ *A bútorfigyelő bot sikeresen lefutott.* Jelenleg nincs új elvihető tárgy a csoportokban. 💤"
    payload = {"chat_id": CHAT_ID, "text": status_message, "parse_mode": "Markdown"}
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
