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
            if poszt_id == utolso_mentett_id:
                break
            poszt_szoveg = entry.get("title", "") + " " + entry.get("summary", "")
            if len(poszt_szoveg) > 250: poszt_szoveg = poszt_szoveg[:250] + "..."
            uj_bejegyzesek.append({"id": poszt_id, "link": poszt_link, "text": poszt_szoveg})
            
        if utolso_mentett_id is None and feed.entries:
            state[url] = feed.entries[0].get("id", feed.entries[0].get("link", "1"))
            continue

    # B: HA DIRECT FACEBOOK LINK
    else:
        url_tisztitott = url.replace("www.facebook.com", "mbasic.facebook.com")
        print(f"\n🔍 Direkt Facebook ellenőrzése: {url_tisztitott}")
        try:
            response = session.get(url_tisztitott, timeout=15)
            soup = BeautifulSoup(response.text, "html.parser")
            posztok = soup.find_all("div", id=lambda x: x and x.startswith("story_story_id")) or soup.find_all("table", role="article")
            
            for poszt in posztok:
                link_elem = None
                for a in poszt.find_all("a", href=True):
                    if "permalink" in a["href"] or "/story.php" in a["href"]:
                        link_elem = a
                        break
                if not link_elem: continue
                
                poszt_link = "https://www.facebook.com" + link_elem["href"].split("&")[0].split("?")[0].replace("mbasic.", "www.")
                poszt_id = poszt_link.split("id=")[-1] if "id=" in poszt_link else poszt_link
                
                # ITT VOLT A HIBA - JAVÍTVA:
                if poszt_id == utolso_mentett_id:
                    break
                    
                szoveg_doboz = poszt.find("div")
                poszt_szoveg = szoveg_doboz.get_text(strip=True) if szoveg_doboz else "Új hirdetés"
                if len(poszt_szoveg) > 250: poszt_szoveg = poszt_szoveg[:250] + "..."
                uj_bejegyzesek.append({"id": poszt_id, "link": poszt_link, "text": poszt_szoveg})
                
            if utolso_mentett_id is None:
                state[url] = uj_bejegyzesek[0]["id"] if uj_bejegyzesek else "1"
                continue
        except Exception as e:
            print(f"❌ Hiba a direkt FB csoportnál: {e}")
            continue

    # Új posztok kiküldése
    if uj_bejegyzesek:
        print(f"🆕 {len(uj_bejegyzesek)} db ÚJ POSZT! Küldés...")
        for p in reversed(uj_bejegyzesek):
            total_uj_posztok += 1
            message = f"🆕 *Új poszt!*\n\n📝 {p['text']}\n\n🔗 [Megtekintés Facebookon]({p['link']})"
            payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
        state[url] = uj_bejegyzesek[0]["id"]

# --- 5. MENTÉS ÉS KIKÜLDÉS ---
with open("state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

if total_uj_posztok == 0:
    print(f"ℹ️ Nincs új poszt. Státusz állása: {statusz_kapcsolo}")
    if statusz_kapcsolo == "TRUE" and not parancs_erkezett:
        status_message = "✅*Sikeres Futtatás.*❌ Nincs új tárgy.❌"
        payload = {"chat_id": CHAT_ID, "text": status_message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
