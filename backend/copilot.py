import os
import json
import datetime
import pandas as pd
import numpy as np
import joblib
from dotenv import load_dotenv

# Import SQLAlchemy session & DB models
from backend.database import db_session
from backend.models_db import Plant, Equipment, GenerationData, WeatherData, Anomaly, InverterHealth, ModelResult

# Import LangChain utilities
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# Load env variables from root directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

# Load plant metadata config
METADATA_PATH = os.path.join(os.path.dirname(__file__), 'plant_metadata.json')
with open(METADATA_PATH, 'r') as f:
    PLANT_METADATA = json.load(f)


# Define AI Tools
@tool
def get_plant_performance(plant_id: str) -> str:
    """
    Retrieves aggregate operational telemetry metrics for a solar plant.
    Includes active capacity, actual power, health, and anomaly statistics.
    Input must be '4135001' (Plant 1) or '4136001' (Plant 2).
    """
    plant_id = str(plant_id)
    if plant_id not in PLANT_METADATA:
        return f"Error: Invalid plant_id '{plant_id}'. Available plant IDs are '4135001' (Plant 1) and '4136001' (Plant 2)."

    # Query health cards
    health_cards = db_session.query(InverterHealth).filter(InverterHealth.plant_id == plant_id).all()
    if not health_cards:
        return f"Plant {plant_id} found in config, but no active database logs exist."

    num_inverters = len(health_cards)
    avg_health = sum(c.health_score for c in health_cards) / num_inverters
    avg_efficiency = sum(c.average_efficiency for c in health_cards) / num_inverters
    
    low_risk = sum(1 for c in health_cards if c.risk_level == 'LOW')
    med_risk = sum(1 for c in health_cards if c.risk_level == 'MEDIUM')
    high_risk = sum(1 for c in health_cards if c.risk_level == 'HIGH')
    
    # Query anomalies
    anomalies = db_session.query(Anomaly).filter(Anomaly.plant_id == plant_id).all()
    total_anomalies = len(anomalies)
    total_loss = sum(a.financial_loss_rs for a in anomalies)
    
    meta = PLANT_METADATA[plant_id]
    
    result = (
        f"Plant Name: {meta['name']}\n"
        f"Location: {meta['location']}\n"
        f"Design Capacity: {meta['capacity_kw']} kW\n"
        f"Active Inverter Units: {num_inverters}\n"
        f"Aggregate Health Index: {avg_health:.1f}%\n"
        f"Average Inverter Efficiency: {avg_efficiency:.2f}%\n"
        f"Equipment Risk Distribution: {low_risk} Low, {med_risk} Warning, {high_risk} Critical\n"
        f"Total Logged Anomalies: {total_anomalies} occurrences\n"
        f"Estimated Total Revenue Loss: Rs. {total_loss:,.2f}"
    )
    return result

@tool
def get_recent_anomalies(plant_id: str, limit: int = 5) -> str:
    """
    Retrieves a list of recent flagged anomalies for a plant, showing issues, probable causes, and financial impacts.
    Input must be '4135001' (Plant 1) or '4136001' (Plant 2).
    """
    plant_id = str(plant_id)
    if plant_id not in PLANT_METADATA:
        return f"Error: Invalid plant_id '{plant_id}'."
        
    anomalies = db_session.query(Anomaly).filter(Anomaly.plant_id == plant_id).order_by(Anomaly.timestamp.desc()).limit(limit).all()
    
    if not anomalies:
        return f"No anomalies logged for Plant {plant_id}."
        
    lines = [f"Recent anomalies for Plant {PLANT_METADATA[plant_id]['name']}:"]
    for a in anomalies:
        lines.append(
            f"- Timestamp: {a.timestamp.strftime('%Y-%m-%d %H:%M')} | "
            f"Inverter ID: {a.equipment_id} | "
            f"Issue: {a.issue} | "
            f"Action: {a.recommended_action} | "
            f"Loss: Rs. {a.financial_loss_rs:.2f}"
        )
    return "\n".join(lines)

