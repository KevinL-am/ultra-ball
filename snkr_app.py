import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os, sys, subprocess, re, time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 1. 頁面設定
st.set_page_config(page_title="TCG Ultra Quant (SNKR PSA10)", page_icon="🟡", layout="wide")

# --- 2. 自動安裝瀏覽器 (Playwright) ---
@st.cache_resource
def install_playwright_browser():
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
        return True
    except: return False

install_playwright_browser()

# --- 3. 高級球 (Ultra Ball) 專屬造型 ---
st.markdown("""
    <style>
    [data-testid="stSidebarNav"], section[data-testid="stSidebar"], .stAppDeployButton {display: none;}
    div.stButton > button:first-child {
        background: linear-gradient(#ffcc00 48%, #333 48%, #333 52%, #ffffff 52%) !important;
        color: #333 !important;
        border-radius: 50% !important;
        width: 140px !important; height: 140px !important;
        border: 8px solid #333 !important;
        font-size: 70px !important; font-weight: 900 !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3) !important;
        margin: 0 auto !important; display: block !important;
        line-height: 1 !important; padding-bottom: 45px !important;
    }
    .price-display {
        font-size: 32px; font-weight: 900; color: #d4a017;
        padding: 20px; border: 3px solid #ffcc00; border-radius: 15px;
        background: #fffdf5; margin: 10px 0; text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# 4. Google Sheet 連接
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

# 5. 精準 PSA 10 捕捉引擎
def fetch_snkr_psa10(url):
    with sync_playwright() as p:
        # 扮真電腦，唔好畀佢知我係 Robot
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 搵 PSA 10 粒掣
            # 我哋用 text= 嚟搵，最準
            psa10_xpath = "//button[contains(text(), 'PSA 10') or contains(span/text(), 'PSA 10')]"
            page.wait_for_selector(psa10_xpath, timeout=10000)
            page.click(psa10_xpath)
            
            # 撳完之後，等個價錢跳 (SNKR 係動態更新嘅)
            time.sleep(2) 
            
            # 執個價錢
            # SNKR 嘅價錢通常喺一個有 "HK $" 嘅元素入面
            price_locator = page.locator("text=/HK\s?\$/")
            if price_locator.count() > 0:
                # 攞最大字體或者第一個見到嘅 HK$
                price_text = price_locator.first.inner_text()
            else:
                # 備用方案：執返網頁原始碼搵
                soup = BeautifulSoup(page.content(), 'html.parser')
                price_text = soup.find(string=re.compile(r'HK\s?\$')) or "N/A"

            # 攞名
            name = page.title().split('|')[0].strip()

            return {"名稱": name, "價格": price_text, "網址": url}
        except Exception as e:
            return {"名稱": f"捕捉失敗", "價格": "N/A", "網址": url}
        finally:
            browser.close()

# 6. UI 介面
st.title("🟡 高級球 PSA 10 監控")
run = st.button("H")

if run:
    if main_sheet:
        urls = [u.strip() for u in main_sheet.col_values(1) if "snkrdunk.com" in u]
        if urls:
            status = st.status("🟡 高級球「PSA 10」捕捉中...")
            results = []
            for url in urls:
                res = fetch_snkr_psa10(url)
                if res:
                    results.append(res)
                    st.markdown(f"### {res['名稱']}")
                    st.markdown(f'<div class="price-display">{res["價格"]}</div>', unsafe_allow_html=True)
                    st.caption(f"來源: {res['網址']}")
            
            if snkr_history and results:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                h_rows = [[now, r["名稱"], r["價格"], r["網址"]] for r in results]
                snkr_history.append_rows(h_rows)
            status.update(label="✅ 捕捉完成！數據已入庫。", state="complete")
        else:
            st.warning("Google Sheet 仲未有 SNKR 連結呀大佬！")
