import socketio
import time
import struct
import serial

sio = socketio.Client()

# --- UART Setup ---
# Ensure your port matches (/dev/serial0 or /dev/ttyAMA0)
ser = serial.Serial('/dev/ttyAMA0', baudrate=115200, timeout=0.1)
HEADER = 0xAA


@sio.event
def connect():
    print("Connected to base station server!", flush=True)

@sio.event
def disconnect():
    print("Disconnected from server.", flush=True)

# Listen for commands explicitly sent to this node
@sio.on('target_command')
def handle_target_command(data):
    print(f"COMMAND RECEIVED FROM BASE: {data}", flush=True)
    # Add your hardware trigger code here (e.g., control motors, read sensors)

@sio.event
def server_response(data):
    pass # Keep it quiet for telemetry ACKs

def connect_to_server():
    """Helper function to try connecting without permanently blocking startup."""
    try:
        print("Connecting to base station...", flush=True)
        sio.connect('http://127.0.0.1:8000', wait_timeout=2)
    except Exception:
        print("Server not online yet. Continuing locally...", flush=True)

n = 0

def test_uart_loop():
    print("Starting UART Test Loop. Press Ctrl+C to stop.", flush=True)
    
    # Counter to change values slightly each send, just to see it move
    counter = 0
    
    try:
        while True:
            # 1. SEND: Create a 4-integer command array (0-255 each)
            counter = (counter + 1) % 256
            cmd_array = [counter, 128, 1, 0]
            
            # Pack with header and send
            packet = struct.pack('<B 4B', HEADER, *cmd_array)
            ser.write(packet)
            print(f"--> Sent to PIC: {cmd_array}", flush=True)
            
            # 2. RECEIVE: Check if the PIC sent telemetry back (1 header byte + 4 data bytes = 5 bytes)
            if ser.in_waiting >= 5:
                header = ser.read(1)[0]
                if header == HEADER:
                    payload = ser.read(4)
                    telemetry = struct.unpack('<4B', payload)
                    print(f"<-- Received from PIC: {list(telemetry)}", flush=True)
                else:
                    print(f"Warning: Received invalid header byte: {hex(header)}", flush=True)
            else:
                print("<-- No telemetry received this cycle.", flush=True)
                
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        ser.close()
        print("\nUART test stopped and port closed.", flush=True)


if __name__ == '__main__':
    # Initial connection attempt
    connect_to_server()
    
    # Runs your exact UART test loop now that startup won't freeze indefinitely
    test_uart_loop()

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
                    print(f"Emit failed (connection likely dropped): {e}", flush=True)
            
            # If the connection dropped mid-run, loop back and try reconnecting
            if not sio.connected:
                print("Disconnected. Waiting for server to return...", flush=True)
                connect_to_server()
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.", flush=True)