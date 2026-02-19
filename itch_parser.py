import struct
import sys
import datetime

# --- CONFIG ---
# file is excluded from repo due to size.
# can be downloaded from https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/01302019.NASDAQ_ITCH50.gz
FILE_PATH = 'data/01302019.NASDAQ_ITCH50'
# Pre-market open starts 4am, we want to reach market open,
# so:
MAX_MESSAGES = 15000000 # Catching a good chunck of market action
TARGET_TICKER = 'AAPL'

def parse_timestamp(timestamp_bytes):
    # Converts 6-byte nanosecond timestamp to human-readable string
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
    stock_directory = {}
    
    # --- STATE MANAGEMENT ---
    # This set will remember the Order IDs of AAPL so we can track their lifecycle
    tracked_orders = set()

    try:
        while msg_count < MAX_MESSAGES:
            # Read the 2-byte length prefix
            # Nasdaq hist data is pre-pended with 2 bytes to tell us
            # how long the upcoming entry is
            # and then read that length.
            length_bytes = f.read(2)
            if not length_bytes:
                print("End of file reached.")
                break
            
            # Unpack the 2-byte integer
            # Big-Endian Unsigned Short for NASDAQ but my Intel CPU works with Little-Endian.
            msg_length = struct.unpack('>H', length_bytes)[0]
            
            # Read the Message Type (1 byte)
            msg_type = f.read(1)
            
            # Read the payload (Length minus the 1 byte we just read for msg_type)
            payload = f.read(msg_length - 1)
            
            # --- PARSING LOGIC ---
            
            if msg_type == b'S':
                # Unpack System Event: Locate(2), Tracking(2), Time(6), EventCode(1)
                unpacked = struct.unpack('>HH6sc', payload)
                timestamp = parse_timestamp(unpacked[2])
                event_code = unpacked[3].decode('ascii')
                print(f"[{timestamp}] SYSTEM EVENT: {event_code}")

            elif msg_type == b'R':
                # Unpack Stock Directory
                header = struct.unpack('>HH6s8s', payload[:18])
                stock_locate = header[0]
                timestamp = parse_timestamp(header[2])
                symbol = header[3].decode('ascii').strip()
                
                stock_directory[stock_locate] = symbol
                print(f"[{timestamp}] STOCK DIRECTORY: ID {stock_locate} -> {symbol}")

            elif msg_type == b'A':
                # Unpack Add Order (35 bytes payload)
                # >HH6sQcI8sI from https://docs.python.org/3/library/struct.html#format-characters
                unpacked = struct.unpack('>HH6sQcI8sI', payload)
                
                stock_locate = unpacked[0]
                timestamp = parse_timestamp(unpacked[2])
                order_ref = unpacked[3]
                side = unpacked[4].decode('ascii')
                shares = unpacked[5]
                stock = unpacked[6].decode('ascii').strip()
                price = unpacked[7] / 10000.0  # Convert integer to 4-decimal float
                
                # Filter for a specific stock to avoid console spam
                if stock == TARGET_TICKER:
                    # Remember this order ID!
                    tracked_orders.add(order_ref)
                    print(f"[{timestamp}] ADD     ({side}): {shares} shrs @ ${price:.4f} [ID: {order_ref}]")

            elif msg_type == b'E':
                # Order Executed: >HH6sQIQ (30 bytes)
                unpacked = struct.unpack('>HH6sQIQ', payload)
                order_ref = unpacked[3]
                
                if order_ref in tracked_orders:
                    timestamp = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    print(f"[{timestamp}] EXECUTE    : {exec_shares} shrs traded!       [ID: {order_ref}]")

            elif msg_type == b'X':
                # Order Cancel (Partial): >HH6sQI (22 bytes)
                unpacked = struct.unpack('>HH6sQI', payload)
                order_ref = unpacked[3]
                
                if order_ref in tracked_orders:
                    timestamp = parse_timestamp(unpacked[2])
                    cancel_shares = unpacked[4]
                    print(f"[{timestamp}] CANCEL     : {cancel_shares} shrs canceled      [ID: {order_ref}]")

            elif msg_type == b'D':
                # Order Delete (Full): >HH6sQ (18 bytes)
                unpacked = struct.unpack('>HH6sQ', payload)
                order_ref = unpacked[3]
                
                if order_ref in tracked_orders:
                    timestamp = parse_timestamp(unpacked[2])
                    print(f"[{timestamp}] DELETE     : Order completely removed [ID: {order_ref}]")
                    # Clean up memory so our set doesn't grow infinitely
                    tracked_orders.remove(order_ref)

            elif msg_type == b'U':
                # Order Replace: >HH6sQQII (34 bytes)
                unpacked = struct.unpack('>HH6sQQII', payload)
                orig_order_ref = unpacked[3]
                
                if orig_order_ref in tracked_orders:
                    timestamp = parse_timestamp(unpacked[2])
                    new_order_ref = unpacked[4]
                    new_shares = unpacked[5]
                    new_price = unpacked[6] / 10000.0
                    
                    print(f"[{timestamp}] REPLACE    : {new_shares} shrs @ ${new_price:.4f} [Old: {orig_order_ref} -> New: {new_order_ref}]")
                    # Update our tracker memory
                    tracked_orders.remove(orig_order_ref)
                    tracked_orders.add(new_order_ref)

            elif msg_type == b'C':
                # Order Executed with Price: >HH6sQIQcI (35 bytes)
                unpacked = struct.unpack('>HH6sQIQcI', payload)
                order_ref = unpacked[3]
                
                if order_ref in tracked_orders:
                    timestamp = parse_timestamp(unpacked[2])
                    exec_shares = unpacked[4]
                    exec_price = unpacked[7] / 10000.0
                    print(f"[{timestamp}] EXEC(PRC)  : {exec_shares} shrs @ ${exec_price:.4f} [ID: {order_ref}]")

            msg_count += 1

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        f.close()
        print(f"\nProcessed {msg_count} messages.")
        print(f"Loaded {len(stock_directory)} symbols into memory.")
        print(f"Currently tracking {len(tracked_orders)} live {TARGET_TICKER} orders in memory.")

if __name__ == "__main__":
    parse_itch_file(FILE_PATH)