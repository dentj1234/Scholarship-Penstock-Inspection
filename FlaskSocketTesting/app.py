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
    # Find and remove the node when it drops off
    node_name = connected_nodes.pop(request.sid, "Unknown Node")
    print(f"Node disconnected: {node_name} (Session ID: {request.sid})")

@socketio.on('robot_telemetry')
def handle_telemetry(data):
    node_name = str(data.get('node', 'unknown_node'))
    
    # Map this session ID to this specific node name
    connected_nodes[request.sid] = node_name
    node_to_sid[node_name] = request.sid 
    
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
    socketio.run(app, host='0.0.0.0', port=8000)