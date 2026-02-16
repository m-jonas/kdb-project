import asyncio
import websockets
import json
import os
import pykx as kx
from datetime import datetime

# --- Configuration ---
TP_HOST = os.getenv('TP_HOST', 'localhost')
TP_PORT = int(os.getenv('TP_PORT', 5010))
KRAKEN_WS_URL = 'wss://ws.kraken.com'

# --- Normalization Map ---
# Kraken uses 'XBT', we use 'BTC'. We map them to a unified symbol.
SYM_MAP = {
    "XBT/USD": "BTC-USD"
}

async def run_kraken_feed():
    print(f"🔌 Connecting to Tickerplant at {TP_HOST}:{TP_PORT}...")
    try:
        # Connect to KDB+
        q = kx.SyncQConnection(host=TP_HOST, port=TP_PORT)
    except Exception as e:
        print(f"❌ Failed to connect to TP: {e}")
        return

    async with websockets.connect(KRAKEN_WS_URL, ping_interval=None) as ws:
        # Subscribe to Kraken 'ticker' channel
        sub_msg = {
            "event": "subscribe",
            "pair": list(SYM_MAP.keys()),
            "subscription": {"name": "ticker"}
        }
        await ws.send(json.dumps(sub_msg))
        print(f"✅ Subscribed to Kraken Feeds: {list(SYM_MAP.keys())}")

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)

                # Kraken sends updates as a List: [ChannelID, Payload, ChannelName, Pair]
                if isinstance(data, list):
                    payload = data[1]
                    pair = data[-1]

                    # 1. Check if it is a Ticker Payload (must be a dict)
                    if not isinstance(payload, dict):
                        continue

                    # 2. SYMBOLOGY NORMALIZATION
                    # Map Kraken 'XBT/USD' -> System 'BTC-USD'
                    sym = SYM_MAP.get(pair, pair)

                    # 3. FIELD NORMALIZATION
                    # Kraken structure: 'c': [Price, Vol], 'a': [Ask, ...], 'b': [Bid, ...]
                    if 'c' in payload and 'a' in payload and 'b' in payload:
                        price = float(payload['c'][0])
                        size = float(payload['c'][1])
                        bid = float(payload['b'][0])
                        ask = float(payload['a'][0])
                        bid_size = float(payload['b'][1])
                        ask_size = float(payload['a'][1])

                        # 4. PUBLISH TO KDB+
                        # Schema: (time; sym; price; size; bid; ask; bidSize; askSize)
                        row = [
                            # datetime.now(),
                            kx.List([kx.SymbolAtom(sym)]),
                            kx.List([price]),
                            kx.List([size]),
                            kx.List([bid]),
                            kx.List([ask]),
                            kx.List([bid_size]),
                            kx.List([ask_size])
                        ]
                        
                        # IPC Call
                        q(".u.upd", kx.SymbolAtom("ticker"), row)
                        
                        # Debug Log (shows source is Kraken)
                        print(f"Kraken -> KDB: {sym} @ {price}")

            except Exception as e:
                print(f"⚠️ Error: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(run_kraken_feed())
    except KeyboardInterrupt:
        print("Stopping Feed Handler")