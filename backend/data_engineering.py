import os
import json
import pandas as pd
import numpy as np

# Load plant metadata config
METADATA_PATH = os.path.join(os.path.dirname(__file__), 'plant_metadata.json')
with open(METADATA_PATH, 'r') as f:
    PLANT_METADATA = json.load(f)

# File paths
RAW_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Datasets file names
PLANT_1_GEN_FILE = os.path.join(RAW_DIR, 'Plant_1_Generation_Data.csv')
PLANT_1_WEA_FILE = os.path.join(RAW_DIR, 'Plant_1_Weather_Sensor_Data.csv')
PLANT_2_GEN_FILE = os.path.join(RAW_DIR, 'Plant_2_Generation_Data.csv')
PLANT_2_WEA_FILE = os.path.join(RAW_DIR, 'Plant_2_Weather_Sensor_Data.csv')

def load_and_clean_dataset(gen_path, weather_path, plant_id):
    """
    Loads, cleans, and merges generation and weather datasets for a specific plant.
    """
    if not os.path.exists(gen_path) or not os.path.exists(weather_path):
        raise FileNotFoundError(f"Missing generation or weather file for Plant {plant_id}")
        
    print(f"Loading files for Plant {plant_id}...")
    
    # 1. Load data
    gen_df = pd.read_csv(gen_path)
    wea_df = pd.read_csv(weather_path)
    
    # 2. Parse Date/Times
    # Kaggle datetime strings can contain mixed formats (dd-mm-yyyy or yyyy-mm-dd)
    gen_df['DATE_TIME'] = pd.to_datetime(gen_df['DATE_TIME'], format='mixed')
    wea_df['DATE_TIME'] = pd.to_datetime(wea_df['DATE_TIME'], format='mixed')
    
    # Standardize column casing & IDs
    gen_df['PLANT_ID'] = gen_df['PLANT_ID'].astype(str)
    wea_df['PLANT_ID'] = wea_df['PLANT_ID'].astype(str)
    
    # 3. Merge Datasets
    # Merge weather data on timestamp and plant ID
    # Since weather data is at plant level, it merges with all inverters of that plant.
    merged_df = pd.merge(
        gen_df,
        wea_df.drop(columns=['PLANT_ID', 'SOURCE_KEY'], errors='ignore'),
        on='DATE_TIME',
        how='inner'
    )
    
    return merged_df

def simulate_rainfall(dates):
    """
    Simulates rainfall history for the duration of the dataset (May-June 2020 in India).
    Returns a pandas Series indicating rainfall intensity (mm).
    """
    # Create a DataFrame of dates
    df_temp = pd.DataFrame(index=dates)
    df_temp['rainfall'] = 0.0
    
    # Define a few specific simulated rainfall events (afternoons during hot pre-monsoon storm)
    # May 25 afternoon, June 8 afternoon, June 12 morning
    rain_events = [
        ('2020-05-25 14:00:00', '2020-05-25 16:30:00', 8.5),
        ('2020-06-08 15:00:00', '2020-06-08 18:00:00', 12.0),
        ('2020-06-12 08:00:00', '2020-06-12 10:00:00', 5.0)
    ]
    
    for start, end, amount in rain_events:
        mask = (df_temp.index >= pd.to_datetime(start)) & (df_temp.index <= pd.to_datetime(end))
        df_temp.loc[mask, 'rainfall'] = amount
        
    return df_temp['rainfall'].values

def compute_hours_since_last_rain(df):
    """
    Computes hours since last rain event (> 0.1mm) chronologically.
    """
    # Sort chronologically
    df = df.sort_values(by='DATE_TIME')
    
    # Identify unique dates
    unique_times = pd.Series(df['DATE_TIME'].unique()).sort_values()
    
    # Simulate rainfall at the unique timestamp level
    rainfall_arr = simulate_rainfall(unique_times)
    
    # Compute elapsed hours
    last_rain_time = unique_times.min() - pd.Timedelta(days=10) # default offset
    hours_since = []
    
    for i, t in enumerate(unique_times):
        if rainfall_arr[i] > 0.0:
            last_rain_time = t
        elapsed_hours = (t - last_rain_time).total_seconds() / 3600.0
        hours_since.append((t, rainfall_arr[i], elapsed_hours))
        
    rain_df = pd.DataFrame(hours_since, columns=['DATE_TIME', 'rainfall', 'hours_since_last_rain'])
    
    # Merge back to full dataframe
    df = pd.merge(df, rain_df, on='DATE_TIME', how='left')
    return df

