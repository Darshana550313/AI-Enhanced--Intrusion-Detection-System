"""
Run this ONCE on your machine to retrain and save the model locally.
    python retrain_local.py
"""
import os, sys
import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATASET_PATH = 'dataset/NSL_KDD_Train.csv'
MODEL_PATH   = 'models/best_model.pkl'
os.makedirs('models', exist_ok=True)

# ── 1. Load ────────────────────────────────────────────────────────────────────
if not os.path.exists(DATASET_PATH):
    sys.exit(f"❌ Dataset not found: {DATASET_PATH}\n"
             "   Make sure NSL_KDD_Train.csv is inside the 'dataset/' folder.")

logging.info("Loading dataset...")
df = pd.read_csv(DATASET_PATH)
logging.info(f"Loaded → shape: {df.shape}")

# ── 2. Preprocess ──────────────────────────────────────────────────────────────
logging.info("Preprocessing...")

if 'class' in df.columns:
    df.rename(columns={'class': 'label'}, inplace=True)

# Drop difficulty column if present (not a real feature)
if 'difficulty' in df.columns:
    df.drop(columns=['difficulty'], inplace=True)

df.replace([np.inf, -np.inf], np.nan, inplace=True)
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)

# Encode categoricals
categorical_cols = ['protocol_type', 'service', 'flag']
le_dict = {}
for col in categorical_cols:
    if col in df.columns:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        le_dict[col] = le

# Map labels → 5 classes
dos   = ['back','land','neptune','pod','smurf','teardrop','apache2','udpstorm','processtable','mailbomb']
probe = ['satan','ipsweep','nmap','portsweep','mscan','saint']
r2l   = ['guess_passwd','ftp_write','imap','phf','multihop','warezmaster','warezclient',
         'spy','xlock','xsnoop','snmpguess','snmpgetattack','httptunnel','sendmail','named']
u2r   = ['buffer_overflow','loadmodule','rootkit','perl','sqlattack','xterm','ps']

def map_label(x):
    x = str(x).strip().lower()
    if x == 'normal': return 0
    elif x in dos:    return 1
    elif x in probe:  return 2
    elif x in r2l:    return 3
    elif x in u2r:    return 4
    else:             return 0

df['label'] = df['label'].apply(map_label)

X = df.drop('label', axis=1)
y = df['label']
feature_names = list(X.columns)

scaler  = StandardScaler()
X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=feature_names)

# ── 3. Train ───────────────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y)

best_model, best_name, best_f1 = None, '', 0

candidates = {
    'Decision Tree': DecisionTreeClassifier(random_state=42, max_depth=20),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
}

# XGBoost optional
try:
    import xgboost as xgb
    candidates['XGBoost'] = xgb.XGBClassifier(eval_metric='mlogloss', random_state=42, verbosity=0)
except ImportError:
    logging.warning("XGBoost not installed – skipping.")

results = {}
for name, mdl in candidates.items():
    logging.info(f"Training {name}...")
    mdl.fit(X_train, y_train)
    y_pred = mdl.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1  = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    results[name] = {'Accuracy': acc, 'F1': f1}
    logging.info(f"  {name} → Accuracy: {acc:.4f}  F1: {f1:.4f}")
    if f1 > best_f1:
        best_f1, best_model, best_name = f1, mdl, name

# ── 4. Save ────────────────────────────────────────────────────────────────────
model_data = {
    'model':    best_model,
    'scaler':   scaler,
    'encoders': le_dict,
    'features': feature_names,
}
with open(MODEL_PATH, 'wb') as f:
    pickle.dump(model_data, f)

report = os.path.join('models', 'training_report.txt')
with open(report, 'w') as f:
    f.write(f"Best Model: {best_name}\n\n")
    f.write(f"{'Model':<20} {'Accuracy':>10} {'F1':>10}\n")
    f.write("-" * 45 + "\n")
    for n, m in results.items():
        f.write(f"{n:<20} {m['Accuracy']:>10.4f} {m['F1']:>10.4f}\n")

print("\n" + "=" * 50)
print("  TRAINING COMPLETE!")
print("=" * 50)
print(f"  Best Model : {best_name}")
print(f"  Accuracy   : {results[best_name]['Accuracy']:.4f}")
print(f"  F1 Score   : {results[best_name]['F1']:.4f}")
print(f"  Saved to   : {MODEL_PATH}")
print("=" * 50)
print("\n✅ Now run:  python app.py")
