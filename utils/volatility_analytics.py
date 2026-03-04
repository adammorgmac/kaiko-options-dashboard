"""
Enhanced Volatility Smile Analytics with Kaiko Proprietary IV
"""

import plotly.graph_objects as go
import pandas as pd


def plot_iv_smile_with_kaiko_iv(df_exchange, df_kaiko, spot_price, asset_name, expiry):
    """
    Plot IV smile showing:
    - Kaiko IV as main BLACK line (proprietary calculation)
    - Exchange bid/ask IV as green/red triangles (for reference)
    - ONLY show puts left of spot, calls right of spot (eliminates duplicates)
    
    Parameters:
    - df_exchange: DataFrame with exchange bid_iv, ask_iv from /risk endpoint
    - df_kaiko: DataFrame with Kaiko calculated IV from /implied_volatility_smile
    - spot_price: Current spot price
    - asset_name: Asset ticker (e.g., 'BTC')
    - expiry: Expiration date string
    
    Returns:
    - Plotly figure
    """
    
    fig = go.Figure()
    
    # ========== KAIKO IV (Main black line - proprietary) ==========
    if df_kaiko is not None and not df_kaiko.empty:
        df_kaiko_sorted = df_kaiko.sort_values('strike').copy()
        
        fig.add_trace(go.Scatter(
            x=df_kaiko_sorted['strike'],
            y=df_kaiko_sorted['implied_volatility'] * 100,  # Convert to percentage
            mode='lines+markers',
            name='Kaiko IV',
            line=dict(color='black', width=3),
            marker=dict(size=8, color='black'),
            hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                         '<b>Kaiko IV:</b> %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
    
    # ========== EXCHANGE DATA (bid/ask for reference) ==========
    if df_exchange is not None and not df_exchange.empty:
        # Add option_type if not present (determine from strike vs spot)
        if 'option_type' not in df_exchange.columns:
            df_exchange['option_type'] = df_exchange['strike_price'].apply(
                lambda x: 'put' if x < spot_price else 'call'
            )
        
        # Filter: Only show PUTS below spot, CALLS above spot
        puts_df = df_exchange[
            (df_exchange['option_type'] == 'put') & 
            (df_exchange['strike_price'] <= spot_price)
        ].copy()
        
        calls_df = df_exchange[
            (df_exchange['option_type'] == 'call') & 
            (df_exchange['strike_price'] >= spot_price)
        ].copy()
        
        # Combine filtered data
        df_filtered = pd.concat([puts_df, calls_df], ignore_index=True)
        
        # Deduplicate by strike (in case there are still any duplicates)
        df_dedup = df_filtered.groupby('strike_price').agg({
            'bid_iv': 'first',
            'ask_iv': 'first'
        }).reset_index()
        
        # ========== ASK IV (Red triangles down) ==========
        df_ask = df_dedup[df_dedup['ask_iv'].notna()].copy()
        if not df_ask.empty:
            fig.add_trace(go.Scatter(
                x=df_ask['strike_price'],
                y=df_ask['ask_iv'],
                mode='markers',
                name='Exchange Ask IV',
                marker=dict(
                    size=7,
                    color='red',
                    symbol='triangle-down',
                    line=dict(width=1, color='darkred'),
                    opacity=0.6
                ),
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                             '<b>Ask IV:</b> %{y:.2f}%<br>' +
                             '<extra></extra>'
            ))
        
        # ========== BID IV (Green triangles up) ==========
        df_bid = df_dedup[df_dedup['bid_iv'].notna()].copy()
        if not df_bid.empty:
            fig.add_trace(go.Scatter(
                x=df_bid['strike_price'],
                y=df_bid['bid_iv'],
                mode='markers',
                name='Exchange Bid IV',
                marker=dict(
                    size=7,
                    color='green',
                    symbol='triangle-up',
                    line=dict(width=1, color='darkgreen'),
                    opacity=0.6
                ),
                hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                             '<b>Bid IV:</b> %{y:.2f}%<br>' +
                             '<extra></extra>'
            ))
    
    # ========== Spot price vertical line ==========
    fig.add_vline(
        x=spot_price,
        line_dash="dot",
        line_color="blue",
        line_width=2,
        annotation_text=f"Spot: ${spot_price:,.0f}",
        annotation_position="top"
    )
    
    # Layout
    fig.update_layout(
        title=f"{asset_name} Volatility Smile - {expiry}<br>" +
              "<sub>Kaiko Proprietary IV (black) vs Exchange Bid/Ask (triangles) | Puts ← Spot → Calls</sub>",
        xaxis_title="Strike Price (USD)",
        yaxis_title="Implied Volatility (%)",
        height=550,
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="gray",
            borderwidth=1
        ),
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True, 
            gridcolor='lightgray',
            zeroline=False
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='lightgray',
            zeroline=False
        ),
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    return fig