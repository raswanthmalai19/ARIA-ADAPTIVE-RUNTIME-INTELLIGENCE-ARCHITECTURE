import React, { useState } from 'react';
import { BarChart3, TrendingUp, Zap, Clock, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

const AnalysisView = ({ showToast }) => {
  const [selectedMetric, setSelectedMetric] = useState('latency');

  const metrics = [
    {
      label: 'Avg Latency',
      value: '342ms',
      icon: Clock,
      color: 'from-indigo-500 to-indigo-600',
      change: '-12%',
      positive: true,
    },
    {
      label: 'Tokens/Sec',
      value: '47.2',
      icon: Zap,
      color: 'from-cyan-500 to-cyan-600',
      change: '+8%',
      positive: true,
    },
    {
      label: 'Model Hits',
      value: '1,250',
      icon: Cpu,
      color: 'from-emerald-500 to-emerald-600',
      change: '+25%',
      positive: true,
    },
    {
      label: 'Memory Peak',
      value: '4.2GB',
      icon: TrendingUp,
      color: 'from-amber-500 to-amber-600',
      change: '-5%',
      positive: true,
    },
  ];

  return (
    <div className="p-8 h-full overflow-y-auto space-y-8">
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric, idx) => {
          const Icon = metric.icon;
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="glass-panel p-6 rounded-xl border border-white/5 hover:border-white/10 transition-colors cursor-pointer group"
              onClick={() => setSelectedMetric(metric.label.toLowerCase())}
            >
              <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${metric.color} p-3 mb-4 shadow-lg group-hover:scale-110 transition-transform`}>
                <Icon size={20} className="text-white" />
              </div>
              <div className="text-sm text-gray-400 mb-2">{metric.label}</div>
              <div className="flex items-baseline gap-2">
                <div className="text-2xl font-bold text-white">{metric.value}</div>
                <div className={`text-xs font-semibold \${metric.positive ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {metric.change}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Analysis Details */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-8 rounded-xl border border-white/5"
      >
        <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-3">
          <BarChart3 className="text-cyan-400" />
          Performance Analytics
        </h2>
        
        <div className="space-y-4">
          {['Dynamic Layer Utilization', 'Cache Efficiency', 'Model Selection Accuracy'].map((item, idx) => (
            <div key={idx} className="flex items-center justify-between p-4 bg-white/[0.02] rounded-lg border border-white/5">
              <span className="text-gray-300 font-medium">{item}</span>
              <div className="flex items-center gap-3">
                <div className="w-48 h-2 bg-gray-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${85 + idx * 5}%` }}
                    transition={{ duration: 1, delay: 0.5 }}
                    className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500"
                  />
                </div>
                <span className="text-sm font-bold text-cyan-400 w-12 text-right">${85 + idx * 5}%</span>
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default AnalysisView;