@tool
def get_inverter_status(source_key: str) -> str:
    """
    Retrieves health index metrics, operating runtime hours, efficiency drops,
    and recommended inspection actions for a specific inverter.
    Input must be the exact inverter SOURCE_KEY (e.g. '1BY6WEcLGh8j5v7').
    """
    source_key = str(source_key).strip()
    health = db_session.query(InverterHealth).filter(InverterHealth.source_key == source_key).first()
    
    if not health:
        # Check list of valid keys to help user
        all_keys = [h.source_key for h in db_session.query(InverterHealth.source_key).all()]
        match_keys = [k for k in all_keys if source_key.lower() in k.lower()]
        help_msg = f"Inverter key '{source_key}' not found in database."
        if match_keys:
            help_msg += f" Did you mean: {', '.join(match_keys[:3])}?"
        return help_msg
        
    result = (
        f"Inverter Key: {health.source_key}\n"
        f"Facility: {health.plant.plant_name} (ID: {health.plant_id})\n"
        f"Health Rating: {health.health_score}%\n"
        f"Status: {health.status} ({health.risk_level} Risk)\n"
        f"Average Efficiency: {health.average_efficiency}%\n"
        f"Total Accumulated Runtime: {health.total_runtime_hours:.1f} hours\n"
        f"Dynamic Anomaly Alerts: {health.anomaly_count} times\n"
        f"Maintenance Recommendation: {health.recommended_action}"
    )
    return result

@tool
def predict_future_yield(plant_id: str, ambient_temp: float, module_temp: float, irradiation: float) -> str:
    """
    Runs live ML model inference to predict expected AC energy output (kW) and confidence range
    for a plant based on forecasted weather variables.
    Input:
      - plant_id: '4135001' or '4136001'
      - ambient_temp: Ambient temperature forecast (in Celsius, e.g. 35.5)
      - module_temp: Module temperature forecast (in Celsius, e.g. 50.0)
      - irradiation: Irradiance value forecast (in kW/m^2, e.g. 0.8)
    """
    plant_id = str(plant_id)
    if plant_id not in PLANT_METADATA:
        return f"Error: Invalid plant_id '{plant_id}'."
        
    folder = 'plant_1' if plant_id == '4135001' else 'plant_2'
    model_path = os.path.join(MODELS_DIR, folder, 'model.joblib')
    metrics_path = os.path.join(MODELS_DIR, folder, 'metrics.json')
    features_path = os.path.join(MODELS_DIR, folder, 'features.json')
    
    if not (os.path.exists(model_path) and os.path.exists(metrics_path) and os.path.exists(features_path)):
        return "Error: ML models and registry configurations are missing. Retrain models first."
        
    # Load model & configs
    model = joblib.load(model_path)
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)
    with open(features_path, 'r') as f:
        features_config = json.load(f)
        
    sigma = metrics.get('error_std_sigma', 30.0)
    
    # Reconstruct input features
    # Because models are trained per inverter (SOURCE_KEY), we can estimate plant-wide yield by:
    # 1. Running inference for each of the 22 registered inverter keys.
    # 2. Summing up their predicted outputs.
    # This matches training distribution precisely!
    
    inverter_keys = features_config['inverter_keys']
    base_features = features_config['base_features']
    feature_columns = features_config['feature_columns']
    
    # Reconstruct current dates for time features (e.g. assume typical sunny peak hour)
    now = datetime.datetime.now()
    
    # Build a DataFrame containing one row per inverter
    rows = []
    for inv_key in inverter_keys:
        row_dict = {
            'AMBIENT_TEMPERATURE': float(ambient_temp),
            'MODULE_TEMPERATURE': float(module_temp),
            'IRRADIATION': float(irradiation),
            'rainfall': 0.0,
            'hours_since_last_rain': 240.0, # 10 days default
            'hour': now.hour,
            'month': now.month,
            'day_of_year': now.timetuple().tm_yday,
            'previous_generation': 30.0, # nominal lag
            'rolling_average_generation': 35.0, # nominal rolling average
            'SOURCE_KEY': inv_key
        }
        rows.append(row_dict)
        
    df_predict = pd.DataFrame(rows)
    
    # One-hot encode
    for key in inverter_keys:
        df_predict[f"SOURCE_KEY_{key}"] = (df_predict['SOURCE_KEY'] == key).astype(float)
        
    # Standardize columns list
    for col in feature_columns:
        if col not in df_predict.columns:
            df_predict[col] = 0.0
            
    X = df_predict[feature_columns].values
    preds = model.predict(X)
    preds = np.clip(preds, 0.0, None)
    
    total_predicted_kw = sum(preds)
    
    # Calculate plant-wide confidence bounds (std of sum = sqrt(num_inverters) * sigma)
    num_inverters = len(inverter_keys)
    plant_sigma = (num_inverters ** 0.5) * sigma
    
    lower_bound = max(0.0, total_predicted_kw - 2 * plant_sigma)
    upper_bound = total_predicted_kw + 2 * plant_sigma
    
    result = (
        f"Plant: {PLANT_METADATA[plant_id]['name']} ({PLANT_METADATA[plant_id]['location']})\n"
        f"Model algorithm: {metrics['model_name']}\n"
        f"Inputs: Irradiance={irradiation} kW/m², Temp={ambient_temp}°C (Module={module_temp}°C)\n"
        f"Predicted Total AC Yield: {total_predicted_kw:.2f} kW\n"
        f"95% Confidence Interval: {lower_bound:.2f} kW to {upper_bound:.2f} kW\n"
        f"Statistical margin of error (2σ): ±{2*plant_sigma:.2f} kW"
    )
    return result


