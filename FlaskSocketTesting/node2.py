import socketio
import time
import serial

sio = socketio.Client()
ser = serial.Serial(
    port='/dev/ttyAMA0',
    baudrate=115200,
    timeout=0.1,
)

last_char = 0
this_char = 0
telemetry_packet = bytearray(5)
packet_runner = 0
TELEMETRY_PACKET_LENGTH = 5
CURRENT_BYTE_STEP_AMPS = 0.2
ADC_REFERENCE_VOLTS = 3.3
TEMPERATURE_ZERO_C_VOLTS = 0.400
TEMPERATURE_SLOPE_VOLTS_PER_C = 0.0195


@sio.event
def connect():
    print("Connected to base station server!", flush=True)

    def registration_ack(response):
        print(f"Base station registration response: {response}", flush=True)

    sio.emit('register_node', {'node': '2'}, callback=registration_ack)


@sio.event
def disconnect():
    print("Disconnected from server.", flush=True)


@sio.on('target_command')
def handle_target_command(data):
    if data.get('action') != 'keepalive':
        print(f"COMMAND RECEIVED FROM BASE: {data}", flush=True)


def try_connect():
    try:
        sio.connect('http://192.168.1.1:8000')
    except Exception:
        pass


if __name__ == '__main__':
    try_connect()
    last_connect_attempt = time.monotonic()

    try:
        while True:
            while ser.in_waiting > 0:
                byte_in = ser.read(1)
                if not byte_in:
                    break

                last_char = this_char
                this_char = byte_in[0]

                # Frame is [0xA1, 0xB2, battery, current, temperature].
                if packet_runner == 0:
                    if this_char == 0xB2 and last_char == 0xA1:
                        telemetry_packet[0] = 0xA1
                        telemetry_packet[1] = 0xB2
                        packet_runner = 2
                else:
                    telemetry_packet[packet_runner] = this_char
                    packet_runner += 1

                    if packet_runner == TELEMETRY_PACKET_LENGTH:
                        packet_runner = 0

                        battery_byte = telemetry_packet[2]
                        current_byte = telemetry_packet[3]
                        temperature_byte = telemetry_packet[4]

                        estimated_battery_adc = battery_byte * 16
                        battery_pin_voltage = (estimated_battery_adc / 4095.0) * ADC_REFERENCE_VOLTS
                        battery_voltage = round(battery_pin_voltage * 4, 2)
                        current_amps = round(current_byte * CURRENT_BYTE_STEP_AMPS, 1)

                        estimated_temperature_adc = temperature_byte * 16
                        temperature_pin_voltage = (
                            estimated_temperature_adc / 4095.0
                        ) * ADC_REFERENCE_VOLTS
                        temperature_c = round(
                            (temperature_pin_voltage - TEMPERATURE_ZERO_C_VOLTS)
                            / TEMPERATURE_SLOPE_VOLTS_PER_C
                        )

                        print(
                            f"RECEIVED TELEMETRY: battery={battery_voltage}V, "
                            f"total_current={current_amps}A, temperature={temperature_c}C",
                            flush=True,
                        )

                        if sio.connected:
                            telemetry_data = {
                                'battery_voltage': battery_voltage,
                                'current_a': current_amps,
                                'temperature_c': temperature_c,
                                'node': '2',
                            }
                            try:
                                sio.emit('robot_telemetry', telemetry_data)
                            except Exception as e:
                                print(f"Emit failed: {e}", flush=True)

            if not sio.connected and time.monotonic() - last_connect_attempt >= 3.0:
                try_connect()
                last_connect_attempt = time.monotonic()

            time.sleep(0.01)

    except KeyboardInterrupt:
        if sio.connected:
            sio.disconnect()
        print("Client stopped by user.", flush=True)
