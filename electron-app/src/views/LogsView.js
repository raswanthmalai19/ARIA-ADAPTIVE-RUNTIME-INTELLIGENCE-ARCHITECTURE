import React, { useState } from 'react';
import { Terminal, Filter, Copy, Download, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

const LogsView = ({ showToast }) => {
  const [logLevel, setLogLevel] = useState('all');

  const logs = [
    { time: '14:32:45', level: 'info', message: 'Model loaded successfully', color: 'text-cyan-400' },
    { time: '14:32:44', level: 'debug', message: 'Cache allocated: 2048MB', color: 'text-gray-400' },
    { time: '14:32:42', level: 'info', message: 'Inference request received', color: 'text-cyan-400' },
    { time: '14:32:41', level: 'warning', message: 'Memory pressure: 85%', color: 'text-amber-400' },
    { time: '14:32:40', level: 'info', message: 'Query classified as: complex', color: 'text-cyan-400' },
    { time: '14:32:39', level: 'debug', message: 'Attention head profile: 12/16 active', color: 'text-gray-400' },
    { time: '14:32:38', level: 'info', message: 'Model selection: 3B (full)', color: 'text-cyan-400' },
  ];

  const filteredLogs = logLevel === 'all' ? logs : logs.filter(l => l.level === logLevel);

  return (
    <div className="p-8 h-full flex flex-col space-y-4">
      {/* Toolbar */}
      <div className="flex gap-3 items-center">
        <div className="flex gap-2 bg-white/5 border border-white/10 rounded-lg p-2">
          {['all', 'info', 'warning', 'debug'].map(level => (
            <button
              key={level}
              onClick={() => setLogLevel(level)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-all \${
                logLevel === level
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
              }`}
            >
              {level.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="ml-auto flex gap-2">
          <button className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors" title="Copy logs">
            <Copy size={16} className="text-gray-400" />
          </button>
          <button className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors" title="Download logs">
            <Download size={16} className="text-gray-400" />
          </button>
          <button className="p-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-colors" title="Clear logs">
            <Trash2 size={16} className="text-gray-400" />
          </button>
        </div>
      </div>

      {/* Logs Container */}
      <div className="flex-1 bg-[#0A0D14] border border-white/5 rounded-lg p-4 font-mono text-sm overflow-y-auto custom-scrollbar">
        {filteredLogs.map((log, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="py-1 text-gray-400"
          >
            <span className="text-gray-600">{log.time}</span>
            <span className="mx-3 text-gray-700">│</span>
            <span className={`font-bold ${log.color}`}>{log.level.toUpperCase()}</span>
            <span className="mx-3 text-gray-700">│</span>
            <span className="text-gray-300">{log.message}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default LogsView;
