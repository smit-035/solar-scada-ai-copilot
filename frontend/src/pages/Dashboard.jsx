import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Sun, Activity, ShieldAlert, BadgeIndianRupee, TrendingUp, AlertTriangle } from 'lucide-react';

export default function Dashboard({ plantId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    const url = plantId 
      ? `http://localhost:5000/api/dashboard?plant_id=${plantId}`
      : 'http://localhost:5000/api/dashboard';
      
    axios.get(url)
      .then(res => {
        setData(res.data);
        setError(null);
      })
      .catch(err => {
        console.error("Dashboard error:", err);
        setError("Failed to connect to the backend server. Please make sure Flask is running.");
      })
      .finally(() => setLoading(false));
  }, [plantId]);

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
        <AlertTriangle className="h-10 w-10 text-red-500 shrink-0" />
        <div>
          <h3 className="font-bold text-lg">Server Connection Failed</h3>
          <p className="text-sm opacity-90">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-extrabold text-white leading-none">Operational Overview</h2>
        <p className="text-slate-400 mt-1 text-sm">Real-time solar telemetry and plant performance analytics.</p>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Current Generation */}
        <div className="glass-panel-glow p-5 rounded-xl transition duration-300 hover:scale-[1.02]">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Telemetry AC Power</p>
              <h3 className="text-3xl font-bold text-white mt-1">{data.current_ac_power_kw.toLocaleString()} <span className="text-sm text-slate-400">kW</span></h3>
              <p className="text-xs text-slate-400 mt-2">Active: {data.inverters_count} inverters</p>
            </div>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Sun className="h-6 w-6" />
            </div>
          </div>
        </div>

        {/* Plant Health */}
        <div className="glass-panel p-5 rounded-xl transition duration-300 hover:scale-[1.02]">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Aggregate Health</p>
              <h3 className={`text-3xl font-bold mt-1 ${data.average_health_score > 85 ? 'text-emerald-400' : 'text-yellow-400'}`}>
                {data.average_health_score}%
              </h3>
              <p className="text-xs text-slate-400 mt-2">Nominal conversion rating</p>
            </div>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
              <Activity className="h-6 w-6" />
            </div>
          </div>
        </div>

        {/* Anomalies Detected */}
        <div className="glass-panel p-5 rounded-xl transition duration-300 hover:scale-[1.02]">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Flagged Anomalies</p>
              <h3 className={`text-3xl font-bold mt-1 ${data.anomalies_count > 0 ? 'text-red-400' : 'text-slate-200'}`}>
                {data.anomalies_count}
              </h3>
              <p className="text-xs text-slate-400 mt-2">Statistical limit deviations</p>
            </div>
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400">
              <ShieldAlert className="h-6 w-6" />
            </div>
          </div>
        </div>

        {/* Financial Revenue Loss */}
        <div className="glass-panel p-5 rounded-xl transition duration-300 hover:scale-[1.02]">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Estimated Revenue Loss</p>
              <h3 className="text-3xl font-bold text-white mt-1">Rs. {data.estimated_loss_rs.toLocaleString()}</h3>
              <p className="text-xs text-slate-400 mt-2">Calculated at Rs. 4/kWh</p>
            </div>
            <div className="p-2 rounded-lg bg-yellow-500/10 text-yellow-400">
              <BadgeIndianRupee className="h-6 w-6" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hourly Generation Curve */}
        <div className="glass-panel p-5 rounded-xl lg:col-span-2 space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-bold text-slate-200">Daily Generation Profile</h3>
              <p className="text-xs text-slate-400">Average historical AC generation curve by hour of day.</p>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full font-medium">
              <TrendingUp className="h-4.5 w-4.5" />
              Diurnal Cycle
            </div>
          </div>
          
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.hourly_curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="acGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                <XAxis 
                  dataKey="hour" 
                  stroke="#64748b" 
                  fontSize={11} 
                  tickFormatter={h => `${h}:00`} 
                />
                <YAxis stroke="#64748b" fontSize={11} unit=" kW" />
                <Tooltip 
                  contentStyle={{ background: '#0d111c', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px' }}
                  labelStyle={{ color: '#94a3b8' }}
                  itemStyle={{ color: '#fff' }}
                  formatter={(val) => [`${val.toLocaleString()} kW`, 'Average Output']}
                  labelFormatter={(label) => `Time: ${label}:00`}
                />
                <Area 
                  type="monotone" 
                  dataKey="ac_power" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#acGlow)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Equipment Risk Matrix Summary */}
        <div className="glass-panel p-5 rounded-xl flex flex-col justify-between">
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-slate-200">Equipment Health Index</h3>
            <p className="text-xs text-slate-400">Aggregated breakdown of inverter health risk categories.</p>
          </div>

          <div className="space-y-4 my-6">
            {/* Low Risk */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-400">
                <span className="font-semibold text-emerald-400">Low Risk (Healthy)</span>
                <span>{data.risk_summary.low} / {data.inverters_count} inverters</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5">
                <div 
                  className="bg-emerald-500 h-2.5 rounded-full" 
                  style={{ width: `${(data.risk_summary.low / data.inverters_count) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* Medium Risk */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-400">
                <span className="font-semibold text-yellow-400">Medium Risk (Warning)</span>
                <span>{data.risk_summary.medium} / {data.inverters_count} inverters</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5">
                <div 
                  className="bg-yellow-500 h-2.5 rounded-full" 
                  style={{ width: `${(data.risk_summary.medium / data.inverters_count) * 100}%` }}
                ></div>
              </div>
            </div>

            {/* High Risk */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs text-slate-400">
                <span className="font-semibold text-red-500">High Risk (Critical)</span>
                <span>{data.risk_summary.high} / {data.inverters_count} inverters</span>
              </div>
              <div className="w-full bg-slate-900 rounded-full h-2.5">
                <div 
                  className="bg-red-500 h-2.5 rounded-full" 
                  style={{ width: `${(data.risk_summary.high / data.inverters_count) * 100}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900/60 border border-white/5 rounded-lg p-3 text-xs text-slate-400">
            {data.risk_summary.high > 0 ? (
              <p className="text-red-300 flex items-center gap-1.5">
                <AlertTriangle className="h-4.5 w-4.5 text-red-500 shrink-0" />
                {data.risk_summary.high} critical equipment alerts require immediate maintenance inspection.
              </p>
            ) : (
              <p className="text-slate-400">
                All inverter arrays operating within normal bounds. No immediate actions required.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
