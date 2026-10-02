import socketio
import time
import serial

sio = socketio.Client()

ser = serial.Serial(
    port='/dev/ttyAMA0',
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

payload_array = [0x20, 0x40, 1, 0, 0, 1, 186, 200]

if __name__ == '__main__':
    # Initial connection attempt
    try_connect()

    # Main application loop
    try:
        while True:
            # 1. Run your UART communication continuously regardless of connection status
            try:
                ser.write(bytes(payload_array))
                print("Sent payload to UART.")
                time.sleep(0.05) # Short breath for UART response
                
                # Check for incoming telemetry bytes from the PIC [0x30, 0x50, battery_byte]
                if ser.in_waiting > 0:
                    incoming_data = ser.read(ser.in_waiting)
                    
                    # Scan for the telemetry header [0x30, 0x50]
                    for i in range(len(incoming_data) - 2):
                        if incoming_data[i] == 0x30 and incoming_data[i+1] == 0x50:
                            battery_byte = incoming_data[i+2]
                            
                            # Convert 8-bit byte back to real 3S battery voltage
                            estimated_adc = battery_byte * 16
                            pin_voltage = (estimated_adc / 4095.0) * 3.3
                            battery_voltage = round(pin_voltage * 4, 2)
                            
                            print(f"Received Battery Telemetry: {battery_voltage}V")

                            # 2. Handle Socket.IO telemetry emission with real data
                            if sio.connected:
                                try:
                                    telemetry_data = {'battery_voltage': battery_voltage, 'node': '0'}
                                    sio.emit('robot_telemetry', telemetry_data)
                                except Exception as e:
                                    print(f"Emit failed (connection dropped): {e}")
                            break
                            
            except Exception as uart_err:
                print(f"UART Error: {uart_err}")

            # If disconnected, try reconnecting once this cycle
            if not sio.connected:
                try_connect()
                
            # Loop delay
            time.sleep(1)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.")