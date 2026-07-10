import os
import json
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import func, desc, text
from backend.database import db_session
from backend.models_db import Plant, Equipment, GenerationData, WeatherData, Anomaly, InverterHealth, ModelResult
from backend.copilot import CopilotAgentSystem

app = Flask(__name__)
# Enable CORS for all routes (to connect to React frontend on port 5173/3000)
CORS(app)

# Initialize the Operations AI Copilot Agent System
copilot_agent = CopilotAgentSystem()

# Load plant metadata config
METADATA_PATH = os.path.join(os.path.dirname(__file__), 'plant_metadata.json')
with open(METADATA_PATH, 'r') as f:
    PLANT_METADATA = json.load(f)

# Load model metrics to get dynamic error std devs (sigmas) for confidence bands
MODELS_DIR = os.path.join(os.path.dirname(__file__), 'models')

def get_plant_sigma(plant_id):
    folder = 'plant_1' if str(plant_id) == '4135001' else 'plant_2'
    metrics_path = os.path.join(MODELS_DIR, folder, 'metrics.json')
    if os.path.exists(metrics_path):
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
            return metrics.get('error_std_sigma', 30.0)
    return 30.0

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Closes database session after each request context terminates."""
    db_session.remove()

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_summary():
    plant_id = request.args.get('plant_id')
    
    # 1. Base query filter
    health_query = db_session.query(InverterHealth)
    gen_query = db_session.query(GenerationData)
    anomaly_query = db_session.query(Anomaly)
    
    if plant_id:
        health_query = health_query.filter(InverterHealth.plant_id == plant_id)
        gen_query = gen_query.filter(GenerationData.plant_id == plant_id)
        anomaly_query = anomaly_query.filter(Anomaly.plant_id == plant_id)

    # 2. Compute aggregate metrics
    health_cards = health_query.all()
    if not health_cards:
        return jsonify({"error": f"No data found for Plant {plant_id}"}), 404
        
    num_inverters = len(health_cards)
    avg_health = sum(c.health_score for c in health_cards) / num_inverters
    avg_efficiency = sum(c.average_efficiency for c in health_cards) / num_inverters
    
    # Risk counts
    low_risk = sum(1 for c in health_cards if c.risk_level == 'LOW')
    med_risk = sum(1 for c in health_cards if c.risk_level == 'MEDIUM')
    high_risk = sum(1 for c in health_cards if c.risk_level == 'HIGH')
    
    # Total losses & total anomalies
    anomalies_list = anomaly_query.all()
    total_anomalies = len(anomalies_list)
    total_loss = sum(a.financial_loss_rs for a in anomalies_list)
    
    # Get latest generation metrics
    # Find maximum timestamp in dataset
    latest_timestamp_row = db_session.query(func.max(GenerationData.timestamp)).first()
    latest_time = latest_timestamp_row[0] if latest_timestamp_row else None
    
    current_ac = 0.0
    current_dc = 0.0
    
    if latest_time:
        latest_gen_query = db_session.query(
            func.sum(GenerationData.ac_power),
            func.sum(GenerationData.dc_power)
        ).filter(GenerationData.timestamp == latest_time)
        
        if plant_id:
            latest_gen_query = latest_gen_query.filter(GenerationData.plant_id == plant_id)
            
        gen_sums = latest_gen_query.first()
        current_ac = gen_sums[0] or 0.0
        current_dc = gen_sums[1] or 0.0
        
    # Get plant capacity
    if plant_id:
        total_capacity = PLANT_METADATA.get(plant_id, {}).get("capacity_kw", 30800.0)
    else:
        total_capacity = sum(info["capacity_kw"] for info in PLANT_METADATA.values())
        
    # 3. Hourly generation averages for charting (typical sunny day curve)
    # We aggregate total AC power by hour of day
    hourly_query = db_session.query(
        func.extract('hour', GenerationData.timestamp).label('hour_num'),
        func.avg(GenerationData.ac_power * num_inverters).label('avg_ac')
    )
    if plant_id:
        hourly_query = hourly_query.filter(GenerationData.plant_id == plant_id)
        
    hourly_gen = hourly_query.group_by('hour_num').order_by('hour_num').all()
    hourly_data = [{"hour": int(row.hour_num), "ac_power": round(float(row.avg_ac), 2)} for row in hourly_gen]
    
    return jsonify({
        "plant_id": plant_id or "all",
        "plant_name": "Combined Plants" if not plant_id else PLANT_METADATA.get(plant_id, {}).get("name", "Unknown"),
        "total_capacity_kw": total_capacity,
        "current_ac_power_kw": round(current_ac, 2),
        "current_dc_power_kw": round(current_dc, 2),
        "average_health_score": round(avg_health, 1),
        "average_efficiency_pct": round(avg_efficiency, 2),
        "inverters_count": num_inverters,
        "risk_summary": {
            "low": low_risk,
            "medium": med_risk,
            "high": high_risk
        },
        "anomalies_count": total_anomalies,
        "estimated_loss_rs": round(total_loss, 2),
        "hourly_curve": hourly_data
    })

@app.route('/api/forecast', methods=['GET'])
def get_forecast():
    plant_id = request.args.get('plant_id', '4135001') # Default to Plant 1
    
    # Check plant metadata
    if plant_id not in PLANT_METADATA:
        return jsonify({"error": f"Invalid plant_id: {plant_id}"}), 400
        
    sigma = get_plant_sigma(plant_id)
    
    # To show predicted vs actual on a chart without overwhelming Recharts,
    # we take the last 4 days of records in model_results.
    # Group by timestamp (sum/average across all inverters)
    latest_ts_row = db_session.query(func.max(ModelResult.timestamp)).filter(ModelResult.plant_id == plant_id).first()
    latest_ts = latest_ts_row[0] if latest_ts_row else None
    
    if not latest_ts:
        return jsonify({"error": "No model prediction logs found. Ingest database first."}), 404
        
    start_time = latest_ts - datetime.timedelta(days=3)
    
    forecast_rows = db_session.query(
        ModelResult.timestamp,
        func.sum(ModelResult.predicted_generation).label('pred'),
        func.sum(ModelResult.actual_generation).label('act')
    ).filter(
        ModelResult.plant_id == plant_id,
        ModelResult.timestamp >= start_time
    ).group_by(ModelResult.timestamp).order_by(ModelResult.timestamp).all()
    
    data = []
    for row in forecast_rows:
        ts_str = row.timestamp.strftime('%Y-%m-%d %H:%M')
        pred = float(row.pred)
        act = float(row.act)
        
        # Calculate dynamic confidence intervals (2 * sigma * sqrt(num_inverters) or simple sum bounds)
        # Sum of 22 independent normal variables has std = sqrt(22) * sigma
        num_inverters = 22
        plant_sigma = (num_inverters ** 0.5) * sigma
        
        lower_bound = max(0.0, pred - 2 * plant_sigma)
        upper_bound = pred + 2 * plant_sigma
        
        data.append({
            "timestamp": ts_str,
            "predicted": round(pred, 2),
            "actual": round(act, 2),
            "lower_bound": round(lower_bound, 2),
            "upper_bound": round(upper_bound, 2)
        })
        
    return jsonify({
        "plant_id": plant_id,
        "plant_name": PLANT_METADATA[plant_id]["name"],
        "sigma_kw": sigma,
        "data": data
    })

@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    plant_id = request.args.get('plant_id')
    limit = request.args.get('limit', 100, type=int)
    
    query = db_session.query(Anomaly)
    if plant_id:
        query = query.filter(Anomaly.plant_id == plant_id)
        
    anomalies = query.order_by(desc(Anomaly.timestamp)).limit(limit).all()
    
    data = []
    for a in anomalies:
        data.append({
            "id": a.id,
            "timestamp": a.timestamp.strftime('%Y-%m-%d %H:%M'),
            "plant_id": a.plant_id,
            "plant_name": PLANT_METADATA.get(a.plant_id, {}).get("name", "Unknown"),
            "equipment_id": a.equipment_id,
            "issue": a.issue,
            "severity": a.severity,
            "probable_cause": a.probable_cause,
            "recommended_action": a.recommended_action,
            "financial_loss_rs": round(a.financial_loss_rs, 2)
        })
        
    return jsonify(data)

@app.route('/api/maintenance', methods=['GET'])
def get_maintenance():
    plant_id = request.args.get('plant_id')
    
    query = db_session.query(InverterHealth)
    if plant_id:
        query = query.filter(InverterHealth.plant_id == plant_id)
        
    healths = query.order_by(InverterHealth.health_score).all() # lowest health first
    
    data = []
    for h in healths:
        data.append({
            "source_key": h.source_key,
            "plant_id": h.plant_id,
            "plant_name": PLANT_METADATA.get(h.plant_id, {}).get("name", "Unknown"),
            "health_score": h.health_score,
            "risk_level": h.risk_level,
            "status": h.status,
            "average_efficiency": h.average_efficiency,
            "total_runtime_hours": h.total_runtime_hours,
            "anomaly_count": h.anomaly_count,
            "recommended_action": h.recommended_action
        })
        
    return jsonify(data)

@app.route('/api/chat', methods=['POST'])
def chat_assistant():
    """AI Assistant route. Resolves query using LangChain Gemini Agent with SQL & ML tools."""
    req_data = request.get_json() or {}
    message = req_data.get('message', '')
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
        
    response_text = copilot_agent.query(message)
    
    return jsonify({
        "response": response_text
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # Run Flask server locally
    app.run(host='0.0.0.0', port=port, debug=True)
