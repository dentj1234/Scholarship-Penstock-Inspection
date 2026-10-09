const socket = io();

socket.on('connect', () => {
    console.log(`Connected to base Socket.IO server: ${socket.id}`);
});

socket.on('connect_error', (error) => {
    console.error('Socket.IO connection error:', error.message);
});

socket.on('disconnect', (reason) => {
    console.warn('Disconnected from base Socket.IO server:', reason);
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

const arrowKeyMap = {
    'ArrowUp': 'forward',
    'ArrowDown': 'backward',
    'ArrowLeft': 'left',
    'ArrowRight': 'right'
};

// Function to dynamically update the iframe source when a camera button is clicked
function switchCamera(streamUrl) {
    const iframeElement = document.getElementById('camStream');
    iframeElement.src = streamUrl;
    console.log(`Switched camera feed to: ${streamUrl}`);
}

document.querySelectorAll('.cmd-btn').forEach(button => {
    button.addEventListener('click', () => {
        const selectedNode = document.getElementById('nodeSelect').value;
        const actionType = button.getAttribute('data-action');
        
        sendRobotCommand(selectedNode, actionType);
    });
});

document.addEventListener('keydown', (event) => {
    const action = arrowKeyMap[event.key];
    if (!action) return; // Ignore other keys

    // Prevent default browser scrolling behavior for arrow keys
    event.preventDefault();

    const selectedNode = document.getElementById('nodeSelect').value;

    sendRobotCommand(selectedNode, action);
});


socket.on('update_telemetry', (data) => {
    const telemetrySpan = document.getElementById('telemetryData');
    telemetrySpan.innerText = `Node: ${data.node} | Battery: ${data.battery}V`;
});
