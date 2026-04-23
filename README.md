# 🚀 AI Dropout Prediction & Counselling System

## 📌 Overview

AI Dropout Prediction & Counselling System is a full-stack web application that predicts the risk of student dropout using machine learning and provides personalized counselling recommendations.

This system helps identify at-risk students early and suggests actionable improvements.

---

## 🎯 Features

### 🔐 Authentication System

* User Registration & Login
* Role-based Access (Admin & User)
* Restricted Admin Access (specific emails only)

---

### 📊 Prediction System

* Manual input or CSV upload
* Predicts student risk level:

  * 🟢 Low Risk
  * 🟡 Medium Risk
  * 🔴 High Risk
* Uses ML model for analysis

---

### 📂 CSV Upload

* Bulk student prediction
* Required columns:

  * attendance
  * avg_marks
  * study_hours
  * backlogs
* Handles invalid formats & encoding issues

---

### 📈 Dashboard

* Total Students
* Risk Distribution (High / Medium / Low)
* Interactive Charts:

  * Pie Chart
  * Bar Graph
  * Radar Chart

---

### 🧠 Counselling System

* Personalized suggestions based on risk level
* Improvement recommendations
* Study and performance guidance

---

### 📄 Reports

* Student performance reports
* Risk analysis
* Counselling recommendations

---

### 🎨 UI/UX

* Modern Dark Theme 🌙
* Glassmorphism Design
* Responsive (Mobile + Desktop)
* Smooth animations & hover effects

---

## 🛠 Tech Stack

* **Frontend:** HTML, CSS, JavaScript
* **Backend:** Flask (Python)
* **Machine Learning:** Scikit-learn
* **Visualization:** Chart.js
* **Database:** SQLite
* **Hosting:** Render
* **Version Control:** GitHub

---

## 📦 Installation (Local Setup)

```bash
git clone https://github.com/your-username/dropout-ai.git
cd dropout-ai
pip install -r requirements.txt
python app.py
```

---

## 🌐 Live Demo

👉 https://dropoutai.onrender.com

---

## 📊 Input Parameters

| Parameter   | Description           |
| ----------- | --------------------- |
| Attendance  | % of classes attended |
| Avg Marks   | Academic performance  |
| Study Hours | Daily study time      |
| Backlogs    | Failed subjects       |

---

## 🚀 Future Improvements

* 📧 Bulk Email Notifications
* 📄 PDF Report Generation
* 📅 Date Range Analytics
* 🤖 AI Chatbot Counselling
* 🌍 Custom Domain & SEO

---

## 👨‍💻 Author

**Your Name**
B.Tech AIML Student

---

## ⭐ Support

If you like this project, give it a ⭐ on GitHub!
