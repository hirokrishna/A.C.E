// JavaScript for Charts in Student Prediction System

document.addEventListener("DOMContentLoaded", function () {
    var passFailCanvas = document.getElementById("passFailChart");
    var riskCanvas = document.getElementById("riskChart");

    // Only run if chart canvas elements exist on this page
    if (passFailCanvas && riskCanvas) {
        fetch("/api/chart-data")
            .then(function (response) {
                return response.json();
            })
            .then(function (data) {
                // 1. Pass vs Fail Pie Chart
                new Chart(passFailCanvas, {
                    type: "pie",
                    data: {
                        labels: ["Pass", "Fail"],
                        datasets: [{
                            data: [data.pass_count, data.fail_count],
                            backgroundColor: ["#28a745", "#dc3545"]
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: "bottom"
                            }
                        }
                    }
                });

                // 2. Risk Level Bar Chart
                new Chart(riskCanvas, {
                    type: "bar",
                    data: {
                        labels: ["High Risk", "Medium Risk", "Low Risk"],
                        datasets: [{
                            label: "Number of Students",
                            data: [data.high_risk_count, data.medium_risk_count, data.low_risk_count],
                            backgroundColor: ["#dc3545", "#fd7e14", "#28a745"]
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            }
                        }
                    }
                });
            })
            .catch(function (error) {
                console.log("Error loading chart data:", error);
            });
    }
});
