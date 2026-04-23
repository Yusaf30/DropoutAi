<!-- # Quick Start Guide - Flask App Setup

## Run These Commands in Order

### 1. Open PowerShell/Terminal in Project Folder
```
cd "c:\Users\Admin\OneDrive\Desktop\web development\Ai dropout prediction and councelling system"
```

### 2. Create Virtual Environment
```
python -m venv .venv
```

### 3. Activate Virtual Environment
```
.venv\Scripts\Activate.ps1
```
*(You should see `(.venv)` in terminal now)*

### 4. Install All Packages
```
pip install -r requirements.txt
```

### 5. Train the ML Model (First Time Only)
```
python train_model.py
```
*(This creates `model.pkl`)*

### 6. Run Flask App
```
python app.py
```

### 7. Open in Browser
Visit: **http://127.0.0.1:5000**

### 8. Stop Flask
Press: **Ctrl + C** in terminal

### 9. Deactivate Virtual Environment
```
deactivate
```

---

## VS Code Setup (After Virtual Environment is Created)

1. **Press**: `Ctrl + Shift + P`
2. **Search**: "Python: Select Interpreter"
3. **Choose**: `.\.venv\Scripts\python.exe` (the one with .venv)
4. **Restart** VS Code to apply changes

---

## Expected Output

When you run `python app.py`, you should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
WARNING: This is a development server. Do not use it in production.
 * Restarting with reloader
```

Then go to `http://127.0.0.1:5000` in your browser.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: flask` | Did you activate `.venv`? Run `.venv\Scripts\Activate.ps1` |
| "Port 5000 in use" | Run `python app.py` from a fresh terminal |
| VS Code shows red squiggles | Select `.venv` interpreter in VS Code (Ctrl+Shift+P) |
| `model.pkl` not found | Run `python train_model.py` first |

---

That's it! Your Flask app is ready. 🎉 -->
