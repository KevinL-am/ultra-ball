import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import sys
import subprocess
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 1. 頁面設定
st.set_page_config(page_title="TCG Ultra Quant (SNKR PSA10)", page_icon="🟡", layout="wide")

# --- 2. 自動安裝手腳 (Playwright 瀏覽器) ---
@st.cache_resource
def install_playwright_browser():
    try:
        # 強制安裝 chromium 瀏覽器內核
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        return True
    except Exception as e:
        st.error(f"安裝瀏覽器失敗: {e}")
        return False

installed = install_playwright_browser()

# --- 3. 高級球 (Ultra Ball) 專屬造型 ---
st.markdown("""
    <style>
    [data-testid="stSidebarNav"], section[data-testid="stSidebar"], .stAppDeployButton {display: none;}
    div.stButton > button:first-child {
        background: linear-gradient(#ffcc00 48%, #333 48%, #333 52%, #ffffff 52%) !important;
        color: #333 !important;
        border-radius: 50% !important;
        width: 150px !important; height: 150px !important;
        border: 8px solid #333 !important;
        font-size: 80px !important; font-weight: 900 !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        margin: 0 auto !important; display: block !important;
        line-height: 1 !important; padding-bottom: 50px !important;
    }
    .snkr-card {
        border: 2px solid #ffcc00; padding: 15px; border-radius: 15px;
        background-color: #fffdf5; box-shadow: 4px 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px; text-align: center;
    }
    .price-val { font-weight: 900; color: #d4a017; font-size: 24px; }
    </style>
""", unsafe_allow_html=True)

# 4. 數據與 Google Sheet 連接
def parse_price(p_str):
    try:
        num = re.sub(r'[^\d]', '', str(p_str))
        return float(num) if num else 0
    except: return 0

@st.cache_resource
def connect_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # 對準大佬張新 Sheet ID
        ss = client.open_by_key("1EFSlY13D9Ns8PAise9BTfSiCNHxuC3q3NHpSQ8tOLgs")
        main = ss.sheet1
        try: hist = ss.worksheet("SNKR_PSA10_History")
        except: 
            hist = ss.add_worksheet(title="SNKR_PSA10_History", rows="1000", cols="10")
            hist.append_row(["時間", "名稱", "PSA10 價格", "網址"])
        return main, hist
    except: return None, None

main_sheet, snkr_history = connect_gsheet()

# 5. 精準 PSA 10 捕捉程式
def fetch_snkr_psa10(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 1. 搵 PSA 10 粒掣並撳落去
            # 呢度會搵包含 "PSA 10" 嘅掣
            psa10_btn = page.locator("button:has-text('PSA 10')").first
            if psa10_btn.is_visible():
                psa10_btn.click()
                page.wait_for_timeout(2000) # 等個價錢跳
            
            # 2. 執個價錢 (搵 HK$ 或者 ¥ 符號)
            # 根據大佬張相，價錢通常喺一個好大嘅字體入面
            soup = BeautifulSoup(page.content(), 'html.parser')
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "未知卡片"
            
            # 搵包含 HK$ 或 ¥ 嘅大價錢
            price_text = "N/A"
            price_elements = soup.find_all(string=re.compile(r'(HK\s?\$|¥|US\s?\$)\s?[\d,]+'))
            if price_elements:
                # 攞第一個見到嘅大價錢
                price_text = price_elements[0].strip()

            # 搵圖
            img_tag = soup.find('img', class_=re.compile(r'product-image')) or soup.find('main').find('img')
            img_url = img_tag.get('src') if img_tag else "N/A"

            return {"名稱": name, "圖片": img_url, "價格": price_text, "網址": url}
        except: return None
        finally: browser.close()

# 6. UI
st.title("🟡 高級球 PSA 10 監控")
if not installed:
    st.warning("正在初始化環境，請稍候...")
else:
    run = st.button("H")

if run:
    if main_sheet:
        all_urls = main_sheet.col_values(1)
        snkr_urls = [u.strip() for u in all_urls if "snkrdunk.com" in u]
        if snkr_urls:
            status = st.status("🟡 高級球「PSA 10」精準捕捉中...")
            results = []
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(fetch_snkr_psa10, url) for url in snkr_urls]
                display = st.container()
                for f in futures:
                    res = f.result()
                    if res:
                        results.append(res)
                        with display:
                            st.divider()
                            c1, c2 = st.columns([1, 2])
                            with c1: st.image(res["圖片"], width=150)
                            with c2:
                                st.markdown(f"### {res['名稱']}")
                                st.markdown(f'<div class="snkr-card"><span class="price-val">{res["價格"]}</span></div>', unsafe_allow_html=True)
            if snkr_history and results:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                h_rows = [[now, r["名稱"], r["價格"], r["網址"]] for r in results]
                snkr_history.append_rows(h_rows)
            status.update(label="✅ PSA 10 收服完畢！", state="complete")
        else:
            st.warning("Google Sheet A 欄未有網址。")
