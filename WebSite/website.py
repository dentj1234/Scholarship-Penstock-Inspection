import socket
import time

from flask import *

host = '127.0.0.1'
port = 8080

client = None  # Global connection

i = 0


# Function to create a connection to the socket server
def get_client():
    """Get or create persistent connection"""
    global client
    if client is None:
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
            print("Connected to socket server")
        except Exception as e:
            print(f"Connection error: {e}")
            client = None
    return client

# Flask app setup
app = Flask(__name__)
app.secret_key = 'drewismyidol'

# Route for home page
@app.route('/home')
def home():
    return render_template("index.html")

# Route to fetch data from the socket server
@app.route('/data')
def data():
    global i
    try:
        c = get_client()
        if c:
            c.sendall(str(i).encode())  # Send a request to the socket server
            i += 1
            received_data = c.recv(1024).decode()
            print(f"Received: {received_data}")
            return jsonify({"data": received_data})
    except Exception as e:
        print(f"Error: {e}")
        global client
        client = None  # Reset on error so it reconnects next time
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)