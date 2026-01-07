const token = localStorage.getItem("token");

// -------- LOAD CURRENT THRESHOLDS --------
fetch("/admin/thresholds", {
    headers: {
        "Authorization": "Bearer " + token
    }
})
.then(res => res.json())
.then(data => {
    document.getElementById("zone1").value = data.zone1;
    document.getElementById("zone2").value = data.zone2;
});

// -------- SAVE THRESHOLDS --------
function saveThresholds() {
    const data = {
        zone1: parseInt(document.getElementById("zone1").value),
        zone2: parseInt(document.getElementById("zone2").value)
    };

    fetch("/admin/thresholds", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(resp => {
        document.getElementById("status").innerText = resp.message;
    });
}
