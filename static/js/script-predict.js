function generateInputs() {
    let count = document.getElementById("subjectCount").value;
    let container = document.getElementById("subjectsContainer");

    container.innerHTML = "";

    for (let i = 1; i <= count; i++) {
        container.innerHTML += `
            <label>Subject ${i} Marks:</label>
            <input type="number" class="marks" required><br>
        `;
    }
}

function calculateAverage() {
    let marks = document.querySelectorAll(".marks");
    let total = 0;

    marks.forEach(input => {
        total += parseFloat(input.value) || 0;
    });

    let avg = total / marks.length;

    document.getElementById("avgMarks").value = avg;
}