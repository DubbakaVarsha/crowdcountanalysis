setInterval(() => {
    fetch("/analytics")
        .then(res => res.json())
        .then(data => {
            // Total
            document.getElementById("total").innerText = data.total;

            // Zones dynamically
            const container = document.getElementById("zonesContainer");
            container.innerHTML = "";
            for (const zoneName in data.zones) {
                container.innerHTML += `
                    <div class="card">
                        🟢 ${zoneName}: <span>${data.zones[zoneName]}</span>
                    </div>
                `;
            }

            // Alert
            document.getElementById("alertBox").style.display =
                data.alert ? "block" : "none";
        });
}, 1000);