class CopilotAgentSystem:
    def __init__(self):
        self.agent_executor = None
        self.error_msg = None
        self.initialize_agent()

    def initialize_agent(self):
        if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
            self.error_msg = (
                "Gemini API key is not configured. Please open the .env file in the "
                "project root, add your valid API key to GEMINI_API_KEY, and restart the backend."
            )
            return

        try:
            # Initialize Gemini model via ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-3.5-flash",
                google_api_key=GEMINI_API_KEY,
                temperature=0.25
            )

            # Tools registry
            tools = [
                get_plant_performance,
                get_recent_anomalies,
                get_inverter_status,
                predict_future_yield
            ]

            # Define System Prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", 
                 "You are an AI-Powered Solar Plant Analytics and Operations Copilot, designed "
                 "to assist field engineers and plant managers. You are connected to a database containing "
                 "real-time generation values, weather factors, anomaly registers, and equipment health cards "
                 "for Plant 1 (Gandhinagar, ID: 4135001) and Plant 2 (Jodhpur, ID: 4136001).\n\n"
                 "When answering questions, follow these guidelines:\n"
                 "- Use the provided python tools to fetch accurate real-time metrics, logs, and run live forecast predictions.\n"
                 "- Always give clear, domain-specific, and actionable feedback.\n"
                 "- Format financial metrics in Rupees (Rs.) and power outputs in kW / kWh.\n"
                 "- Do not claim absolute certainty for diagnostic suggestions, frame them as probable causes.\n"
                 "- Be concise and present analytical findings using clean markdown lists or tables where relevant.\n"
                 "If the user asks about future predictions or custom weather situations, call the predict_future_yield tool."
                 ),
                ("placeholder", "{chat_history}"),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ])

            # Construct Tool-Calling Agent
            agent = create_tool_calling_agent(llm, tools, prompt)
            self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
            print("LangChain Gemini Copilot Agent successfully initialized!")
        except Exception as e:
            self.error_msg = f"Agent initialization failed: {str(e)}"
            print(self.error_msg)

    def query(self, user_prompt: str) -> str:
        if self.error_msg:
            return self.error_msg
            
        try:
            response = self.agent_executor.invoke({"input": user_prompt})
            output = response.get("output", "I could not resolve an output.")
            
            # Extract text parts if output is list-formatted
            if isinstance(output, list):
                text_parts = []
                for part in output:
                    if isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                    elif isinstance(part, str):
                        text_parts.append(part)
                output = "\n".join(text_parts)
                
            return output
        except Exception as e:
            return f"Operational Copilot Error: {str(e)}"
