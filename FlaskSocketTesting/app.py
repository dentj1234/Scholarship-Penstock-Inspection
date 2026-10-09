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
    print(f"Socket.IO client connected: sid={request.sid}", flush=True)

@socketio.on('disconnect')
def handle_disconnect(auth=None):
    # Remove the node's routing entry when this session drops off.
    node_name = connected_nodes.pop(request.sid, None)
    if node_name and node_to_sid.get(node_name) == request.sid:
        node_to_sid.pop(node_name, None)
    if node_name is None:
        node_name = "Unknown Node"
    print(f"Socket.IO client disconnected: node={node_name} sid={request.sid}", flush=True)

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
        print(f"Rejected node registration without a node name: {data!r}", flush=True)
        return {'ok': False, 'error': 'missing_node'}

    register_node_session(node_name, request.sid)
    print(f"Registered node: node={node_name} sid={request.sid}", flush=True)
    return {'ok': True, 'node': node_name}

@socketio.on('robot_telemetry')
def handle_telemetry(data):
    node_name = str(data.get('node', 'unknown_node'))
    
    # Keep this session's routing registration in sync with its telemetry.
    register_node_session(node_name, request.sid)
    
    print(f"Telemetry from node={node_name}: {data!r}", flush=True)
    socketio.emit('update_telemetry', data)

@socketio.on('web_trigger_command')
def handle_web_command(data):
    target_node = str(data.get('target_node'))
    action = data.get('action')
    print(f"Web command received: node={target_node} action={action}", flush=True)
    sent = send_command(target_node, {'action': action})
    return {
        'ok': sent,
        'target_node': target_node,
        'action': action,
        'status': 'forwarded' if sent else 'node_not_registered',
    }

def send_command(node_name, command_payload):
    target_sid = node_to_sid.get(node_name)
    if target_sid:
        socketio.emit('target_command', command_payload, to=target_sid)
        print(f"Forwarded command to node={node_name} payload={command_payload!r}", flush=True)
        return True
    else:
        print(f"No active session registered for node={node_name}", flush=True)
        return False

@app.route('/')
def index():
    return render_template('testingindex.html')

if __name__ == '__main__':
    # Listen on all interfaces on port 8000
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