def feature_engineering(df):
    """
    Performs feature engineering for a plant.
    Assumes df is already merged and sorted chronologically per inverter.
    """
    plant_id = str(df['PLANT_ID'].iloc[0])
    plant_config = PLANT_METADATA.get(plant_id, {"capacity_kw": 14000.0})
    
    # 1. Number of unique inverters to divide plant capacity
    num_inverters = df['SOURCE_KEY'].nunique()
    inverter_capacity_kw = plant_config['capacity_kw'] / max(num_inverters, 1)
    
    # 2. Time Features
    df['hour'] = df['DATE_TIME'].dt.hour
    df['month'] = df['DATE_TIME'].dt.month
    df['day_of_year'] = df['DATE_TIME'].dt.dayofyear
    
    # 3. Inverter Efficiency & Performance Ratio (PR)
    # For Plant 1 (4135001), DC_POWER is scaled by 10 in the Kaggle dataset.
    # To compute standard efficiency, we divide Plant 1's DC_POWER by 10.
    if plant_id == '4135001':
        dc_scaled = df['DC_POWER'] / 10.0
    else:
        dc_scaled = df['DC_POWER']

    df['inverter_efficiency'] = np.where(
        dc_scaled > 0.0,
        df['AC_POWER'] / dc_scaled,
        0.0
    )
    # Clip unrealistic efficiencies (e.g. measurement glitches > 1.0 or < 0.0)
    df['inverter_efficiency'] = df['inverter_efficiency'].clip(0.0, 1.0)
    
    df['performance_ratio'] = np.where(
        df['IRRADIATION'] > 0.01, # only calculate when there is usable sunlight
        df['AC_POWER'] / (inverter_capacity_kw * df['IRRADIATION']),
        0.0
    )
    # PR is typically between 0 and 1, but clipping at 1.2 to allow slight over-performance/glitches
    df['performance_ratio'] = df['performance_ratio'].clip(0.0, 1.2)
    
    # 4. Lag Features for Forecasting (calculated per inverter to prevent data cross-talk)
    df_list = []
    for inverter, group in df.groupby('SOURCE_KEY'):
        group = group.sort_values(by='DATE_TIME')
        
        # In the Kaggle dataset, the frequency is 15 minutes.
        # lag_1h = 4 steps shift
        # lag_2h = 8 steps shift
        # lag_24h = 96 steps shift
        group['previous_generation'] = group['AC_POWER'].shift(4).fillna(0.0)
        group['rolling_average_generation'] = group['AC_POWER'].rolling(window=12, min_periods=1).mean().shift(1).fillna(0.0)
        
        # Calculate inverter cumulative runtime (sum of 15 min steps where AC > 0)
        # We compute this sequentially as a running cumulative sum
        group['is_operating'] = (group['AC_POWER'] > 0.1).astype(int)
        group['estimated_runtime_hours'] = (group['is_operating'].cumsum() * 15.0) / 60.0
        group = group.drop(columns=['is_operating'])
        
        df_list.append(group)
        
    df = pd.concat(df_list).sort_values(by=['PLANT_ID', 'DATE_TIME', 'SOURCE_KEY'])
    return df

def run_data_engineering_pipeline():
    """
    Main pipeline to process Plant 1 and Plant 2 datasets and save the output.
    """
    # Check if files exist
    files_exist = (
        os.path.exists(PLANT_1_GEN_FILE) and 
        os.path.exists(PLANT_1_WEA_FILE) and 
        os.path.exists(PLANT_2_GEN_FILE) and 
        os.path.exists(PLANT_2_WEA_FILE)
    )
    
    if not files_exist:
        print("\n" + "="*60)
        print("ERROR: Kaggle CSV datasets are missing!")
        print("Please place the following files inside 'data/raw/':")
        print(f"1. {os.path.basename(PLANT_1_GEN_FILE)}")
        print(f"2. {os.path.basename(PLANT_1_WEA_FILE)}")
        print(f"3. {os.path.basename(PLANT_2_GEN_FILE)}")
        print(f"4. {os.path.basename(PLANT_2_WEA_FILE)}")
        print("="*60 + "\n")
        return False
        
    # Process Plant 1
    df1 = load_and_clean_dataset(PLANT_1_GEN_FILE, PLANT_1_WEA_FILE, '4135001')
    df1 = compute_hours_since_last_rain(df1)
    df1 = feature_engineering(df1)
    
    # Process Plant 2
    df2 = load_and_clean_dataset(PLANT_2_GEN_FILE, PLANT_2_WEA_FILE, '4136001')
    df2 = compute_hours_since_last_rain(df2)
    df2 = feature_engineering(df2)
    
    # Combine datasets
    combined_df = pd.concat([df1, df2], ignore_index=True)
    
    # Sort final dataset
    combined_df = combined_df.sort_values(by=['PLANT_ID', 'DATE_TIME', 'SOURCE_KEY'])
    
    # Save to processed directory
    output_file = os.path.join(PROCESSED_DIR, 'processed_dataset.csv')
    combined_df.to_csv(output_file, index=False)
    print(f"\nSuccess! Saved processed dataset ({combined_df.shape[0]} rows, {combined_df.shape[1]} columns) to {output_file}")
    return True

if __name__ == '__main__':
    run_data_engineering_pipeline()
