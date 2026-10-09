from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import time
import threading

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_nodes = {}
sid_to_node = {}
node_to_sid = {}

@socketio.on('connect')
def handle_connect(auth=None):
    print(f"A node has connected. Session ID: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect(auth=None):
    # Remove the node's routing entry when this session drops off.
    node_name = connected_nodes.pop(request.sid, None)
    if node_name and node_to_sid.get(node_name) == request.sid:
        node_to_sid.pop(node_name, None)
    if node_name is None:
        node_name = "Unknown Node"
    print(f"Node disconnected: {node_name} (Session ID: {request.sid})")

def register_node_session(node_name, sid):
    # If the same node reconnects, discard its old session mapping.
    previous_sid = node_to_sid.get(node_name)
    if previous_sid and previous_sid != sid:
        connected_nodes.pop(previous_sid, None)

    connected_nodes[sid] = node_name
    node_to_sid[node_name] = sid

@socketio.on('register_node')
def handle_register_node(data):
    node_name = str(data.get('node', '')).strip()
    if not node_name:
        print(f"Rejected node registration without a node name: {data}")
        return {'ok': False, 'error': 'missing_node'}

    register_node_session(node_name, request.sid)
    print(f"Registered node [{node_name}] (Session ID: {request.sid})")
    return {'ok': True, 'node': node_name}

@socketio.on('robot_telemetry')
def handle_telemetry(data):
    node_name = str(data.get('node', 'unknown_node'))
    
    # Keep this session's routing registration in sync with its telemetry.
    register_node_session(node_name, request.sid)
    
    print(f"Received from [{node_name}]: Battery={data.get('battery')}V")
    socketio.emit('update_telemetry', data)

@socketio.on('web_trigger_command')
def handle_web_command(data):
    target_node = str(data.get('target_node'))
    action = data.get('action')
    send_command(target_node, {'action': action})

def send_command(node_name, command_payload):
    target_sid = node_to_sid.get(node_name)
    if target_sid:
        socketio.emit('target_command', command_payload, to=target_sid)
        print(f"Sent command to {node_name}: {command_payload}")
    else:
        print(f"Could not find active session for node: {node_name}")

@app.route('/')
def index():
    return render_template('testingindex.html')

if __name__ == '__main__':
    # Listen on all interfaces on port 8000
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
