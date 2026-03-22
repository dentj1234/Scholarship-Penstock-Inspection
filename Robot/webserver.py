import socket

# Setup: AF_INET (IPv4), SOCK_STREAM (TCP)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('127.0.0.1', 8080)) # Bind to IP and Port
server.listen(2) # Listen for connections


print("Waiting for connection...")
try:
    while True:
        conn, addr = server.accept() # Accept connections
        print(f"Connected by {addr}")
        
        try:
            while True:
                data = conn.recv(1024).decode() # Receive
                if not data:
                    print(f"Disconnected by {addr}")
                    break
                print(f"Received: {data}")
                conn.sendall(data.encode()) # Echo back
        except Exception as e:
            print(f"Error with {addr}: {e}")
        finally:
            conn.close()
            print("Waiting for connection...")
except KeyboardInterrupt:
    print("Server shutting down...")
finally:
    server.close()
