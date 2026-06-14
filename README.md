# Taiwan Stock & Foreign Institutional Tracker

An interactive, premium-designed financial dashboard built in Python using **Streamlit** and **Plotly**. It visualizes daily stock price trends alongside Foreign Institutional Investors' Net Buy/Sell volume over a rolling 6-month period for TAIEX and the top 5 weighted stocks in the Taiwan market.

---

## Features

1. **Dynamic Timeframe**: Automatically calculates a rolling 6-month historical window from the current execution date.
2. **Assets Tracked**:
   - **TAIEX** (Taiwan Capitalization Weighted Stock Index)
   - **TSMC** (2330.TW)
   - **Foxconn** (2317.TW)
   - **MediaTek** (2454.TW)
   - **Quanta Computer** (2382.TW)
   - **Fubon Financial** (2881.TW)
3. **Dual-Axis Subplots**:
   - **Top Subplot**: Interactive price charts supporting both **Candlestick** and **Line** layouts.
   - **Bottom Subplot**: Color-coded bar charts showing Foreign Institutional Investors' Net Flows (Emerald Green for net buys, Rose Red for net sells).
4. **Key Metric Indicators**: High-level KPI cards displaying the latest closing price, daily changes, daily net capital flows, and cumulative flows for the selected timeframe.
5. **Robust Caching & Rate Limiting**: Implements Streamlit `st.cache_data` (1-hour TTL) and a realistic fallback simulation layer to prevent API blocks or app crashes.
6. **Data Export**: Displays recent transaction records in an interactive table with a direct download button to export the combined datasets as CSV.

---

## Installation & Setup

Ensure you have **Python 3.11+** installed.

### 1. Clone or Open the Workspace
Navigate to the project root directory:
```bash
cd python_TW_Stock_Foreign_Tracker
```

### 2. Set Up a Virtual Environment (Recommended)
If you do not have a virtual environment initialized, create one:
```bash
python3 -m venv .venv
```

Activate the virtual environment:
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```
- **Windows (Command Prompt)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

### 3. Install Dependencies
Install all package dependencies declared in `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## How to Execute

To launch the interactive dashboard locally, execute the following command in your terminal:

```bash
streamlit run app.py
```

Once running, Streamlit will print the local host URLs. Your web browser should open the dashboard automatically. If it doesn't, navigate to:
👉 **[http://localhost:8501](http://localhost:8501)**

### Dashboard Control Panel (Sidebar)
- **Target Asset**: Select between TAIEX or the top 5 stocks.
- **Timeframe (Start/End Date)**: Customize the date range for your analysis (defaults to the last 6 months).
- **Price Chart Style**: Toggle the main price visualization between **Candlestick** and **Line** views.
- **FinMind API Token (Optional)**: Input your FinMind API token to increase API rate limits (useful if you query multiple stocks rapidly).