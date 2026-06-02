import json
import os
import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Program elindult (Telegram parancsvezérléssel)...")

# --- 1. TELEGRAM PARANCSOK ELLENŐRZÉSE ---
# Megkérdezzük a Telegramot a legutóbbi üzenetekről
try:
    updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    updates = requests.get(updates_url, timeout=10).json()
    
    # Alapértelmezett állapot, ha még nincs elmentve semmi
    statusz_kapcsolo = "TRUE" 

    if updates.get("ok") and updates.get("result"):
        # Végigmegyünk a legutóbbi üzeneteken (a legfrissebbtől visszafele)
        for update in reversed(updates["result"]):
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"].strip()
                user_chat_id = str(update["message"]["chat"]["id"])
                
                # Biztonsági ellenőrzés: csak a te CHAT_ID-dról fogadunk el parancsot!
                if user_chat_id == str(CHAT_ID):
                    if text == "/status_off":
                        statusz_kapcsolo = "FALSE"
                        print("🔕 Felhasználói parancs észlelve: Státusz KIKAPCSOLVA")
                        break
                    elif text == "/status_on":
                        statusz_kapcsolo = "TRUE"
                        print("🔔 Felhasználói parancs észlelve: Státusz BEKAPCSOLVA")
                        break
except Exception as e:
    print(f"⚠️ Nem sikerült ellenőrizni a Telegram parancsokat: {e}")
    statusz_kapcsolo = "TRUE" # Hiba esetén biztonságból bekapcsolva hagyjuk

# --- 2. ÁLLAPOTOK BETÖLTÉSE ---
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

# Ha a state.json-ban már van elmentett kapcsoló állás, és a Telegramon nem küldtél újat, azt használjuk
if "KULD_STATUSZT" in state and 'text' not in locals():
    statusz_kapcsolo = state["KULD_STATUSZT"]
else:
    # Ha a Telegramon jött új parancs, felülírjuk a state-ben
    state["KULD_STATUSZT"] = statusz_kapcsolo

total_uj_posztok = 0

# --- 3. CSOPORTOK ELLENŐRZÉSE ---
for feed_url in feeds:
    print(f"\n🔍 Feed ellenőrzése: {feed_url}")
    feed = feedparser.parse(feed_url)

    if not feed.entries:
        continue

    utolso_mentett_link = state.get(feed_url)
    uj_bejegyzesek = []
    
    for entry in feed.entries:
        jelenlegi_link = entry.get("link", "")
        if jelenlegi_link == utolso_mentett_link:
            break
        uj_bejegyzesek.append(entry)

    if utolso_mentett_link is None:
        state[feed_url] = feed.entries[0].get("link", "")
        continue

    if not uj_bejegyzesek:
        continue

    print(f"🆕 {len(uj_bejegyzesek)} db ÚJ POSZT! Küldés...")
    
    for latest in reversed(uj_bejegyzesek):
        link = latest.get("link", "")
        title = latest.get("title", "Új poszt")
        total_uj_posztok += 1

        image_url = None
        if "media_content" in latest:
            try: image_url = latest.media_content[0]["url"]
            except: pass
        elif "links" in latest:
            for l in latest.links:
                if "image" in l.get("type", ""):
                    image_url = l.get("href")
                    break

        feed_name = feed.feed.get("title", "Facebook Csoport")
        message = f"🆕 *Új poszt itt:* {feed_name}\n\n📝 {title}\n\n🔗 [Megtekintés Facebookon]({link})"

        if image_url:
            payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": message, "parse_mode": "Markdown"}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=payload)
        else:
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

    state[feed_url] = feed.entries[0].get("link", "")

# --- 4. KIKÜLDÉS ÉS MENTÉS ---
# Elmentjük az aktuális állapotokat (a kapcsoló állását is!)
with open("state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

# Státuszjelentés kezelése az új tárolt kapcsoló szerint
if total_uj_posztok == 0:
    print("ℹ️ Nem volt új poszt egyik csoportban sem.")
    if statusz_kapcsolo == "TRUE":
        print("📲 Státuszüzenet küldése...")
        status_message = "✅ *A bútorfigyelő bot sikeresen lefutott.* Jelenleg nincs új elvihető tárgy. 💤\n\n_Kikapcsoláshoz küldd ezt:_ /status_off"
        payload = {"chat_id": CHAT_ID, "text": status_message, "parse_mode": "Markdown"}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
    else:
        print("🔕 Státuszüzenet elnémítva.")
