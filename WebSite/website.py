import socket
import time

host = '127.0.0.1'
port = 8080 # Same as server

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((host, port)) # Connect

try:
    while True:
        client.sendall(b"Hello, Server") # Send
        data = client.recv(1024) # Receive
        print(f"Received: {data.decode()}")
        time.sleep(1)  # Send every second
except KeyboardInterrupt:
    print("Disconnecting...")
finally:
    client.close()
