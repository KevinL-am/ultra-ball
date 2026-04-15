import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 1. 頁面設定
st.set_page_config(page_title="TCG Ultra Quant (SNKR PSA10)", page_icon="🟡", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 高級球 (Ultra Ball) 專屬造型 ---
st.markdown("""
    <style>
    [data-testid="stSidebarNav"], section[data-testid="stSidebar"], .stAppDeployButton {display: none;}
    div.stButton > button:first-child {
        background: linear-gradient(#ffcc00 48%, #333 48%, #333 52%, #ffffff 52%) !important;
        color: #333 !important;
        border-radius: 50% !important;
        width: 180px !important;
        height: 180px !important;
        border: 8px solid #333 !important;
        font-size: 100px !important;
        font-weight: 900 !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3) !important;
        transition: all 0.2s ease !important;
        line-height: 1 !important;
        padding-bottom: 70px !important;
        position: relative !important;
        margin: 0 auto !important;
        display: block !important;
    }
    .snkr-card {
        border: 2px solid #ffcc00;
        padding: 15px;
        border-radius: 15px;
        background-color: #fffdf5;
        box-shadow: 4px 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .price-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .price-label { font-weight: bold; color: #666; font-size: 14px; }
    .price-val { font-weight: 900; color: #d4a017; font-size: 18px; }
    </style>
""", unsafe_allow_html=True)

# 3. 數據與 Google Sheet 連接
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
      ss = client.open_by_key("1EFSlY13D9Ns8PAise9BTfSiCNHxuC3q3NHpSQ8tOLgs")
        main = ss.sheet1
        try: hist = ss.worksheet("SNKR_PSA10_History")
        except: 
            hist = ss.add_worksheet(title="SNKR_PSA10_History", rows="1000", cols="10")
            hist.append_row(["時間", "名稱", "PSA10日元價", "PSA10港幣價", "網址"])
        return main, hist
    except: return None, None

main_sheet, snkr_history = connect_gsheet()

# 4. SNKRDUNK PSA10 專用爬蟲
def fetch_snkr_psa10(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        try:
            page.goto(url, wait_until="networkidle", timeout=60000)
            soup = BeautifulSoup(page.content(), 'html.parser')
            name = soup.find('h1').get_text(strip=True) if soup.find('h1') else "未知卡片"
            img_tag = soup.find('img', alt=True)
            img_url = img_tag.get('src') if img_tag else "N/A"
            psa10_price = "N/A"
            elements = page.query_selector_all("text='PSA 10'")
            if not elements: elements = page.query_selector_all("text='鑑定済 (PSA10)'")
            if elements:
                for el in elements:
                    parent = el.evaluate_handle("e => e.parentElement.parentElement")
                    price_text = parent.as_element().inner_text()
                    match = re.search(r'(¥|HK\$|US\$)\s?([\d,]+)', price_text)
                    if match:
                        psa10_price = f"¥{match.group(2)}"
                        break
            return {"名稱": name, "圖片": img_url, "PSA10價": psa10_price, "網址": url}
        except: return None
        finally: browser.close()

# 5. UI
st.title("🟡 TCG Ultra Quant: SNKR PSA10")
rate = st.number_input("日元匯率 (JPY/HKD)", value=0.051, format="%.4f")
run = st.button("H")

if run:
    if main_sheet:
        all_urls = main_sheet.col_values(1)
        snkr_urls = [u.strip() for u in all_urls if "snkrdunk.com" in u]
        if snkr_urls:
            status = st.status("🟡 高級球「PSA 10」捕捉中...")
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
                                yen = parse_price(res["PSA10價"])
                                st.markdown(f'<div class="snkr-card">¥ {yen:,.0f} / HK$ {yen*rate:,.0f}</div>', unsafe_allow_html=True)
            if snkr_history and results:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                h_rows = [[now, r["名稱"], r["PSA10價"], f"HK$ {parse_price(r['PSA10價'])*rate:,.0f}", r["網址"]] for r in results]
                snkr_history.append_rows(h_rows)
            status.update(label="✅ 高級球 PSA 10 收服完畢！", state="complete")
