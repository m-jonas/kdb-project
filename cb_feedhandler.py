import json
import pykx as kx
from coinbase.websocket import WSClient
import os

# 1. Credentials
# Credentials are loaded from a local json file.
with open("C:/Users/jonas/Downloads/cdp_api_key.json", "r") as f:
    api_credentials = json.load(f) 

name = api_credentials["name"]
privateKey = api_credentials["privateKey"]

# 2. Initialize KDB+ Connection
print("--- Step 1: Connecting to KDB+ ---")
try:
    os.environ['PYKX_SKIP_SIGNAL_HANDLING'] = '1' 
    # connecting to TickerPlant
    q = kx.SyncQConnection(host='127.0.0.1', port=5010)
    print("KDB+ Connection Established.")
except Exception as e:
    print(f"KDB+ Connection Failed: {e}")
    exit(1)

# Coinbase API code mixed with pykx
def on_message(msg):
    data = json.loads(msg)
    channel = data.get('channel')
    
    if channel == 'ticker' and 'events' in data:
        for event in data['events']:
            tickers = event.get('tickers', [])
            for t in tickers:
                try:
                    # Explicit time generation removed.
                    # TP will populate time automatically.
                    sym_val = kx.SymbolAtom(t['product_id'])
                    price_val = float(t.get('price') or 0.0)
                    size_val = float(t.get('volume_24_h') or 0.0)
                    bid_val = float(t.get('best_bid') or 0.0)
                    ask_val = float(t.get('best_ask') or 0.0)
                    bidSize_val = float(t.get('best_bid_quantity') or 0.0)
                    askSize_val = float(t.get('best_ask_quantity') or 0.0)

                    # only sending 7 columns for schema of 8 columns
                    # but TP will populate time column itself.
                    vals = [
                        kx.List([sym_val]),
                        kx.List([price_val]),
                        kx.List([size_val]),
                        kx.List([bid_val]),
                        kx.List([ask_val]),
                        kx.List([bidSize_val]),
                        kx.List([askSize_val])
                    ]

                    # 3. Push to KDB+
                    # Resulting Data in TP: (Timestamp; Sym; Price; ...; AskSize) -> 8 Cols
                    q('.u.upd', kx.SymbolAtom('ticker'), vals, wait=False)

                    print(f">>> KDB PUSH SUCCESS: {t['product_id']} @ {price_val}")

                except Exception as e:
                    print(f"Push Error: {e}")

# 3. Setup Coinbase Client
print("--- Step 2: Starting Coinbase ---")
ws_client = WSClient(api_key=name, api_secret=privateKey, on_message=on_message)

try:
    ws_client.open()
    ws_client.subscribe(["BTC-USD"], ["ticker", "heartbeats"]) 
    print("Pipeline Active. Check below for incoming debug logs...")
    ws_client.run_forever_with_exception_check()
except Exception as e:
    print(f"Pipeline Error: {e}")
finally:
    ws_client.close()
    if 'q' in locals():
        q.close()