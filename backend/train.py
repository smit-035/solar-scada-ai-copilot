import os
import json
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
import joblib

# Paths
PROCESSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'processed_dataset.csv')
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

# Plant mapping names for folder names
PLANT_FOLDERS = {
    4135001: 'plant_1',
    4136001: 'plant_2'
}

def train_and_evaluate_for_plant(df_plant, plant_id):
    """
    Trains LR, RF, and XGB models on the plant's data, logs metrics,
    and serializes the best model + metadata to its registry directory.
    """
    plant_folder_name = PLANT_FOLDERS.get(plant_id, f"plant_{plant_id}")
    registry_dir = os.path.join(MODELS_DIR, plant_folder_name)
    os.makedirs(registry_dir, exist_ok=True)
    
    print(f"\n" + "="*50)
    print(f"TRAINING PIPELINE FOR PLANT: {plant_folder_name} (ID: {plant_id})")
    print("="*50)
    
    # 1. Prepare Features & One-Hot Encode Inverter Keys
    # We copy to avoid modifying original df
    df_model = df_plant.copy()
    
    # Ensure chronological order
    df_model['DATE_TIME'] = pd.to_datetime(df_model['DATE_TIME'])
    df_model = df_model.sort_values(by='DATE_TIME')
    
    # Features list (preventing data leakage of PR and target AC_POWER)
    base_features = [
        'AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION',
        'rainfall', 'hours_since_last_rain', 'hour', 'month', 'day_of_year',
        'previous_generation', 'rolling_average_generation'
    ]
    
    # One-hot encode SOURCE_KEY (inverter)
    # We save unique keys to features config to allow matching columns during inference
    inverter_keys = sorted(df_model['SOURCE_KEY'].unique().tolist())
    
    df_features = pd.get_dummies(df_model[base_features + ['SOURCE_KEY']], columns=['SOURCE_KEY'], dtype=float)
    feature_columns = df_features.columns.tolist()
    
    X = df_features.values
    y = df_model['AC_POWER'].values
    
    # 2. Chronological Train-Test Split (80% train, 20% test)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Data split: {len(X_train)} training rows, {len(X_test)} testing rows.")
    
    # 3. Model Zoo Setup
    models = {
        'Linear Regression (Baseline)': LinearRegression(),
        'Random Forest Regressor': RandomForestRegressor(n_estimators=50, max_depth=12, random_state=42, n_jobs=-1),
        'XGBoost Regressor': XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.08, random_state=42, n_jobs=-1)
    }
    
    best_r2 = -float('inf')
    best_model_name = None
    best_model = None
    best_metrics = {}
    best_residuals_std = 0.0
    
    # 4. Train & Evaluate
    for name, clf in models.items():
        print(f"\nTraining {name}...")
        clf.fit(X_train, y_train)
        
        # Predict & Evaluate
        y_pred = clf.predict(X_test)
        
        mae = mean_absolute_error(y_test, y_pred)
        rmse = root_mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Calculate standard deviation of errors (residuals)
        residuals = y_test - y_pred
        residuals_std = np.std(residuals)
        
        print(f"Metrics - MAE: {mae:.4f} kW | RMSE: {rmse:.4f} kW | R2 Score: {r2:.4f}")
        
        # Check if this model is the best
        if r2 > best_r2:
            best_r2 = r2
            best_model_name = name
            best_model = clf
            best_residuals_std = residuals_std
            best_metrics = {
                "model_name": name,
                "mae": float(mae),
                "rmse": float(rmse),
                "r2": float(r2),
                "error_std_sigma": float(residuals_std)
            }
            
    print(f"\nSelected Model: {best_model_name} (R2: {best_r2:.4f})")
    
    # 5. Serialize Models & Registry Metadata
    model_path = os.path.join(registry_dir, 'model.joblib')
    joblib.dump(best_model, model_path)
    print(f"Saved serialized model to {model_path}")
    
    # Save metrics.json
    metrics_path = os.path.join(registry_dir, 'metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(best_metrics, f, indent=2)
    print(f"Saved performance metrics to {metrics_path}")
    
    # Save features.json
    features_config = {
        "base_features": base_features,
        "inverter_keys": inverter_keys,
        "feature_columns": feature_columns,
        "plant_id": str(plant_id),
        "plant_name": plant_folder_name
    }
    features_path = os.path.join(registry_dir, 'features.json')
    with open(features_path, 'w') as f:
        json.dump(features_config, f, indent=2)
    print(f"Saved feature registry config to {features_path}")

def run_training_pipeline():
    """
    Main training script to load processed CSV and train models for Plant 1 and Plant 2.
    """
    if not os.path.exists(PROCESSED_FILE):
        print(f"ERROR: Processed dataset not found at {PROCESSED_FILE}.")
        print("Please run data_engineering.py first.")
        return
        
    df = pd.read_csv(PROCESSED_FILE)
    
    # Train separately for each plant
    for plant_id in [4135001, 4136001]:
        df_plant = df[df['PLANT_ID'] == plant_id]
        if df_plant.empty:
            print(f"Warning: No data found in processed file for Plant ID {plant_id}")
            continue
        train_and_evaluate_for_plant(df_plant, plant_id)
        
    print("\nModel training pipeline complete!")

if __name__ == '__main__':
    run_training_pipeline()
