<!-- # Flask AI Dropout Prediction System - Setup Guide

## Issues Fixed
✅ Python interpreter confusion
✅ Import resolution errors (pandas, flask, etc.)
✅ Flask app startup issues
✅ Jinja/JavaScript template errors

---

## Setup Instructions (Step-by-Step)

### Step 1: Create a Virtual Environment

A virtual environment isolates your project dependencies from your system Python.

**On Windows (PowerShell or CMD):**
```bash
cd "c:\Users\Admin\OneDrive\Desktop\web development\Ai dropout prediction and councelling system"
python -m venv .venv
```

**Activate the virtual environment:**
```bash
.venv\Scripts\Activate.ps1
```

(You should see `(.venv)` appear at the start of your terminal line)

---

### Step 2: Select the Python Interpreter in VS Code

1. Open VS Code
2. Press `Ctrl + Shift + P` to open the Command Palette
3. Search for and select: **Python: Select Interpreter**
4. Choose the option that shows: `.\.venv\Scripts\python.exe`
   - It should be listed as `./venv/Scripts/python.exe` (the local environment)

This ensures VS Code uses the virtual environment Python, not the system Python.

---

### Step 3: Install Required Packages

With the virtual environment activated, install all dependencies:

```bash
pip install -r requirements.txt
```

This command reads `requirements.txt` and installs:
- Flask (web framework)
- pandas (data manipulation)
- scikit-learn (machine learning)
- Werkzeug (Flask dependencies)
- Jinja2 (templating)

**Verify installation:**
```bash
pip list
```

You should see `Flask`, `pandas`, and `scikit-learn` in the list.

---

### Step 4: Train the ML Model (First Time Only)

Before running the Flask app, you need to generate `model.pkl`:

```bash
python train_model.py
```

This creates the trained model file that `app.py` loads at startup.

---

### Step 5: Run Flask Properly

**DO NOT use VS Code Live Server** (that's for static HTML, not Flask).

Instead, run Flask directly:

```bash
python app.py
```

**Output should show:**
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

- **Open the app:** Visit `http://127.0.0.1:5000` in your browser
- **To stop the app:** Press `Ctrl + C` in the terminal

---

### Step 6: Deactivate Virtual Environment (When Done)

When you finish working:

```bash
deactivate
```

The `(.venv)` prefix will disappear from your terminal.

---

## Troubleshooting

### Issue: "Flask could not be resolved"
**Solution:** 
- Make sure you selected the `.venv` interpreter (Step 2)
- Restart VS Code after selecting the interpreter

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution:**
- Check if virtual environment is activated (look for `(.venv)` in terminal)
- Run `pip install -r requirements.txt` again

### Issue: "Port 5000 already in use"
**Solution:**
- Kill the existing Flask process or use a different port:
  ```bash
  python -c "import os; os.environ['FLASK_ENV']='development'; exec(open('app.py').read())"
  ```

### Issue: "model.pkl not found"
**Solution:**
- First time: Run `python train_model.py` to train the model
- This generates `model.pkl` in the project root

---

## How Flask Should Run

1. **Start the Flask server** with `python app.py`
2. **Flask automatically reloads** when you save Python files (debug mode)
3. **Access the app** through the browser at `http://localhost:5000`
4. **Stop the server** with `Ctrl + C`

---

## Project Architecture

```
Ai dropout prediction and councelling system/
├── app.py                   # Flask backend
├── train_model.py          # ML model training
├── requirements.txt        # Python dependencies
├── model.pkl              # Trained model (auto-generated)
├── users.db               # SQLite database (auto-created)
├── static/
│   ├── css/               # All styling
│   └── js/                # All JavaScript
└── templates/             # HTML pages with Jinja
```

---

## Key Files Explained

- **app.py**: Main Flask application with all routes
- **requirements.txt**: Lists all Python packages needed
- **.venv/**: Virtual environment folder (created automatically)
- **model.pkl**: Trained ML model (run `train_model.py` to create)
- **users.db**: User database (created automatically on first run)

---

## Development Workflow

1. **Activate venv**: `.venv\Scripts\Activate.ps1`
2. **Run Flask**: `python app.py`
3. **Edit code** in VS Code (Flask auto-reloads on save)
4. **Test in browser**: `http://localhost:5000`
5. **Deactivate venv** when done: `deactivate`

---

## Summary of Fixes

✅ **Virtual Environment**: Isolated Python dependencies
✅ **Interpreter Selection**: VS Code uses `.venv` Python
✅ **Package Installation**: All dependencies installed via `requirements.txt`
✅ **Jinja/JavaScript**: Using `tojson` filter for safe variable injection
✅ **Flask Startup**: Works with `python app.py` (not Live Server)

Your Flask project is now ready to run! 🚀 -->
