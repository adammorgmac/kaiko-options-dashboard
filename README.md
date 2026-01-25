# Kaiko Options Analytics Dashboard

A lightweight Streamlit dashboard for quick crypto options analysis using Kaiko’s API (with Deribit options coverage). Built for fast answers to: where is OI sitting, where is gamma concentrated, and what does that imply for market behavior?

# What is it?

The dashboard has a several views:

- Open Interest (OI): OI by strike and notional so you can see where positioning is concentrated
- Gamma Concentration (GEX): where gamma is sitting (default unsigned), with an optional signed proxy mode
- Multi‑Expiry: compare gamma across expiries to see which tenor “matters” most
- Calls vs Puts: clean side‑by‑side OI breakdown
- IV Visuals: IV smile + a 3D IV surface (cached daily for speed)Export: download datasets as CSV

# Features

### Multi-Asset Support
- BTC, ETH (liquidity and volumes patchy for other assets as markets less mature)

### How to use

- Pick an asset (BTC, ETH, etc.) in the sidebar
- Click Load expiries to pull available expiration dates
- Select an expiry from the dropdown
- Turn on the ATM filter (recommended—massive speed-up)
- Hit Fetch data and start clicking around

### Performance
- Configurable instrument limits for faster loading
- Progress indicators during data fetching
- Cached API connections
- Use the ATM filter (±30%) — it usually cuts fetch time by 5–10x

### troubleshooting

“No data available”
- Try a different expiry (some dates won’t have meaningful options data)
- Verify you’re not filtering too aggressively

Dashboard feels slow
- Turn on the ATM filter
- Reduce the number of expiries in Multi‑Expiry
- Refresh only when needed (caching does the rest)

Charts not loading
- Often just means there’s no data for that slice/metric
- Try another expiry or asset


##  requirements

- Python 3.8 or higher
- A Kaiko API key with access to:
  - Derivatives Reference Data
  - Derivatives Risk Data
  - Analytics IV Surface (optional)


- Built by Adam Morgan, Kaiko Research. 
- For API questions or general queries: adam.mccarthy@kaiko.com