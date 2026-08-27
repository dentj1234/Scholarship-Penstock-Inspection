import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to base station server!")

@sio.event
def disconnect():
    print("Disconnected from server.")

@sio.event
def server_response(data):
    print(f"Response from base: {data}")

# Listen for commands explicitly sent to this node
@sio.on('target_command')
def handle_target_command(data):
    print(f"COMMAND RECEIVED FROM BASE: {data}")
    # Add your hardware trigger code here (e.g., control motors, read sensors)

@sio.event
def server_response(data):
    pass # Keep it quiet for telemetry ACKs

def connect_to_server():
    """Helper function to block and retry until connection is established."""
    while not sio.connected:
        try:
            print("Connecting to base station...")
            sio.connect('http://127.0.0.1:8000')
        except Exception:
            print("Server not online yet. Retrying in 3 seconds...")
            time.sleep(3)

# Connect to your Base Station's IP and Flask port

n = 0

if __name__ == '__main__':
    # Initial connection
    connect_to_server()

    # Main application loop
    try:
        while True:
            if sio.connected:
                try:
                    # Emit telemetry data to the server
                    n += 1
                    telemetry_data = {'battery': n, 'node': '0'}
                    sio.emit('robot_telemetry', telemetry_data)
                except Exception as e:
                    print(f"Emit failed (connection likely dropped): {e}")
            
            # If the connection dropped mid-run, loop back and reconnect
            if not sio.connected:
                print("Disconnected. Waiting for server to return...")
                connect_to_server()
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.")