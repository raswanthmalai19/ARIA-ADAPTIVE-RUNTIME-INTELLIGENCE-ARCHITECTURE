import React, { useState } from 'react';
import { MessageSquare, Activity, Cpu, Settings, Plus, Database, Clock, ChevronDown, Terminal, BarChart3, Eye, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = ({ activeView, setActiveView }) => {
  const [expandedSection, setExpandedSection] = useState('main');

  const mainItems = [
    { id: 'chat', label: 'Playground', icon: MessageSquare },
    { id: 'knowledge', label: 'Knowledge Base', icon: Database },
    { id: 'models', label: 'Models', icon: Cpu },
    { id: 'metrics', label: 'Metrics', icon: Activity },
  ];

  const advancedItems = [
    { id: 'analysis', label: 'Analysis', icon: BarChart3 },
    { id: 'logs', label: 'System Logs', icon: Terminal },
    { id: 'inspector', label: 'Layer Inspector', icon: Eye },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const recentChats = [
    { id: 1, title: 'API Design Pattern', time: '2h ago' },
    { id: 2, title: 'Quantum Computing', time: 'Yesterday' },
    { id: 3, title: 'Python Concurrency', time: 'Mar 28' },
  ];

  return (
    <motion.div 
      initial={{ x: -300 }}
      animate={{ x: 0 }}
      className="w-64 border-r border-white/5 glass-panel flex flex-col z-20 h-full overflow-hidden"
    >
      {/* Logo Section */}
      <motion.div 
        whileHover={{ scale: 1.02 }}
        className="p-5 border-b border-white/5 flex items-center gap-3 shrink-0 cursor-pointer hover:bg-white/[0.02] transition-colors"
      >
        <div className="w-12 h-12 rounded-2xl overflow-hidden flex items-center justify-center shadow-xl bg-white/10 border border-indigo-500/20">
          <img src="/aria-logo.png" alt="ARIA" className="w-10 h-10 object-contain" style={{ filter: 'drop-shadow(0 2px 8px rgba(99,102,241,0.18))' }} />
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400">ARIA</h1>
          <p className="text-[9px] text-cyan-500/80 uppercase tracking-widest font-mono">v2.0 Pro</p>
        </div>
      </motion.div>

      {/* New Session Button */}
      <div className="p-4 shrink-0">
        <button 
          onClick={() => setActiveView('chat')}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600/30 to-cyan-600/30 hover:from-indigo-600/40 hover:to-cyan-600/40 border border-indigo-500/30 text-indigo-300 transition-all shadow-[0_0_10px_rgba(99,102,241,0.1)] hover:shadow-[0_0_15px_rgba(99,102,241,0.2)]"
        >
          <Plus size={16} />
          <span className="text-sm font-semibold">New Query</span>
        </button>
      </div>

      {/* Navigation Sections */}
      <div className="flex-1 overflow-y-auto custom-scrollbar px-3 py-2 space-y-4">
        {/* Main Navigation */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'main' ? null : 'main')}
            className="flex items-center justify-between w-full px-3 py-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest hover:text-gray-300 transition-colors"
          >
            <span>Navigation</span>
            <motion.div animate={{ rotate: expandedSection === 'main' ? 180 : 0 }}>
              <ChevronDown size={12} />
            </motion.div>
          </button>
          
          <motion.div
            animate={{ height: expandedSection === 'main' ? 'auto' : 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-1 mt-2">
              {mainItems.map((item) => {
                const isActive = activeView === item.id;
                const Icon = item.icon;
                return (
                  <motion.button
                    key={item.id}
                    whileHover={{ x: 4 }}
                    onClick={() => setActiveView(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm text-left ${isActive ? 'bg-white/10 text-indigo-300 border border-white/5 shadow-inner' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}
                  >
                    <Icon size={16} className="flex-shrink-0" />
                    <span className="font-medium truncate">{item.label}</span>
                    {isActive && (
                      <motion.div layoutId="sidebar-indicator" className="w-1.5 h-1.5 rounded-full bg-indigo-400 ml-auto shadow-[0_0_8px_rgba(99,102,241,0.8)]" />
                    )}
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        </div>

        {/* Advanced Tools */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'advanced' ? null : 'advanced')}
            className="flex items-center justify-between w-full px-3 py-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest hover:text-gray-300 transition-colors"
          >
            <span>Advanced</span>
            <motion.div animate={{ rotate: expandedSection === 'advanced' ? 180 : 0 }}>
              <ChevronDown size={12} />
            </motion.div>
          </button>
          
          <motion.div
            animate={{ height: expandedSection === 'advanced' ? 'auto' : 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-1 mt-2">
              {advancedItems.map((item) => {
                const isActive = activeView === item.id;
                const Icon = item.icon;
                return (
                  <motion.button
                    key={item.id}
                    whileHover={{ x: 4 }}
                    onClick={() => setActiveView(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm text-left ${isActive ? 'bg-white/10 text-cyan-300 border border-white/5 shadow-inner' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200'}`}
                  >
                    <Icon size={16} className="flex-shrink-0" />
                    <span className="font-medium truncate">{item.label}</span>
                    {isActive && (
                      <motion.div layoutId="sidebar-indicator-adv" className="w-1.5 h-1.5 rounded-full bg-cyan-400 ml-auto" />
                    )}
                  </motion.button>
                );
              })}
            </div>
          </motion.div>
        </div>

        {/* Recent Sessions */}
        <div>
          <button
            onClick={() => setExpandedSection(expandedSection === 'recent' ? null : 'recent')}
            className="flex items-center justify-between w-full px-3 py-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest hover:text-gray-300 transition-colors"
          >
            <span>Recent</span>
            <motion.div animate={{ rotate: expandedSection === 'recent' ? 180 : 0 }}>
              <ChevronDown size={12} />
            </motion.div>
          </button>

          <motion.div
            animate={{ height: expandedSection === 'recent' ? 'auto' : 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-1 mt-2">
              {recentChats.map((chat) => (
                <button key={chat.id} className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 transition-colors group">
                  <div className="text-xs text-gray-300 truncate group-hover:text-indigo-300 transition-colors font-medium">{chat.title}</div>
                  <div className="text-[9px] text-gray-600 mt-0.5">{chat.time}</div>
                </button>
              ))}
            </div>
          </motion.div>
        </div>
      </div>

      {/* User Profile Footer */}
      <div className="p-4 border-t border-white/5 shrink-0">
        <motion.button
          whileHover={{ scale: 1.02 }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-900/50 border border-white/5 cursor-pointer hover:bg-gray-800/50 hover:border-indigo-500/30 transition-all"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-xs font-bold ring-2 ring-indigo-500/20">
            AR
          </div>
          <div className="flex flex-col text-left min-w-0">
            <span className="text-xs font-semibold text-gray-200 truncate">ARIA Engine</span>
            <span className="text-[10px] text-gray-500">v2.0 Pro</span>
          </div>
          <Zap size={12} className="text-cyan-400 ml-auto flex-shrink-0" />
        </motion.button>
      </div>
    </motion.div>
  );
};

export default Sidebar;
