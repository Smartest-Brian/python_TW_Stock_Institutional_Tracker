import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, date, timedelta
import numpy as np

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Taiwan Stock & Foreign Institutional Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Google Font: Outfit & Premium Card layouts)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

/* Main font style */
html, body, [data-testid="stSidebar"] {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Custom Header with Gradient */
.main-title-container {
    padding: 1.5rem 0rem;
}
.main-title {
    font-weight: 700;
    font-size: 2.8rem;
    background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
    letter-spacing: -0.02em;
}
.main-subtitle {
    font-size: 1.1rem;
    color: #8E9CAE;
    margin-top: 0.2rem;
    margin-bottom: 1.5rem;
    font-weight: 400;
}

/* Metric Cards Style */
.custom-card {
    background-color: #1E293B;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    border: 1px solid #334155;
    box-shadow: 0 4px 12px 0 rgba(0, 0, 0, 0.05);
    margin-bottom: 1rem;
}
.card-label {
    font-size: 0.85rem;
    font-weight: 600;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}
.card-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #F8FAFC;
    line-height: 1.2;
}
.card-delta {
    font-size: 0.9rem;
    margin-top: 0.4rem;
    font-weight: 600;
    display: flex;
    align-items: center;
}
.delta-positive {
    color: #10B981;
}
.delta-negative {
    color: #F43F5E;
}
.delta-neutral {
    color: #94A3B8;
}
</style>
""", unsafe_allow_html=True)

# Helper Function: Subtract exactly 6 months
def get_six_months_ago(ref_date):
    year = ref_date.year
    month = ref_date.month
    day = ref_date.day
    
    new_month = month - 6
    new_year = year
    if new_month <= 0:
        new_month += 12
        new_year -= 1
        
    while True:
        try:
            return date(new_year, new_month, day)
        except ValueError:
            # Handle days out of range (e.g. Feb 30 does not exist, so try Feb 29/28)
            day -= 1

# Default date range
DEFAULT_END_DATE = date.today()
DEFAULT_START_DATE = get_six_months_ago(DEFAULT_END_DATE)

# Tickers and ID configurations
ASSET_CONFIGS = {
    "TAIEX (Taiwan Weighted Index)": {
        "yf_ticker": "^TWII",
        "finmind_id": "TAIEX",
        "is_index": True,
        "price_unit": "Points",
        "volume_unit": "NT$ Billion",
        "display_name": "TAIEX Index"
    },
    "2330.TW (TSMC)": {
        "yf_ticker": "2330.TW",
        "finmind_id": "2330",
        "is_index": False,
        "price_unit": "NT$",
        "volume_unit": "Million Shares",
        "display_name": "TSMC (2330)"
    },
    "2317.TW (Foxconn)": {
        "yf_ticker": "2317.TW",
        "finmind_id": "2317",
        "is_index": False,
        "price_unit": "NT$",
        "volume_unit": "Million Shares",
        "display_name": "Foxconn (2317)"
    },
    "2454.TW (MediaTek)": {
        "yf_ticker": "2454.TW",
        "finmind_id": "2454",
        "is_index": False,
        "price_unit": "NT$",
        "volume_unit": "Million Shares",
        "display_name": "MediaTek (2454)"
    },
    "2382.TW (Quanta Computer)": {
        "yf_ticker": "2382.TW",
        "finmind_id": "2382",
        "is_index": False,
        "price_unit": "NT$",
        "volume_unit": "Million Shares",
        "display_name": "Quanta Computer (2382)"
    },
    "2881.TW (Fubon Financial)": {
        "yf_ticker": "2881.TW",
        "finmind_id": "2881",
        "is_index": False,
        "price_unit": "NT$",
        "volume_unit": "Million Shares",
        "display_name": "Fubon Financial (2881)"
    }
}

# Sidebar - Configuration Panel
st.sidebar.markdown("### ⚙️ Control Dashboard")

# Asset selection
selected_asset_name = st.sidebar.selectbox(
    "Target Asset",
    list(ASSET_CONFIGS.keys()),
    index=0
)
config = ASSET_CONFIGS[selected_asset_name]

# Date selection
st.sidebar.markdown("#### Timeframe")
start_input = st.sidebar.date_input("Start Date", DEFAULT_START_DATE)
end_input = st.sidebar.date_input("End Date", DEFAULT_END_DATE)

# Chart type toggle
chart_type = st.sidebar.radio(
    "Price Chart Style",
    ["Candlestick", "Line"],
    index=0
)

# API Token (optional)
st.sidebar.markdown("#### API settings")
finmind_token = st.sidebar.text_input(
    "FinMind API Token (Optional)",
    type="password",
    help="Enter your free or premium token to increase rate limit thresholds."
)

# Fetching & Caching functions
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_prices(ticker, start_date_str, end_date_str):
    try:
        df = yf.download(ticker, start=start_date_str, end=end_date_str)
        if df.empty:
            return pd.DataFrame()
        
        # Flatten MultiIndex columns if necessary
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df = df.reset_index()
        # Convert DatetimeIndex to string date YYYY-MM-DD
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        st.error(f"Error fetching price data from yfinance: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_foreign_investors_data(finmind_id, is_index, start_date_str, end_date_str, token=None):
    url = "https://api.finmindtrade.com/api/v4/data"
    
    # Select appropriate dataset
    dataset = "TaiwanStockTotalInstitutionalInvestors" if is_index else "TaiwanStockInstitutionalInvestorsBuySell"
    
    params = {
        "dataset": dataset,
        "start_date": start_date_str,
        "end_date": end_date_str
    }
    
    if not is_index:
        params["data_id"] = finmind_id
        
    if token:
        params["token"] = token
        
    try:
        response = requests.get(url, params=params, timeout=15)
        res_data = response.json()
        
        if res_data.get("status") == 200:
            df = pd.DataFrame(res_data.get("data", []))
            if df.empty:
                return pd.DataFrame()
            
            # Filter only for Foreign Institutional Investors (Foreign_Investor)
            # In FinMind datasets, name is 'Foreign_Investor'
            df_filtered = df[df["name"] == "Foreign_Investor"].copy()
            
            # Calculate net buy sell (buy - sell)
            df_filtered["net_buy_sell"] = df_filtered["buy"] - df_filtered["sell"]
            return df_filtered[["date", "buy", "sell", "net_buy_sell"]]
        else:
            # Return empty if rate-limited or error
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# Generate realistic mock institutional data in case of API failure
def generate_mock_net_buysell(dates, prices):
    # Create simple net buy/sell values correlated with daily returns for visualization fallback
    np.random.seed(42)
    returns = np.diff(prices) / prices[:-1]
    # pad return with a zero at the beginning
    returns = np.insert(returns, 0, 0.0)
    
    mock_volume = []
    for ret in returns:
        # Net volume is proportional to daily return + some random noise
        noise = np.random.normal(0, 0.01)
        scaled_val = (ret + noise) * 1e8  # scale to NTD value size
        mock_volume.append(scaled_val)
        
    return pd.DataFrame({
        "date": dates,
        "buy": [abs(v)*1.2 for v in mock_volume],
        "sell": [abs(v)*0.8 if v >= 0 else abs(v)*1.5 for v in mock_volume],
        "net_buy_sell": mock_volume
    })

# Main Execution flow
start_str = start_input.strftime("%Y-%m-%d")
end_str = end_input.strftime("%Y-%m-%d")

# Dashboard Title Section
st.markdown(
    f"""
    <div class="main-title-container">
        <h1 class="main-title">Taiwan Stock & Foreign Capital Dashboard</h1>
        <div class="main-subtitle">Interactive analysis of Daily Prices and Foreign Institutional Investors' Net Flows</div>
    </div>
    """, 
    unsafe_allow_html=True
)

# Fetching Data spinner
with st.spinner("Fetching market data..."):
    prices_df = fetch_stock_prices(config["yf_ticker"], start_str, end_str)
    
    if not prices_df.empty:
        # Try fetching foreign investor net flows
        foreign_df = fetch_foreign_investors_data(
            config["finmind_id"], 
            config["is_index"], 
            start_str, 
            end_str, 
            token=finmind_token
        )
        
        using_fallback = False
        if foreign_df.empty:
            using_fallback = True
            st.warning("⚠️ FinMind API rate limits exceeded or service offline. Displaying realistic simulated Foreign Net Buy/Sell volume for visualization.")
            # Generate mock data matching price dates
            dates_list = prices_df["Date"].tolist()
            prices_list = prices_df["Close"].tolist()
            # Scale mock volumes: Index (Billions NTD) vs Stocks (Millions Shares)
            # Default mock is in NTD value, scale down for shares volume
            raw_mock = generate_mock_net_buysell(dates_list, prices_list)
            if not config["is_index"]:
                # Individual stock volumes are usually in shares. A typical volume might be millions of shares.
                # Average daily trading volume of TSMC is ~30-50M shares, foreign net buy/sell ~5-15M shares
                raw_mock["net_buy_sell"] = raw_mock["net_buy_sell"] / 100.0
                raw_mock["buy"] = raw_mock["buy"] / 100.0
                raw_mock["sell"] = raw_mock["sell"] / 100.0
            else:
                # Total market is in NTD. 1e8 to 1e9 NTD range
                raw_mock["net_buy_sell"] = raw_mock["net_buy_sell"] * 100.0
                raw_mock["buy"] = raw_mock["buy"] * 100.0
                raw_mock["sell"] = raw_mock["sell"] * 100.0
            
            foreign_df = raw_mock
            
        # Merge datasets
        merged_df = pd.merge(prices_df, foreign_df, left_on="Date", right_on="date", how="inner")
        
        if not merged_df.empty:
            # Sort chronologically just in case
            merged_df = merged_df.sort_values("Date").reset_index(drop=True)
            
            # Formatted Columns for Volume Display
            if config["is_index"]:
                # Total market values are in NTD. Convert to Billion NTD
                merged_df["net_display"] = merged_df["net_buy_sell"] / 1e9
                merged_df["buy_display"] = merged_df["buy"] / 1e9
                merged_df["sell_display"] = merged_df["sell"] / 1e9
            else:
                # Individual stock volumes are in Shares. Convert to Million Shares
                merged_df["net_display"] = merged_df["net_buy_sell"] / 1e6
                merged_df["buy_display"] = merged_df["buy"] / 1e6
                merged_df["sell_display"] = merged_df["sell"] / 1e6

            # ---------------- KPI CARDS SECTION ----------------
            kpi_cols = st.columns(3)
            
            # Fetch latest and previous values for KPIs
            latest_row = merged_df.iloc[-1]
            prev_row = merged_df.iloc[-2] if len(merged_df) > 1 else latest_row
            
            latest_price = latest_row["Close"]
            prev_price = prev_row["Close"]
            price_diff = latest_price - prev_price
            price_pct = (price_diff / prev_price) * 100 if prev_price != 0 else 0
            
            # Define pricing formats
            price_fmt = f"{latest_price:,.2f}" if config["is_index"] else f"{latest_price:,.1f}"
            diff_fmt = f"{price_diff:+.2f}" if config["is_index"] else f"{price_diff:+.1f}"
            
            # Determine card style color indicators
            price_class = "delta-positive" if price_diff >= 0 else "delta-negative"
            price_arrow = "▲" if price_diff >= 0 else "▼"
            
            latest_net = latest_row["net_display"]
            net_class = "delta-positive" if latest_net >= 0 else "delta-negative"
            net_arrow = "▲ Net Buy" if latest_net >= 0 else "▼ Net Sell"
            
            cumulative_net = merged_df["net_display"].sum()
            cum_class = "delta-positive" if cumulative_net >= 0 else "delta-negative"
            cum_arrow = "▲ Net Accum. Buy" if cumulative_net >= 0 else "▼ Net Accum. Sell"

            with kpi_cols[0]:
                st.markdown(f"""
                <div class="custom-card">
                    <div class="card-label">Latest Closing Price</div>
                    <div class="card-value">{price_fmt} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{config["price_unit"]}</span></div>
                    <div class="card-delta {price_class}">
                        {price_arrow} {diff_fmt} ({price_pct:+.2f}%) <span style="color:#94A3B8; font-weight:normal; margin-left:6px;">vs previous day</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_cols[1]:
                st.markdown(f"""
                <div class="custom-card">
                    <div class="card-label">Foreign Capital Flow (Latest Day)</div>
                    <div class="card-value">{latest_net:+,.2f} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{config["volume_unit"]}</span></div>
                    <div class="card-delta {net_class}">
                        {net_arrow} on {latest_row["Date"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            with kpi_cols[2]:
                st.markdown(f"""
                <div class="custom-card">
                    <div class="card-label">Cumulative Net Flow (6 Months)</div>
                    <div class="card-value">{cumulative_net:+,.2f} <span style="font-size:0.95rem; font-weight:normal; color:#94A3B8;">{config["volume_unit"]}</span></div>
                    <div class="card-delta {cum_class}">
                        {cum_arrow} across the selected period
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # ---------------- CHARTS SECTION ----------------
            st.markdown(f"### 📊 Interactive Analysis: {config['display_name']}")
            
            # Setup Plotly Subplots (shared X-axis)
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                subplot_titles=(
                    f"Price Movement ({config['price_unit']})",
                    f"Foreign Net Buy/Sell Volume ({config['volume_unit']})"
                ),
                row_width=[0.4, 0.6]  # Bottom subplot height 40%, Top subplot height 60%
            )
            
            # Render Top Chart: Candlestick or Line
            if chart_type == "Candlestick":
                fig.add_trace(
                    go.Candlestick(
                        x=merged_df["Date"],
                        open=merged_df["Open"],
                        high=merged_df["High"],
                        low=merged_df["Low"],
                        close=merged_df["Close"],
                        name="Stock Price",
                        increasing_line_color="#10B981", # Emerald
                        decreasing_line_color="#F43F5E", # Rose
                        increasing_fillcolor="rgba(16, 185, 129, 0.3)",
                        decreasing_fillcolor="rgba(244, 63, 94, 0.3)"
                    ),
                    row=1, col=1
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=merged_df["Date"],
                        y=merged_df["Close"],
                        mode="lines",
                        name="Price (Close)",
                        line=dict(color="#3B82F6", width=2.5), # Sleek Blue
                        fill='tozeroy',
                        fillcolor='rgba(59, 130, 246, 0.05)' # light gradient feel
                    ),
                    row=1, col=1
                )
                
            # Render Bottom Chart: Color-Coded Bar Chart
            bar_colors = ["#10B981" if val >= 0 else "#F43F5E" for val in merged_df["net_display"]]
            fig.add_trace(
                go.Bar(
                    x=merged_df["Date"],
                    y=merged_df["net_display"],
                    marker=dict(
                        color=bar_colors,
                        line=dict(color=bar_colors, width=0.5)
                    ),
                    name="Net Buy/Sell Volume",
                    hovertemplate="%{x}<br>Net Flow: %{y:+.2f} " + config['volume_unit'] + "<extra></extra>"
                ),
                row=2, col=1
            )
            
            # Configure Layout
            fig.update_layout(
                height=650,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False,
                xaxis_rangeslider_visible=False,
                xaxis2_rangeslider_visible=False,
                hovermode="x unified",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Outfit", color="#94A3B8")
            )
            
            # Style subplots grid and axes
            fig.update_xaxes(
                showgrid=True,
                gridcolor="#334155",
                gridwidth=0.5,
                zeroline=False,
                row=1, col=1
            )
            fig.update_xaxes(
                showgrid=True,
                gridcolor="#334155",
                gridwidth=0.5,
                zeroline=False,
                row=2, col=1
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor="#334155",
                gridwidth=0.5,
                zeroline=False,
                row=1, col=1
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor="#334155",
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor="#475569",
                row=2, col=1
            )
            
            # Render to streamlit page
            st.plotly_chart(fig, use_container_width=True)

            # ---------------- RECENT DATA TABLE & EXPORT ----------------
            st.markdown("### 📋 Recent Historical Transactions")
            
            # Prepare clean historical dataframe for display & download
            export_df = merged_df[["Date", "Open", "High", "Low", "Close", "Volume", "buy_display", "sell_display", "net_display"]].copy()
            export_df.columns = ["Date", "Open", "High", "Low", "Close", "Market Volume", "Foreign Buy", "Foreign Sell", "Foreign Net Flow"]
            
            # Format display df (reverse chronological for reading latest first)
            display_df = export_df.sort_values("Date", ascending=False).copy()
            
            # Round numeric columns for tabular aesthetics
            format_dict = {
                "Open": "{:,.2f}" if config["is_index"] else "{:,.1f}",
                "High": "{:,.2f}" if config["is_index"] else "{:,.1f}",
                "Low": "{:,.2f}" if config["is_index"] else "{:,.1f}",
                "Close": "{:,.2f}" if config["is_index"] else "{:,.1f}",
                "Market Volume": "{:,.0f}",
                "Foreign Buy": "{:,.2f}",
                "Foreign Sell": "{:,.2f}",
                "Foreign Net Flow": "{:+.2f}"
            }
            
            # Render DataFrame and CSV download button
            tbl_col, btn_col = st.columns([4, 1])
            with tbl_col:
                # Style rows beautifully and limit default view to 10 entries with scroll option
                st.dataframe(
                    display_df.style.format(format_dict),
                    use_container_width=True,
                    height=280
                )
                
            with btn_col:
                st.markdown("<br>", unsafe_allow_html=True)
                csv = export_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Full Merged CSV",
                    data=csv,
                    file_name=f"{config['finmind_id']}_merged_history_{start_str}_to_{end_str}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                st.markdown(
                    f"""
                    <div style="background-color: #0F172A; border-radius: 8px; padding: 1rem; border: 1px dashed #334155; font-size: 0.85rem; color: #94A3B8; margin-top: 1rem;">
                        <strong>Data Summary</strong><br>
                        • Total Days: {len(merged_df)}<br>
                        • Buy Unit: {config['volume_unit']}<br>
                        • Price Unit: {config['price_unit']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.error("No overlap dates found between Price dataset and Foreign Investor dataset. Adjust the timeframe or verify data source stability.")
    else:
        st.error(f"Failed to fetch stock prices for ticker '{config['yf_ticker']}' via yfinance. Please verify the stock ticker symbol or network settings.")
