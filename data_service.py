import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import date, datetime
from typing import Tuple, List

class AssetConfig:
    """
    Represents the configuration and metadata of a target financial asset.
    Supports index tracking (TAIEX) and stock tracking.
    """
    def __init__(self, ticker: str, finmind_id: str, is_index: bool, display_name: str, price_unit: str, volume_unit: str):
        self.ticker = ticker
        self.finmind_id = finmind_id
        self.is_index = is_index
        self.display_name = display_name
        self.price_unit = price_unit
        self.volume_unit = volume_unit

    @classmethod
    def from_ticker(cls, ticker_input: str) -> "AssetConfig":
        """
        Factory method to dynamically construct an AssetConfig from any user-input ticker.
        E.g. "2330", "2330.TW", "^TWII", or "TAIEX"
        """
        ticker_clean = ticker_input.strip().upper()
        
        # Handle index case
        if ticker_clean == "^TWII" or ticker_clean == "TAIEX":
            return cls(
                ticker="^TWII",
                finmind_id="TAIEX",
                is_index=True,
                display_name="TAIEX Index",
                price_unit="Points",
                volume_unit="NT$ Billion"
            )
        
        # Normalize stock code: "2330.TW" -> "2330", "2330" -> "2330"
        code = ticker_clean
        if "." in ticker_clean:
            code = ticker_clean.split(".")[0]
            
        if code.isdigit():
            # Standard Taiwan Stock
            yf_ticker = f"{code}.TW"
            return cls(
                ticker=yf_ticker,
                finmind_id=code,
                is_index=False,
                display_name=f"Stock {code}",
                price_unit="NT$",
                volume_unit="Million Shares"
            )
        else:
            # Fallback configuration for any unrecognized stock symbol input
            return cls(
                ticker=ticker_clean,
                finmind_id=ticker_clean,
                is_index=False,
                display_name=ticker_clean,
                price_unit="NT$",
                volume_unit="Million Shares"
            )


