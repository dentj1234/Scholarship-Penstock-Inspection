const socket = io();

let activeControl = null;
let keepaliveTimer = null;
let lastControlTarget = null;
const fanSpeedByNode = { '0': 1, '1': 1 };
const fanDutyPercentByLevel = [0, 10, 20, 30, 50];
const motorSpeedByNode = { '0': 1, '1': 1 };
const motorSpeedPercentByLevel = [20, 40, 60, 80, 100];

socket.on('connect', () => {
    console.log(`Connected to base Socket.IO server: ${socket.id}`);
    socket.emit('request_unifi_ap_signals');

    // If the page reconnected after a network interruption, force a safe stop.
    if (lastControlTarget !== null) {
        sendRobotCommand(lastControlTarget, 'stop');
    }

    // Keep the selected node's speed in sync after a page reconnect.
    sendMotorSpeed(motorSpeedByNode[selectedNode()] ?? 1);
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

function updateMotorSpeedDisplay() {
    const level = motorSpeedByNode[selectedNode()] ?? 1;
    document.getElementById('motorSpeedValue').textContent = level;
    document.getElementById('motorSpeedPercent').textContent = `${motorSpeedPercentByLevel[level - 1]}% of drive limit`;
}

function sendMotorSpeed(speed) {
    const targetNode = selectedNode();
    socket.emit('web_trigger_command', {
        target_node: targetNode,
        action: 'motor_speed',
        speed: speed
    }, (ack) => {
        console.log('Base station motor speed result:', ack);
    });
    console.log(`Motor speed requested: level ${speed} (${motorSpeedPercentByLevel[speed - 1]}%) to Node ${targetNode}; connected=${socket.connected}`);
}

function changeMotorSpeed(delta) {
    const targetNode = selectedNode();
    const currentSpeed = motorSpeedByNode[targetNode] ?? 1;
    const newSpeed = Math.max(1, Math.min(5, currentSpeed + delta));
    if (newSpeed === currentSpeed) return;

    motorSpeedByNode[targetNode] = newSpeed;
    updateMotorSpeedDisplay();
    sendMotorSpeed(newSpeed);
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
    updateMotorSpeedDisplay();
    sendMotorSpeed(motorSpeedByNode[selectedNode()] ?? 1);
});

document.getElementById('fanSpeedDown').addEventListener('click', () => changeFanSpeed(-1));
document.getElementById('fanSpeedUp').addEventListener('click', () => changeFanSpeed(1));
document.getElementById('motorSpeedDown').addEventListener('click', () => changeMotorSpeed(-1));
document.getElementById('motorSpeedUp').addEventListener('click', () => changeMotorSpeed(1));
updateFanSpeedDisplay();
updateMotorSpeedDisplay();

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

function apSignalLabel(signalDbm) {
    if (signalDbm >= -60) return 'Strong';
    if (signalDbm >= -70) return 'Marginal';
    return 'Weak';
}

function appendApDetail(container, label, value) {
    if (value === undefined || value === null || value === '') return;
    const detail = document.createElement('div');
    detail.className = 'ap-link-detail';
    detail.textContent = `${label}: ${value}`;
    container.appendChild(detail);
}

function renderUniFiApSignals(payload) {
    const updated = document.getElementById('apLinksUpdated');
    const list = document.getElementById('apLinkList');
    const aps = Array.isArray(payload?.aps) ? payload.aps : [];

    if (payload?.updated_at) {
        const timeText = new Date(payload.updated_at * 1000).toLocaleTimeString();
        updated.textContent = payload.status === 'ok'
            ? `Updated ${timeText}`
            : `Last update ${timeText} · polling error`;
    } else {
        updated.textContent = payload?.message || 'Waiting for AP data...';
    }

    list.replaceChildren();
    if (aps.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'ap-links-empty';
        empty.textContent = payload?.message || 'No APs returned by UniFi.';
        list.appendChild(empty);
        return;
    }

    for (const ap of aps) {
        const card = document.createElement('article');
        card.className = 'ap-link-card';

        const heading = document.createElement('div');
        heading.className = 'ap-link-name';
        heading.textContent = ap.name || 'UniFi AP';
        card.appendChild(heading);

        const identity = document.createElement('div');
        identity.className = 'ap-link-identity';
        identity.textContent = ap.mac || ap.ip || '';
        card.appendChild(identity);

        const metric = document.createElement('div');
        if (!ap.online) {
            metric.className = 'ap-link-metric offline';
            metric.textContent = 'Offline';
        } else if (ap.uplink_type === 'wireless'
            && ap.signal_dbm !== null
            && ap.signal_dbm !== undefined
            && Number.isFinite(Number(ap.signal_dbm))) {
            const signal = Number(ap.signal_dbm);
            const quality = apSignalLabel(signal);
            metric.className = `ap-link-metric ${quality.toLowerCase()}`;
            metric.textContent = `${signal} dBm · ${quality}`;
        } else if (ap.uplink_type === 'wire') {
            metric.className = 'ap-link-metric wired';
            metric.textContent = 'Wired uplink';
        } else {
            metric.className = 'ap-link-metric unknown';
            metric.textContent = 'Uplink signal unavailable';
        }
        card.appendChild(metric);

        const parent = ap.parent_name || ap.parent_mac;
        if (parent) appendApDetail(card, 'Parent AP', parent);
        if (ap.channel !== undefined && ap.channel !== null && ap.channel !== '') {
            appendApDetail(card, 'Channel', ap.channel);
        }
        list.appendChild(card);
    }
}

socket.on('unifi_ap_signals', renderUniFiApSignals);
