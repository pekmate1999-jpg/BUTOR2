import json
import os
import feedparser
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Program elindult (Egyedi üzenettel és gombokkal)...")

# --- TELEGRAM GOMBOK STRUKTÚRÁJA ---
GOMB_ELRENDEZES = {
    "keyboard": [
        [{"text": "/status_on"}, {"text": "/status_off"}]
    ],
    "resize_keyboard": True,       
    "one_time_keyboard": False     
}

# --- 1. ÁLLAPOTOK BETÖLTÉSE ---
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

statusz_kapcsolo = state.get("KULD_STATUSZT", "TRUE")
utolso_update_id = state.get("UTOLSO_UPDATE_ID", 0)

# --- 2. TELEGRAM PARANCSOK OLVASÁSA ÉS NYUGTÁZÁSA ---
parancs_erkezett = False
try:
    updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={utolso_update_id + 1}"
    updates = requests.get(updates_url, timeout=10).json()

    if updates.get("ok") and updates.get("result"):
        for update in updates["result"]:
            update_id = update["update_id"]
            if update_id > utolso_update_id:
                utolso_update_id = update_id
            
            if "message" in update and "text" in update["message"]:
                text = update["message"]["text"].strip()
                user_chat_id = str(update["message"]["chat"]["id"])
                
                if user_chat_id == str(CHAT_ID):
                    if text == "/status_off":
                        statusz_kapcsolo = "FALSE"
                        parancs_erkezett = "OFF"
                        print("🔕 Új parancs: Státusz KIKAPCSOLVA")
                    elif text == "/status_on":
                        statusz_kapcsolo = "TRUE"
                        parancs_erkezett = "ON"
                        print("🔔 Új parancs: Státusz BEKAPCSOLVA")
                        
        state["KULD_STATUSZT"] = statusz_kapcsolo
        state["UTOLSO_UPDATE_ID"] = utolso_update_id
except Exception as e:
    print(f"⚠️ Nem sikerült ellenőrizni a Telegram parancsokat: {e}")

# Visszaigazolás gombnyomásra
if parancs_erkezett:
    visszaigazolas = "🟢 *A státuszértesítések bekapcsolva.* 5 percenként jelentkezem!" if parancs_erkezett == "ON" else "🔴 *A státuszértesítések kikapcsolva.* Csak akkor szólok, ha új bútor van!"
    payload = {
        "chat_id": CHAT_ID, 
        "text": visszaigazolas, 
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(GOMB_ELRENDEZES)
    }
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

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
            payload = {"chat_id": CHAT_ID, "photo": image_url, "caption": message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data=payload)
        else:
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

    state[feed_url] = feed.entries[0].get("link", "")

# --- 4. MENTÉS ÉS KIKÜLDÉS ---
with open("state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

if total_uj_posztok == 0:
    print(f"ℹ️ Nem volt új poszt. Státuszküldés állása: {statusz_kapcsolo}")
    # Ha a státusz be van kapcsolva, és most nem történt parancsfelülírás
    if statusz_kapcsolo == "TRUE" and not parancs_erkezett:
        # A te egyedi módosított üzeneted:
        status_message = "✅*Sikeres Futtatás.✅*❌ Nincs új tárgy.❌"
        payload = {
            "chat_id": CHAT_ID, 
            "text": status_message, 
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(GOMB_ELRENDEZES) 
        }
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
