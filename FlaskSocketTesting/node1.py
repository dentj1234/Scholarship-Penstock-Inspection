import socketio
import time
import serial

sio = socketio.Client()

ser = serial.Serial(
    port='/dev/ttyAMA0',
    baudrate=115200,
    timeout=0.1, # Short timeout so read doesn't block forever
)

@sio.event
def connect():
    print("Connected to base station server!")

@sio.event
def disconnect():
    print("Disconnected from server.")

@sio.on('target_command')
def handle_target_command(data):
    print(f"COMMAND RECEIVED FROM BASE: {data}")

@sio.event
def server_response(data):
    pass 

def try_connect():
    try:
        print("Attempting to connect to base station...")
        sio.connect('http://127.0.0.1:8000')
    except Exception:
        print("Server not online yet. Will retry...")

payload_array = [0x20, 0x40, 1, 0, 0, 1, 186, 200]

if __name__ == '__main__':
    try_connect()

    last_command_time = 0

    try:
        while True:
            # 1. Send command packet to PIC every 0.1 seconds
            if time.time() - last_command_time >= 0.1:
                try:
                    ser.write(bytes(payload_array))
                    last_command_time = time.time()
                except Exception as uart_err:
                    print(f"UART Write Error: {uart_err}")

            # 2. Check for incoming telemetry bytes (wait for at least 3 bytes)
            if ser.in_waiting >= 3:
                raw_bytes = ser.read(3) # Grab the exact 3-byte chunk
                print(f"DEBUG: Read 3 bytes -> {raw_bytes}")
                
                if raw_bytes[0] == 0x30 and raw_bytes[1] == 0x50:
                    battery_byte = raw_bytes[2]
                    
                    # Convert 8-bit byte back to real 3S battery voltage
                    estimated_adc = battery_byte * 16
                    pin_voltage = (estimated_adc / 4095.0) * 3.3
                    battery_voltage = round(pin_voltage * 4, 2)
                    
                    print(f"🔥 RECEIVED BATTERY TELEMETRY: {battery_voltage}V (Byte: {battery_byte})")

                    # Emit to Socket.IO if connected
                    if sio.connected:
                        try:
                            telemetry_data = {'battery_voltage': battery_voltage, 'node': '0'}
                            sio.emit('robot_telemetry', telemetry_data)
                        except Exception as e:
                            print(f"Emit failed: {e}")
                else:
                    # If we accidentally locked onto a misaligned byte, put it back or flush
                    pass

            # Reconnect to server if dropped
            if not sio.connected:
                try_connect()
                
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.")