import socketio
import time
import serial

sio = socketio.Client()

ser = serial.Serial(
    port='/dev/ttyAMA0',
    baudrate=115200,
    timeout=0.1,
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

def try_connect():
    try:
        sio.connect('http://192.168.1.1:8000') # Base station Pi
    except Exception:
        pass

# Telemetry state machine variables (mirrors your PIC code logic)
last_char = 0
this_char = 0
telemetry_packet = [0, 0, 0]
packet_runner = 0

# Payload array is: Header Byte 1, Header Byte 2, Forward, Backward, Turn Left, Turn Right, Motor Speed, Fan speed
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

            # 2. Byte-by-byte state machine parser (identical to your PIC logic)
            while ser.in_waiting > 0:
                byte_in = ser.read(1)
                if not byte_in:
                    break
                
                last_char = this_char
                this_char = byte_in[0]

                # Check for 2-byte sync header: 0x30 followed by 0x50 ('0', 'P')
                if this_char == 0x50 and last_char == 0x30:
                    telemetry_packet[0] = 0x30
                    telemetry_packet[1] = 0x50
                    packet_runner = 2 # Start filling data at index 2
                
                elif packet_runner >= 2:
                    telemetry_packet[packet_runner] = this_char
                    packet_runner += 1

                    # Once we have collected all 3 bytes of the telemetry packet
                    if packet_runner == 3:
                        packet_runner = 0 # Reset for the next packet
                        
                        battery_byte = telemetry_packet[2]
                        
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

            if not sio.connected:
                try_connect()
                
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.")
