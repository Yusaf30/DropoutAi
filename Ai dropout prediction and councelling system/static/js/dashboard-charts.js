window.addEventListener('DOMContentLoaded', () => {
    const dashboardData = window.dashboardData || {};
    const totalValue = Number(dashboardData.total || 0);
    const highValue = Number(dashboardData.high || 0);
    const mediumValue = Number(dashboardData.medium || 0);
    const lowValue = Number(dashboardData.low || 0);

    const pieCtx = document.getElementById('pieChart');
    const barCtx = document.getElementById('barChart');

    if (typeof Chart !== 'undefined' && pieCtx && barCtx) {
        new Chart(pieCtx, {
            type: 'pie',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    data: [highValue, mediumValue, lowValue],
                    backgroundColor: ['#f97316', '#38bdf8', '#22c55e'],
                    borderColor: '#0f172a',
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#e2e8f0'
                        }
                    }
                }
            }
        });

        new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: ['Total', 'High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Students',
                    data: [totalValue, highValue, mediumValue, lowValue],
                    backgroundColor: ['#64748b', '#f97316', '#38bdf8', '#22c55e'],
                    borderColor: 'rgba(255,255,255,0.12)',
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        ticks: {
                            color: '#e2e8f0'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        ticks: {
                            color: '#e2e8f0'
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
    }
});
