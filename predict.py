import pandas as pd
import pickle
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

def load_model():
    with open('models/best_model.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['model'], data['scaler'], data['encoders'], data['features']

def predict_batch(input_path, output_path='results/predictions.csv'):
    model, scaler, encoders, features = load_model()

    df = pd.read_csv(input_path)

    for col in ['protocol_type', 'service', 'flag']:
        if col in df.columns and col in encoders:
            df[col] = encoders[col].transform(df[col].astype(str))

    df = df.reindex(columns=features, fill_value=0)
    df_scaled = scaler.transform(df)

    predictions = model.predict(df_scaled)

    attack_types = {0: 'Normal', 1: 'DoS', 2: 'Probe', 3: 'R2L', 4: 'U2R'}
    df['prediction'] = [attack_types.get(p, 'Unknown') for p in predictions]

    df.to_csv(output_path, index=False)
    logging.info(f"Predictions saved to {output_path}")
    return df

if __name__ == '__main__':
    predict_batch('dataset/test_data.csv')
