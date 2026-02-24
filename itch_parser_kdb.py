import struct
import sys
import datetime
import time
import os
import pykx as kx

# --- CONFIG ---
FILE_PATH = 'data/01302019.NASDAQ_ITCH50'
MAX_MESSAGES = 15000000
TARGET_TICKER = 'AAPL'

# --- KDB+ CONNECTION ---
try:
    # Connect to the Tickerplant asynchronously
    q = kx.AsyncQConnection(host='localhost', port=5010)
    print(">>> Successfully connected to KDB+ Tickerplant via PyKX (Port 5010)")
except Exception as e:
    print(f"FATAL: Could not connect to KDB+. Is Docker running? Error: {e}")
    sys.exit(1)

def parse_timestamp(timestamp_bytes):
    ns = int.from_bytes(timestamp_bytes, byteorder='big')
    td = datetime.timedelta(microseconds=ns / 1000)
    return str(td), ns

def parse_itch_file(filepath):
    print(f"Opening ITCH file: {filepath}...")
    
    try:
        f = open(filepath, 'rb')
    except FileNotFoundError:
        print("Error: File not found.")
        return

    msg_count = 0
    orders = {} 
    bids = {}
    asks = {}
    prev_bbo = (0.0, 0.0)

    def update_lob(side, price, shares_delta):
        book = bids if side == 'B' else asks
        book[price] = book.get(price, 0) + shares_delta
        if book[price] <= 0:
            del book[price]

    try:
        while msg_count < MAX_MESSAGES:
            length_bytes = f.read(2)
            if not length_bytes: break
            
            msg_length = struct.unpack('>H', length_bytes)[0]
            msg_type = f.read(1)
            payload = f.read(msg_length - 1)
            
            timestamp_str = ""
            ns_time = 0 
            
            if msg_type == b'A':
                unpacked = struct.unpack('>HH6sQcI8sI', payload)
                stock = unpacked[6].decode('ascii').strip()
                if stock == TARGET_TICKER:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    order_ref = unpacked[3]
                    side = unpacked[4].decode('ascii')
                    shares = unpacked[5]
                    price = unpacked[7] / 10000.0
                    
                    orders[order_ref] = {'side': side, 'price': price, 'shares': shares}
                    update_lob(side, price, shares)

            elif msg_type == b'E':
                unpacked = struct.unpack('>HH6sQIQ', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'C':
                unpacked = struct.unpack('>HH6sQIQcI', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'X':
                unpacked = struct.unpack('>HH6sQI', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    cancel_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -cancel_shares)
                    order['shares'] -= cancel_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'D':
                unpacked = struct.unpack('>HH6sQ', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -order['shares'])
                    del orders[order_ref]

            elif msg_type == b'U':
                unpacked = struct.unpack('>HH6sQQII', payload)
                orig_ref = unpacked[3]
                if orig_ref in orders:
                    timestamp_str, ns_time = parse_timestamp(unpacked[2])
                    new_ref = unpacked[4]
                    new_shares = unpacked[5]
                    new_price = unpacked[6] / 10000.0
                    order = orders[orig_ref]
                    side = order['side']
                    
                    update_lob(side, order['price'], -order['shares'])
                    del orders[orig_ref]
                    
                    orders[new_ref] = {'side': side, 'price': new_price, 'shares': new_shares}
                    update_lob(side, new_price, new_shares)

            msg_count += 1
            
            # --- PUBLISH BBO TO KDB+ ---
            if timestamp_str:
                best_bid = max(bids.keys()) if bids else 0.0
                best_ask = min(asks.keys()) if asks else 0.0
                current_bbo = (best_bid, best_ask)
                
                if current_bbo != prev_bbo:
                    bid_size = bids.get(best_bid, 0)
                    ask_size = asks.get(best_ask, 0)
                    
                    # 1. Update terminal visualization
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print(f"=== {TARGET_TICKER} ORDER BOOK @ {timestamp_str} ===")
                    print(f"  BID: {bid_size} @ {best_bid}  ||  ASK: {ask_size} @ {best_ask}")
                    print("  >>> PUBLISHING TO KDB+ TICKERPLANT...")
                    
                    # 2. Construct the KDB+ update query
                    q_msg = f".u.upd[`bbo; enlist ({ns_time}n; `{TARGET_TICKER}; {bid_size}j; {best_bid}f; {ask_size}j; {best_ask}f)]"
                    
                    # 3. Send asynchronously via PyKX
                    q(q_msg)
                    
                    prev_bbo = current_bbo
                    time.sleep(0.01) # Slightly faster visualization

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        f.close()
        q.close() # Always close the connection cleanly
        print(f"\nProcessed {msg_count} messages.")

if __name__ == "__main__":
    parse_itch_file(FILE_PATH)