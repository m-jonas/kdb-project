import struct
import sys
import datetime

# --- CONFIG ---
# file is excluded from repo due to size.
# can be downloaded from https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/01302019.NASDAQ_ITCH50.gz
FILE_PATH = 'data/01302019.NASDAQ_ITCH50'
MAX_MESSAGES = 100000

def parse_timestamp(timestamp_bytes):
    """ Converts 6-byte nanosecond timestamp to human-readable string """
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

    try:
        while msg_count < MAX_MESSAGES:
            # Read the 2-byte length prefix
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

            msg_count += 1

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        f.close()
        print(f"\nProcessed {msg_count} messages.")
        print(f"Loaded {len(stock_directory)} symbols into memory.")

if __name__ == "__main__":
    parse_itch_file(FILE_PATH)