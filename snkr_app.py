import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, sys, subprocess, re, time
from datetime import datetime

# 1. 頁面設定
st.set_page_config(page_title="TCG Ultra Quant (SNKR PSA10)", page_icon="🟡", layout="wide")

# --- 2. 自動裝機 (Playwright) ---
@st.cache_resource
def install_playwright():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
install_playwright()

# --- 3. 高級球專屬 CSS ---
st.markdown("""
    <style>
    [data-testid="stSidebarNav"], section[data-testid="stSidebar"], .stAppDeployButton {display: none;}
    div.stButton > button:first-child {
        background: linear-gradient(#ffcc00 48%, #333 48%, #333 52%, #ffffff 52%) !important;
        color: #333 !important; border-radius: 50% !important;
        width: 120px !important; height: 120px !important;
        border: 6px solid #333 !important; font-size: 60px !important;
        font-weight: 900 !important; margin: 0 auto !important; display: block !important;
    }
    .price-box {
        font-size: 40px; font-weight: 900; color: #d4a017;
        text-align: center; padding: 20px; border: 4px solid #ffcc00;
        border-radius: 20px; background: #fffdf5; margin: 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# 4. 連接 Google Sheet
@st.cache_resource
def connect_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        ss = client.open_by_key("1EFSlY13D9Ns8PAise9BTfSiCNHxuC3q3NHpSQ8tOLgs")
        main = ss.sheet1
        try: hist = ss.worksheet("SNKR_PSA10_History")
        except: 
            hist = ss.add_worksheet(title="SNKR_PSA10_History", rows="1000", cols="10")
            hist.append_row(["時間", "名稱", "價格", "網址"])
        return main, hist
    except: return None, None

main_sheet, snkr_history = connect_gsheet()

# 5. 「扮真人」精準爬蟲引擎
def fetch_snkr_data(url):
    with sync_playwright() as p:
        # 扮真電腦瀏覽器，避開防爬蟲
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        try:
            # 去嗰張卡嘅網址
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 第一步：搵「PSA 10」呢粒掣
            # 我哋直接搵文字包含 PSA 10 嘅 button
            psa10_btn = page.locator('button:has-text("PSA 10")').first
            if psa10_btn.is_visible():
                psa10_btn.click()
                time.sleep(2) # 撳完一定要等，等個價錢跳
            
            # 第二步：執個「HK $」價錢
            # 我哋搵網頁入面所有包含 HK $ 嘅字眼
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # 優先搵大標題價錢 (通常係大佬想要嗰個)
            price_match = re.search(r'HK\s?\$[\d,]+', content)
            price_text = price_match.group(0) if price_match else "搵唔到價錢"
            
            # 攞名
            name = page.title().split('|')[0].strip()
            
            return {"名稱": name, "價格": price_text, "網址": url}
        except Exception as e:
            return {"名稱": "連線超時", "價格": "N/A", "網址": url}
        finally:
            browser.close()

# 6. UI
st.title("🟡 高級球 PSA 10 精準監控")
run = st.button("H")

if run:
    if main_sheet:
        urls = [u.strip() for u in main_sheet.col_values(1) if "snkrdunk.com" in u]
        if urls:
            status = st.status("🟡 高級球「扮真人」捕捉中...")
            results = []
            for url in urls:
                res = fetch_snkr_data(url)
                if res:
                    results.append(res)
                    st.markdown(f"### {res['名稱']}")
                    st.markdown(f'<div class="price-box">{res["價格"]}</div>', unsafe_allow_html=True)
            
            if snkr_history and results:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                h_rows = [[now, r["名稱"], r["價格"], r["網址"]] for r in results]
                snkr_history.append_rows(h_rows)
            status.update(label="✅ 成功收服！", state="complete")
        else:
            st.warning("Google Sheet 仲係空嘅？快啲貼條 SNKR 網址入 A 欄啦！")
