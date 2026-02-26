import socket
import pykx as kx
import simplefix
import time
import os

# --- CONFIG ---
KDB_HOST = os.getenv('KDB_HOST', '127.0.0.1')
KDB_PORT = int(os.getenv('KDB_PORT', 5011))
EXCHANGE_HOST = os.getenv('EXCHANGE_HOST', '127.0.0.1')
EXCHANGE_PORT = int(os.getenv('EXCHANGE_PORT', 9876))

def run_gateway():
    # 1. Connect to the Mock Exchange
    print(f"🔗 Connecting to Mock Exchange at {EXCHANGE_HOST}:{EXCHANGE_PORT}...")
    try:
        exchange_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        exchange_sock.connect((EXCHANGE_HOST, EXCHANGE_PORT))
        print("✅ Connected to Exchange!")
    except ConnectionRefusedError:
        print("❌ Could not connect to Exchange. Make sure mock_exchange.py is running.")
        return

    # 2. Connect to KDB+ RDB
    print(f"📡 Connecting to KDB+ RDB at {KDB_HOST}:{KDB_PORT}...")
    try:
        q = kx.QConnection(host=KDB_HOST, port=KDB_PORT)
        print("✅ Connected to KDB+.")
    except Exception as e:
        print(f"❌ KDB+ Connection Error: {e}")
        return

    print("🚀 Gateway Active. Listening for KDB+ trading signals...")
    
    last_processed_row = 0
    parser = simplefix.FixParser()

    try:
        # Polling loop to check for new signals
        while True:
            # Check how many signals exist in the database
            current_count = q("count signals").py()
            
            if current_count > last_processed_row:
                # Fetch only the brand new rows
                new_signals = q(f"{last_processed_row}_ signals")
                records = new_signals.pd().to_dict('records')
                
                for row in records:
                    sym = str(row['sym'])
                    side = "1" if row['side'] == 'BUY' else "2"
                    qty = int(row['qty'])
                    price = float(row['price'])

                    # --- CONSTRUCT THE FIX 4.2 MESSAGE ---
                    fix_msg = simplefix.FixMessage()
                    fix_msg.append_pair(8, "FIX.4.2")        # BeginString
                    fix_msg.append_pair(35, "D")             # MsgType = New Order Single
                    fix_msg.append_pair(55, sym)             # Symbol
                    fix_msg.append_pair(54, side)            # Side (1=Buy, 2=Sell)
                    fix_msg.append_pair(38, qty)             # OrderQty
                    fix_msg.append_pair(44, price)           # Price
                    
                    # Send raw FIX string over the network
                    exchange_sock.send(fix_msg.encode())
                    print(f"\n>>> SENT ORDER: {row['side']} {qty} {sym} @ ${price}")
                    
                    # Wait for execution report from the exchange
                    data = exchange_sock.recv(1024)
                    if data:
                        parser.append_buffer(data)
                        reply = parser.get_message()
                        if reply and reply.get(35).decode() == '8':
                            print(f"<<< FILL CONFIRMED: Executed {qty} shares @ ${price}")
                
                # Update tracker
                last_processed_row = current_count
                
            time.sleep(1) # Poll every second
            
    except KeyboardInterrupt:
        print("\nGateway shutting down.")
    finally:
        exchange_sock.close()
        q.close()

if __name__ == "__main__":
    run_gateway()