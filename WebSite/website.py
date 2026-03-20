import socket
import time
import json

from flask import *

host = '127.0.0.1'
port = 8080

client = None  # Global connection

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

i = 0
data_array = [0,0,0,0]

# Route to receive commands from the web page
@app.route('/command', methods=['POST'])
def command():
    global data_array
    try:
        cmd = request.json
        index = cmd.get('index')
        value = cmd.get('value')
        if 0 <= index < len(data_array):
            data_array[index] = value
            print(f"Set array[{index}] = {value}")
        return jsonify({"status": "ok"})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)})
    
# Route to fetch data from the socket server
@app.route('/data')
def data():
    global i
    try:
        c = get_client()
        if c:
            c.sendall(json.dumps(data_array).encode())  # Send a request to the socket server
            received_data = c.recv(1024).decode()
            print(f"Received: {received_data}")
            return jsonify({"data": json.loads(received_data)})
        else:
            return jsonify({"error": "Unable to connect to socket server"})
    except Exception as e:
        print(f"Error: {e}")
        global client
        client = None  # Reset on error so it reconnects next time
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)