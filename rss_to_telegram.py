import json
import os
import feedparser
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Hibrid Bútorfigyelő Bot indítása...")

GOMB_ELRENDEZES = {
    "keyboard": [[{"text": "/status_on"}, {"text": "/status_off"}]],
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

# --- 2. TELEGRAM PARANCSOK OLVASÁSA ---
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
                    elif text == "/status_on":
                        statusz_kapcsolo = "TRUE"
                        parancs_erkezett = "ON"
                        
        state["KULD_STATUSZT"] = statusz_kapcsolo
        state["UTOLSO_UPDATE_ID"] = utolso_update_id
except Exception as e:
    print(f"⚠️ Telegram parancs hiba: {e}")

if parancs_erkezett:
    visszaigazolas = "🟢 *A státuszértesítések bekapcsolva.*" if parancs_erkezett == "ON" else "🔴 *A státuszértesítések kikapcsolva.*"
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": visszaigazolas, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)})

total_uj_posztok = 0

# --- 3. FACEBOOK SESSIONS ELŐKÉSZÍTÉSE ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36"
})

# --- 4. FORRÁSOK ELLENŐRZÉSE ---
for url in feeds:
    uj_bejegyzesek = []
    utolso_mentett_id = state.get(url)

    # A: HA RSS FEED
    if "rss" in url or "xml" in url or "feed" in url:
        print(f"\n📡 RSS Feed ellenőrzése: {url}")
        feed = feedparser.parse(url)
        if not feed.entries:
            continue
            
        for entry in feed.entries:
            poszt_link = entry.get("link", "")
            poszt_id = entry.get("id", poszt_link)
            if poszt_id == utolso
        
