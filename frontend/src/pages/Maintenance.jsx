import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { ShieldCheck, ShieldAlert, Cpu, Heart, CheckCircle2 } from 'lucide-react';

export default function Maintenance({ plantId }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    const url = plantId && plantId !== 'all'
      ? `http://localhost:5000/api/maintenance?plant_id=${plantId}`
      : 'http://localhost:5000/api/maintenance';
      
    axios.get(url)
      .then(res => {
        setData(res.data);
        setError(null);
      })
      .catch(err => {
        console.error("Maintenance error:", err);
        setError("Failed to fetch equipment health cards from database.");
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
        <ShieldAlert className="h-10 w-10 text-red-500 shrink-0" />
        <div>
          <h3 className="font-bold text-lg">Error Loading Health Metrics</h3>
          <p className="text-sm opacity-90">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-extrabold text-white leading-none">Equipment Health Dashboard</h2>
        <p className="text-slate-400 mt-1 text-sm">Aggregated health index cards and maintenance diagnostics for all active inverter modules.</p>
      </div>

      {/* Grid of Inverters */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data.map((item, index) => {
          // Color coding depending on risk status
          const isHigh = item.risk_level === 'HIGH';
          const isMed = item.risk_level === 'MEDIUM';
          
          let cardStyle = "glass-panel";
          let borderGlow = "border-white/5";
          let statusText = "text-emerald-400";
          let iconBg = "bg-emerald-500/10 text-emerald-400";
          
          if (isHigh) {
            cardStyle = "glass-panel-danger";
            borderGlow = "border-red-500/35";
            statusText = "text-red-500";
            iconBg = "bg-red-500/10 text-red-400";
          } else if (isMed) {
            cardStyle = "glass-panel-glow";
            borderGlow = "border-yellow-500/30";
            statusText = "text-yellow-400";
            iconBg = "bg-yellow-500/10 text-yellow-400";
          }

          return (
            <div 
              key={index} 
              className={`p-5 rounded-xl border ${borderGlow} ${cardStyle} transition duration-300 hover:scale-[1.01] flex flex-col justify-between h-72`}
            >
              {/* Card Header */}
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500 font-bold text-[10px] bg-slate-900 px-2 py-0.5 rounded border border-white/5 uppercase">
                      {item.plant_name}
                    </span>
                  </div>
                  <h4 className="text-base font-bold font-mono text-cyan-400 mt-1.5">{item.source_key}</h4>
                </div>
                <div className={`p-2 rounded-lg ${iconBg}`}>
                  <Cpu className="h-5 w-5" />
                </div>
              </div>

              {/* Health Score Slider */}
              <div className="space-y-2 my-4">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-400 font-semibold flex items-center gap-1">
                    <Heart className="h-4 w-4 text-red-500 fill-red-500/20" /> Health Rating
                  </span>
                  <span className={`font-bold ${statusText}`}>{item.health_score}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${isHigh ? 'bg-red-500' : (isMed ? 'bg-yellow-500' : 'bg-emerald-500')}`} 
                    style={{ width: `${item.health_score}%` }}
                  ></div>
                </div>
              </div>

              {/* Secondary Specs */}
              <div className="grid grid-cols-3 gap-2 border-y border-white/5 py-3 text-[11px] text-slate-400 font-medium">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Efficiency</p>
                  <p className="text-slate-200 font-bold mt-0.5">{item.average_efficiency}%</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Anomalies</p>
                  <p className="text-slate-200 font-bold mt-0.5">{item.anomaly_count} alerts</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">Runtime</p>
                  <p className="text-slate-200 font-bold mt-0.5">{item.total_runtime_hours.toLocaleString()} hrs</p>
                </div>
              </div>

              {/* Maintenance recommendation */}
              <div className="mt-3.5 flex items-start gap-1.5 text-xs text-slate-400 leading-normal">
                {isHigh || isMed ? (
                  <ShieldAlert className={`h-4.5 w-4.5 shrink-0 ${statusText}`} />
                ) : (
                  <ShieldCheck className="h-4.5 w-4.5 text-emerald-400 shrink-0" />
                )}
                <p className="line-clamp-2">{item.recommended_action}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
