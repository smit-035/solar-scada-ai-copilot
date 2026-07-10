import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, AlertTriangle, HelpCircle, BadgeCheck } from 'lucide-react';

export default function Anomalies({ plantId }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    setLoading(true);
    const url = plantId && plantId !== 'all'
      ? `http://localhost:5000/api/anomalies?plant_id=${plantId}`
      : 'http://localhost:5000/api/anomalies';
      
    axios.get(url)
      .then(res => {
        setData(res.data);
        setError(null);
      })
      .catch(err => {
        console.error("Anomalies error:", err);
        setError("Failed to fetch anomaly log from database.");
      })
      .finally(() => setLoading(false));
  }, [plantId]);

  // Filter anomalies based on search term (searching Inverter ID or Issue text)
  const filteredAnomalies = data.filter(item => 
    item.equipment_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    item.issue.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
          <h3 className="font-bold text-lg">Error Loading Anomalies</h3>
          <p className="text-sm opacity-90">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-extrabold text-white leading-none">Anomalies & Alerts Log</h2>
        <p className="text-slate-400 mt-1 text-sm">Real-time flagged SCADA deviations compared against ML predictions.</p>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-3 h-5 w-5 text-slate-500" />
          <input 
            type="text" 
            placeholder="Search by Inverter Key or Root Cause issue..." 
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-slate-900/60 border border-white/5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition"
          />
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
          Showing {filteredAnomalies.length} anomaly logs
        </div>
      </div>

      {/* Log Table */}
      {filteredAnomalies.length === 0 ? (
        <div className="glass-panel p-12 rounded-xl flex flex-col items-center justify-center text-center">
          <BadgeCheck className="h-16 w-16 text-emerald-500/30 mb-4" />
          <h3 className="text-lg font-bold text-slate-200">All Clear</h3>
          <p className="text-xs text-slate-400 max-w-sm mt-1">No anomalies matched your search parameters. Telemetry is fully normal.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden border border-white/5">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-white/5 bg-slate-900/40 text-slate-400 text-xs font-bold uppercase tracking-wider">
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Plant</th>
                  <th className="p-4">Inverter ID</th>
                  <th className="p-4">Flagged Issue</th>
                  <th className="p-4">Recommended Action</th>
                  <th className="p-4 text-right">Revenue Loss</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300 text-xs">
                {filteredAnomalies.map((item, index) => (
                  <tr key={index} className="hover:bg-white/5 transition">
                    <td className="p-4 whitespace-nowrap text-slate-400 font-medium">{item.timestamp}</td>
                    <td className="p-4 whitespace-nowrap">{item.plant_name}</td>
                    <td className="p-4 whitespace-nowrap font-mono text-cyan-400 font-semibold">{item.equipment_id}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-red-500 shrink-0"></span>
                        <span className="font-semibold text-slate-200">{item.issue}</span>
                      </div>
                    </td>
                    <td className="p-4 text-slate-400">{item.recommended_action}</td>
                    <td className="p-4 text-right whitespace-nowrap font-bold text-yellow-400">
                      Rs. {item.financial_loss_rs.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
