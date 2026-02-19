import struct
import sys
import datetime
import time
import os

# --- CONFIG ---
FILE_PATH = 'data/01302019.NASDAQ_ITCH50'
MAX_MESSAGES = 15000000
TARGET_TICKER = 'AAPL'

def parse_timestamp(timestamp_bytes):
    ns = int.from_bytes(timestamp_bytes, byteorder='big')
    td = datetime.timedelta(microseconds=ns / 1000)
    return str(td)

def parse_itch_file(filepath):
    print(f"Opening ITCH file: {filepath}...")
    
    try:
        f = open(filepath, 'rb')
    except FileNotFoundError:
        print("Error: File not found.")
        return

    msg_count = 0
    
    # --- LOB STATE MANAGEMENT ---
    # 1. Track individual orders: {order_id: {'side': 'B', 'price': 150.0, 'shares': 100}}
    orders = {} 
    
    # 2. Track aggregated price levels: {price: total_shares}
    bids = {}
    asks = {}
    
    # 3. Track the previous BBO to only print when it changes
    prev_bbo = (0.0, 0.0)

    def update_lob(side, price, shares_delta):
        """ Helper function to add/remove shares from a price level """
        book = bids if side == 'B' else asks
        book[price] = book.get(price, 0) + shares_delta
        
        # If all shares at this price level are gone, remove the price level entirely
        if book[price] <= 0:
            del book[price]

    try:
        while msg_count < MAX_MESSAGES:
            length_bytes = f.read(2)
            if not length_bytes: break
            
            msg_length = struct.unpack('>H', length_bytes)[0]
            msg_type = f.read(1)
            payload = f.read(msg_length - 1)
            
            # --- PARSING LOGIC ---
            timestamp = "" # We will populate this if it's an AAPL event
            
            if msg_type == b'A':
                unpacked = struct.unpack('>HH6sQcI8sI', payload)
                stock = unpacked[6].decode('ascii').strip()
                
                if stock == TARGET_TICKER:
                    timestamp = parse_timestamp(unpacked[2])
                    order_ref = unpacked[3]
                    side = unpacked[4].decode('ascii')
                    shares = unpacked[5]
                    price = unpacked[7] / 10000.0
                    
                    # 1. Save order details
                    orders[order_ref] = {'side': side, 'price': price, 'shares': shares}
                    # 2. Add shares to the book
                    update_lob(side, price, shares)

            elif msg_type == b'E':
                unpacked = struct.unpack('>HH6sQIQ', payload)
                order_ref = unpacked[3]
                
                if order_ref in orders:
                    timestamp = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    
                    # 1. Remove shares from book
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    
                    # 2. Update/Delete order
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0:
                        del orders[order_ref]

            elif msg_type == b'C':
                # Order Executed with Price (Price on book doesn't change, just shares)
                unpacked = struct.unpack('>HH6sQIQcI', payload)
                order_ref = unpacked[3]
                
                if order_ref in orders:
                    timestamp = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0:
                        del orders[order_ref]

            elif msg_type == b'X':
                unpacked = struct.unpack('>HH6sQI', payload)
                order_ref = unpacked[3]
                
                if order_ref in orders:
                    timestamp = parse_timestamp(unpacked[2])
                    cancel_shares = unpacked[4]
                    
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -cancel_shares)
                    
                    order['shares'] -= cancel_shares
                    if order['shares'] <= 0:
                        del orders[order_ref]

            elif msg_type == b'D':
                unpacked = struct.unpack('>HH6sQ', payload)
                order_ref = unpacked[3]
                
                if order_ref in orders:
                    timestamp = parse_timestamp(unpacked[2])
                    order = orders[order_ref]
                    
                    # Remove entire remaining size from the book
                    update_lob(order['side'], order['price'], -order['shares'])
                    del orders[order_ref]

            elif msg_type == b'U':
                unpacked = struct.unpack('>HH6sQQII', payload)
                orig_ref = unpacked[3]
                
                if orig_ref in orders:
                    timestamp = parse_timestamp(unpacked[2])
                    new_ref = unpacked[4]
                    new_shares = unpacked[5]
                    new_price = unpacked[6] / 10000.0
                    
                    order = orders[orig_ref]
                    side = order['side']
                    
                    # 1. Remove old order from book
                    update_lob(side, order['price'], -order['shares'])
                    del orders[orig_ref]
                    
                    # 2. Add new order to book
                    orders[new_ref] = {'side': side, 'price': new_price, 'shares': new_shares}
                    update_lob(side, new_price, new_shares)

            msg_count += 1
            
            
            # --- BBO CALCULATION ---
            if timestamp:
                best_bid = max(bids.keys()) if bids else 0.0
                best_ask = min(asks.keys()) if asks else 0.0
                current_bbo = (best_bid, best_ask)
                
                if current_bbo != prev_bbo:
                    # Clear the terminal screen to create a static dashboard effect
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    print(f"=== {TARGET_TICKER} ORDER BOOK @ {timestamp} ===")
                    
                    # 1. Sort and print top 5 ASKS
                    # In a trading terminal, the lowest ask is just above the spread
                    top_asks = sorted(asks.items())[:5]
                    for p, s in reversed(top_asks):
                        print(f"  ASK | {s:5} shrs @ ${p:<8.4f}")
                        
                    print("  --------------------------------")
                    
                    # 2. Sort and print top 5 BIDS
                    # The highest bid is just below the spread
                    top_bids = sorted(bids.items(), reverse=True)[:5]
                    for p, s in top_bids:
                        print(f"  BID | {s:5} shrs @ ${p:<8.4f}")
                        
                    print("====================================")
                    
                    prev_bbo = current_bbo
                    
                    # Pause for 100 milliseconds so your eyes can read it
                    time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        f.close()
        print(f"\nProcessed {msg_count} messages.")
        print(f"Active limit orders in memory: {len(orders)}")

if __name__ == "__main__":
    parse_itch_file(FILE_PATH)