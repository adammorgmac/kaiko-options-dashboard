"""
Kaiko API wrapper for fetching cryptocurrency options data.
Handles authentication, data fetching, and error handling.
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class KaikoAPI:
    """Wrapper class for Kaiko API calls"""

    def __init__(self, api_key: str):
        """
        Initialize Kaiko API client.

        Args:
            api_key: Your Kaiko API key
        """
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'X-Api-Key': api_key
        }
        self.base_url = "https://us.market-api.kaiko.io"

    def convert_date(self, date) -> str:
        """
        Converts pandas datetime to Kaiko API format (UTC).

        Args:
            date: String or pandas datetime object

        Returns:
            ISO 8601 formatted string with milliseconds
        """
        if isinstance(date, str):
            date = pd.to_datetime(date)
        return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def get_spot_price(self, base: str, quote: str) -> float:
        """
        Fetch current spot price from Kaiko OHLCV endpoint.

        Args:
            base: Base asset (e.g., 'btc')
            quote: Quote currency (e.g., 'usd')

        Returns:
            Current spot price as float, or None if unavailable
        """
        # Try multiple exchanges for spot price
        exchanges = ['cbse', 'krkn', 'bnce']  # Coinbase, Kraken, Binance

        for exchange in exchanges:
            try:
                url = f"{self.base_url}/v2/data/trades.v1/exchanges/{exchange}/spot/{base}-{quote}/aggregations/count_ohlcv_vwap"
                params = {
                    'page_size': 1,
                    'sort': 'desc',
                    'interval': '1m'
                }

                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                result = data.get('data', [])
                if result and len(result) > 0:
                    # Use VWAP as spot price
                    price = result[0].get('price')
                    if price:
                        return float(price)

            except Exception as e:
                continue  # Try next exchange

        # If all exchanges fail, return None
        print(f"Could not fetch spot price for {base}-{quote}")
        return None

    def get_instruments(self, base: str, quote: str, start_date: datetime,
                       end_date: datetime, exchange: str = 'drbt') -> pd.DataFrame:
        """
        Fetch available option instruments from Kaiko Reference API.

        Args:
            base: Base asset (e.g., 'btc', 'eth')
            quote: Quote currency (e.g., 'usd', 'usdc')
            start_date: Start date for filtering
            end_date: End date for filtering
            exchange: Exchange code (default: 'drbt' for Deribit)

        Returns:
            DataFrame with instrument details (strike, expiry, option_type, etc.)
        """
        url = f"{self.base_url}/v2/data/derivatives.v2/reference"
        params = {
            'exchange': exchange,
            'instrument_class': 'option',
            'base_assets': base,
            'quote_assets': quote,
            'start_time': self.convert_date(start_date),
            'end_time': self.convert_date(end_date)
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            instruments = data.get('data', [])

            if not instruments:
                return pd.DataFrame()

            df = pd.DataFrame(instruments)
            return df

        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching instruments: {e}")
            return pd.DataFrame()

    def get_expiries(self, base: str, quote: str, start_date: datetime,
                    end_date: datetime, exchange: str = 'drbt') -> List[str]:
        """
        Get list of unique expiry dates for options.

        Args:
            base: Base asset (e.g., 'btc', 'eth')
            quote: Quote currency (e.g., 'usd', 'usdc')
            start_date: Start date for filtering
            end_date: End date for filtering
            exchange: Exchange code (default: 'drbt')

        Returns:
            Sorted list of expiry date strings
        """
        df = self.get_instruments(base, quote, start_date, end_date, exchange)

        if df.empty:
            return []

        expiries = df['expiry'].dropna().unique().tolist()
        expiries = [e for e in expiries if e and e.strip()]
        expiries = sorted(expiries)
        return expiries

    def get_risk_data(self, instrument: str, exchange: str = 'drbt',
                     page_size: int = 1) -> Dict[str, Any]:
        """
        Fetch risk data (OI, IV, Greeks) for a specific instrument.

        Args:
            instrument: Instrument code (e.g., 'btc27mar26125000p')
            exchange: Exchange code (default: 'drbt')
            page_size: Number of records to fetch (default: 1 for latest)

        Returns:
            Dictionary with latest risk metrics, or empty dict if not available
        """
        url = f"{self.base_url}/v2/data/derivatives.v2/risk"
        params = {
            'exchange': exchange,
            'instrument_class': 'option',
            'instrument': instrument,
            'page_size': page_size,
            'sort': 'desc'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json().get('data', [])

            if data:
                return data[0]
            return {}

        except requests.exceptions.RequestException:
            return {}

    def _fetch_single_instrument_risk(self, row: pd.Series, exchange: str) -> Optional[Dict]:
        """
        Helper function to fetch risk data for a single instrument (for parallel execution).

        Args:
            row: Row from instruments DataFrame
            exchange: Exchange code

        Returns:
            Dictionary with instrument data or None
        """
        instrument = row['instrument']
        risk = self.get_risk_data(instrument, exchange)

        if not risk:
            return None

        def to_float(val):
            try:
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        return {
            'instrument': instrument,
            'strike_price': to_float(row.get('strike_price')),
            'option_type': 'call' if instrument.lower().endswith('c') else 'put',
            'expiry': row.get('expiry'),
            'open_interest': to_float(risk.get('open_interest')),
            'mark_iv': to_float(risk.get('mark_iv')),
            'bid_iv': to_float(risk.get('bid_iv')),
            'ask_iv': to_float(risk.get('ask_iv')),
            'delta': to_float(risk.get('delta')),
            'gamma': to_float(risk.get('gamma')),
            'vega': to_float(risk.get('vega')),
            'theta': to_float(risk.get('theta')),
            'rho': to_float(risk.get('rho'))
        }

    def get_options_data(self, base: str, quote: str, expiry: str,
                        exchange: str = 'drbt', max_instruments: int = None,
                        atm_filter_pct: float = None) -> pd.DataFrame:
        """
        Fetch complete options data (instruments + risk metrics) for a specific expiry.
        Uses parallel fetching for 5-10x speed improvement.

        Args:
            base: Base asset (e.g., 'btc', 'eth')
            quote: Quote currency (e.g., 'usd', 'usdc')
            expiry: Specific expiry date (from get_expiries)
            exchange: Exchange code (default: 'drbt')
            max_instruments: Limit number of instruments (for testing/speed)
            atm_filter_pct: If set, only fetch strikes within this % of estimated ATM
                           (e.g., 0.2 = ±20% from ATM). Speeds up fetching significantly.

        Returns:
            DataFrame with columns: instrument, strike_price, option_type, expiry,
                                   open_interest, mark_iv, delta, gamma, etc.
        """
        expiry_date = pd.to_datetime(expiry)
        start_date = expiry_date - timedelta(days=30)
        end_date = expiry_date + timedelta(days=1)

        instruments_df = self.get_instruments(base, quote, start_date, end_date, exchange)

        if instruments_df.empty:
            return pd.DataFrame()

        instruments_df = instruments_df[instruments_df['expiry'] == expiry].copy()

        if instruments_df.empty:
            return pd.DataFrame()

        # ATM Filter: Only fetch strikes near current price
        if atm_filter_pct and 'strike_price' in instruments_df.columns:
            instruments_df['strike_price_num'] = pd.to_numeric(instruments_df['strike_price'], errors='coerce')
            instruments_df = instruments_df[instruments_df['strike_price_num'].notna()]

            if not instruments_df.empty:
                # Estimate ATM as median strike
                estimated_atm = instruments_df['strike_price_num'].median()
                lower_bound = estimated_atm * (1 - atm_filter_pct)
                upper_bound = estimated_atm * (1 + atm_filter_pct)

                instruments_df = instruments_df[\
                    (instruments_df['strike_price_num'] >= lower_bound) &\
                    (instruments_df['strike_price_num'] <= upper_bound)\
                ]

        if max_instruments:
            instruments_df = instruments_df.head(max_instruments)

        total = len(instruments_df)

        if total == 0:
            return pd.DataFrame()

        # Parallel fetching with ThreadPoolExecutor
        risk_data = []
        completed = 0

        # Use 10 parallel workers (adjust based on API rate limits)
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_row = {
                executor.submit(self._fetch_single_instrument_risk, row, exchange): idx
                for idx, row in instruments_df.iterrows()
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_row):
                completed += 1

                result = future.result()
                if result:
                    risk_data.append(result)

        if not risk_data:
            return pd.DataFrame()

        result_df = pd.DataFrame(risk_data)
        return result_df

    def get_multi_expiry_options_data(self, base: str, quote: str, expiries: List[str],
                                     exchange: str = 'drbt', max_instruments_per_expiry: int = None,
                                     atm_filter_pct: float = None) -> pd.DataFrame:
        """
        Fetch options data for multiple expiries at once.

        Args:
            base: Base asset (e.g., 'btc', 'eth')
            quote: Quote currency (e.g., 'usd', 'usdc')
            expiries: List of expiry dates to fetch
            exchange: Exchange code (default: 'drbt')
            max_instruments_per_expiry: Limit per expiry
            atm_filter_pct: ATM filter percentage

        Returns:
            Combined DataFrame with all expiries
        """
        all_data = []

        for expiry in expiries:
            try:
                expiry_data = self.get_options_data(
                    base=base,
                    quote=quote,
                    expiry=expiry,
                    exchange=exchange,
                    max_instruments=max_instruments_per_expiry,
                    atm_filter_pct=atm_filter_pct
                )

                if not expiry_data.empty:
                    all_data.append(expiry_data)

            except Exception as e:
                print(f"Error fetching {expiry}: {e}")
                continue

        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()

    def get_kaiko_iv_smile(self, base: str, quote: str, value_time: str, 
                        expiry: str, strikes: List[float] = None, 
                        exchange: str = 'drbt') -> Dict[str, Any]:
        """
        Fetch Kaiko's proprietary IV smile calculation for specific strikes.
        
        Args:
            base: Asset (btc, eth, sol, xrp)
            quote: Quote currency (usd, usdc)
            value_time: Valuation timestamp (ISO format)
            expiry: Option expiry (ISO format)
            strikes: List of strike prices to calculate IV for
            exchange: Exchange code (default: drbt)
        
        Returns:
            Dictionary with IV smile data
        """
        url = f"{self.base_url}/v2/data/analytics.v2/implied_volatility_smile"
        
        if strikes and len(strikes) > 0:
            # Use specific strikes
            strikes_str = ",".join([str(int(s)) for s in sorted(strikes)])
            
            params = {
                'base': base,
                'quote': quote,
                'value_time': value_time,
                'expiry': expiry,
                'exchanges': exchange,
                'strikes': strikes_str
            }
        else:
            # Fallback to deltas if no strikes provided
            deltas = ",".join([str(round(d, 2)) for d in np.arange(0.05, 1.0, 0.05)])
            
            params = {
                'base': base,
                'quote': quote,
                'value_time': value_time,
                'expiry': expiry,
                'exchanges': exchange,
                'deltas': deltas
            }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Kaiko IV smile: {e}")
            return {'data': []}

    def get_iv_surface(self, base: str, quote: str, value_time: datetime,
                      tte_min: float = 0.01, tte_max: float = 1.0,
                      tte_step: float = 0.02) -> pd.DataFrame:
        """
        Fetch IV surface data from Kaiko API using delta grid.

        Args:
            base: Base currency (e.g., 'btc')
            quote: Quote currency (e.g., 'usd')
            value_time: Timestamp for the surface
            tte_min: Minimum time to expiry in years
            tte_max: Maximum time to expiry in years
            tte_step: Step size for time to expiry

        Returns:
            DataFrame with IV surface data
        """
        delta_min = 0.1
        delta_max = 0.9
        delta_step = 0.1

        value_time_str = value_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

        url = f"{self.base_url}/v2/data/analytics.v2/implied_volatility_surface"
        params = {
            "base": base,
            "quote": quote,
            "exchanges": "drbt",
            "value_time": value_time_str,
            "tte_min": tte_min,
            "tte_max": tte_max,
            "tte_step": tte_step,
            "delta_min": delta_min,
            "delta_max": delta_max,
            "delta_step": delta_step
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            rows = []
            for surface in data.get("data", []):
                expiry = surface.get("expiry")
                tte = surface.get("time_to_expiry")

                for point in surface.get("implied_volatilities", []):
                    rows.append({
                        "delta": point.get("delta"),
                        "implied_volatility": point.get("implied_volatility"),
                        "time_to_expiry": tte,
                        "expiry": expiry
                    })

            if rows:
                return pd.DataFrame(rows)
            else:
                return pd.DataFrame()

        except Exception as e:
            st.error(f"Error fetching IV surface: {e}")
            return pd.DataFrame()