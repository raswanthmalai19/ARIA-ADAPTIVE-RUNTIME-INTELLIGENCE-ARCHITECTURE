import React from 'react';
import { Activity, Cpu, HardDrive, Zap, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

const MetricsView = ({ health }) => {
  const stats = health.details?.stats || {};
  
  const cards = [
    { title: 'Current VRAM Usage', value: stats.vram_allocated || '0 MB', icon: HardDrive, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
    { title: 'Active Model', value: stats.current_model?.split('/').pop() || 'None', icon: Cpu, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    { title: 'Compute Target', value: (stats.device || 'cpu').toUpperCase(), icon: Zap, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    { title: 'Engine Uptime', value: 'System Online', icon: Clock, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  ];

  return (
    <div className="p-8 max-w-6xl mx-auto h-full overflow-y-auto">
      <div className="mb-8">
        <h2 className="text-3xl font-extrabold text-white mb-2">Engine Analytics</h2>
        <p className="text-gray-400">Real-time inference telemetry and hardware statistics.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {cards.map((card, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="glass-panel p-6 rounded-2xl border border-white/5 hover:border-white/10 transition-colors"
          >
            <div className={`w-12 h-12 rounded-xl border border-white/5 flex items-center justify-center mb-4 ${card.bg}`}>
              <card.icon className={card.color} size={24} />
            </div>
            <h3 className="text-gray-500 text-sm font-semibold uppercase tracking-wider mb-1">{card.title}</h3>
            <p className="text-2xl font-bold text-gray-100">{card.value}</p>
          </motion.div>
        ))}
      </div>

      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}
        className="glass-panel p-8 rounded-2xl border border-white/5"
      >
        <div className="flex items-center gap-3 mb-6">
          <Activity className="text-indigo-400" />
          <h3 className="text-xl font-bold">Memory Pool State</h3>
        </div>
        
        <div className="h-48 w-full bg-[#0A0D14] rounded-xl border border-white/5 flex items-center justify-center flex-col relative overflow-hidden">
           <div className="absolute inset-x-0 bottom-0 top-1/2 bg-gradient-to-t from-indigo-900/20 to-transparent"></div>
           <div className="text-center relative z-10">
             <div className="text-4xl font-black text-white mix-blend-plus-lighter drop-shadow-[0_0_15px_rgba(99,102,241,0.5)]">
               {stats.vram_allocated || '0 MB'}
             </div>
             <div className="text-sm text-gray-500 mt-2 tracking-widest font-mono uppercase">Reserved Memory</div>
           </div>
        </div>
      </motion.div>
    </div>
  );
};
export default MetricsView;
