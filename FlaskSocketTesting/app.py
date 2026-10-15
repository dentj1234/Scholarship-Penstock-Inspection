from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

connected_nodes = {}
sid_to_node = {}
node_to_sid = {}

UNIFI_BASE_URL = 'https://192.168.1.1:11443'
UNIFI_SITE = 'default'
UNIFI_USERNAME = os.environ.get('UNIFI_USERNAME', '').strip()
UNIFI_PASSWORD = os.environ.get('UNIFI_PASSWORD', '')
UNIFI_POLL_INTERVAL = 5

latest_unifi_signal = {
    'status': 'not_configured',
    'message': 'Set UniFi credentials in /etc/basecode/unifi.env to enable AP link readings.',
    'aps': [],
    'updated_at': None,
}


def unifi_is_configured():
    return bool(UNIFI_USERNAME and UNIFI_PASSWORD)


class UniFiApi:
    """Keep a UniFi login cookie and read the current AP uplinks."""

    def __init__(self):
        self.session = requests.Session()
        # This is a closed local network; UniFi's local HTTPS certificate is not validated.
        self.session.verify = False
        self.logged_in = False

    def login(self):
        response = self.session.post(
            f'{UNIFI_BASE_URL}/api/auth/login',
            json={'username': UNIFI_USERNAME, 'password': UNIFI_PASSWORD, 'remember': True},
            timeout=8,
        )
        response.raise_for_status()
        self.logged_in = True

    def get_devices(self):
        if not self.logged_in:
            self.login()

        url = f'{UNIFI_BASE_URL}/proxy/network/api/s/{UNIFI_SITE}/stat/device'
        response = self.session.get(url, timeout=8)
        if response.status_code in (401, 403):
            self.login()
            response = self.session.get(url, timeout=8)
        response.raise_for_status()

        result = response.json()
        if result.get('meta', {}).get('rc') != 'ok':
            self.logged_in = False
            self.login()
            response = self.session.get(url, timeout=8)
            response.raise_for_status()
            result = response.json()
        if result.get('meta', {}).get('rc') != 'ok':
            raise RuntimeError('UniFi returned an unsuccessful response')
        return result


def extract_ap_uplink_signals(response):
    devices = response.get('data', []) if isinstance(response, dict) else []
    aps = []
    for device in devices:
        if device.get('type') != 'uap' and device.get('is_access_point') is not True:
            continue

        uplink = device.get('uplink') or {}
        signal = uplink.get('signal')
        try:
            signal_dbm = round(float(signal)) if signal is not None else None
        except (TypeError, ValueError):
            signal_dbm = None

        raw_state = device.get('state')
        is_online = raw_state == 1 or str(raw_state).upper() in ('ONLINE', 'CONNECTED')
        uplink_type = str(uplink.get('type', '')).lower()
        if not uplink_type:
            last_uplink = device.get('last_uplink') or {}
            uplink_type = str(last_uplink.get('type', '')).lower()

        aps.append({
            'name': device.get('name') or device.get('model') or 'UniFi AP',
            'mac': device.get('mac', ''),
            'ip': device.get('ip', ''),
            'online': is_online,
            'uplink_type': uplink_type,
            'parent_name': uplink.get('uplink_device_name') or uplink.get('name') or '',
            'parent_mac': uplink.get('uplink_mac') or uplink.get('ap_mac') or '',
            'signal_dbm': signal_dbm if uplink_type == 'wireless' else None,
            'channel': uplink.get('channel'),
            'radio': uplink.get('radio_name') or uplink.get('radio'),
        })

    aps.sort(key=lambda ap: ap['name'].lower())
    return aps


def publish_unifi_signal(payload):
    global latest_unifi_signal
    latest_unifi_signal = payload
    socketio.emit('unifi_ap_signals', payload)


