const socket = io();

document.getElementById('cmdBtn').addEventListener('click', () => {
    // Grab the currently selected node from your dropdown/toggle
    const selectedNode = document.getElementById('nodeSelect').value;

    socket.emit('web_trigger_command', {
        target_node: selectedNode,
        action: 'ping_sensor'
    });
    
    console.log(`Sent command to Node ${selectedNode}`);
});