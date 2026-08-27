const socket = io();
let activeTarget = 0; // Default to Node 0 (End Robot)
let currentVideoNode = 0;

function setTarget(nodeId) {
    activeTarget = nodeId;
    document.getElementById('target-display').textContent = `Controlling: Node ${nodeId}`;
}

function sendCommand(index, value) {
    socket.emit('send_command_to_node', {
        target: activeTarget,
        index: index,
        value: value
    });
}

function switchCamera(targetNode, ip) {
    // Stop current stream to save mesh bandwidth
    socket.emit('toggle_video_stream', { target: currentVideoNode, action: 'stop' });
    
    // Start target stream
    socket.emit('toggle_video_stream', { target: targetNode, action: 'start' });
    currentVideoNode = targetNode;

    document.getElementById('video-feed').src = `http://${ip}:8889/cam1`;
}

// Mouse Listeners
for (let i = 0; i < 4; i++) {
    const btn = document.getElementById(`btn-${i}`);
    if (btn) {
        btn.addEventListener('mousedown', () => sendCommand(i, 1));
        btn.addEventListener('mouseup', () => sendCommand(i, 0));
    }
}

// Keyboard Driving Listeners
window.addEventListener('keydown', (e) => {
    if (e.repeat) return;
    if (e.key === 'ArrowUp' || e.key === 'w') sendCommand(0, 1);
    if (e.key === 'ArrowDown' || e.key === 's') sendCommand(1, 1);
    if (e.key === 'ArrowLeft' || e.key === 'a') sendCommand(2, 1);
    if (e.key === 'ArrowRight' || e.key === 'd') sendCommand(3, 1);
});

window.addEventListener('keyup', (e) => {
    if (e.key === 'ArrowUp' || e.key === 'w') sendCommand(0, 0);
    if (e.key === 'ArrowDown' || e.key === 's') sendCommand(1, 0);
    if (e.key === 'ArrowLeft' || e.key === 'a') sendCommand(2, 0);
    if (e.key === 'ArrowRight' || e.key === 'd') sendCommand(3, 0);
});

// Telemetry Listener
socket.on('ui_update', (data) => {
    if (data['0']) {
        document.getElementById('node-0-telemetry').textContent = `Batt: ${data['0'].battery}V | Cam: ${data['0'].camera_active}`;
    }
    if (data['1']) {
        document.getElementById('node-1-telemetry').textContent = `Batt: ${data['1'].battery}V | Cam: ${data['1'].camera_active}`;
    }
});