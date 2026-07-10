import os
import json
import pandas as pd
import numpy as np
import joblib

# Paths
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')
PLANT_METADATA_PATH = os.path.join(os.path.dirname(__file__), 'plant_metadata.json')

with open(PLANT_METADATA_PATH, 'r') as f:
    PLANT_METADATA = json.load(f)

# PPA electricity rate (Rupees per kWh)
PPA_RATE = 4.0

class PlantIntelligenceSystem:
    def __init__(self, plant_id):
        self.plant_id = str(plant_id)
        self.plant_folder = 'plant_1' if self.plant_id == '4135001' else 'plant_2'
        self.registry_dir = os.path.join(MODELS_DIR, self.plant_folder)
        
        # Load model registry
        self.model = None
        self.metrics = {}
        self.features_config = {}
        self.error_std = 30.0 # default fallback
        
        self.load_registry()

    def load_registry(self):
        """Loads serialized model, test metrics, and feature configurations from the registry."""
        model_path = os.path.join(self.registry_dir, 'model.joblib')
        metrics_path = os.path.join(self.registry_dir, 'metrics.json')
        features_path = os.path.join(self.registry_dir, 'features.json')
        
        if os.path.exists(model_path) and os.path.exists(metrics_path) and os.path.exists(features_path):
            self.model = joblib.load(model_path)
            with open(metrics_path, 'r') as f:
                self.metrics = json.load(f)
            with open(features_path, 'r') as f:
                self.features_config = json.load(f)
            self.error_std = self.metrics.get('error_std_sigma', 30.0)
            print(f"Loaded ML model and configs for Plant {self.plant_id}. Error Std (Sigma): {self.error_std:.2f} kW")
        else:
            print(f"Warning: Registry not complete for Plant {self.plant_id} at {self.registry_dir}. Running with default configs.")

    def predict_expected_generation_batch(self, df):
        """
        Takes a DataFrame of inputs and returns a Series of expected generation values (AC_POWER).
        Rebuilds one-hot encoded inverter columns based on features.json.
        """
        if self.model is None or not self.features_config:
            # Fallback to simple baseline: capacity * irradiation * 0.75 efficiency
            cap = PLANT_METADATA.get(self.plant_id, {}).get("capacity_kw", 14000.0) / 22.0
            return df['IRRADIATION'] * cap * 0.75

        df_features = df.copy()
        
        # Ensure base features exist
        base_features = self.features_config['base_features']
        for col in base_features:
            if col not in df_features.columns:
                df_features[col] = 0.0

        # One-hot encode SOURCE_KEY inverter column
        inverter_keys = self.features_config['inverter_keys']
        for key in inverter_keys:
            col_name = f"SOURCE_KEY_{key}"
            df_features[col_name] = (df_features['SOURCE_KEY'] == key).astype(float)
            
        # Reorder columns to match model training signature
        feature_columns = self.features_config['feature_columns']
        for col in feature_columns:
            if col not in df_features.columns:
                df_features[col] = 0.0
                
        X = df_features[feature_columns].values
        preds = self.model.predict(X)
        return pd.Series(np.clip(preds, 0.0, None), index=df.index)

    def analyze_anomalies_and_diagnose(self, df_merged):
        """
        Runs batch anomaly detection, root cause diagnostics, and financial estimations.
        Returns a DataFrame with columns:
          - expected_generation (kW)
          - is_anomaly (boolean)
          - anomaly_deviation (kW)
          - root_cause (string)
          - recommended_action (string)
          - financial_loss_rs (float)
        """
        df = df_merged.copy()
        
        # 1. Compute predictions
        df['expected_generation'] = self.predict_expected_generation_batch(df)
        
        # 2. Flag anomalies dynamically
        # Standard threshold: actual is below prediction by > 2 * sigma_error
        # Also require actual is at least 15% below expected to avoid tiny fluctuations.
        df['anomaly_deviation'] = df['expected_generation'] - df['AC_POWER']
        
        # Check active generation window: irradiation > 0.05 kW/m^2
        active_sun = df['IRRADIATION'] > 0.05
        deviation_large = df['anomaly_deviation'] > (2 * self.error_std)
        percentage_drop = df['AC_POWER'] < (df['expected_generation'] * 0.85)
        
        df['is_anomaly'] = active_sun & deviation_large & percentage_drop
        
        # 3. Diagnose root cause & compute financials
        diagnoses = []
        actions = []
        losses = []
        
        for idx, row in df.iterrows():
            if row['is_anomaly']:
                # Calculate energy lost during the 15-minute interval (hours = 0.25)
                energy_loss_kwh = max(0.0, row['anomaly_deviation']) * 0.25
                financial_loss = energy_loss_kwh * PPA_RATE
                losses.append(round(financial_loss, 2))
                
                # Diagnostics rules tree
                # Case 1: Inverter issue
                # Panels produce DC power, but conversion to AC is highly inefficient
                if row['DC_POWER'] > 10.0 and row['inverter_efficiency'] < 0.82:
                    diagnoses.append("Inverter Efficiency Degradation")
                    actions.append("Schedule electrical inspection of the inverter conversion bridge.")
                
                # Case 2: Solar side issue
                # High module temp / good sunlight, but DC power is low
                elif row['IRRADIATION'] > 0.25 and row['DC_POWER'] < (row['expected_generation'] * 1.15):
                    # Check hours since last rain (Dust/Soiling proxy)
                    if row['hours_since_last_rain'] > 360: # 15 days
                        diagnoses.append("Panel Soiling (Dust Accumulation)")
                        actions.append("Initiate automated panel washing or cleaning cycle.")
                    else:
                        diagnoses.append("Solar Panel Shading / String Failure")
                        actions.append("Check for localized shading obstructions or open string circuits.")
                
                # Case 3: Environmental conditions
                # Low irradiation matches low output, but model overpredicted due to lag averages
                elif row['IRRADIATION'] <= 0.25:
                    diagnoses.append("Heavy Cloud Cover / Weather Event")
                    actions.append("No action required. Natural solar irradiance reduction.")
                
                else:
                    diagnoses.append("Unclassified Performance Deviation")
                    actions.append("Review local inverter telemetry log.")
            else:
                losses.append(0.0)
                diagnoses.append("Normal Operation")
                actions.append("None")
                
        df['root_cause'] = diagnoses
        df['recommended_action'] = actions
        df['financial_loss_rs'] = losses
        
        return df

    def calculate_inverter_health_scores(self, df_analyzed):
        """
        Aggregates inverter health metrics over a recent window (e.g. last 7 days of dataset).
        Returns a DataFrame of inverter health recommendations.
        """
        # Sort chronologically
        df = df_analyzed.sort_values(by='DATE_TIME')
        
        # We aggregate over the entire dataset duration to show historical report cards
        inverter_healths = []
        
        for inverter_key, group in df.groupby('SOURCE_KEY'):
            # Nominal parameters
            total_records = len(group)
            anomalies = group['is_anomaly'].sum()
            anomaly_rate = anomalies / max(total_records, 1)
            
            # Mean inverter conversion efficiency during active sun hours (DC_POWER > 50)
            active_sun_group = group[group['DC_POWER'] > 50.0]
            if not active_sun_group.empty:
                avg_efficiency = active_sun_group['inverter_efficiency'].mean()
            else:
                avg_efficiency = 0.95 # nominal fallback
                
            # Runtime hours
            max_runtime = group['estimated_runtime_hours'].max()
            
            # Module temperature stress (fraction of time spent above 55 degrees)
            hot_records = (group['MODULE_TEMPERATURE'] > 55.0).sum()
            temp_stress_rate = hot_records / max(total_records, 1)
            
            # Health Calculation logic
            # Starting point = 100
            health = 100.0
            
            # Deduct for efficiency drop (nominal 96% down)
            if avg_efficiency < 0.95:
                eff_drop = 0.95 - avg_efficiency
                health -= (eff_drop * 150.0) # 10% drop = -15% health
                
            # Deduct for anomalies
            health -= (anomaly_rate * 120.0) # 10% anomaly rate = -12% health
            
            # Deduct for thermal stress
            health -= (temp_stress_rate * 15.0) # high heat exposure
            
            # Small aging factor based on running hours (e.g. 1000 hours = -2% health)
            health -= (max_runtime * 0.002)
            
            health = max(0.0, min(100.0, health))
            
            # Risk categorisation
            if health >= 85.0:
                risk_level = "LOW"
                status = "Healthy"
                rec = "Continue scheduled maintenance cycles."
            elif health >= 70.0:
                risk_level = "MEDIUM"
                status = "Warning"
                rec = "Schedule panel cleaning and check string wiring connections."
            else:
                risk_level = "HIGH"
                status = "Critical"
                rec = "Urgent: Dispatch technician to inspect inverter conversion circuit board."
                
            inverter_healths.append({
                "source_key": inverter_key,
                "plant_id": self.plant_id,
                "plant_name": self.plant_folder.replace('_', ' ').title(),
                "health_score": round(health, 1),
                "risk_level": risk_level,
                "status": status,
                "average_efficiency": round(avg_efficiency * 100.0, 2),
                "total_runtime_hours": round(max_runtime, 1),
                "anomaly_count": int(anomalies),
                "recommended_action": rec
            })
            
        return pd.DataFrame(inverter_healths)

