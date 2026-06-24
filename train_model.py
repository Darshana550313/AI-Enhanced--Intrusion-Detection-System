import os
import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Config
DATASET_PATH = 'dataset/NSL_KDD_Train.csv'
MODEL_DIR = 'models'
os.makedirs(MODEL_DIR, exist_ok=True)

def load_data():
    logging.info("Loading dataset...")
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(
            f"Dataset not found at '{DATASET_PATH}'.\n"
            "Please make sure 'NSL_KDD_Train.csv' is inside the 'dataset/' folder."
        )
    df = pd.read_csv(DATASET_PATH)
    logging.info(f"Dataset loaded! Shape: {df.shape}")
    return df

def preprocess_data(df):
    logging.info("Preprocessing data...")

    # Normalize label column name
    if 'class' in df.columns:
        df.rename(columns={'class': 'label'}, inplace=True)

    # Drop 'difficulty' column if present (not a real feature)
    if 'difficulty' in df.columns:
        df.drop(columns=['difficulty'], inplace=True)
        logging.info("Dropped 'difficulty' column.")

    # Handle missing / inf values
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)

    # Encode categorical features
    categorical_cols = ['protocol_type', 'service', 'flag']
    le_dict = {}
    for col in categorical_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            le_dict[col] = le

    # Map labels to 5 attack categories
    dos    = ['back','land','neptune','pod','smurf','teardrop','apache2','udpstorm','processtable','mailbomb']
    probe  = ['satan','ipsweep','nmap','portsweep','mscan','saint']
    r2l    = ['guess_passwd','ftp_write','imap','phf','multihop','warezmaster','warezclient',
              'spy','xlock','xsnoop','snmpguess','snmpgetattack','httptunnel','sendmail','named']
    u2r    = ['buffer_overflow','loadmodule','rootkit','perl','sqlattack','xterm','ps']

    def map_label(x):
        x = str(x).strip().lower()
        if x == 'normal':   return 0
        elif x in dos:      return 1
        elif x in probe:    return 2
        elif x in r2l:      return 3
        elif x in u2r:      return 4
        else:               return 0   # unknown → treat as normal

    df['label'] = df['label'].apply(map_label)

    X = df.drop('label', axis=1)
    y = df['label']

    # Feature Scaling
    scaler = StandardScaler()
    X_scaled = pd.DataFrame(scaler.fit_transform(X), columns=X.columns)

    return X_scaled, y, scaler, le_dict, list(X.columns)

def train_models(X_train, y_train, X_test, y_test):
    logging.info("Training models...")

    models = {
        'Decision Tree':  DecisionTreeClassifier(random_state=42, max_depth=20),
        'Random Forest':  RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
    }

    results = {}
    best_model = None
    best_score = 0
    best_name  = ''

    for name, mdl in models.items():
        logging.info(f"Training {name}...")
        mdl.fit(X_train, y_train)
        y_pred = mdl.predict(X_test)

        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec  = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1   = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        results[name] = {'Accuracy': acc, 'Precision': prec, 'Recall': rec, 'F1': f1}
        logging.info(f"{name} — Accuracy: {acc:.4f}, F1: {f1:.4f}")

        if f1 > best_score:
            best_score = f1
            best_model = mdl
            best_name  = name

    # Try XGBoost (optional – skip if not installed)
    try:
        import xgboost as xgb
        name = 'XGBoost'
        logging.info(f"Training {name}...")
        mdl = xgb.XGBClassifier(eval_metric='mlogloss', random_state=42, verbosity=0)
        mdl.fit(X_train, y_train)
        y_pred = mdl.predict(X_test)
        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec  = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1   = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        results[name] = {'Accuracy': acc, 'Precision': prec, 'Recall': rec, 'F1': f1}
        logging.info(f"{name} — Accuracy: {acc:.4f}, F1: {f1:.4f}")
        if f1 > best_score:
            best_score = f1
            best_model = mdl
            best_name  = name
    except ImportError:
        logging.warning("XGBoost not installed, skipping.")

    logging.info(f"Best Model: {best_name} with F1: {best_score:.4f}")
    return best_model, results, best_name

def save_results(best_model, results, best_name, scaler, le_dict, feature_names):
    model_data = {
        'model':    best_model,
        'scaler':   scaler,
        'encoders': le_dict,
        'features': feature_names
    }
    pkl_path = os.path.join(MODEL_DIR, 'best_model.pkl')
    with open(pkl_path, 'wb') as f:
        pickle.dump(model_data, f)
    logging.info(f"Model saved to {pkl_path}")

    report_path = os.path.join(MODEL_DIR, 'training_report.txt')
    with open(report_path, 'w') as f:
        f.write(f"Best Model: {best_name}\n\n")
        f.write("Model Comparison:\n")
        header = f"{'Model':<20} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10}\n"
        f.write(header)
        f.write("-" * 65 + "\n")
        for mname, metrics in results.items():
            f.write(f"{mname:<20} {metrics['Accuracy']:>10.4f} {metrics['Precision']:>10.4f} "
                    f"{metrics['Recall']:>10.4f} {metrics['F1']:>10.4f}\n")
    logging.info(f"Training report saved to {report_path}")

if __name__ == '__main__':
    try:
        df = load_data()
        X, y, scaler, le_dict, feature_names = preprocess_data(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        best_model, results, best_name = train_models(X_train, y_train, X_test, y_test)
        save_results(best_model, results, best_name, scaler, le_dict, feature_names)

        print("\n" + "="*55)
        print(" TRAINING COMPLETE!")
        print("="*55)
        print(f"  Best Model : {best_name}")
        print(f"  Accuracy   : {results[best_name]['Accuracy']:.4f}")
        print(f"  F1 Score   : {results[best_name]['F1']:.4f}")
        print("  Model saved: models/best_model.pkl")
        print("="*55)

    except FileNotFoundError as e:
        print(f"\n❌ {e}")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
