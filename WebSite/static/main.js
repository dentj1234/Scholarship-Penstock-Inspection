function updateData() {
    fetch('/data')
        .then(response => response.json())
        .then(data => {
            // Update the data display on the page
            document.getElementById('data-display').textContent = data.data;
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

setInterval(function() {
    updateData();
}, 250);