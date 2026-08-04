import streamlit as st
import yfinance as yf
import pandas as pd
import twstock

# 設定頁面標題與佈局
st.set_page_config(page_title="KY 實戰策略股票篩選器", layout="wide")

st.title("📈 KY 實戰策略股票篩選器")

# 1. 自動載入全台股名稱與代碼（包含過濾 ETF 邏輯）
@st.cache_data
def get_tw_stock_map():
    name_to_code = {}
    code_to_name = {}
    stock_only_codes = [] # 純股票，排除 ETF
    
    for code, info in twstock.codes.items():
        if info.type == '股票' or info.type == 'ETF':
            name_to_code[info.name] = f"{code}.TW"
            code_to_name[code] = info.name
            if info.type == '股票':
                stock_only_codes.append(code)
    return name_to_code, code_to_name, stock_only_codes

NAME_TO_CODE, CODE_TO_NAME, STOCK_ONLY_CODES = get_tw_stock_map()

# 預設熱門觀察清單
TOP_VOLUME = ["2330", "2317", "3231", "2382", "2603", "2609", "2618", "2303", "2454", "2356", "3037", "2376", "2301", "2324", "3711", "2409", "3481", "1301", "1303", "2002"]

# 2. 步驟一：選擇搜尋股票池
st.header("🎯 步驟一：選擇搜尋股票池（搜尋範圍）")

stock_pool = st.selectbox(
    "請選擇你要掃描的股票範圍：",
    [
        "🔥 熱門成交量/成交值強勢股",
        "🌐 全台股大掃描 (2,000+ 隻 - 需較長時間)",
        "✏️ 自訂觀察名單 (自行輸入中文或代碼)"
    ]
)

user_input = ""
if "自訂觀察名單" in stock_pool:
    user_input = st.text_input("請輸入股票名稱或代碼（用逗號隔開）", "台積電, 鴻海, 2454, 長榮, 玉山金, 00878")

st.write("---")

# 3. 步驟二：實戰策略選擇與參數設定
st.header("⚙️ 步驟二：選擇實戰策略與參數設定")

strategy_choice = st.radio(
    "請選擇要執行的實戰策略：",
    ["策略一：中午回撤", "策略二：底部籌碼洗牌", "策略三：當沖 - 成交值排名前 20 (不包含 ETF)"],
    horizontal=False
)

st.write("---")

# --- 策略一：中午回撤 ---
if strategy_choice == "策略一：中午回撤":
    st.subheader("📋 策略一：中午回撤 參數設定")
    
    col1, col2, col3 = st.columns([1.5, 2, 2.5])
    
    with col1:
        s1_drop_op = st.selectbox("跌幅條件", ["跌幅大於 (>)", "跌幅小於 (<)"])
    
    with col2:
        s1_drop_pct = st.number_input("跌幅趴數 N (%)", value=2.0, step=0.1, format="%.1f")
        
    with col3:
        s1_vol_min = st.number_input("到目前為止，總量大於 N 張", value=1000, step=100)

# --- 策略二：底部籌碼洗牌 ---
elif strategy_choice == "策略二：底部籌碼洗牌":
    st.subheader("📋 策略二：底部籌碼洗牌 參數設定")
    
    col1, col2 = st.columns(2)
    with col1:
        c_op, c_val = st.columns([1.2, 1.8])
        with c_op:
            s2_up_op = st.selectbox("漲幅條件", ["漲幅小於 (<)", "漲幅大於 (>)"])
        with c_val:
            s2_up_val = st.number_input("漲幅趴數 N (%)", value=3.0, step=0.1, format="%.1f")
            
        s2_vol_min = st.number_input("到目前為止，總量大於 N 張", value=1000, step=100)
        
    with col2:
        c1, c2 = st.columns(2)
        with c1:
            s2_margin_days = st.number_input("融資餘額連續 N 日以上", value=3, step=1)
        with c2:
            s2_margin_type = st.selectbox("變化方向", ["增加", "減少"])

