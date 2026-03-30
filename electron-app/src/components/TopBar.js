import React, { useState } from 'react';
import { Search, Bell, Settings, Power, Copy } from 'lucide-react';
import { motion } from 'framer-motion';

const TopBar = ({ health, activeView }) => {
  const [showSearch, setShowSearch] = useState(false);

  const viewTitles = {
    chat: 'Playground',
    knowledge: 'Knowledge Base',
    models: 'Models',
    metrics: 'Metrics',
    analysis: 'Analysis',
    logs: 'System Logs',
    inspector: 'Layer Inspector',
    settings: 'Settings',
  };

  return (
    <div className="h-16 border-b border-white/5 glass-panel flex items-center justify-between px-6 z-10">
      <div className="flex items-center gap-4 flex-1">
        <h2 className="text-xl font-bold text-white">{viewTitles[activeView] || 'Dashboard'}</h2>
      </div>

      <div className="flex items-center gap-4">
        {/* Health Status */}
        <motion.div
          whileHover={{ scale: 1.05 }}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 border border-white/10 cursor-pointer hover:bg-white/10 transition-colors"
        >
          <div className={`w-2.5 h-2.5 rounded-full \${health?.status === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-rose-500'}`} />
          <span className="text-xs font-mono text-gray-300">{health?.status === 'online' ? 'Backend Online' : 'Offline'}</span>
        </motion.div>

        {/* Search */}
        <motion.div
          animate={{ width: showSearch ? 240 : 40 }}
          transition={{ duration: 0.2 }}
          className="relative"
        >
          {showSearch ? (
            <input
              type="text"
              placeholder="Search or ask..."
              autoFocus
              onBlur={() => setShowSearch(false)}
              className="w-full px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white placeholder-gray-500 outline-none focus:border-indigo-500/50 transition-colors"
            />
          ) : (
            <button
              onClick={() => setShowSearch(true)}
              className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <Search size={16} className="text-gray-400" />
            </button>
          )}
        </motion.div>

        {/* Notifications */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          className="relative w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors"
        >
          <Bell size={16} className="text-gray-400" />
          <div className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full animate-pulse" />
        </motion.button>

        {/* Settings */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center hover:bg-white/10 transition-colors"
        >
          <Settings size={16} className="text-gray-400" />
        </motion.button>

        {/* Power Status */}
        <motion.div
          whileHover={{ scale: 1.05 }}
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 ml-2"
        >
          <Power size={14} className="text-emerald-400" />
          <span className="text-xs font-semibold text-emerald-300">Online</span>
        </motion.div>
      </div>
    </div>
  );
};

export default TopBar;