def poll_unifi_ap_signals():
    client = UniFiApi()
    last_error_log = 0.0
    while True:
        try:
            response = client.get_devices()
            aps = extract_ap_uplink_signals(response)
            payload = {
                'status': 'ok',
                'message': '',
                'aps': aps,
                'updated_at': time.time(),
            }
            publish_unifi_signal(payload)
        except Exception as error:
            now = time.monotonic()
            if now - last_error_log >= 30:
                print(f'UniFi AP signal poll failed: {type(error).__name__}: {error}', flush=True)
                last_error_log = now
            publish_unifi_signal({
                'status': 'error',
                'message': 'UniFi AP readings unavailable; check basecode.service journal and UniFi settings.',
                'aps': latest_unifi_signal.get('aps', []),
                'updated_at': latest_unifi_signal.get('updated_at'),
            })
        socketio.sleep(UNIFI_POLL_INTERVAL)

@socketio.on('connect')
def handle_connect(auth=None):
    print(f"Socket.IO client connected: sid={request.sid}", flush=True)

@socketio.on('request_unifi_ap_signals')
def handle_request_unifi_ap_signals():
    emit('unifi_ap_signals', latest_unifi_signal, to=request.sid)

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
    socketio.emit('node_registered', {'node': node_name}, skip_sid=request.sid)
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
    command_payload = {'action': action}
    if action in ('fan_speed', 'motor_speed'):
        try:
            speed = int(data.get('speed'))
        except (TypeError, ValueError):
            speed = 0
        if speed < 1 or speed > 5:
            print(f"Rejected {action} command: node={target_node} speed={data.get('speed')!r}", flush=True)
            return {
                'ok': False,
                'target_node': target_node,
                'action': action,
                'status': f'invalid_{action}',
            }
        command_payload['speed'] = speed
    elif action == 'motor_trim':
        trim_side = str(data.get('side', '')).lower()
        try:
            trim_percent = int(data.get('percent'))
        except (TypeError, ValueError):
            trim_percent = -1
        valid_clear = trim_side == 'none' and trim_percent == 0
        valid_trim = trim_side in ('left', 'right') and 1 <= trim_percent <= 20
        if not (valid_clear or valid_trim):
            print(
                f"Rejected motor trim command: node={target_node} "
                f"side={trim_side!r} percent={data.get('percent')!r}",
                flush=True,
            )
            return {
                'ok': False,
                'target_node': target_node,
                'action': action,
                'status': 'invalid_motor_trim',
            }
        command_payload.update({'side': trim_side, 'percent': trim_percent})

    print(f"Web command received: node={target_node} payload={command_payload!r}", flush=True)
    sent = send_command(target_node, command_payload)
    return {
        'ok': sent,
        'target_node': target_node,
        'action': action,
        'speed': command_payload.get('speed'),
        'side': command_payload.get('side'),
        'percent': command_payload.get('percent'),
        'status': 'forwarded' if sent else 'node_not_registered',
    }

@socketio.on('web_control_keepalive')
def handle_web_control_keepalive(data):
    # Heartbeats refresh the node's deadman timer without repeating the
    # movement command or filling the service journal with command logs.
    target_node = str(data.get('target_node'))
    sent = send_command(target_node, {'action': 'keepalive'}, log=False)
    return {'ok': sent}

def send_command(node_name, command_payload, log=True):
    target_sid = node_to_sid.get(node_name)
    if target_sid:
        socketio.emit('target_command', command_payload, to=target_sid)
        if log:
            print(f"Forwarded command to node={node_name} payload={command_payload!r}", flush=True)
        return True
    else:
        if log:
            print(f"No active session registered for node={node_name}", flush=True)
        return False

@app.route('/')
def index():
    return render_template('testingindex.html')

if __name__ == '__main__':
    # Listen on all interfaces on port 8000
    if unifi_is_configured():
        socketio.start_background_task(poll_unifi_ap_signals)
        print(f'UniFi AP signal polling started: site={UNIFI_SITE} interval={UNIFI_POLL_INTERVAL}s', flush=True)
    else:
        print('UniFi AP signal polling disabled: configure /etc/basecode/unifi.env', flush=True)
    socketio.run(app, host='0.0.0.0', port=8000, allow_unsafe_werkzeug=True)