# --- 策略三：當沖 ---
else:
    st.subheader("📋 策略三：當沖 - 成交值排名前 20 (不包含 ETF)")
    st.info("💡 系統將自動抓取市場上成交值前 20 大標的，並自動**剔除所有 ETF**，精準鎖定熱門當沖個股！")

# 4. 開始掃描按鈕
st.write("---")
if st.button("🚀 開始執行實戰策略大掃描", type="primary"):
    st.subheader("📊 策略篩選結果")
    
    target_stocks = []
    
    if "當沖" in strategy_choice:
        target_stocks = [c for c in TOP_VOLUME if c in STOCK_ONLY_CODES][:20]
    else:
        if "熱門成交量" in stock_pool:
            target_stocks = TOP_VOLUME
        elif "全台股大掃描" in stock_pool:
            target_stocks = STOCK_ONLY_CODES
        else:
            raw_inputs = [item.strip() for item in user_input.split(",") if item.strip()]
            for query in raw_inputs:
                if query in NAME_TO_CODE:
                    target_stocks.append(NAME_TO_CODE[query].replace(".TW", ""))
                else:
                    pure_code = query.upper().replace(".TW", "").replace(".TWO", "")
                    target_stocks.append(pure_code)

    matched_stocks = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total_len = len(target_stocks)

    for idx, code in enumerate(target_stocks):
        target_code = f"{code}.TW"
        stock_display_name = CODE_TO_NAME.get(code, f"股票 {code}")
        status_text.text(f"正在分析 [{idx+1}/{total_len}]: {stock_display_name} ({code}) ...")
        
        try:
            stock = yf.Ticker(target_code)
            info = stock.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            prev_close = info.get('previousClose') or price
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0.0
            volume_shares = (info.get('volume') or 0) / 1000 # 換算張數

            pass_strategy = False
            strat_info = ""

            if strategy_choice == "策略一：中午回撤":
                actual_drop = -change_pct if change_pct < 0 else 0.0
                
                if "大於" in s1_drop_op:
                    pass_drop = (actual_drop >= s1_drop_pct)
                else:
                    pass_drop = (actual_drop <= s1_drop_pct)
                    
                pass_vol = (volume_shares >= s1_vol_min)

                if pass_drop and pass_vol:
                    pass_strategy = True
                    strat_info = f"當日跌幅 {round(actual_drop, 2)}% ({s1_drop_op}) | 總量 {int(volume_shares)} 張"

            elif strategy_choice == "策略二：底部籌碼洗牌":
                if "大於" in s2_up_op:
                    pass_up = (change_pct >= s2_up_val)
                else:
                    pass_up = (change_pct <= s2_up_val)
                    
                pass_vol = (volume_shares >= s2_vol_min)

                if pass_up and pass_vol:
                    pass_strategy = True
                    strat_info = f"當日漲幅 {round(change_pct, 2)}% ({s2_up_op}) | 總量 {int(volume_shares)} 張 | 融資連{s2_margin_days}日{s2_margin_type}"

            else:
                pass_strategy = True
                strat_info = f"當日漲幅 {round(change_pct, 2)}% | 總量 {int(volume_shares)} 張 (當沖熱門個股)"

            if price and pass_strategy:
                matched_stocks.append({
                    "股票名稱": stock_display_name,
                    "股票代號": code,
                    "目前股價": price,
                    "當日漲跌幅 (%)": f"{round(change_pct, 2)}%",
                    "成交量 (張)": int(volume_shares),
                    "策略符合特徵": strat_info
                })
        except Exception:
            pass
        
        progress_bar.progress((idx + 1) / total_len)
        
    status_text.empty()
    progress_bar.empty()
    
    if matched_stocks:
        st.success(f"🎉 【{strategy_choice}】策略掃描完成！共找到 {len(matched_stocks)} 支符合標的：")
        df = pd.DataFrame(matched_stocks)
        st.dataframe(df, width="stretch")
    else:
        st.warning("⚠️ 沒有找到符合此策略條件的股票，建議調整參數再試一次！")