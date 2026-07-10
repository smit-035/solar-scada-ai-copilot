import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, Sparkles, MessageSquare, Terminal, ChevronRight } from 'lucide-react';

export default function Assistant({ plantId }) {
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: "Hello! I am your AI-Powered Renewable Energy Copilot. I can query active generation values, forecast outputs, dynamic anomaly reports, and equipment health score logs for both solar plants. Ask me anything about current plant statuses or maintenance needs!"
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const suggestionQueries = [
    "Why was generation low yesterday?",
    "Summarize equipment risks for Plant 1",
    "Compare the models used for forecasting",
    "Show the biggest financial losses"
  ];

  // Auto scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSendMessage = (textToSend) => {
    const queryText = textToSend || input;
    if (!queryText.trim()) return;

    // Append user query
    setMessages(prev => [...prev, { sender: 'user', text: queryText }]);
    if (!textToSend) setInput('');
    setLoading(true);

    axios.post('http://localhost:5000/api/chat', { 
      message: queryText,
      plant_id: plantId
    })
      .then(res => {
        setMessages(prev => [...prev, { sender: 'ai', text: res.data.response }]);
      })
      .catch(err => {
        console.error("Chat error:", err);
        setMessages(prev => [...prev, { 
          sender: 'ai', 
          text: "System Alert: I encountered a connection issue when trying to speak with the backend server. Please make sure the Flask app is active on port 5000." 
        }]);
      })
      .finally(() => setLoading(false));
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] glass-panel rounded-xl overflow-hidden">
      {/* Copilot Header */}
      <div className="p-4 bg-slate-900/50 border-b border-white/5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-200">Helios Operations Copilot</h3>
            <p className="text-[10px] text-slate-500">Connected to active PostgreSQL and ML tools</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] font-semibold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
          <Sparkles className="h-3.5 w-3.5" />
          Gemini 3.5 Active
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, idx) => (
          <div 
            key={idx} 
            className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`max-w-xl p-3.5 rounded-xl text-xs leading-relaxed ${
                m.sender === 'user' 
                  ? 'bg-blue-600 text-white rounded-tr-none' 
                  : 'bg-slate-900 border border-white/5 text-slate-300 rounded-tl-none'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-900 border border-white/5 text-slate-400 rounded-xl rounded-tl-none p-3.5 text-xs flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce"></span>
              <span className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce delay-100"></span>
              <span className="h-2 w-2 rounded-full bg-cyan-500 animate-bounce delay-200"></span>
              <span>Evaluating solar telemetry...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestion Chips */}
      {messages.length === 1 && (
        <div className="px-4 py-2 shrink-0 border-t border-white/5 bg-slate-950/20">
          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-2">Suggestion Prompts</p>
          <div className="flex flex-wrap gap-2">
            {suggestionQueries.map((query, index) => (
              <button
                key={index}
                onClick={() => handleSendMessage(query)}
                className="text-[11px] text-slate-400 bg-slate-900/60 border border-white/5 hover:border-cyan-500/30 hover:text-cyan-400 px-3 py-1.5 rounded-lg transition text-left flex items-center"
              >
                {query} <ChevronRight className="h-3 w-3 ml-1" />
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input container */}
      <div className="p-4 border-t border-white/5 bg-slate-900/30 shrink-0">
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
          className="flex gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask a question about plant anomalies, forecast metrics, or inverter health..."
            className="flex-1 bg-slate-950 border border-white/5 rounded-lg px-4 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white transition shrink-0"
          >
            <Send className="h-4.5 w-4.5" />
          </button>
        </form>
      </div>
    </div>
  );
}
