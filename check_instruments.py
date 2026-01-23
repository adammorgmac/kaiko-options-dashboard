from utils.kaiko_api import KaikoAPI
from datetime import datetime

with open('.streamlit/secrets.toml', 'r') as f:
    content = f.read()
    for line in content.split('\n'):
        if 'KAIKO_API_KEY' in line:
            api_key = line.split('=')[1].strip().strip('"').strip("'")
            break

api = KaikoAPI(api_key)

df = api.get_instruments('btc', 'usd', datetime(2026, 1, 20), datetime(2026, 1, 24))

if not df.empty:
    print("Sample instruments:")
    print(df['instrument'].head(10).tolist())
    print("\nChecking last character of each instrument:")
    for inst in df['instrument'].head(10):
        print(f"  {inst} -> ends with: '{inst[-1]}'")