import socketio
import time
import serial

sio = socketio.Client()

ser = serial.Serial(
    port='/dev/serial0',
    baudrate=115200,
    timeout=1,
)

@sio.event
def connect():
    print("Connected to base station server!")

@sio.event
def disconnect():
    print("Disconnected from server.")

# Listen for commands explicitly sent to this node
@sio.on('target_command')
def handle_target_command(data):
    print(f"COMMAND RECEIVED FROM BASE: {data}")
    # Add your hardware trigger code here (e.g., control motors, read sensors)

@sio.event
def server_response(data):
    pass # Keep it quiet for telemetry ACKs

def try_connect():
    """Attempt a single connection connection without permanently blocking the loop."""
    try:
        print("Attempting to connect to base station...")
        sio.connect('http://127.0.0.1:8000')
    except Exception:
        print("Server not online yet. Will retry...")

n = 0

if __name__ == '__main__':
    # Initial connection attempt
    try_connect()

    # Main application loop
    try:
        while True:
            # 1. Run your UART communication continuously regardless of connection status
            try:
                ser.write(b'AT\r\n')
                time.sleep(0.1)
                response = ser.read(ser.in_waiting or 1)
                if response:
                    print(f"Response: {response.decode(errors='ignore')}")
            except Exception as uart_err:
                print(f"UART Error: {uart_err}")

            # 2. Handle Socket.IO connection state and telemetry
            if sio.connected:
                try:
                    n += 1
                    telemetry_data = {'battery': n, 'node': '0'}
                    sio.emit('robot_telemetry', telemetry_data)
                except Exception as e:
                    print(f"Emit failed (connection dropped): {e}")
            else:
                # If disconnected, try reconnecting once this cycle
                try_connect()
                
            # Loop delay
            time.sleep(2)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.")