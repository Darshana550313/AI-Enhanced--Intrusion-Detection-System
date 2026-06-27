# AI-Enhanced Intrusion Detection System

## Overview
A Machine Learning-based Intrusion Detection System (IDS) that analyzes network traffic, detects malicious activities, classifies attack types, and visualizes results via a professional Flask dashboard.

## Features
- **Multi-Model Training:** Decision Tree, Random Forest, XGBoost.
- **Auto-Model Selection:** Automatically picks the best performing model.
- **Attack Detection:** Normal, DoS, Probe, R2L, U2R.
- **Alert System:** Real-time alert generation.
- **Data Logging:** SQLite database for persistent storage.
- **Dashboard:** Interactive charts and statistics.

## Tech Stack
- **Backend:** Python, Flask
- **ML Libraries:** Scikit-learn, XGBoost, Pandas
- **Database:** SQLite
- **Frontend:** HTML, CSS, Bootstrap, Chart.js

## Project Structure
```
AI_Enhanced_Intrusion_Detection_System/
├── dataset/              # Place your NSL_KDD_Train.csv here
├── notebook/             # Jupyter notebook for training
├── models/               # Trained model saved here
├── database/             # SQLite DB (auto-created)
├── static/
│   ├── css/style.css     # Professional styling
│   ├── js/               # JavaScript files
│   └── images/           # Screenshots/assets
├── templates/
│   ├── index.html        # Home Page
│   ├── about.html        # Project Info
│   ├── upload.html       # Dataset Upload
│   ├── predict.html      # Detection Engine
│   ├── result.html       # Prediction Results
│   ├── dashboard.html    # Charts & Stats
│   └── logs.html         # Detection History
├── app.py                # Flask Backend
├── train_model.py        # ML Training Script
├── predict.py            # Batch Prediction
├── requirements.txt      # Dependencies
└── README.md             # Documentation
```

## Setup Instructions

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Add Your Dataset
1. Download primus11 NSL-KDD dataset from Kaggle
2. Copy the CSV file to `dataset/` folder
3. Rename it to `NSL_KDD_Train.csv` (or update path in notebook)

### Step 3: Train the Model (Jupyter Notebook)
```bash
jupyter notebook notebook/train_and_save.ipynb
```
- Run all cells in the notebook
- Model will be saved to `models/best_model.pkl`

### Step 4: Run the Flask App
```bash
python app.py
```
- Open browser: http://localhost:5000

## Deployment
### Render
1. Connect GitHub repo to Render.
2. Use Python environment.
3. Set start command: `gunicorn app:app`

### PythonAnywhere
1. Upload files via Files tab.
2. Open Bash console and run `pip install -r requirements.txt`.
3. Configure WSGI file to point to `app.py`.
