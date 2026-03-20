// Setup button listeners
document.getElementById('btn-0').addEventListener('mousedown', () => sendCommand(0, 1));
document.getElementById('btn-0').addEventListener('mouseup', () => sendCommand(0, 0));
document.getElementById('btn-1').addEventListener('mousedown', () => sendCommand(1, 1));
document.getElementById('btn-1').addEventListener('mouseup', () => sendCommand(1, 0));
document.getElementById('btn-2').addEventListener('mousedown', () => sendCommand(2, 1));
document.getElementById('btn-2').addEventListener('mouseup', () => sendCommand(2, 0));
document.getElementById('btn-3').addEventListener('mousedown', () => sendCommand(3, 1));
document.getElementById('btn-3').addEventListener('mouseup', () => sendCommand(3, 0));

window.addEventListener('keydown', (event) => {
    if (event.repeat) return; // Prevents the command from spamming if held down
    if (event.key === 'ArrowUp') {
    sendCommand(3, 1);
  }
});
window.addEventListener('keyup', (event) => {
  if (event.key === 'ArrowUp') {
    sendCommand(3, 0); // For example, sending '0' to stop the action
  }
});

function sendCommand(index, value) {
    fetch('/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: index, value: value })
    });
}

function updateData() {
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            // Update the data display on the page
            if (Array.isArray(data.data)) {
                data.data.forEach((value, index) => {
                    const element = document.getElementById(`data-display-${index}`);
                    if (element) {
                        const label = element.getAttribute('data-label');
                        element.textContent = `${label}: ${value}`;
                    }
                });
            }
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

setInterval(function() {
    updateData();
}, 100);