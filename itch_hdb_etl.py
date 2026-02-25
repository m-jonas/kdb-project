import struct
import pykx as kx

# --- CONFIG ---
FILE_PATH = 'data/01302019.NASDAQ_ITCH50'
MAX_MESSAGES = 15000000
TARGET_TICKER = 'AAPL'
HISTORICAL_DATE = '2019.01.30'

def parse_itch_etl(filepath):
    print(f"🚀 Starting ETL Pipeline for {filepath}...")
    
    try:
        f = open(filepath, 'rb')
    except FileNotFoundError:
        print("Error: File not found.")
        return

    msg_count = 0
    orders, bids, asks = {}, {}, {}
    prev_bbo = (0.0, 0.0)
    
    # This list will hold our extracted rows in memory
    bbo_records = []

    def update_lob(side, price, shares_delta):
        book = bids if side == 'B' else asks
        book[price] = book.get(price, 0) + shares_delta
        if book[price] <= 0:
            del book[price]

    print("⏳ Extracting and Transforming data (Parsing Binary)...")
    try:
        while msg_count < MAX_MESSAGES:
            length_bytes = f.read(2)
            if not length_bytes: break
            
            msg_length = struct.unpack('>H', length_bytes)[0]
            msg_type = f.read(1)
            payload = f.read(msg_length - 1)
            ns_time = 0 
            
            if msg_type == b'A':
                unpacked = struct.unpack('>HH6sQcI8sI', payload)
                stock = unpacked[6].decode('ascii').strip()
                if stock == TARGET_TICKER:
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
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
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
                    exec_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'C':
                unpacked = struct.unpack('>HH6sQIQcI', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
                    exec_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -exec_shares)
                    order['shares'] -= exec_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'X':
                unpacked = struct.unpack('>HH6sQI', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
                    cancel_shares = unpacked[4]
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -cancel_shares)
                    order['shares'] -= cancel_shares
                    if order['shares'] <= 0: del orders[order_ref]

            elif msg_type == b'D':
                unpacked = struct.unpack('>HH6sQ', payload)
                order_ref = unpacked[3]
                if order_ref in orders:
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
                    order = orders[order_ref]
                    update_lob(order['side'], order['price'], -order['shares'])
                    del orders[order_ref]

            elif msg_type == b'U':
                unpacked = struct.unpack('>HH6sQQII', payload)
                orig_ref = unpacked[3]
                if orig_ref in orders:
                    ns_time = int.from_bytes(unpacked[2], byteorder='big')
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
            
            # --- BATCH TO MEMORY ---
            if ns_time:
                best_bid = max(bids.keys()) if bids else 0.0
                best_ask = min(asks.keys()) if asks else 0.0
                current_bbo = (best_bid, best_ask)
                
                if current_bbo != prev_bbo:
                    bid_size = bids.get(best_bid, 0)
                    ask_size = asks.get(best_ask, 0)
                    
                    # Append raw record to list instead of sending to KDB+
                    bbo_records.append({
                        'time': ns_time,
                        'sym': TARGET_TICKER,
                        'bidSize': bid_size,
                        'bidPrice': best_bid,
                        'askSize': ask_size,
                        'askPrice': best_ask
                    })
                    prev_bbo = current_bbo

    except KeyboardInterrupt:
        pass
    finally:
        f.close()
    
    # DEBUG
    print(bbo_records[:10])
    
    print(f"✅ Extraction complete. Processed {msg_count} messages. Generated {len(bbo_records)} BBO updates.")
    
    print("💾 Connecting to KDB+ to bulk write HDB partitions...")
    try:
        # Connect to the RDB (5011)
        q = kx.QConnection(host='localhost', port=5011)
        
        # 1. Extract pure Python lists from our dictionaries
        times = [r['time'] for r in bbo_records]
        syms = [r['sym'] for r in bbo_records]
        bid_sizes = [r['bidSize'] for r in bbo_records]
        bid_prices = [r['bidPrice'] for r in bbo_records]
        ask_sizes = [r['askSize'] for r in bbo_records]
        ask_prices = [r['askPrice'] for r in bbo_records]
        
        print("   -> Pushing raw data structures across the network...")
        # 2. Push raw lists directly into KDB+ temporary variables
        q['tmp_t'] = times
        q['tmp_s'] = syms
        q['tmp_bs'] = bid_sizes
        q['tmp_bp'] = bid_prices
        q['tmp_as'] = ask_sizes
        q['tmp_ap'] = ask_prices
        
        print("   -> Assembling and casting un-keyed table natively in KDB+...")
        # 3. Assemble the table entirely inside KDB+ memory to guarantee perfect types
        q_build = "bbo_batch: flip `time`sym`bidSize`bidPrice`askSize`askPrice ! (`timespan$tmp_t; `$tmp_s; `long$tmp_bs; `float$tmp_bp; `long$tmp_as; `float$tmp_ap)"
        q(q_build)
        
        print("   -> Executing .Q.dpft to partition and write to disk...")
        # 4. Use .Q.dpft to partition the data by Date, enumerate symbols, and write to disk
        save_cmd = f".Q.dpft[`:/app/hdb; {HISTORICAL_DATE}; `sym; `bbo_batch]"
        q(save_cmd)
        
        # 5. Clean up the RDB memory so it stays fresh
        q("delete tmp_t, tmp_s, tmp_bs, tmp_bp, tmp_as, tmp_ap, bbo_batch from `.")
        q.close()
        
        print(f"🎉 SUCCESS: Data natively partitioned and written to HDB disk for {HISTORICAL_DATE}.")
        
    except Exception as e:
        print(f"FATAL: Failed to load into KDB+. Error: {e}")

if __name__ == "__main__":
    parse_itch_etl(FILE_PATH)