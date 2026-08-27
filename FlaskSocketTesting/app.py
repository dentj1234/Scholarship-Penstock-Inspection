from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'drewismyidol'
socketio = SocketIO(app, cors_allowed_origins="*")

telemetry_store = {}

@app.route('/')
@app.route('/home')
def home():
    return render_template('testingindex.html')

# Robot Node connects and registers its integer ID (e.g. 0, 1, 2)
@socketio.on('register_node')
def handle_register(data):
    node_id = data.get('node_id') # e.g. 0 or 1
    if node_id is not None:
        join_room(str(node_id))
        print(f"✅ Robot Node registered: Node {node_id}")

@socketio.on('telemetry')
def handle_telemetry(data):
    node_id = data.get('node_id')
    if node_id is not None:
        telemetry_store[str(node_id)] = data
        emit('ui_update', telemetry_store, broadcast=True)

# Target node command routing
@socketio.on('send_command_to_node')
def handle_node_command(data):
    target = str(data.get('target'))  # "0", "1", etc.
    index = data.get('index')
    value = data.get('value')
    
    emit('execute_command', {'index': index, 'value': value}, to=target)

@socketio.on('toggle_video_stream')
def handle_video_toggle(data):
    target = str(data.get('target'))
    action = data.get('action') # 'start' or 'stop'
    emit('camera_control', {'action': action}, to=target)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=False)