const socket = io();

let activeControl = null;
let keepaliveTimer = null;
let lastControlTarget = null;
const fanSpeedByNode = { '0': 1, '2': 1 };
const fanDutyPercentByLevel = [0, 10, 20, 30, 50];

socket.on('connect', () => {
    console.log(`Connected to base Socket.IO server: ${socket.id}`);

    // If the page reconnected after a network interruption, force a safe stop.
    if (lastControlTarget !== null) {
        sendRobotCommand(lastControlTarget, 'stop');
    }
});

socket.on('connect_error', (error) => {
    console.error('Socket.IO connection error:', error.message);
});

socket.on('disconnect', (reason) => {
    console.warn('Disconnected from base Socket.IO server:', reason);

    // No stop can be delivered while disconnected. The node's command timeout
    // clears its movement flags if keepalives stop arriving.
    if (activeControl) {
        lastControlTarget = activeControl.targetNode;
        clearActiveControl();
    }
});

function sendRobotCommand(targetNode, action) {
    socket.emit('web_trigger_command', {
        target_node: targetNode,
        action: action
    }, (ack) => {
        console.log('Base station command result:', ack);
    });

    console.log(`Command requested: [${action}] to Node ${targetNode}; connected=${socket.connected}`);
}

function selectedNode() {
    return document.getElementById('nodeSelect').value;
}

function updateFanSpeedDisplay() {
    const level = fanSpeedByNode[selectedNode()] ?? 1;
    document.getElementById('fanSpeedValue').textContent = level;
    document.getElementById('fanSpeedDuty').textContent = `${fanDutyPercentByLevel[level - 1]}% PWM duty`;
}

function sendFanSpeed(speed) {
    const targetNode = selectedNode();
    socket.emit('web_trigger_command', {
        target_node: targetNode,
        action: 'fan_speed',
        speed: speed
    }, (ack) => {
        console.log('Base station fan speed result:', ack);
    });
    console.log(`Fan speed requested: level ${speed} to Node ${targetNode}; connected=${socket.connected}`);
}

function changeFanSpeed(delta) {
    const targetNode = selectedNode();
    const currentSpeed = fanSpeedByNode[targetNode] ?? 1;
    const newSpeed = Math.max(1, Math.min(5, currentSpeed + delta));
    if (newSpeed === currentSpeed) return;

    fanSpeedByNode[targetNode] = newSpeed;
    updateFanSpeedDisplay();
    sendFanSpeed(newSpeed);
}

function clearActiveControl() {
    if (keepaliveTimer !== null) {
        clearInterval(keepaliveTimer);
        keepaliveTimer = null;
    }
    activeControl = null;
}

function startControl(action, owner) {
    if (activeControl && activeControl.owner === owner && activeControl.action === action) {
        return;
    }

    // Only one direction is active at a time. Stop the old target before
    // starting a newly selected direction or node.
    if (activeControl) {
        stopControl();
    }

    const targetNode = selectedNode();
    activeControl = { action, owner, targetNode };
    lastControlTarget = targetNode;
    sendRobotCommand(targetNode, action);

    // Refresh the node's deadman timer while the control remains held.
    keepaliveTimer = setInterval(() => {
        if (activeControl && socket.connected) {
            socket.emit('web_control_keepalive', {
                target_node: activeControl.targetNode
            });
        }
    }, 250);
}

function stopControl() {
    const targetNode = activeControl?.targetNode ?? lastControlTarget ?? selectedNode();
    clearActiveControl();
    lastControlTarget = targetNode;
    sendRobotCommand(targetNode, 'stop');
}

const arrowKeyMap = {
    ArrowUp: 'forward',
    ArrowDown: 'backward',
    ArrowLeft: 'left',
    ArrowRight: 'right'
};

function isEditableTarget(target) {
    return target instanceof Element && target.closest('input, textarea, select, [contenteditable="true"]');
}

function switchCamera(streamUrl) {
    document.getElementById('camStream').src = streamUrl;
    console.log(`Switched camera feed to: ${streamUrl}`);
}

document.querySelectorAll('.cmd-btn:not(#btnStop)').forEach((button) => {
    const action = button.dataset.action;

    button.addEventListener('pointerdown', (event) => {
        event.preventDefault();
        button.setPointerCapture(event.pointerId);
        startControl(action, `pointer:${event.pointerId}`);
    });

    const releasePointer = (event) => stopControlIfOwner(`pointer:${event.pointerId}`);
    button.addEventListener('pointerup', releasePointer);
    button.addEventListener('pointercancel', releasePointer);
    button.addEventListener('lostpointercapture', releasePointer);

    // Keep the controls usable from the keyboard as well as touch and mouse.
    button.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            startControl(action, `button-key:${button.id}:${event.code}`);
        }
    });
    button.addEventListener('keyup', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            stopControlIfOwner(`button-key:${button.id}:${event.code}`);
        }
    });
});

function stopControlIfOwner(owner) {
    if (activeControl && activeControl.owner === owner) {
        stopControl();
    }
}

document.getElementById('btnStop').addEventListener('click', stopControl);

document.addEventListener('keydown', (event) => {
    const action = arrowKeyMap[event.key];
    if (!action || isEditableTarget(event.target)) return;

    event.preventDefault();
    startControl(action, `key:${event.code}`);
});

document.addEventListener('keyup', (event) => {
    if (arrowKeyMap[event.key]) {
        stopControlIfOwner(`key:${event.code}`);
    }
});

// Release-to-stop should also apply if the user switches tabs or the window
// loses focus while holding a direction.
window.addEventListener('blur', stopControl);
document.addEventListener('visibilitychange', () => {
    if (document.hidden) stopControl();
});
document.getElementById('nodeSelect').addEventListener('change', () => {
    if (activeControl) stopControl();
    updateFanSpeedDisplay();
});

document.getElementById('fanSpeedDown').addEventListener('click', () => changeFanSpeed(-1));
document.getElementById('fanSpeedUp').addEventListener('click', () => changeFanSpeed(1));
updateFanSpeedDisplay();

socket.on('update_telemetry', (data) => {
    const nodeId = String(data.node);
    const telemetrySpan = document.getElementById(`telemetryNode${nodeId}`);
    if (!telemetrySpan) {
        console.warn(`Telemetry received for unknown node: ${nodeId}`, data);
        return;
    }

    const batteryVoltage = data.battery_voltage ?? data.battery;
    const batteryText = batteryVoltage === undefined
        ? 'Battery: unavailable'
        : `Battery: ${batteryVoltage}V`;
    const currentText = data.current_a === undefined
        ? 'Current: unavailable'
        : `Total current: ${Number(data.current_a).toFixed(1)}A`;
    const temperatureText = data.temperature_c === undefined
        ? 'Temperature: unavailable'
        : `Temperature: ${Number(data.temperature_c).toFixed(0)}°C`;
    telemetrySpan.innerText = `${batteryText} | ${currentText} | ${temperatureText}`;
});
