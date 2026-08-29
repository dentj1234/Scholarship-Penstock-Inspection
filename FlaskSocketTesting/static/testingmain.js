const socket = io();

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
        
        socket.emit('web_trigger_command', {
            target_node: selectedNode,
            action: actionType
        });
        
        console.log(`Sent command [${actionType}] to Node ${selectedNode}`);
    });
});

document.addEventListener('keydown', (event) => {
    const action = arrowKeyMap[event.key];
    if (!action) return; // Ignore other keys

    // Prevent default browser scrolling behavior for arrow keys
    event.preventDefault();

    const selectedNode = document.getElementById('nodeSelect').value;

    socket.emit('web_trigger_command', {
        target_node: selectedNode,
        action: action
    });

    console.log(`Keyboard command [${action}] sent to Node ${selectedNode}`);
});


socket.on('update_telemetry', (data) => {
    const telemetrySpan = document.getElementById('telemetryData');
    telemetrySpan.innerText = `Node: ${data.node} | Battery: ${data.battery}V`;
});