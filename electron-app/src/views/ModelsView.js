import React from 'react';
import { Cpu, CheckCircle2, DownloadCloud } from 'lucide-react';
import { motion } from 'framer-motion';

const ModelsView = ({ health }) => {
  const currentModel = health?.details?.stats?.current_model;

  const models = [
    { id: 'Qwen/Qwen2.5-0.5B-Instruct', type: 'LLM', status: currentModel === 'Qwen/Qwen2.5-0.5B-Instruct' ? 'active' : 'cached', size: '1.2 GB' },
    { id: 'gpt2', type: 'Fallback', status: currentModel === 'gpt2' ? 'active' : 'cached', size: '500 MB' },
    { id: 'distilgpt2', type: 'Fallback', status: currentModel === 'distilgpt2' ? 'active' : 'cached', size: '300 MB' },
    { id: 'meta-llama/Llama-2-7b-chat', type: 'LLM', status: 'cloud', size: '13.5 GB' },
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto h-full overflow-y-auto">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-extrabold text-white mb-2">Model Cache Hierarchy</h2>
          <p className="text-gray-400">Manage and dynamically route local models via Cache.</p>
        </div>
        <button onClick={() => alert("Model fetch feature requires terminal access.")} className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 flex items-center gap-2 text-sm text-gray-200 transition-colors">
          <DownloadCloud size={16} /> Fetch Model
        </button>
      </div>

      <div className="space-y-4">
        {models.map((model, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`p-5 rounded-2xl border flex items-center justify-between group ${
              model.status === 'active' 
                ? 'bg-indigo-900/20 border-indigo-500/50 shadow-[0_0_20px_rgba(99,102,241,0.1)]' 
                : 'glass-panel border-white/5 hover:border-white/10'
            }`}
          >
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center border border-white/5 ${
                model.status === 'active' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-white/5 text-gray-400'
              }`}>
                <Cpu size={24} />
              </div>
              <div>
                <h4 className="text-lg font-bold text-gray-100 flex items-center gap-2">
                  {model.id}
                  {model.status === 'active' && <CheckCircle2 size={16} className="text-emerald-400" />}
                </h4>
                <div className="flex items-center gap-3 text-xs mt-1">
                  <span className="px-2 py-0.5 rounded bg-white/5 text-gray-400 font-mono">{model.type}</span>
                  <span className="text-gray-500 border-l border-white/10 pl-3">{model.size}</span>
                </div>
              </div>
            </div>

            <div>
              {model.status === 'active' ? (
                <span className="px-3 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 text-xs font-bold uppercase tracking-wider">
                  Loaded in RAM
                </span>
              ) : model.status === 'cached' ? (
                <button className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors">
                  Load Cache
                </button>
              ) : (
                <button className="px-4 py-2 rounded-lg border border-white/10 hover:bg-white/5 text-gray-300 text-sm font-medium transition-colors flex items-center gap-2">
                  <DownloadCloud size={14} /> Download
                </button>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
};
export default ModelsView;