def run_diagnostics_dry_run():
    """
    Dry-run test loading processed CSV and computing anomalies,
    root causes, and health reports.
    """
    processed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'processed_dataset.csv')
    if not os.path.exists(processed_path):
        print(f"Error: Processed dataset not found at {processed_path}")
        return
        
    df = pd.read_csv(processed_path)
    
    for plant_id in [4135001, 4136001]:
        print(f"\nProcessing diagnostics for Plant {plant_id}...")
        df_plant = df[df['PLANT_ID'] == plant_id]
        
        system = PlantIntelligenceSystem(plant_id)
        df_analyzed = system.analyze_anomalies_and_diagnose(df_plant)
        
        anomaly_count = df_analyzed['is_anomaly'].sum()
        total_loss = df_analyzed['financial_loss_rs'].sum()
        
        print(f"Found {anomaly_count} anomalies out of {len(df_plant)} records.")
        print(f"Estimated Revenue Loss: Rs. {total_loss:,.2f}")
        
        # Calculate inverter health
        health_df = system.calculate_inverter_health_scores(df_analyzed)
        print("\nInverter Health Summary:")
        print(health_df[['source_key', 'health_score', 'risk_level', 'average_efficiency']].head(3).to_string(index=False))

if __name__ == '__main__':
    run_diagnostics_dry_run()