class DataFetcher:
    """
    Handles daily price fetches from yfinance and institutional flows from FinMind API.
    """
    @staticmethod
    def fetch_prices(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches daily prices from yfinance and cleans columns.
        """
        try:
            from datetime import datetime, timedelta
            # yfinance end_date is exclusive, add 1 day to make it inclusive
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_inclusive = (end_date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
            
            df = yf.download(ticker, start=start_date, end=end_inclusive)
            if df.empty:
                return pd.DataFrame()
            
            # Remove MultiIndex level in columns if present (common in newer yfinance versions)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
                
            df = df.reset_index()
            # Convert DatetimeIndex or Timestamp to string date representation (YYYY-MM-DD)
            df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
            return df
        except Exception as e:
            print(f"Error fetching prices for {ticker}: {e}")
            return pd.DataFrame()

    @staticmethod
    def fetch_institutional_flows(finmind_id: str, is_index: bool, start_date: str, end_date: str, token: str = None, investor_type: str = "Foreign Investors (外資)") -> pd.DataFrame:
        """
        Fetches institutional net buys/sells from FinMind API and filters by investor type.
        """
        url = "https://api.finmindtrade.com/api/v4/data"
        dataset = "TaiwanStockTotalInstitutionalInvestors" if is_index else "TaiwanStockInstitutionalInvestorsBuySell"
        
        params = {
            "dataset": dataset,
            "start_date": start_date,
            "end_date": end_date
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
                
                # Filter specifically for the chosen Institutional Investor
                if investor_type == "Summary (綜合比較)":
                    foreign_names = ["Foreign_Investor", "Foreign_Dealer_Self"]
                    trust_names = ["Investment_Trust"]
                    dealer_names = ["Dealer_self", "Dealer_Hedging"]
                    all_names = foreign_names + trust_names + dealer_names
                    
                    df_filtered = df[df["name"].isin(all_names)].copy()
                    if df_filtered.empty:
                        return pd.DataFrame()
                        
                    df_filtered["net"] = df_filtered["buy"] - df_filtered["sell"]
                    
                    def assign_group(name):
                        if name in foreign_names: return "Foreign"
                        if name in trust_names: return "Trust"
                        if name in dealer_names: return "Dealer"
                        return "Other"
                        
                    df_filtered["group"] = df_filtered["name"].apply(assign_group)
                    
                    df_group = df_filtered.groupby(["date", "group"])["net"].sum().reset_index()
                    df_wide = df_group.pivot(index="date", columns="group", values="net").fillna(0).reset_index()
                    
                    for col in ["Foreign", "Trust", "Dealer"]:
                        if col not in df_wide.columns:
                            df_wide[col] = 0.0
                            
                    df_total = df_filtered.groupby("date")[["buy", "sell"]].sum().reset_index()
                    df_total["net_buy_sell"] = df_total["buy"] - df_total["sell"]
                    
                    df_final = pd.merge(df_total, df_wide, on="date", how="left")
                    return df_final
                elif investor_type == "Foreign Investors (外資)":
                    names = ["Foreign_Investor", "Foreign_Dealer_Self"]
                elif investor_type == "Investment Trust (投信)":
                    names = ["Investment_Trust"]
                elif investor_type == "Dealers (自營商)":
                    names = ["Dealer_self", "Dealer_Hedging"]
                elif investor_type == "Total Institutional (三大法人合計)":
                    names = ["Foreign_Investor", "Foreign_Dealer_Self", "Investment_Trust", "Dealer_self", "Dealer_Hedging"]
                else:
                    names = ["Foreign_Investor"]

                df_filtered = df[df["name"].isin(names)].copy()
                if df_filtered.empty:
                    return pd.DataFrame()
                
                # Aggregate by date
                df_agg = df_filtered.groupby("date")[["buy", "sell"]].sum().reset_index()
                df_agg["net_buy_sell"] = df_agg["buy"] - df_agg["sell"]
                return df_agg[["date", "buy", "sell", "net_buy_sell"]]
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()


class FallbackGenerator:
    """
    Generates return-correlated simulation data when the external API rate limit is exceeded.
    """
    @staticmethod
    def generate_mock_flows(dates: List[str], prices: List[float], is_index: bool) -> pd.DataFrame:
        """
        Generates daily buy/sell volumes correlated with asset price returns.
        """
        np.random.seed(42)
        prices_arr = np.array(prices)
        returns = np.diff(prices_arr) / prices_arr[:-1]
        returns = np.insert(returns, 0, 0.0)
        
        mock_volume = []
        for ret in returns:
            # Net flow is proportional to returns plus random normal noise
            noise = np.random.normal(0, 0.01)
            val = (ret + noise) * 1e8
            mock_volume.append(val)
            
        # Scale differently for Index (NTD) vs Stock (Shares)
        scale = 100.0 if is_index else 0.01
        scaled_net = [v * scale for v in mock_volume]
        
        return pd.DataFrame({
            "date": dates,
            "buy": [abs(v) * 1.2 * scale for v in mock_volume],
            "sell": [abs(v) * 0.8 * scale if v >= 0 else abs(v) * 1.5 * scale for v in mock_volume],
            "net_buy_sell": scaled_net
        })


class MarketDataService:
    """
    Coordinator class orchestrating fetch operations, mock fallbacks, and column formatting.
    """
    def __init__(self, token: str = None):
        self.token = token

    def get_merged_data(self, asset: AssetConfig, start_date: str, end_date: str, investor_type: str = "Foreign Investors (外資)") -> Tuple[pd.DataFrame, bool]:
        """
        Fetches, aligns, and merges stock price and institutional net flows.
        Returns a tuple of (merged_df, using_mock_fallback).
        """
        prices_df = DataFetcher.fetch_prices(asset.ticker, start_date, end_date)
        if prices_df.empty:
            return pd.DataFrame(), False
            
        flows_df = DataFetcher.fetch_institutional_flows(asset.finmind_id, asset.is_index, start_date, end_date, self.token, investor_type)
        
        is_mocked = False
        if flows_df.empty:
            is_mocked = True
            # Activate simulation fallback when FinMind data is missing/rate-limited
            dates = prices_df["Date"].tolist()
            prices = prices_df["Close"].tolist()
            flows_df = FallbackGenerator.generate_mock_flows(dates, prices, asset.is_index)
            if investor_type == "Summary (綜合比較)":
                flows_df["Foreign"] = flows_df["net_buy_sell"] * 0.6
                flows_df["Trust"] = flows_df["net_buy_sell"] * 0.3
                flows_df["Dealer"] = flows_df["net_buy_sell"] * 0.1
            
        # Aligns price dates and flow dates
        merged_df = pd.merge(prices_df, flows_df, left_on="Date", right_on="date", how="outer")
        if merged_df.empty:
            return pd.DataFrame(), False
            
        merged_df["Date"] = merged_df["Date"].fillna(merged_df["date"])
        merged_df = merged_df.sort_values("Date").reset_index(drop=True)
        
        # Mark missing data
        merged_df["Price_Missing"] = merged_df["Close"].isna()
        merged_df["Flow_Missing"] = merged_df["net_buy_sell"].isna()
        
        # Forward fill missing prices for continuous charting
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].ffill()
                
        # Fill missing institutional flows with 0
        for col in ["buy", "sell", "net_buy_sell"]:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].fillna(0)

        
        # Scale values: Index in Billions of NTD (10^9), Stocks in Millions of Shares (10^6)
        scale_factor = 1e9 if asset.is_index else 1e6
        merged_df["net_display"] = merged_df["net_buy_sell"] / scale_factor
        merged_df["buy_display"] = merged_df["buy"] / scale_factor
        merged_df["sell_display"] = merged_df["sell"] / scale_factor
        
        if investor_type == "Summary (綜合比較)":
            for col in ["Foreign", "Trust", "Dealer"]:
                if col in merged_df.columns:
                    merged_df[f"net_{col}_display"] = merged_df[col] / scale_factor
                else:
                    merged_df[f"net_{col}_display"] = 0.0
                    
        return merged_df, is_mocked
