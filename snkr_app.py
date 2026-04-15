import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth
import sys, subprocess, re, time, random

# 1. 頁面設定
st.set_page_config(page_title="i-Craft Ultra Quant", page_icon="🟡")

# --- 2. 雲端環境安裝 (最緊要) ---
@st.cache_resource
def install_playwright():
    # 呢度係叫雲端裝返必要嘅組件
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

install_playwright()

# --- 3. 造型 ---
st.markdown("<style>div.stButton > button {background: #ffcc00; color: #333; border-radius: 50%; width: 100px; height: 100px; font-weight: 900; margin: 0 auto; display: block;}</style>", unsafe_allow_html=True)

# 4. Google Sheet 連線
@st.cache_resource
def connect_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key("1EFSlY13D9Ns8PAise9BTfSiCNHxuC3q3NHpSQ8tOLgs")
        return ss.sheet1
    except: return None

sheet = connect_gsheet()

# 5. 隱形捕捉核心
def fetch_psa10_stealth(url):
    with sync_playwright() as p:
        # 強力偽裝啟動
        browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0")
        page = context.new_page()
        stealth(page) # 戴上面具
        
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(3) # 扮人睇嘢
            
            # 搵 PSA 10 掣
            btn = page.locator('button:has-text("PSA 10")').first
            if btn.is_visible():
                btn.click()
                time.sleep(2) # 等價錢跳
            
            content = page.content()
            # 搵 HK $XXXX，大佬要嘅精準位
            price = re.search(r'HK\s?\$[\d,]+', content)
            price_val = price.group(0) if price else "執唔到價錢 (防禦太強)"
            
            return {"名稱": page.title()[:20], "價格": price_val}
        except:
            return {"名稱": "超時", "價格": "N/A"}
        finally:
            browser.close()

# 6. UI
st.title("🟡 高級球 Stealth")
if st.button("H"):
    if sheet:
        urls = [u.strip() for u in sheet.col_values(1) if "snkrdunk.com" in u]
        if urls:
            with st.status("🕵️ 隱形球滲透中...") as s:
                for url in urls:
                    data = fetch_psa10_stealth(url)
                    st.write(f"**{data['名稱']}**: {data['價格']}")
            st.success("任務完成！")
