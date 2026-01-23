# Kaiko Options Analytics Dashboard

A Streamlit dashboard for analyzing cryptocurrency options data from Deribit via Kaiko's Market Data API and using Kaiko's IV tool.

# Features

### Multi-Asset Support
- BTC, ETH
- Real-time options data from Deribit

### Interactive Visualizations
- **Overview Tab**: Open Interest & Implied Volatility smile charts
- **Greeks & Exposure Tab**: Professional gamma exposure analysis (dealer positioning)
- **Calls vs Puts Tab**: Call/Put OI comparison with Put/Call ratio metrics
- **IV Surface Tab**: Interactive 3D volatility surface across delta and time to maturity

### Data Export
- CSV download with timestamps
- Complete options chain data including strikes, OI, IV, and Greeks

### Performance
- Configurable instrument limits for faster loading
- Progress indicators during data fetching
- Cached API connections

##  Prerequisites

- Python 3.8 or higher
- Kaiko API key with access to:
  - Derivatives Reference Data
  - Derivatives Risk Data
  - Analytics IV Surface (optional)


Contact: adam.mccarthy@kaiko.com
