"""
Kaiko Options Analytics Dashboard
Displays Open Interest and Implied Volatility for cryptocurrency options
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timezone, timedelta
from utils.kaiko_api import KaikoAPI

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="Kaiko Options Analytics",
    page_icon="./assets/kaiko_icon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize API client
@st.cache_resource
def get_api_client():
    """Initialize and cache the Kaiko API client"""
    return KaikoAPI(st.secrets["KAIKO_API_KEY"])

api = get_api_client()

# Kaiko brand colors
KAIKO_NAVY = "#000046"
KAIKO_ORANGE = "#FC9E21"
KAIKO_LIGHT_ORANGE = "#FCB51E"
KAIKO_BLUE = "#003DA6"
KAIKO_LIGHT_BLUE = "#99D1FF"

# Helper function for formatting large numbers
def format_large_number(value, precision=1):
    """Format large numbers with M/B suffixes"""
    if pd.isna(value):
        return "N/A"
    
    abs_value = abs(value)
    
    if abs_value >= 1e9:
        return f"${value/1e9:.{precision}f}B"
    elif abs_value >= 1e6:
        return f"${value/1e6:.{precision}f}M"
    elif abs_value >= 1e3:
        return f"${value/1e3:.{precision}f}K"
    else:
        return f"${value:.{precision}f}"

# ============================================================================
# PASSWORD PROTECTION
# ============================================================================

def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "🔐 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.info("Please enter the password to access the dashboard.")
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "🔐 Enter Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# ============================================================================
# MAIN APP (Only shown after password is correct)
# ============================================================================

# Custom CSS for Kaiko branding
st.markdown(f"""
<style>
    /* Kaiko brand colors */
    :root {{
        --kaiko-navy: {KAIKO_NAVY};
        --kaiko-orange: {KAIKO_ORANGE};
        --kaiko-blue: {KAIKO_BLUE};
    }}
    
    /* Style headers */
    h1, h2, h3 {{
        color: var(--kaiko-navy) !important;
    }}
    
    /* Style metrics */
    [data-testid="stMetricValue"] {{
        color: var(--kaiko-navy) !important;
    }}
    
    /* Custom styling for tabs */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-bottom-color: var(--kaiko-orange) !important;
    }}
    
    /* Footer branding */
    footer {{
        visibility: hidden;
    }}
    footer:after {{
        content:'Kaiko © 2026';
        visibility: visible;
        display: block;
        position: relative;
        padding: 5px;
        top: 2px;
        color: var(--kaiko-navy);
    }}
