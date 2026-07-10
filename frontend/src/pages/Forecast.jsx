import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Sparkles, BarChart3, AlertCircle } from 'lucide-react';

export default function Forecast({ plantId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Set default plant to Plant 1 if "all" is selected (since forecasting models are plant-specific)
  const activePlantId = !plantId || plantId === 'all' ? '4135001' : plantId;

  useEffect(() => {
    setLoading(true);
    axios.get(`http://localhost:5000/api/forecast?plant_id=${activePlantId}`)
      .then(res => {
        setData(res.data);
        setError(null);
      })
      .catch(err => {
        console.error("Forecast error:", err);
        setError("Failed to fetch forecast. Make sure database ingestion has been completed.");
      })
      .finally(() => setLoading(false));
  }, [activePlantId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel-danger p-6 rounded-xl flex items-center gap-4 text-red-200">
        <AlertCircle className="h-10 w-10 text-red-500 shrink-0" />
        <div>
          <h3 className="font-bold text-lg">Forecast Data Unavailable</h3>
          <p className="text-sm opacity-90">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // Static display metrics depending on selected plant
  const modelStats = activePlantId === '4135001' 
    ? { name: "XGBoost Regressor v1.0", r2: "97.54%", mae: "18.18 kW", rmse: "54.52 kW", sigma: "54.52 kW" }
    : { name: "Random Forest Regressor v1.0", r2: "79.01%", mae: "44.63 kW", rmse: "129.44 kW", sigma: "129.44 kW" };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-3xl font-extrabold text-white leading-none">Generation Forecasting</h2>
          <p className="text-slate-400 mt-1 text-sm">Compare expected generation outputs with actual telemetry curves.</p>
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-cyan-400 bg-cyan-500/10 px-3 py-1.5 rounded-full border border-cyan-500/20">
          <Sparkles className="h-4.5 w-4.5" />
          Active Model: {modelStats.name}
        </div>
      </div>

      {/* Model Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-panel p-4 rounded-xl">
          <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Model R² Accuracy</span>
          <h4 className="text-2xl font-bold text-cyan-400 mt-1">{modelStats.r2}</h4>
          <p className="text-slate-500 text-[10px] mt-1">Variance explained</p>
        </div>
        <div className="glass-panel p-4 rounded-xl">
          <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Mean Absolute Error (MAE)</span>
          <h4 className="text-2xl font-bold text-slate-200 mt-1">{modelStats.mae}</h4>
          <p className="text-slate-500 text-[10px] mt-1">Average absolute prediction deviation</p>
        </div>
        <div className="glass-panel p-4 rounded-xl">
          <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Root Mean Squared Error</span>
          <h4 className="text-2xl font-bold text-slate-200 mt-1">{modelStats.rmse}</h4>
          <p className="text-slate-500 text-[10px] mt-1">RMSE quadratic penalty scale</p>
        </div>
        <div className="glass-panel p-4 rounded-xl">
          <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">Error Std Dev (Sigma)</span>
          <h4 className="text-2xl font-bold text-yellow-400 mt-1">{modelStats.sigma}</h4>
          <p className="text-slate-500 text-[10px] mt-1">Used for dynamic anomaly boundary</p>
        </div>
      </div>

      {/* Primary Forecast Chart */}
      <div className="glass-panel p-5 rounded-xl space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-200">Expected vs. Actual Generation Output</h3>
          <p className="text-xs text-slate-400">Showing the latest 3 days. Shaded region indicates the **95% Confidence Interval** ($\pm 2\sigma$ error band).</p>
        </div>

        <div className="h-96 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="confidenceGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.08}/>
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.01}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
              <XAxis dataKey="timestamp" stroke="#64748b" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={11} unit=" kW" />
              <Tooltip 
                contentStyle={{ background: '#0d111c', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#fff' }}
              />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px', color: '#94a3b8' }} />
              
              {/* Confidence Interval Shaded Area */}
              <Area 
                name="95% Confidence Band (±2σ)"
                type="monotone"
                dataKey="upper_bound"
                stroke="transparent"
                fill="url(#confidenceGlow)"
                fillId="lower_bound"
                dataKey2="lower_bound" 
              />
              <Area 
                name="Confidence Range Base"
                type="monotone"
                dataKey="lower_bound"
                stroke="transparent"
                fill="none"
              />
              
              {/* Predicted Line */}
              <Line 
                name="ML Expected Forecast" 
                type="monotone" 
                dataKey="predicted" 
                stroke="#06b6d4" 
                strokeWidth={2} 
                dot={false}
              />
              
              {/* Actual Line */}
              <Line 
                name="SCADA Actual Output" 
                type="monotone" 
                dataKey="actual" 
                stroke="#f43f5e" 
                strokeWidth={2} 
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
