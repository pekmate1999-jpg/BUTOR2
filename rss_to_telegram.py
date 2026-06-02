import json
import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

print("🚀 Nyilvános Facebook Csoport Monitor indítása...")

# --- TELEGRAM GOMBOK ---
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

# --- 3. SÜTI ELFOGADÁS SZIMULÁLÁSA A FACEBOOKON ---
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Accept-Language": "hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7"
})

# Először megnyitjuk a sima mbasic főoldalt, hogy megkapjuk a kezdeti sütiket
try:
    res = session.get("https://mbasic.facebook.com/", timeout=15)
    # Ha felugrik a süti elfogadó ablak, elküldjük az elfogadást gombnyomásként
    if "cookie/consent" in res.url or "consent" in res.text:
        # A Facebook süti elfogadó űrlapja általában a /cookie/consent/ címre posztol
        # Szimuláljuk az 'Összes elfogadása' (Accept All) gombot
        consent_data = {"accept_only_essential": "false", "submit": "Accept All"}
        session.post("https://mbasic.facebook.com/cookie/consent/", data=consent_data, timeout=15)
except Exception as e:
    print(f"⚠️ Süti kezelési figyelmeztetés: {e}")

# --- 4. KÖZVETLEN FACEBOOK CSOPORT ELLENŐRZÉS ---
for csoport_url in feeds:
    # Biztosítjuk, hogy az mbasic URL-t használjuk
    url_tisztitott = csoport_url.replace("www.facebook.com", "mbasic.facebook.com")
    print(f"\n🔍 Csoport ellenőrzése: {url_tisztitott}")
    
    try:
        response = session.get(url_tisztitott, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
    except Exception as e:
        print(f"❌ Nem sikerült megnyitni a csoportot: {e}")
        continue

    # Az mbasic felületen a posztok cikkekként (article) vagy story div-ekként szerepelnek
    posztok = soup.find_all("div", id=lambda x: x and x.startswith("story_story_id"))
    if not posztok:
        posztok = soup.find_all("table", role="article")

    utolso_mentett_id = state.get(url_tisztitott)
    uj_bejegyzesek = []

    for poszt in posztok:
        # Megkeressük a poszt egyedi permalinkjét
        link_elem = None
        for a in poszt.find_all("a", href=True):
            if "permalink" in a["href"] or "/story.php" in a["href"]:
                link_elem = a
                break
        
        if not link_elem: continue
        
        # Tisztítjuk az URL-t a felesleges követőkódoktól
        nyers_href = link_elem["href"]
        if "story.php" in nyers_href:
            poszt_link = "https://mbasic.facebook.com" + nyers_href.split("&")[0]
        else:
            poszt_link = "https://mbasic.facebook.com" + nyers_href.split("?")[0]
            
        poszt_id = poszt_link.split("id=")[-1] if "id=" in poszt_link else poszt_link

        if poszt_id == utolso_mentett_id:
            break

        # Szöveges tartalom kinyerése
        szoveg_doboz = poszt.find("div")
        poszt_szoveg = "Új hirdetés (Kép vagy link)"
        if szoveg_doboz:
            # Megkeressük a tényleges szöveges bekezdést a poszton belül
            p_elemek = szoveg_doboz.find_all("p")
            if p_elemek:
                poszt_szoveg = " ".join([p.get_text(strip=True) for p in p_elemek])
            else:
                poszt_szoveg = szoveg_doboz.get_text(strip=True)

        if len(poszt_szoveg) > 250:
            poszt_szoveg = poszt_szoveg[:250] + "..."

        uj_bejegyzesek.append({"id": poszt_id, "link": poszt_link.replace("mbasic.", "www."), "text": poszt_szoveg})

    # Első futás védelme: ha még üres a state, csak elmentjük a legfrissebbet
    if utolso_mentett_id is None:
        print(f"✨ Csoport sikeresen regisztrálva: {url_tisztitott}")
        if uj_bejegyzesek:
            state[url_tisztitott] = uj_bejegyzesek[0]["id"]
        else:
            state[url_tisztitott] = "1"
        continue

    if not uj_bejegyzesek:
        continue

    print(f"🆕 {len(uj_bejegyzesek)} db ÚJ FB POSZT! Küldés...")
    for p in reversed(uj_bejegyzesek):
        total_uj_posztok += 1
        message = f"🆕 *Új poszt a csoportban!*\n\n📝 {p['text']}\n\n🔗 [Megtekintés Facebookon]({p['link']})"
        
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)

    # Elmentjük a legfrissebb poszt ID-ját a következő körhöz
    state[url_tisztitott] = uj_bejegyzesek[0]["id"]

# --- 5. MENTÉS ÉS KIKÜLDÉS ---
with open("state.json", "w", encoding="utf-8") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)

if total_uj_posztok == 0:
    print(f"ℹ️ Nincs új poszt. Státusz állása: {statusz_kapcsolo}")
    if statusz_kapcsolo == "TRUE" and not parancs_erkezett:
        status_message = "❌*Sikeres Futtatás.* Nincs új tárgy."
        payload = {"chat_id": CHAT_ID, "text": status_message, "parse_mode": "Markdown", "reply_markup": json.dumps(GOMB_ELRENDEZES)}
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=payload)
