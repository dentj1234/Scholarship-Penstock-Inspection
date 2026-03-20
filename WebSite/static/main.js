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
}, 250);