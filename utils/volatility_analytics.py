"""
Enhanced Volatility Smile Analytics
"""

import plotly.graph_objects as go
import pandas as pd


def plot_iv_smile_with_bid_ask(df, spot_price, asset_name, expiry):
    """
    Plot IV smile showing mark IV as main line with bid/ask IV as markers
    Single combined smile for all options (calls + puts)
    
    Parameters:
    - df: DataFrame with columns: strike_price, option_type, mark_iv, bid_iv, ask_iv
    - spot_price: Current spot price
    - asset_name: Asset ticker (e.g., 'BTC')
    - expiry: Expiration date string
    
    Returns:
    - Plotly figure
    """
    
    fig = go.Figure()
    
    # Sort by strike price
    df_sorted = df.sort_values('strike_price').copy()
    
    # Filter out NaN values for mark_iv
    df_mark = df_sorted[df_sorted['mark_iv'].notna()].copy()
    
    # ========== MARK IV (Main black line) ==========
    if not df_mark.empty:
        fig.add_trace(go.Scatter(
            x=df_mark['strike_price'],
            y=df_mark['mark_iv'],
            mode='lines+markers',
            name='Kaiko IV',
            line=dict(color='black', width=2),
            marker=dict(size=6, color='black'),
            hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                         '<b>Mark IV:</b> %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
    
    # ========== ASK IV (Red triangles down) ==========
    df_ask = df_sorted[df_sorted['ask_iv'].notna()].copy()
    if not df_ask.empty:
        fig.add_trace(go.Scatter(
            x=df_ask['strike_price'],
            y=df_ask['ask_iv'],
            mode='markers',
            name='Ask IV',
            marker=dict(
                size=8,
                color='red',
                symbol='triangle-down',
                line=dict(width=1, color='darkred')
            ),
            hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                         '<b>Ask IV:</b> %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
    
    # ========== BID IV (Green triangles up) ==========
    df_bid = df_sorted[df_sorted['bid_iv'].notna()].copy()
    if not df_bid.empty:
        fig.add_trace(go.Scatter(
            x=df_bid['strike_price'],
            y=df_bid['bid_iv'],
            mode='markers',
            name='Bid IV',
            marker=dict(
                size=8,
                color='green',
                symbol='triangle-up',
                line=dict(width=1, color='darkgreen')
            ),
            hovertemplate='<b>Strike:</b> $%{x:,.0f}<br>' +
                         '<b>Bid IV:</b> %{y:.2f}%<br>' +
                         '<extra></extra>'
        ))
    
    # ========== Spot price vertical line (dotted) ==========
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
        title=f"{asset_name} Volatility Smile - {expiry}",
        xaxis_title="Strike Price (USD)",
        yaxis_title="Implied Volatility (%)",
        height=500,
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)",
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
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig