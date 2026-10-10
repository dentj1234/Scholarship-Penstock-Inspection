const socket = io();

let activeControl = null;
let keepaliveTimer = null;
let lastControlTarget = null;

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
});

socket.on('update_telemetry', (data) => {
    const telemetrySpan = document.getElementById('telemetryData');
    telemetrySpan.innerText = `Node: ${data.node} | Battery: ${data.battery}V`;
});
