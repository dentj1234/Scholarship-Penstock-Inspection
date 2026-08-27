import time
import subprocess
import socketio

# ----------------------------
# NODE CONFIGURATION
NODE_ID = 0  # 0 = End Robot, 1 = Middle Node, 2+ = Future Nodes
# ----------------------------

BASE_STATION_URL = "http://127.0.0.1:8000"

sio = socketio.Client()
data_array = [0, 0, 0, 0]
camera_process = None

def start_camera():
    global camera_process
    if camera_process is None:
        cmd = "rpicam-vid -t 0 --camera 0 --nopreview --codec yuv420 --width 1280 --height 720 --inline --listen -o - | ffmpeg -f rawvideo -pix_fmt yuv420p -s:v 1280x720 -i /dev/stdin -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://localhost:8554/cam1"
        camera_process = subprocess.Popen(cmd, shell=True, executable='/bin/bash')
        print(f"📷 Node {NODE_ID} Camera started.")

def stop_camera():
    global camera_process
    if camera_process is not None:
        subprocess.run(["pkill", "-f", "rpicam-vid"])
        camera_process = None
        print(f"🛑 Node {NODE_ID} Camera stopped.")

@sio.event
def connect():
    print(f"Connected to Base Station! Registering as Node {NODE_ID}...")
    sio.emit('register_node', {'node_id': NODE_ID})

@sio.on('execute_command')
def on_command(data):
    global data_array
    idx = data.get('index')
    val = data.get('value')
    if 0 <= idx < len(data_array):
        data_array[idx] = val
        print(f"Node {NODE_ID} Received Command: {data_array}")

@sio.on('camera_control')
def on_camera_control(data):
    action = data.get('action')
    if action == 'start':
        start_camera()
    elif action == 'stop':
        stop_camera()

def main():
    while True:
        try:
            if not sio.connected:
                sio.connect(BASE_STATION_URL)
            
            telemetry_payload = {
                'node_id': NODE_ID,
                'battery': 12.4, # Replace with actual ADC hardware read
                'camera_active': camera_process is not None,
                'data_array': data_array
            }
            sio.emit('telemetry', telemetry_payload)
            time.sleep(1.0)
            
        except Exception as e:
            print(f"Reconnecting to Base Station... ({e})")
            time.sleep(2.0)

if __name__ == '__main__':
    main()