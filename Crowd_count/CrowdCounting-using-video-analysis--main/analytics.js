const totalCtx = document.getElementById("totalChart").getContext("2d");
const zoneCtx = document.getElementById("zoneChart").getContext("2d");
const alertCtx = document.getElementById("alertChart").getContext("2d");

let timeLabels = [];
let totalData = [];
let alertData = [];

const totalChart = new Chart(totalCtx, {
    type: "line",
    data: {
        labels: timeLabels,
        datasets: [{
            label: "Total Crowd",
            data: totalData,
            borderWidth: 2,
            fill: false
        }]
    }
});

const zoneChart = new Chart(zoneCtx, {
    type: "bar",
    data: {
        labels: [],
        datasets: [{
            label: "Zone Crowd",
            data: [],
            borderWidth: 1
        }]
    }
});

const alertChart = new Chart(alertCtx, {
    type: "line",
    data: {
        labels: timeLabels,
        datasets: [{
            label: "Alerts",
            data: alertData,
            borderWidth: 2,
            fill: false
        }]
    }
});

function updateAnalytics() {
    fetch("/analytics")
        .then(res => res.json())
        .then(data => {
            // Time
            timeLabels.push(data.time);
            if (timeLabels.length > 20) timeLabels.shift();

            // Total crowd
            totalData.push(data.total);
            if (totalData.length > 20) totalData.shift();

            // Alerts
            alertData.push(data.alert ? 1 : 0);
            if (alertData.length > 20) alertData.shift();

            // Zone-wise
            zoneChart.data.labels = Object.keys(data.zones);
            zoneChart.data.datasets[0].data = Object.values(data.zones);

            totalChart.update();
            zoneChart.update();
            alertChart.update();
        })
        .catch(err => console.error("Analytics error:", err));
}

// Refresh every 2 seconds
setInterval(updateAnalytics, 2000);
