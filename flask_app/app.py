import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import pandas as pd
import numpy as np
import pickle
import sqlite3
from werkzeug.utils import secure_filename

# Initialize Flask App
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'dataset'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Logging Configuration
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Database Initialization
def init_db():
    os.makedirs('database', exist_ok=True)
    conn = sqlite3.connect('database/intrusion_logs.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS detection_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            source_ip TEXT,
            destination_ip TEXT,
            prediction TEXT,
            attack_type TEXT,
            confidence REAL,
            details TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Load Model
MODEL_PATH = 'models/best_model.pkl'
model = None
model_features = None

model_scaler = None
model_encoders = {}

if os.path.exists(MODEL_PATH):
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
        model = model_data['model']
        model_features = model_data['features']
        model_scaler = model_data.get('scaler', None)
        model_encoders = model_data.get('encoders', {})
    logging.info("Model loaded successfully.")
else:
    logging.warning("Model file not found. Please run train_model.py first!")

# Helper: Database Insert
def log_detection(source_ip, dest_ip, prediction, attack_type, confidence, details):
    try:
        conn = sqlite3.connect('database/intrusion_logs.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO detection_logs (timestamp, source_ip, destination_ip, prediction, attack_type, confidence, details)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), source_ip, dest_ip, prediction, attack_type, confidence, details))
        conn.commit()
        conn.close()
        logging.info(f"Log saved: {attack_type}")
    except Exception as e:
        logging.error(f"Database error: {str(e)}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            flash('Dataset uploaded successfully! Proceed to Prediction.', 'success')
            logging.info(f"Dataset uploaded: {filename}")
            return redirect(url_for('predict'))
    return render_template('upload.html')

@app.route('/predict', methods=['GET', 'POST'])
def predict():
    if request.method == 'POST':
        try:
            source_ip = request.form.get('source_ip', '0.0.0.0')
            dest_ip   = request.form.get('dest_ip',   '0.0.0.0')
            skip_keys = {'source_ip', 'dest_ip'}

            # Build input dict — all values are already numeric (dropdowns send encoded ints)
            input_data = {}
            for k, v in request.form.items():
                if k in skip_keys:
                    continue
                try:
                    input_data[k] = float(v)
                except (ValueError, TypeError):
                    input_data[k] = 0.0

            df = pd.DataFrame([input_data])

            # Align columns to trained feature order (fill missing with 0)
            if model_features:
                df = df.reindex(columns=model_features, fill_value=0)

            # Apply scaler
            if model_scaler is not None:
                df = pd.DataFrame(model_scaler.transform(df), columns=df.columns)

            prediction = model.predict(df)[0]
            proba = model.predict_proba(df)[0] if hasattr(model, 'predict_proba') else [0, 0]
            confidence = float(np.max(proba)) * 100

            attack_types = {0: 'Normal', 1: 'DoS', 2: 'Probe', 3: 'R2L', 4: 'U2R'}
            attack_type = attack_types.get(prediction, 'Unknown')

            log_detection(source_ip, dest_ip, str(prediction), attack_type, confidence, str(input_data))

            return render_template('result.html', prediction=attack_type, confidence=confidence, details=input_data)
        except Exception as e:
            logging.error(f"Prediction error: {str(e)}")
            flash(f"Error during prediction: {str(e)}", 'danger')
            return redirect(url_for('predict'))

    return render_template('predict.html')

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect('database/intrusion_logs.db')
    df = pd.read_sql_query("SELECT * FROM detection_logs", conn)
    conn.close()

    stats = {
        'total': len(df),
        'normal': len(df[df['attack_type'] == 'Normal']),
        'dos': len(df[df['attack_type'] == 'DoS']),
        'probe': len(df[df['attack_type'] == 'Probe']),
        'r2l': len(df[df['attack_type'] == 'R2L']),
        'u2r': len(df[df['attack_type'] == 'U2R'])
    }
    return render_template('dashboard.html', stats=stats, logs=df.to_dict('records'))

@app.route('/logs')
def logs():
    conn = sqlite3.connect('database/intrusion_logs.db')
    df = pd.read_sql_query("SELECT * FROM detection_logs ORDER BY timestamp DESC", conn)
    conn.close()
    return render_template('logs.html', logs=df.to_dict('records'))

@app.route('/api/stats')
def api_stats():
    conn = sqlite3.connect('database/intrusion_logs.db')
    df = pd.read_sql_query("SELECT attack_type, COUNT(*) as count FROM detection_logs GROUP BY attack_type", conn)
    conn.close()
    return jsonify(df.to_dict('records'))

if __name__ == '__main__':
    try:
        print("\n✅ Starting AI Intrusion Detection System...")
        print("🌐 Open in browser: http://127.0.0.1:5000")
        print("   Press Ctrl+C to stop\n")
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except OSError:
        print("\n⚠️  Port 5000 busy. Trying port 5001...")
        app.run(debug=True, host='127.0.0.1', port=5001, use_reloader=False)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()
        input("\nPress Enter to exit...")
