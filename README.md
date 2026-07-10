# AI-Powered Renewable Energy Analytics and Operations Copilot

An intelligent decision-support layer built on top of solar power plant SCADA systems. This platform goes beyond traditional monitoring ("what is happening right now") to answer predictive and diagnostic questions: **"What will happen next?"**, **"Why did it happen?"**, and **"What action should be taken?"**.

---

## 🚀 Key Features

1. **Solar Power Generation Forecasting:** Plant-specific machine learning models (XGBoost & Random Forest) trained to predict future AC output based on ambient temperature, module temperature, and irradiance.
2. **Dynamic Anomaly Detection:** Compares real-time SCADA values against ML forecast boundaries ($\pm 2\sigma$ error margins) to flag deviations dynamically under varying weather profiles.
3. **Explainable Root Cause Analysis (RCA):** Logical diagnostic trees that categorize losses into specific causes: solar-string failures, shading, panel dust/soiling accumulation, weather changes, or inverter conversion efficiency drop.
4. **Equipment Health Scoring:** Analyzes cumulative operating runtime, thermal stresses, conversion efficiencies, and anomaly history to generate a 0-100% health score for each inverter array.
5. **Financial Impact Assessment:** Automatically translates power loss during anomalies into estimated revenue loss (in Rupees) based on a configured Power Purchase Agreement (PPA) rate.
6. **Dual-Tool AI Assistant:** A LangChain Copilot utilizing Google Gemini API equipped with SQL tools (for querying historical logs) and ML tools (for live model inference on custom weather forecasts).

---

## 📐 Architecture & Technology Stack

```text
SCADA Raw CSVs ──> Data Engineering & PR Features ──> ML Registry (XGBoost/RF)
                                                                 │
AI assistant Chat <── LangChain (Gemini) <── Flask APIs <── PostgreSQL DB (SQLAlchemy)
                                                 │
                                         React Dashboard (Tailwind + Recharts)
```

*   **Frontend:** React (Vite), Tailwind CSS, Recharts, Lucide React
*   **Backend:** Flask, Python 3.13
*   **Database:** PostgreSQL (with SQLAlchemy ORM)
*   **ML Pipeline:** Scikit-learn, XGBoost, Pandas, Joblib
*   **AI Agent:** LangChain, LangChain Google GenAI (Gemini)

---

## 📊 ML Model Performance Summary

Models are trained plant-specific using a chronological 80/20 train-test split:
*   **Plant 1 (Gandhinagar, ID: 4135001):** Selected **XGBoost Regressor** ($R^2 = 97.54\%$, MAE = $18.18\text{ kW}$, Residual $\sigma_{error} = 54.52\text{ kW}$).
*   **Plant 2 (Jodhpur, ID: 4136001):** Selected **Random Forest Regressor** ($R^2 = 79.01\%$, MAE = $44.63\text{ kW}$, Residual $\sigma_{error} = 129.44\text{ kW}$).

---

## 🛠️ Installation & Setup Guide

### 1. Repository & Data Placement
Clone the repository and place the Kaggle **Solar Power Generation Dataset** CSV files in the raw data folder:
```text
data/raw/
├── Plant_1_Generation_Data.csv
├── Plant_1_Weather_Sensor_Data.csv
├── Plant_2_Generation_Data.csv
└── Plant_2_Weather_Sensor_Data.csv
```

### 2. Environment Configurations
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/solar_copilot
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
PORT=5000
```

### 3. Backend & ML Pipelines setup
Install python requirements, execute data engineering, and train forecasting models:
```bash
# Install packages
pip install -r backend/requirements.txt

# Run data cleaning, merging, and feature engineering
python backend/data_engineering.py

# Train ML models and populate the model registry
python backend/train.py
```

### 4. Database Schema Migration & Ingest
Ensure your local PostgreSQL instance is running, then run the populator script:
```bash
# Resets the public schema and imports 113,378 records + ML diagnostics
python -m backend.db_ingest
```

### 5. Start the Application
Run the backend Flask API and React Vite dev server:

**Terminal 1 (Backend API):**
```bash
python -m backend.app
```

**Terminal 2 (React Frontend Client):**
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🐳 Docker Deployment (Optional)
To orchestrate PostgreSQL database, Flask backend API, and React frontend Nginx services in containers, run:
```bash
docker compose up --build -d
```
The React frontend dashboard will be accessible at `http://localhost:80`.
