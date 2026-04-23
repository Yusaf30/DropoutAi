window.addEventListener('DOMContentLoaded', () => {
    const analyticsData = window.analyticsData || {};

    const attendanceData = {
        high: Number(analyticsData.attendance_high || 40),
        medium: Number(analyticsData.attendance_medium || 65),
        low: Number(analyticsData.attendance_low || 88),
    };

    const backlogsData = {
        high: Number(analyticsData.backlogs_high || 3.2),
        medium: Number(analyticsData.backlogs_medium || 1.3),
        low: Number(analyticsData.backlogs_low || 0.4),
    };

    const studyData = {
        high: Number(analyticsData.study_high || 2.4),
        medium: Number(analyticsData.study_medium || 4.6),
        low: Number(analyticsData.study_low || 6.8),
    };

    const defaultColors = {
        high: '#f97316',
        medium: '#fbbf24',
        low: '#22c55e'
    };

    const attendanceChart = document.getElementById('attendanceChart');
    const backlogsChart = document.getElementById('backlogsChart');
    const studyChart = document.getElementById('studyChart');

    if (typeof Chart !== 'undefined' && attendanceChart && backlogsChart && studyChart) {
        new Chart(attendanceChart, {
            type: 'bar',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Average Attendance (%)',
                    data: [attendanceData.high, attendanceData.medium, attendanceData.low],
                    backgroundColor: [defaultColors.high, defaultColors.medium, defaultColors.low],
                    borderColor: 'rgba(255,255,255,0.18)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: { color: '#e2e8f0' }
                    },
                    x: { ticks: { color: '#e2e8f0' } }
                },
                plugins: { legend: { display: false } }
            }
        });

        new Chart(backlogsChart, {
            type: 'bar',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Average Backlogs',
                    data: [backlogsData.high, backlogsData.medium, backlogsData.low],
                    backgroundColor: [defaultColors.high, defaultColors.medium, defaultColors.low],
                    borderColor: 'rgba(255,255,255,0.18)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#e2e8f0' } },
                    x: { ticks: { color: '#e2e8f0' } }
                },
                plugins: { legend: { display: false } }
            }
        });

        new Chart(studyChart, {
            type: 'bar',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Average Study Hours',
                    data: [studyData.high, studyData.medium, studyData.low],
                    backgroundColor: [defaultColors.high, defaultColors.medium, defaultColors.low],
                    borderColor: 'rgba(255,255,255,0.18)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true, ticks: { color: '#e2e8f0' } },
                    x: { ticks: { color: '#e2e8f0' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
});
