import os
import json
import pandas as pd
from datetime import datetime
from backend.database import db_session, init_db
from backend.models_db import Plant, Equipment, GenerationData, WeatherData, Anomaly, InverterHealth, ModelResult
from backend.intelligence import PlantIntelligenceSystem

from sqlalchemy.engine.url import make_url
from sqlalchemy import create_engine

PROCESSED_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed', 'processed_dataset.csv')
METADATA_PATH = os.path.join(os.path.dirname(__file__), 'plant_metadata.json')

def ensure_database_exists():
    from backend.database import DATABASE_URL
    url = make_url(DATABASE_URL)
    db_name = url.database
    
    if db_name == 'postgres':
        return
        
    # Connect to the default 'postgres' database to check/create the target database
    default_url = url.set(database='postgres')
    engine_default = create_engine(default_url)
    
    try:
        conn = engine_default.raw_connection()
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating database...")
            cursor.execute(f"CREATE DATABASE {db_name}")
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database pre-check warning (will attempt standard connection directly): {str(e)}")
    finally:
        engine_default.dispose()

def ingest_all_data():
    # 0. Ensure Database exists
    ensure_database_exists()
    
    # 1. Initialize Tables
    print("Initializing database tables...")
    init_db()
    
    # 2. Check if processed CSV exists
    if not os.path.exists(PROCESSED_FILE):
        print(f"Error: Processed dataset not found at {PROCESSED_FILE}. Run data_engineering.py and train.py first.")
        return
        
    df = pd.read_csv(PROCESSED_FILE)
    
    # Convert timestamps to python datetime
    df['DATE_TIME'] = pd.to_datetime(df['DATE_TIME'])
    
    # Load metadata config
    with open(METADATA_PATH, 'r') as f:
        plant_config = json.load(f)
        
    # Clear existing data to allow clean re-ingestion
    print("Clearing existing database records for clean ingest...")
    db_session.query(ModelResult).delete()
    db_session.query(Anomaly).delete()
    db_session.query(InverterHealth).delete()
    db_session.query(GenerationData).delete()
    db_session.query(WeatherData).delete()
    db_session.query(Equipment).delete()
    db_session.query(Plant).delete()
    db_session.commit()
    
    # 3. Insert Plants
    print("Ingesting Plants...")
    plants_to_insert = []
    for pid, info in plant_config.items():
        plants_to_insert.append(
            Plant(
                plant_id=pid,
                plant_name=info['name'],
                capacity_kw=info['capacity_kw'],
                location=info['location']
            )
        )
    db_session.add_all(plants_to_insert)
    db_session.commit()
    
    # 4. Insert Equipment (Inverters)
    print("Ingesting Inverters (Equipment)...")
    unique_inverters = df[['PLANT_ID', 'SOURCE_KEY']].drop_duplicates()
    equipments_to_insert = []
    for _, row in unique_inverters.iterrows():
        equipments_to_insert.append(
            Equipment(
                equipment_id=str(row['SOURCE_KEY']),
                plant_id=str(row['PLANT_ID']),
                equipment_type='Inverter',
                status='Active'
            )
        )
    db_session.add_all(equipments_to_insert)
    db_session.commit()
    
    # 5. Run ML Diagnostics on data per plant to get anomalies, health, and predictions
    print("Running diagnostics and generating predictions...")
    all_analyzed_dfs = []
    all_health_dfs = []
    
    for plant_id in [4135001, 4136001]:
        df_plant = df[df['PLANT_ID'] == plant_id]
        if df_plant.empty:
            continue
            
        system = PlantIntelligenceSystem(plant_id)
        df_analyzed = system.analyze_anomalies_and_diagnose(df_plant)
        health_df = system.calculate_inverter_health_scores(df_analyzed)
        
        all_analyzed_dfs.append(df_analyzed)
        all_health_dfs.append(health_df)
        
    combined_analyzed = pd.concat(all_analyzed_dfs, ignore_index=True)
    combined_health = pd.concat(all_health_dfs, ignore_index=True)
    
    # 6. Bulk Ingest Generation Data & Model Results (using fast dict-mapping)
    print("Bulk ingesting Generation Records...")
    gen_mappings = []
    model_mappings = []
    
    # We'll batch model results and generation data
    for _, row in combined_analyzed.iterrows():
        pid = str(row['PLANT_ID'])
        ts = row['DATE_TIME']
        inv_key = str(row['SOURCE_KEY'])
        ac = float(row['AC_POWER'])
        dc = float(row['DC_POWER'])
        
        gen_mappings.append({
            'timestamp': ts,
            'plant_id': pid,
            'source_key': inv_key,
            'dc_power': dc,
            'ac_power': ac,
            'daily_yield': float(row['DAILY_YIELD']),
            'total_yield': float(row['TOTAL_YIELD'])
        })
        
        expected = float(row['expected_generation'])
        error_pct = (abs(expected - ac) / (expected + 1e-5)) * 100.0
        model_name = "XGBoost" if pid == '4135001' else "RandomForest"
        
        model_mappings.append({
            'plant_id': pid,
            'timestamp': ts,
            'predicted_generation': expected,
            'actual_generation': ac,
            'error_percentage': round(min(error_pct, 100.0), 2),
            'model_version': f"{model_name}_v1.0"
        })
        
    # Bulk insert generation data in chunks of 10000
    chunk_size = 10000
    for i in range(0, len(gen_mappings), chunk_size):
        db_session.bulk_insert_mappings(GenerationData, gen_mappings[i:i+chunk_size])
        db_session.bulk_insert_mappings(ModelResult, model_mappings[i:i+chunk_size])
        db_session.commit()
        print(f"  Inserted generation & model records {i} to {min(i+chunk_size, len(gen_mappings))}...")
        
    # 7. Bulk Ingest Weather Data
    # Weather is recorded plant-wide (not inverter level), so we drop duplicates on timestamp/plant_id
    print("Bulk ingesting Weather Records...")
    weather_df = combined_analyzed[['DATE_TIME', 'PLANT_ID', 'AMBIENT_TEMPERATURE', 'MODULE_TEMPERATURE', 'IRRADIATION', 'rainfall', 'hours_since_last_rain']].drop_duplicates(subset=['DATE_TIME', 'PLANT_ID'])
    wea_mappings = []
    for _, row in weather_df.iterrows():
        wea_mappings.append({
            'timestamp': row['DATE_TIME'],
            'plant_id': str(row['PLANT_ID']),
            'ambient_temperature': float(row['AMBIENT_TEMPERATURE']),
            'module_temperature': float(row['MODULE_TEMPERATURE']),
            'irradiation': float(row['IRRADIATION']),
            'rainfall': float(row['rainfall']),
            'hours_since_last_rain': float(row['hours_since_last_rain'])
        })
    db_session.bulk_insert_mappings(WeatherData, wea_mappings)
    db_session.commit()
    
    # 8. Ingest Anomalies (only where is_anomaly is True)
    print("Ingesting Anomaly Logs...")
    anomaly_rows = combined_analyzed[combined_analyzed['is_anomaly'] == True]
    anomaly_mappings = []
    for _, row in anomaly_rows.iterrows():
        anomaly_mappings.append({
            'timestamp': row['DATE_TIME'],
            'plant_id': str(row['PLANT_ID']),
            'equipment_id': str(row['SOURCE_KEY']),
            'issue': str(row['root_cause']),
            'severity': 'HIGH' if 'Urgent' in str(row['recommended_action']) else ('MEDIUM' if 'Schedule' in str(row['recommended_action']) else 'LOW'),
            'probable_cause': str(row['root_cause']),
            'recommended_action': str(row['recommended_action']),
            'financial_loss_rs': float(row['financial_loss_rs'])
        })
    if anomaly_mappings:
        db_session.bulk_insert_mappings(Anomaly, anomaly_mappings)
        db_session.commit()
    print(f"  Inserted {len(anomaly_mappings)} anomalies.")
    
    # 9. Ingest Inverter Health Scores
    print("Ingesting Inverter Health Cards...")
    health_mappings = []
    for _, row in combined_health.iterrows():
        health_mappings.append({
            'source_key': str(row['source_key']),
            'plant_id': str(row['plant_id']),
            'health_score': float(row['health_score']),
            'risk_level': str(row['risk_level']),
            'status': str(row['status']),
            'average_efficiency': float(row['average_efficiency']),
            'total_runtime_hours': float(row['total_runtime_hours']),
            'anomaly_count': int(row['anomaly_count']),
            'recommended_action': str(row['recommended_action'])
        })
    db_session.bulk_insert_mappings(InverterHealth, health_mappings)
    db_session.commit()
    print(f"  Inserted {len(health_mappings)} health reports.")
    
    print("\nDatabase ingestion completed successfully!")

if __name__ == '__main__':
    ingest_all_data()