</style>
""", unsafe_allow_html=True)

# Center the logo and title
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    # Logo above
    st.image("assets/kaiko_logo.png", width=100)
    
    # Title below
    st.title("Options Analytics Dashboard")
    st.markdown("Derivatives analysis powered by Kaiko Research")

st.markdown("""
Analyze cryptocurrency options data from Deribit including:
- **Open Interest** by strike price (in contracts & USD notional)
- **Implied Volatility** smile
- **Gamma Concentration** analysis (USD notional per 1% move)
- **Multi-Expiry** comparison across different expiration dates
- **Call/Put** comparisons
- **3D Volatility Surface**
""")

st.divider()

# ============================================================================
# SIDEBAR CONTROLS
# ============================================================================

st.sidebar.header("Configuration")

# Asset selection
asset = st.sidebar.selectbox(
    "Select Asset",
    options=["BTC", "ETH", "SOL", "XRP"],
    index=0
)

# Quote currency mapping
quote_map = {
    "BTC": "usd",
    "ETH": "usd", 
    "SOL": "usd",
    "XRP": "usd",
}
quote = quote_map[asset]

# Date range for fetching available expiries
st.sidebar.subheader("Date Range")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now().date(),
        key="start_date"
    )
with col2:
    end_date = st.date_input(
        "End Date", 
        value=(datetime.now() + timedelta(days=90)).date(),
        key="end_date"
    )

# Fetch expiries button
if st.sidebar.button("🔍 Load Expiries", type="primary", use_container_width=True):
    with st.spinner("Fetching available expiry dates..."):
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        expiries = api.get_expiries(
            base=asset.lower(),
            quote=quote,
            start_date=start_dt,
            end_date=end_dt
        )
        
        if expiries:
            st.session_state['expiries'] = expiries
            st.sidebar.success(f"✅ Found {len(expiries)} expiry dates")
        else:
            st.sidebar.error("❌ No expiry dates found for this date range")
            st.session_state['expiries'] = []

# Expiry selection (only show if expiries are loaded)
if 'expiries' in st.session_state and st.session_state['expiries']:
    selected_expiry = st.sidebar.selectbox(
        "Select Expiry Date",
        options=st.session_state['expiries'],
        key="selected_expiry"
    )
else:
    st.sidebar.info("👆 Click 'Load Expiries' to see available dates")
    selected_expiry = None

st.sidebar.divider()

# Performance settings
st.sidebar.subheader("⚡ Performance Settings")

# ATM Filter
use_atm_filter = st.sidebar.checkbox(
    "Filter by ATM strikes only",
    value=True,
    help="Only fetch strikes near the money (±30%). Much faster!"
)

if use_atm_filter:
    atm_filter_pct = st.sidebar.slider(
        "ATM Range (%)",
        min_value=10,
        max_value=50,
        value=30,
        step=5,
        help="Fetch strikes within ±X% of estimated ATM price"
    ) / 100
else:
    atm_filter_pct = None

# Max instruments
max_instruments = st.sidebar.number_input(
    "Max instruments (0 = unlimited)",
    min_value=0,
    max_value=500,
    value=0 if not use_atm_filter else 0,
    step=10,
    help="Additional limit on number of instruments"
)

st.sidebar.divider()

# Fetch data button (only enabled if expiry is selected)
fetch_disabled = selected_expiry is None

# Create cache key for data
if selected_expiry:
    cache_key = f"{asset}_{selected_expiry}_{use_atm_filter}_{atm_filter_pct}_{max_instruments}"
else:
    cache_key = None

if st.sidebar.button(
    "📊 Fetch Options Data", 
    type="primary", 
    disabled=fetch_disabled,
    use_container_width=True
):
    st.session_state['fetch_clicked'] = True
    st.session_state['cache_key'] = cache_key
else:
    if 'fetch_clicked' not in st.session_state:
        st.session_state['fetch_clicked'] = False

# ============================================================================
# MAIN CONTENT - DATA FETCHING WITH CACHING
# ============================================================================

if st.session_state.get('fetch_clicked') and selected_expiry:
    
    # Check if we have cached data
    if 'cached_data' in st.session_state and st.session_state.get('cache_key') == cache_key:
        options_df = st.session_state['cached_data']
        spot_price = st.session_state.get('cached_spot_price')
        st.info("✨ Using cached data (click 'Fetch Options Data' again to refresh)")
    else:
        # Fetch new data with clean progress
        progress_placeholder = st.empty()
        
        with progress_placeholder:
            with st.spinner(f"⚡ Fetching options data for {asset} expiring {selected_expiry}..."):
                try:
                    # Fetch spot price (non-blocking - use fallback if fails)
                    try:
                        spot_price = api.get_spot_price(base=asset.lower(), quote=quote)
                    except:
                        spot_price = None
                    
                    # Fetch options data
                    options_df = api.get_options_data(
                        base=asset.lower(),
                        quote=quote,
                        expiry=selected_expiry,
                        max_instruments=max_instruments if max_instruments > 0 else None,
                        atm_filter_pct=atm_filter_pct
                    )
                    
                    # Cache the data
                    st.session_state['cached_data'] = options_df
                    st.session_state['cached_spot_price'] = spot_price
                    st.session_state['cache_key'] = cache_key
                    
                except Exception as e:
                    st.error(f"Error fetching data: {e}")
                    options_df = pd.DataFrame()
                    spot_price = None
        
        # Clear the progress indicator
        progress_placeholder.empty()
    
    if not options_df.empty:
        # Store in session state
        st.session_state['options_data'] = options_df
        st.session_state['spot_price'] = spot_price
        st.session_state['current_asset'] = asset
        st.session_state['current_expiry'] = selected_expiry
        
        st.success(f"✅ Successfully loaded data for {len(options_df)} instruments")
    else:
        st.error("❌ No data available for this selection")
        st.stop()

# ============================================================================
# MAIN CONTENT - DISPLAY DATA
# ============================================================================

if 'options_data' in st.session_state:
    df = st.session_state['options_data']
    spot_price = st.session_state.get('spot_price')
    current_asset = st.session_state['current_asset']
    current_expiry = st.session_state['current_expiry']
    
    # ========================================================================
    # USD NORMALIZATION CALCULATIONS
    # ========================================================================
    
    # Use Kaiko spot price, fallback to OI-weighted estimate
    if spot_price is None:
        if not df.empty and df['open_interest'].notna().any():
            spot_price = (df['strike_price'] * df['open_interest'].fillna(0)).sum() / df['open_interest'].fillna(0).sum()
        else:
            spot_price = df['strike_price'].median() if not df.empty else 100000
        st.warning("⚠️ Using estimated spot price (Kaiko spot data unavailable)")
    
    # Add USD notional columns
    df['oi_usd_notional'] = df['open_interest'] * df['strike_price']
    
    # Display current selection
    st.subheader(f"📈 {current_asset} Options - Expiry: {current_expiry}")
    
    # Key metrics row
    st.markdown("### 📊 Key Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_oi = df['open_interest'].fillna(0).sum()
        st.metric("Total OI (Contracts)", f"{total_oi:,.0f}")
    
    with col2:
        total_oi_usd = df['oi_usd_notional'].fillna(0).sum()
        st.metric("Total OI", format_large_number(total_oi_usd))
    
    with col3:
        num_instruments = len(df)
        instruments_with_oi = df['open_interest'].notna().sum()
        st.metric("Active Instruments", f"{instruments_with_oi}/{num_instruments}")
    
    with col4:
        avg_iv = df['mark_iv'].mean()
        if pd.notna(avg_iv):
            st.metric("Average IV", f"{avg_iv:.1f}%")
        else:
            st.metric("Average IV", "N/A")
    
    with col5:
        st.metric("Spot Price", f"${spot_price:,.0f}")
    
    st.divider()
    
    # ========================================================================
    # CHARTS IN TABS
    # ========================================================================
    
    st.markdown("### 📊 Visualizations")
    
    # Create tabs for different chart categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Overview", "⚡ Gamma Concentration", "📅 Multi-Expiry", "🔵🔴 Calls vs Puts", "🌊 IV Surface"])
    
# ========================================================================
    # TAB 1: Overview - OI and Kaiko IV Smile
    # ========================================================================
    with tab1:
        # Import the enhanced IV smile function
        from utils.volatility_analytics import plot_iv_smile_with_kaiko_iv
        
        # ====================================================================
        # OPEN INTEREST CHART (Full Width on Top)
        # ====================================================================
        st.markdown("#### Open Interest by Strike (USD Notional)")
        
        oi_df = df[df['oi_usd_notional'].notna()].copy()
        oi_df = oi_df.sort_values('strike_price')
        
        if not oi_df.empty:
            fig_oi = go.Figure()
            
            fig_oi.add_trace(go.Bar(
                x=oi_df['strike_price'],
                y=oi_df['oi_usd_notional'] / 1e6,  # Convert to millions
                name='OI USD',
                marker_color=KAIKO_NAVY,
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                              '<b>OI:</b> $%{y:.2f}M<br>' +
                              '<extra></extra>'
            ))
            
            fig_oi.update_layout(
                xaxis_title="Strike Price",
                yaxis_title="Open Interest (USD Millions)",
                hovermode='closest',
                height=400,
                showlegend=False,
                margin=dict(l=50, r=50, t=30, b=50)
            )
            
            st.plotly_chart(fig_oi, use_container_width=True, key="oi_chart")
        else:
            st.warning("No Open Interest data available")
        
        st.markdown("---")  # Divider
        
        # ====================================================================
        # KAIKO PROPRIETARY IV SMILE CHART (Full Width Below)
        # ====================================================================
        st.markdown("#### Volatility Smile - Kaiko Proprietary IV")
        st.caption("Black line: Kaiko's calculated IV | Triangles: Exchange bid/ask IV for reference")
        
        # Prepare exchange data (bid/ask from risk endpoint)
        iv_df_exchange = df[['strike_price', 'option_type', 'bid_iv', 'ask_iv']].copy()
        iv_df_exchange = iv_df_exchange.sort_values('strike_price')
        
        # Get all unique strikes from the current option chain
        exchange_strikes = df['strike_price'].dropna().unique().tolist()
        
        # Fetch Kaiko proprietary IV for those exact strikes
        try:
            # Convert current timestamp and expiry to ISO format
            value_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            expiry_iso = pd.to_datetime(current_expiry).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            with st.spinner("Fetching Kaiko proprietary IV calculation..."):
                # Get Kaiko IV smile for the exact strikes
                kaiko_iv_data = api.get_kaiko_iv_smile(
                    base=current_asset.lower(),
                    quote=quote,
                    value_time=value_time,
                    expiry=expiry_iso,
                    strikes=exchange_strikes,  # Pass actual strikes from exchange
                    exchange='drbt'
                )
                
                # Parse Kaiko IV response
                if kaiko_iv_data.get('data'):
                    iv_data = kaiko_iv_data['data'][0]
                    kaiko_ivs = iv_data.get('implied_volatilities', [])
                    
                    df_kaiko = pd.DataFrame(kaiko_ivs)
                    
                    if not df_kaiko.empty:
                        st.success(f"✓ Loaded {len(df_kaiko)} Kaiko IV data points across full strike range")
                    else:
                        st.warning("No Kaiko IV data available")
                        df_kaiko = pd.DataFrame()
                else:
                    df_kaiko = pd.DataFrame()
                    st.warning("No Kaiko IV data available for this expiry")
        
        except Exception as e:
            st.error(f"Error fetching Kaiko IV: {str(e)}")
            df_kaiko = pd.DataFrame()
        
        # Plot the combined smile
        if not iv_df_exchange.empty or not df_kaiko.empty:
            fig_iv_kaiko = plot_iv_smile_with_kaiko_iv(
                df_exchange=iv_df_exchange,
                df_kaiko=df_kaiko,
                spot_price=spot_price,
                asset_name=current_asset,
                expiry=current_expiry
            )
            
            st.plotly_chart(fig_iv_kaiko, use_container_width=True, key="iv_chart_kaiko")
            
            # Show data source info
            col1, col2 = st.columns(2)
            with col1:
                st.info("🟦 **Kaiko IV**: Proprietary calculation using space interpolation")
            with col2:
                st.info("🔺 **Exchange Bid/Ask**: Deribit-provided values for reference")
            
        else:
            st.warning("No volatility data available")

    # ========================================================================
    # TAB 2: Gamma Concentration
    # ========================================================================
    with tab2:
        st.markdown("#### Gamma Concentration by Strike")
        
        # ====================================================================
        # POSITIONING PRIOR SELECTOR
        # ====================================================================
        
        st.markdown("##### ⚙️ Positioning Assumption")
        
        positioning_prior = st.radio(
            "Select positioning prior:",
            options=[
                "Unsigned only (no positioning assumption)",
                "Assume dealers short calls / long puts (signed proxy)",
                "Assume dealers long calls / short puts (signed proxy)"
            ],
            index=0,
            help="Choose whether to apply a positioning assumption to infer signed gamma exposure"
        )
        
        show_signed = positioning_prior != "Unsigned only (no positioning assumption)"
        dealer_short_calls = positioning_prior == "Assume dealers short calls / long puts (signed proxy)"
        
        st.caption("""
        **Methodology Note:** We observe open interest and greeks, not dealer inventory or trade direction. 
        Magnitudes shown are derived from OI × gamma. Signs (if shown) come from the selected positioning prior.
        """)
        
        st.markdown("---")
        
        # ====================================================================
        # GAMMA CALCULATION
        # ====================================================================
        
        gamma_df = df[df['gamma'].notna() & df['open_interest'].notna()].copy()
        
        if not gamma_df.empty:
            # Consistent gamma exposure metric: USD notional per 1% spot move
            # Formula: gamma × spot² / 100 × OI
            gamma_df['gex_1pct_usd_per_contract'] = gamma_df['gamma'] * (spot_price ** 2) / 100
            gamma_df['gex_1pct_usd'] = gamma_df['gex_1pct_usd_per_contract'] * gamma_df['open_interest']
            
            # Unsigned concentration (always calculated)
            gamma_df['gex_unsigned'] = gamma_df['gex_1pct_usd'].abs()
            
            # Signed proxy (only if positioning prior selected)
            if show_signed:
                if dealer_short_calls:
                    # Dealers short calls (negative), long puts (positive)
                    gamma_df['gex_signed'] = gamma_df.apply(
                        lambda row: row['gex_1pct_usd'] * (-1 if row['option_type'] == 'call' else 1),
                        axis=1
                    )
                else:
                    # Dealers long calls (positive), short puts (negative)
                    gamma_df['gex_signed'] = gamma_df.apply(
                        lambda row: row['gex_1pct_usd'] * (1 if row['option_type'] == 'call' else -1),
                        axis=1
                    )
            
            # Aggregate by strike
            if show_signed:
                gamma_by_strike = gamma_df.groupby('strike_price').agg({
                    'gex_unsigned': 'sum',
                    'gex_signed': 'sum'
                }).reset_index()
            else:
                gamma_by_strike = gamma_df.groupby('strike_price').agg({
                    'gex_unsigned': 'sum'
                }).reset_index()
                gamma_by_strike['gex_signed'] = 0  # Add dummy column for consistency
            
            gamma_by_strike = gamma_by_strike.sort_values('strike_price')
            
            # ================================================================
            # CHART: GAMMA CONCENTRATION
            # ================================================================
            
            if show_signed:
                chart_title = "Gamma Concentration by Strike (Signed Proxy - Assumption-Driven)"
                chart_data = gamma_by_strike['gex_signed']
            else:
                chart_title = "Gamma Concentration by Strike (USD Notional per 1% Move)"
                chart_data = gamma_by_strike['gex_unsigned']
            
            st.markdown(f"#### {chart_title}")
            
            # Determine scaling
            max_abs_value = chart_data.abs().max()
            
            if max_abs_value >= 1e9:
                divisor = 1e9
                unit = "B"
                ylabel = "USD Gamma (1% Move, Billions)"
            elif max_abs_value >= 1e6:
                divisor = 1e6
                unit = "M"
                ylabel = "USD Gamma (1% Move, Millions)"
            elif max_abs_value >= 1e3:
                divisor = 1e3
                unit = "K"
                ylabel = "USD Gamma (1% Move, Thousands)"
            else:
                divisor = 1
                unit = ""
                ylabel = "USD Gamma (1% Move)"
            
            gamma_by_strike['display_value'] = chart_data / divisor
            
            # Create chart with Kaiko colors
            fig_gamma = go.Figure()
            
            if show_signed:
                # Color by sign: Orange for puts (positive), Navy for calls (negative)
                colors = [KAIKO_ORANGE if x >= 0 else KAIKO_NAVY 
                          for x in gamma_by_strike['display_value']]
            else:
                # Single color for unsigned mode
                colors = KAIKO_NAVY
            
            fig_gamma.add_trace(go.Bar(
                x=gamma_by_strike['strike_price'],
                y=gamma_by_strike['display_value'],
                marker_color=colors,
                marker_line_width=0,
                width=gamma_by_strike['strike_price'].diff().median() * 0.8 if len(gamma_by_strike) > 1 else 1000,
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                              f'<b>Gamma:</b> %{{y:.2f}}{unit}<br>' +
                              '<extra></extra>'
            ))
            
            # Add spot price line
            fig_gamma.add_vline(
                x=spot_price, 
                line_dash="dash", 
                line_color="gray", 
                line_width=2,
                annotation_text=f"Spot: ${spot_price:,.0f}",
                annotation_position="top"
            )
            
            # Add zero line for signed mode
            if show_signed:
                fig_gamma.add_hline(y=0, line_dash="solid", line_color="lightgray", line_width=1)
            
            fig_gamma.update_layout(
                xaxis_title="Strike Price (USD)",
                yaxis_title=ylabel,
                hovermode='closest',
                height=500,
                showlegend=False,
                margin=dict(l=60, r=50, t=30, b=60),
                plot_bgcolor='white',
                xaxis=dict(
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0.5,
                    zeroline=False
                ),
                yaxis=dict(
                    showgrid=True,
                    gridcolor='lightgray',
                    gridwidth=0.5,
                    zeroline=False,
                    ticksuffix=unit,
                    tickformat='.1f'
                )
            )
            
            st.plotly_chart(fig_gamma, use_container_width=True, key="gamma_chart")
            
            # ================================================================
            # SUMMARY METRICS
            # ================================================================
            
            st.markdown("---")
            st.markdown("#### 📊 Summary Metrics")
            
            # Calculate metrics
            total_concentration = gamma_by_strike['gex_unsigned'].sum()
            max_conc_strike = gamma_by_strike.loc[gamma_by_strike['gex_unsigned'].idxmax(), 'strike_price']
            
            # Call/Put concentration ratio (unsigned)
            call_conc = gamma_df[gamma_df['option_type'] == 'call']['gex_unsigned'].sum()
            put_conc = gamma_df[gamma_df['option_type'] == 'put']['gex_unsigned'].sum()
            conc_ratio = call_conc / put_conc if put_conc > 0 else 0
            
            if show_signed:
                net_signed_gex = gamma_by_strike['gex_signed'].sum()
                call_signed = gamma_df[gamma_df['option_type'] == 'call']['gex_signed'].sum()
                put_signed = gamma_df[gamma_df['option_type'] == 'put']['gex_signed'].sum()
                signed_ratio = abs(call_signed) / abs(put_signed) if put_signed != 0 else 0
            
            # Display metrics
            if show_signed:
                col1, col2, col3, col4 = st.columns(4)
            else:
                col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Gamma Concentration", format_large_number(total_concentration))
                st.caption("Sum of absolute gamma across all strikes")
            
            with col2:
                st.metric("Max Concentration Strike", f"${max_conc_strike:,.0f}")
                st.caption("Strike with highest gamma concentration")
            
            with col3:
                st.metric("Call/Put Concentration Ratio", f"{conc_ratio:.2f}")
                st.caption("Unsigned ratio (abs values)")
            
            if show_signed:
                with col4:
                    st.metric("Net Signed GEX (Proxy)", format_large_number(net_signed_gex))
                    if net_signed_gex > 1e6:
                        st.caption("🟢 Long gamma proxy")
                    elif net_signed_gex < -1e6:
                        st.caption("🔴 Short gamma proxy")
                    else:
                        st.caption("⚪ Near neutral")
            
            # ================================================================
            # HEDGING IMPLICATIONS (Only if signed mode)
            # ================================================================
            
            if show_signed:
                st.markdown("---")
                st.markdown("#### 🔄 Implied Hedging Under Positioning Prior")
                st.caption("These estimates assume the selected positioning prior is correct")
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    move_pct = st.slider(
                        "Price Move (%)",
                        min_value=0.5,
                        max_value=10.0,
                        value=1.0,
                        step=0.5,
                        help="Select price move % to see implied hedging volume"
                    )
                    
                    move_dollar = spot_price * (move_pct / 100)
                    st.metric("Move Size", f"${move_dollar:,.0f}")
                
                with col2:
                    # Hedging direction logic
                    # Long gamma (net_signed_gex > 0): up => sell, down => buy
                    # Short gamma (net_signed_gex < 0): up => buy, down => sell
                    
                    # Scale for move size (linear approximation for small moves)
                    hedge_magnitude = abs(net_signed_gex) * move_pct
                    
                    col2a, col2b = st.columns(2)
                    
                    with col2a:
                        st.markdown(f"**⬆️ {move_pct}% Up Move**")
                        if net_signed_gex > 0:
                            # Long gamma: dealers sell on rally
                            st.metric("Implied Hedging", format_large_number(hedge_magnitude))
                            st.caption("🔴 Dealers sell (pressure)")
                        else:
                            # Short gamma: dealers buy on rally
                            st.metric("Implied Hedging", format_large_number(hedge_magnitude))
                            st.caption("🟢 Dealers buy (support)")
                    
                    with col2b:
                        st.markdown(f"**⬇️ {move_pct}% Down Move**")
                        if net_signed_gex > 0:
                            # Long gamma: dealers buy on dip
                            st.metric("Implied Hedging", format_large_number(hedge_magnitude))
                            st.caption("🟢 Dealers buy (support)")
                        else:
                            # Short gamma: dealers sell on dip
                            st.metric("Implied Hedging", format_large_number(hedge_magnitude))
                            st.caption("🔴 Dealers sell (pressure)")
            
            # ================================================================
            # INTERPRETATION GUIDE
            # ================================================================
            
            st.markdown("---")
            st.markdown("#### 📖 Interpretation Guide")
            
            with st.expander("🔍 How to Read This Analysis", expanded=False):
                st.markdown("""
                **What We Observe:**
                - Open Interest (OI) and Greeks from options market data
                - Gamma concentration = OI × gamma × spot² / 100
                - This shows USD notional exposure per 1% spot move
                
                **What We Don't Observe:**
                - Actual dealer positions or inventory
                - Trade direction or counterparty identities
                - Real hedging flows
                
                **Positioning Prior Options:**
                
                1. **Unsigned Only (Default):**
                   - Shows absolute gamma concentration by strike
                   - No assumptions about dealer positioning
                   - Useful for identifying key strikes and concentrations
                
                2. **Dealers Short Calls / Long Puts:**
                   - Standard assumption (dealers sell options to customers)
                   - Call gamma = negative (dealers must buy on rallies)
                   - Put gamma = positive (dealers must sell on dips)
                
                3. **Dealers Long Calls / Short Puts:**
                   - Reverse assumption (less common)
                   - Call gamma = positive
                   - Put gamma = negative
                
                **Key Metrics:**
                
                - **Total Gamma Concentration:** Sum of absolute gamma (always shown)
                - **Max Concentration Strike:** Strike with most gamma (acts as price "magnet")
                - **Call/Put Concentration Ratio:** Unsigned ratio showing relative size
                - **Net Signed GEX:** Only shown with positioning prior - indicates long/short gamma
                
                **Hedging Implications (Signed Mode Only):**
                - Estimates assume the selected positioning prior is correct
                - **Long gamma (positive net):** Dealers stabilize (buy dips, sell rallies)
                - **Short gamma (negative net):** Dealers magnify (sell dips, buy rallies)
                - Linear scaling for small moves (< 5%)
                
                **Trading Context:**
                - High concentration at one strike → Price may gravitate toward that level
                - Long gamma near spot → Expect range-bound trading
                - Short gamma away from strikes → Expect trending moves
                - Use alongside other analysis (not standalone trading signal)
                """)
        
        else:
            st.warning("No gamma data available for analysis")
    
    # ========================================================================
    # TAB 3: Multi-Expiry Analysis
    # ========================================================================
    with tab3:
        st.markdown("#### Multi-Expiry Gamma Analysis")
        st.caption("Compare gamma concentration across different expiration dates")
        
        # Multi-expiry selector
        if 'expiries' in st.session_state and st.session_state['expiries']:
            available_expiries = st.session_state['expiries']
            
            st.markdown("##### Select Expiries to Compare")
            
            # Quick select options
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📅 Next 2 Expiries", use_container_width=True):
                    st.session_state['selected_multi_expiries'] = available_expiries[:2]
            with col2:
                if st.button("📅 Next 3 Expiries", use_container_width=True):
                    st.session_state['selected_multi_expiries'] = available_expiries[:3]
            with col3:
                if st.button("📅 Next 5 Expiries", use_container_width=True):
                    st.session_state['selected_multi_expiries'] = available_expiries[:5]
            
            # Manual selection
            selected_expiries = st.multiselect(
                "Or select specific expiries:",
                options=available_expiries,
                default=st.session_state.get('selected_multi_expiries', available_expiries[:2]),
                help="Select multiple expiries to compare"
            )
            
            st.session_state['selected_multi_expiries'] = selected_expiries
            
            if st.button("🔄 Fetch Multi-Expiry Data", type="primary", disabled=len(selected_expiries) == 0):
                st.session_state['fetch_multi_clicked'] = True
            
            # Fetch and analyze multi-expiry data
            if st.session_state.get('fetch_multi_clicked') and len(selected_expiries) > 0:
                
                # Check cache first
                multi_cache_key = f"multi_{current_asset}_{'_'.join(selected_expiries)}"
                
                if multi_cache_key in st.session_state:
                    multi_df = st.session_state[multi_cache_key]
                    st.info("✨ Using cached multi-expiry data")
                else:
                    with st.spinner(f"Fetching data for {len(selected_expiries)} expiries..."):
                        multi_df = api.get_multi_expiry_options_data(
                            base=current_asset.lower(),
                            quote=quote,
                            expiries=selected_expiries,
                            max_instruments_per_expiry=max_instruments if max_instruments > 0 else None,
                            atm_filter_pct=atm_filter_pct
                        )
                        
                        # Cache the result
                        if not multi_df.empty:
                            st.session_state[multi_cache_key] = multi_df
                
                if not multi_df.empty:
                    st.success(f"✅ Loaded {len(multi_df)} instruments across {len(selected_expiries)} expiries")
                    
                    # Calculate gamma for all expiries
                    multi_gamma_df = multi_df[multi_df['gamma'].notna() & multi_df['open_interest'].notna()].copy()
                    
                    if not multi_gamma_df.empty:
                        # Calculate unsigned gamma concentration
                        multi_gamma_df['gex_1pct_usd'] = multi_gamma_df['gamma'] * (spot_price ** 2) / 100 * multi_gamma_df['open_interest']
                        multi_gamma_df['gex_unsigned'] = multi_gamma_df['gex_1pct_usd'].abs()
                        
                        # ====================================================
                        # CHART 1: Gamma by Expiry (Aggregate)
                        # ====================================================
                        
                        st.markdown("---")
                        st.markdown("#### Total Gamma Concentration by Expiry")
                        
                        gamma_by_expiry = multi_gamma_df.groupby('expiry')['gex_unsigned'].sum().reset_index()
                        gamma_by_expiry = gamma_by_expiry.sort_values('expiry')
                        
                        # Determine scaling
                        max_val = gamma_by_expiry['gex_unsigned'].max()
                        if max_val >= 1e9:
                            divisor, unit = 1e9, "B"
                        elif max_val >= 1e6:
                            divisor, unit = 1e6, "M"
                        elif max_val >= 1e3:
                            divisor, unit = 1e3, "K"
                        else:
                            divisor, unit = 1, ""
                        
                        gamma_by_expiry['display'] = gamma_by_expiry['gex_unsigned'] / divisor
                        
                        fig_expiry = go.Figure()
                        
                        fig_expiry.add_trace(go.Bar(
                            x=gamma_by_expiry['expiry'],
                            y=gamma_by_expiry['display'],
                            marker_color=KAIKO_NAVY,
                            hovertemplate='<b>Expiry:</b> %{x}<br>' +
                                          f'<b>Total Gamma:</b> %{{y:.2f}}{unit}<br>' +
                                          '<extra></extra>'
                        ))
                        
                        fig_expiry.update_layout(
                            xaxis_title="Expiry Date",
                            yaxis_title=f"Total Gamma Concentration ({unit})",
                            height=400,
                            showlegend=False,
                            margin=dict(l=50, r=50, t=30, b=100),
                            xaxis=dict(tickangle=-45)
                        )
                        
                        st.plotly_chart(fig_expiry, use_container_width=True, key="multi_expiry_bar")
                        
                        # ====================================================
                        # CHART 2: Gamma by Strike, Colored by Expiry
                        # ====================================================
                        
                        st.markdown("---")
                        st.markdown("#### Gamma Concentration by Strike (All Expiries)")
                        st.caption("Each expiry shown in different color")
                        
                        gamma_by_strike_expiry = multi_gamma_df.groupby(['strike_price', 'expiry'])['gex_unsigned'].sum().reset_index()
                        
                        # Kaiko color palette for expiries
                        colors_palette = [
                            KAIKO_NAVY,
                            KAIKO_ORANGE,
                            KAIKO_BLUE,
                            KAIKO_LIGHT_ORANGE,
                            KAIKO_LIGHT_BLUE,
                            '#FD6F1D',
                            '#F98719',
                            '#003DA6',
                        ]
                        
                        fig_multi = go.Figure()
                        
                        for idx, expiry in enumerate(selected_expiries):
                            expiry_data = gamma_by_strike_expiry[gamma_by_strike_expiry['expiry'] == expiry]
                            expiry_data = expiry_data.sort_values('strike_price')
                            
                            color = colors_palette[idx % len(colors_palette)]
                            
                            fig_multi.add_trace(go.Bar(
                                x=expiry_data['strike_price'],
                                y=expiry_data['gex_unsigned'] / divisor,
                                name=expiry,
                                marker_color=color,
                                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                                              f'<b>Gamma:</b> %{{y:.2f}}{unit}<br>' +
                                              f'<b>Expiry:</b> {expiry}<br>' +
                                              '<extra></extra>'
                            ))
                        
                        # Add spot line
                        fig_multi.add_vline(
                            x=spot_price,
                            line_dash="dash",
                            line_color="gray",
                            line_width=2,
                            annotation_text=f"Spot: ${spot_price:,.0f}",
                            annotation_position="top"
                        )
                        
                        fig_multi.update_layout(
                            xaxis_title="Strike Price (USD)",
                            yaxis_title=f"Gamma Concentration ({unit})",
                            height=500,
                            barmode='stack',
                            hovermode='closest',
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            margin=dict(l=60, r=50, t=80, b=60)
                        )
                        
                        st.plotly_chart(fig_multi, use_container_width=True, key="multi_expiry_stack")
                        
                        # ====================================================
                        # SUMMARY METRICS
                        # ====================================================
                        
                        st.markdown("---")
                        st.markdown("#### Multi-Expiry Summary")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            total_gamma_all = gamma_by_expiry['gex_unsigned'].sum()
                            st.metric("Total Gamma (All Expiries)", format_large_number(total_gamma_all))
                        
                        with col2:
                            dominant_expiry = gamma_by_expiry.loc[gamma_by_expiry['gex_unsigned'].idxmax(), 'expiry']
                            st.metric("Dominant Expiry", dominant_expiry)
                        
                        with col3:
                            dominant_pct = (gamma_by_expiry['gex_unsigned'].max() / total_gamma_all) * 100
                            st.metric("Dominant %", f"{dominant_pct:.1f}%")
                        
                        with col4:
                            num_expiries = len(selected_expiries)
                            st.metric("Expiries Analyzed", num_expiries)
                        
                        # ====================================================
                        # EXPIRY BREAKDOWN TABLE
                        # ====================================================
                        
                        st.markdown("---")
                        st.markdown("#### Expiry Breakdown")
                        
                        breakdown = gamma_by_expiry.copy()
                        breakdown['percentage'] = (breakdown['gex_unsigned'] / total_gamma_all * 100)
                        breakdown['gamma_formatted'] = breakdown['gex_unsigned'].apply(format_large_number)
                        
                        st.dataframe(
                            breakdown[['expiry', 'gamma_formatted', 'percentage']].rename(columns={
                                'expiry': 'Expiry Date',
                                'gamma_formatted': 'Total Gamma',
                                'percentage': '% of Total'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                    else:
                        st.warning("No gamma data available for selected expiries")
                else:
                    st.error("❌ Failed to fetch multi-expiry data")
        else:
            st.info("👆 Please load expiries first from the sidebar")
    
    # ========================================================================
    # TAB 4: Calls vs Puts (USD NOTIONAL IN MILLIONS)
    # ========================================================================
    with tab4:
        st.markdown("#### Call vs Put Open Interest by Strike")
        
        oi_split_df = df[df['oi_usd_notional'].notna()].copy()
        
        if not oi_split_df.empty:
            # Separate calls and puts
            calls = oi_split_df[oi_split_df['option_type'] == 'call'].groupby('strike_price')['oi_usd_notional'].sum().reset_index()
            puts = oi_split_df[oi_split_df['option_type'] == 'put'].groupby('strike_price')['oi_usd_notional'].sum().reset_index()
            
            calls.columns = ['strike_price', 'call_oi_usd']
            puts.columns = ['strike_price', 'put_oi_usd']
            
            # Merge
            combined = calls.merge(puts, on='strike_price', how='outer').fillna(0)
            combined = combined.sort_values('strike_price')
            
            # Create grouped bar chart with Kaiko colors
            fig_cp = go.Figure()
            
            fig_cp.add_trace(go.Bar(
                x=combined['strike_price'],
                y=combined['call_oi_usd'] / 1e6,  # Convert to millions
                name='Calls',
                marker_color=KAIKO_NAVY,
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                              '<b>Call OI:</b> $%{y:.2f}M<br>' +
                              '<extra></extra>'
            ))
            
            fig_cp.add_trace(go.Bar(
                x=combined['strike_price'],
                y=combined['put_oi_usd'] / 1e6,  # Convert to millions
                name='Puts',
                marker_color=KAIKO_ORANGE,
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                              '<b>Put OI:</b> $%{y:.2f}M<br>' +
                              '<extra></extra>'
            ))
            
            fig_cp.update_layout(
                xaxis_title="Strike Price",
                yaxis_title="Open Interest (USD Millions)",
                barmode='group',
                hovermode='closest',
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                margin=dict(l=50, r=50, t=50, b=50)
            )
            
            st.plotly_chart(fig_cp, use_container_width=True, key="calls_puts_chart")
            
            # Add summary metrics
            st.markdown("#### Summary Metrics")
            col1, col2, col3 = st.columns(3)
            with col1:
                total_call_oi_usd = combined['call_oi_usd'].sum()
                st.metric("Total Call OI", format_large_number(total_call_oi_usd))
            with col2:
                total_put_oi_usd = combined['put_oi_usd'].sum()
                st.metric("Total Put OI", format_large_number(total_put_oi_usd))
            with col3:
                pc_ratio = total_put_oi_usd / total_call_oi_usd if total_call_oi_usd > 0 else 0
                st.metric("Put/Call Ratio", f"{pc_ratio:.2f}")
        else:
            st.warning("No open interest data available for call/put split")
    
    # ========================================================================
    # TAB 5: IV Surface
    # ========================================================================
    with tab5:
        st.markdown("#### Implied Volatility Surface")
        st.caption("3D visualization of implied volatility across delta and time to maturity")
        
        # Use yesterday's date at 8:00 UTC (data must be historical)
        surface_time = (datetime.now() - timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
        
        # Check if we have cached IV surface for this asset
        surface_cache_key = f"iv_surface_{current_asset}_{surface_time.strftime('%Y%m%d')}"
        
        if surface_cache_key in st.session_state:
            iv_surface_df = st.session_state[surface_cache_key]
            st.info(f"✨ Using cached IV surface for {surface_time.strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            st.info(f"Fetching IV surface for {surface_time.strftime('%Y-%m-%d %H:%M UTC')}")
            
            # Fetch IV surface data only once
            with st.spinner("Loading IV surface..."):
                iv_surface_df = api.get_iv_surface(
                    base=current_asset.lower(),
                    quote=quote,
                    value_time=surface_time,
                    tte_min=0.01,   # ~3.65 days
                    tte_max=0.5,    # 6 months
                    tte_step=0.02   # ~7 days
                )
                
                # Cache the surface data
                if not iv_surface_df.empty:
                    st.session_state[surface_cache_key] = iv_surface_df
        
        if not iv_surface_df.empty:
            # Create pivot table for surface plot
            surface_pivot = iv_surface_df.pivot_table(
                index='delta',
                columns='time_to_expiry',
                values='implied_volatility',
                aggfunc='mean'
            )
            
            # Create 3D surface plot with Kaiko colors
            fig_surface = go.Figure(data=[go.Surface(
                x=surface_pivot.columns,  # Time to expiry
                y=surface_pivot.index,    # Delta
                z=surface_pivot.values,   # IV
                colorscale=[
                    [0, KAIKO_NAVY],
                    [0.5, KAIKO_LIGHT_BLUE],
                    [1, KAIKO_ORANGE]
                ],
                hovertemplate='<b>TTM:</b> %{x:.3f}y<br>' +
                              '<b>Delta:</b> %{y:.2f}<br>' +
                              '<b>IV:</b> %{z:.2%}<br>' +
                              '<extra></extra>'
            )])
            
            fig_surface.update_layout(
                scene=dict(
                    xaxis=dict(
                        title='Time to Maturity (Years)',
                        autorange='reversed'
                    ),
                    yaxis=dict(title='Delta'),
                    zaxis=dict(title='Implied Volatility'),
                    camera=dict(
                        eye=dict(x=1.5, y=-1.5, z=1.2)
                    )
                ),
                height=600,
                margin=dict(l=0, r=0, t=30, b=0)
            )
            
            st.plotly_chart(fig_surface, use_container_width=True, key="iv_surface_chart")
            
            # Add surface metrics
            st.markdown("#### Surface Metrics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                avg_iv = iv_surface_df['implied_volatility'].mean()
                st.metric("Average IV", f"{avg_iv:.1%}")
            
            with col2:
                min_iv = iv_surface_df['implied_volatility'].min()
                st.metric("Min IV", f"{min_iv:.1%}")
            
            with col3:
                max_iv = iv_surface_df['implied_volatility'].max()
                st.metric("Max IV", f"{max_iv:.1%}")
            
            with col4:
                iv_range = max_iv - min_iv
                st.metric("IV Range", f"{iv_range:.1%}")
            
        else:
            st.warning("⚠️ No IV surface data available")
            st.info("""
            **Possible reasons:**
            - The IV surface endpoint may require specific API permissions
            - Historical data may not be available for the selected date
            - The asset/exchange combination may not support IV surface calculation
            
            Try adjusting the date or contact Kaiko support if the issue persists.
            """)
    
    st.divider()
    
    # ========================================================================
    # CSV DOWNLOAD
    # ========================================================================
    
    st.markdown("### 💾 Export Data")
    
    # Prepare download data
    download_df = df.copy()
    download_df['asset'] = current_asset
    download_df['fetch_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    download_df['spot_price'] = spot_price
    
    # Reorder columns for better CSV layout
    cols_order = ['fetch_time', 'asset', 'spot_price', 'expiry', 'instrument', 'strike_price', 
                  'option_type', 'open_interest', 'oi_usd_notional', 'mark_iv', 'bid_iv', 'ask_iv',
                  'delta', 'gamma', 'vega', 'theta', 'rho']
    
    # Only include columns that exist
    cols_order = [col for col in cols_order if col in download_df.columns]
    download_df = download_df[cols_order]
    
    # Convert to CSV
    csv = download_df.to_csv(index=False)
    
    # Generate filename
    filename = f"kaiko_options_{current_asset}_{current_expiry.replace(' ', '_').replace(':', '-')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Download button
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
        type="primary"
    )
    
    st.divider()
    
    # ========================================================================
    # RAW DATA TABLE
    # ========================================================================
    
    st.markdown("### 📋 Raw Data")
    st.dataframe(
        df[['instrument', 'strike_price', 'option_type', 'open_interest', 'oi_usd_notional', 'mark_iv', 'gamma']],
        use_container_width=True
    )

else:
    # Show instructions if no data loaded yet
    st.info("""
    ### Welcome to Kaiko Options Analytics!
    
    **Get started:**
    1. Select an asset from the sidebar (BTC, ETH, etc.)
    2. Choose a date range
    3. Click "Load Expiries" to see available expiration dates
    4. Select an expiry date
    5. **Enable ATM filter** for faster loading (recommended)
    6. Click "Fetch Options Data" to load the dashboard
    
    **Performance Tips:**
    - Use the ATM filter (±30%) for 5-10x faster loading
    - to refresh click "Fetch Options Data" again and wait
    - Data is cached so switching tabs is instant

    
    **Features:**
    - Real-time spot price from Kaiko
    - Gamma concentration analysis with configurable assumptions
    - Multi-expiry comparison (cached for speed)
    - IV surface with Kaiko branding
    """)
    st.stop()