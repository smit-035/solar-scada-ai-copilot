import React, { useState } from 'react';
import Dashboard from './pages/Dashboard';
import Forecast from './pages/Forecast';
import Anomalies from './pages/Anomalies';
import Maintenance from './pages/Maintenance';
import Assistant from './pages/Assistant';
import { LayoutDashboard, BarChart2, ShieldAlert, Heart, Terminal, Sun, ArrowRightLeft } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [plantId, setPlantId] = useState('all'); // 'all', '4135001' (Plant 1), '4136001' (Plant 2)

  // Sidebar navigation options
  const navItems = [
    { id: 'dashboard', name: 'Dashboard', icon: LayoutDashboard },
    { id: 'forecast', name: 'Forecast Analysis', icon: BarChart2 },
    { id: 'anomalies', name: 'Anomalies & Alerts', icon: ShieldAlert },
    { id: 'maintenance', name: 'Equipment Health', icon: Heart },
    { id: 'assistant', name: 'AI Operations Assistant', icon: Terminal },
  ];

  // Render correct page
  const renderActivePage = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard plantId={plantId === 'all' ? null : plantId} />;
      case 'forecast':
        return <Forecast plantId={plantId} />;
      case 'anomalies':
        return <Anomalies plantId={plantId === 'all' ? null : plantId} />;
      case 'maintenance':
        return <Maintenance plantId={plantId === 'all' ? null : plantId} />;
      case 'assistant':
        return <Assistant plantId={plantId} />;
      default:
        return <Dashboard plantId={plantId === 'all' ? null : plantId} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-[#08090d]">
      {/* Sidebar Panel */}
      <aside className="w-64 border-r border-white/5 bg-[#0a0c14] flex flex-col justify-between shrink-0">
        <div className="p-6 space-y-8">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
              <Sun className="h-6 w-6 animate-pulse-glow" />
            </div>
            <div>
              <h1 className="text-base font-extrabold text-white tracking-wide">HELIOS AI</h1>
              <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">SCADA Copilot Layer</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3.5 px-4 py-3 rounded-lg text-xs font-semibold tracking-wide transition ${
                    isActive 
                      ? 'bg-blue-600/15 border border-blue-500/20 text-blue-400' 
                      : 'text-slate-400 border border-transparent hover:bg-white/5 hover:text-slate-200'
                  }`}
                >
                  <Icon className="h-4.5 w-4.5 shrink-0" />
                  {item.name}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Workspace Footer details */}
        <div className="p-6 border-t border-white/5 bg-slate-950/20 text-[10px] text-slate-500">
          <p className="font-bold text-slate-400 uppercase tracking-wider">Workspace Node</p>
          <p className="mt-1 font-mono text-slate-600 truncate">localhost:5000</p>
        </div>
      </aside>

      {/* Main Panel Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header Bar */}
        <header className="h-16 border-b border-white/5 bg-[#0a0c14]/40 backdrop-blur px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5 text-xs text-slate-400 font-semibold bg-white/5 px-3 py-1.5 rounded-lg border border-white/5">
            <ArrowRightLeft className="h-4 w-4 text-slate-500" />
            <span>Select Active Facility:</span>
            <select 
              value={plantId} 
              onChange={e => setPlantId(e.target.value)}
              className="bg-transparent text-white font-bold focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-[#0c0f1d] text-white">All Plant Facilities</option>
              <option value="4135001" className="bg-[#0c0f1d] text-white">Plant 1 (Gandhinagar)</option>
              <option value="4136001" className="bg-[#0c0f1d] text-white">Plant 2 (Jodhpur)</option>
            </select>
          </div>

          <div className="flex items-center gap-4 text-[11px] text-slate-500 font-semibold">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-300">SCADA Stream: Active</span>
            </div>
          </div>
        </header>

        {/* Dynamic Page Viewer */}
        <main className="flex-1 p-8 overflow-y-auto">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
}
