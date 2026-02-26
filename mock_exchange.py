import socket
import simplefix
import time

# --- CONFIG ---
HOST = '127.0.0.1'
PORT = 9876

def run_mock_exchange():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)
    
    # Set a 1-second timeout so it doesn't block forever
    # This is to accomodate Windows users, as it handles interrupts differently
    # from Linux
    server.settimeout(1.0)
    
    print(f"🏛️  Mock FIX Exchange listening on TCP {HOST}:{PORT}...")
    
    while True:
        try:
            # It will wait 1 second for a connection, then throw a timeout error
            conn, addr = server.accept()
        except socket.timeout:
            # If no connection, loop back to the start (allowing CTRL-C to be caught)
            continue
            
        print(f"\n[+] Accepted FIX connection from Algo Gateway: {addr}")
        
        parser = simplefix.FixParser()
        
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                    
                parser.append_buffer(data)
                msg = parser.get_message()
                
                if msg:
                    msg_type = msg.get(35).decode()
                    
                    if msg_type == 'D':
                        symbol = msg.get(55).decode()
                        side = "BUY" if msg.get(54).decode() == '1' else "SELL"
                        qty = msg.get(38).decode()
                        price = msg.get(44).decode()
                        
                        print(f"INCOMING ORDER: {side} {qty} shares of {symbol} @ ${price}")
                        print("Status: Matching order...")
                        time.sleep(0.5) 
                        
                        reply = simplefix.FixMessage()
                        reply.append_pair(8, "FIX.4.2")
                        reply.append_pair(35, "8")
                        reply.append_pair(39, "2")
                        reply.append_pair(150, "2")
                        reply.append_pair(55, symbol)
                        reply.append_pair(14, qty)
                        reply.append_pair(44, price)
                        
                        encoded_reply = reply.encode()
                        conn.send(encoded_reply)
                        print(">>> Sent filled FIX Exec Report back to Gateway.")
                        
            except ConnectionResetError:
                print("[-] Gateway disconnected.")
                break

if __name__ == "__main__":
    try:
        run_mock_exchange()
    except KeyboardInterrupt:
        print("\n🏛️  Exchange shutting down gracefully.")