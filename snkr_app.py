import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth # 修正咗呢度！
import sys, subprocess, re, time, random
from datetime import datetime

# 1. 頁面設定
st.set_page_config(page_title="TCG Ultra Quant (Stealth)", page_icon="🟡", layout="wide")

# --- 2. 自動安裝瀏覽器 ---
@st.cache_resource
def install_playwright():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])
install_playwright()

# --- 3. 專屬 CSS 造型 ---
st.markdown("""
    <style>
    [data-testid="stSidebarNav"], section[data-testid="stSidebar"], .stAppDeployButton {display: none;}
    div.stButton > button:first-child {
        background: linear-gradient(#ffcc00 48%, #333 48%, #333 52%, #ffffff 52%) !important;
        color: #333 !important; border-radius: 50% !important;
        width: 130px !important; height: 130px !important;
        border: 6px solid #333 !important; font-size: 65px !important;
        font-weight: 900 !important; margin: 0 auto !important; display: block !important;
        line-height: 1 !important; padding-bottom: 45px !important;
    }
    .price-box {
        font-size: 42px; font-weight: 900; color: #d4a017;
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

# 5. 「隱形捕捉」引擎
def fetch_stealth_price(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        stealth(page) # 啟動隱形模式
        
        try:
            # 1. 前往網頁
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(random.uniform(2, 4)) # 扮真人等一等
            
            # 2. 模擬點擊「PSA 10」
            # 搵包含 PSA 10 嘅掣，用 JS 撳避開偵測
            psa10_btn = page.locator('button:has-text("PSA 10")').first
            if psa10_btn.is_visible():
                psa10_btn.evaluate("btn => btn.click()")
                time.sleep(3) # 等個 HK$ 價錢跳出嚟
            
            # 3. 執個價錢
            content = page.content()
            # 用 Regex 搵 HK $XXXX，對應大佬張相
            price_match = re.search(r'HK\s?\$[\d,]+', content)
            price_text = price_match.group(0) if price_match else "執唔到價錢"
            
            name = page.title().split('|')[0].strip()
            return {"名稱": name, "價格": price_text, "網址": url}
        except:
            return {"名稱": "捕捉失敗", "價格": "N/A", "網址": url}
        finally:
            browser.close()

# 6. UI
st.title("🟡 高級球 (Stealth Version)")
run = st.button("H")

if run:
    if main_sheet:
        urls = [u.strip() for u in main_sheet.col_values(1) if "snkrdunk.com" in u]
        if urls:
            status = st.status("🟡 隱形球突破防線中...")
            results = []
            for url in urls:
                res = fetch_stealth_price(url)
                if res:
                    results.append(res)
                    st.markdown(f"### {res['名稱']}")
                    st.markdown(f'<div class="price-box">{res["價格"]}</div>', unsafe_allow_html=True)
            
            if snkr_history and results:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                h_rows = [[now, r["名稱"], r["價格"], r["網址"]] for r in results]
                snkr_history.append_rows(h_rows)
            status.update(label="✅ 捕捉成功！", state="complete")
        else:
            st.warning("Google Sheet 仲係空嘅？貼條 Link 落 A 欄啦！")
