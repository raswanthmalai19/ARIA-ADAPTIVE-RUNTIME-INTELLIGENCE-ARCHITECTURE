import React from 'react';
import { Settings, Shield, Sliders } from 'lucide-react';
import { motion } from 'framer-motion';

const SettingsView = () => {
  return (
    <div className="p-8 max-w-4xl mx-auto h-full overflow-y-auto pb-20">
      <div className="mb-8">
        <h2 className="text-3xl font-extrabold text-white mb-2">Configuration</h2>
        <p className="text-gray-400">Manage ARIA parameters, fallbacks, and system logic.</p>
      </div>

      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/5">
            <Sliders className="text-indigo-400" size={20} />
            <h3 className="text-lg font-bold">Inference Parameters</h3>
          </div>
          
          <div className="space-y-6">
            <div>
              <label className="flex justify-between text-sm font-medium text-gray-300 mb-3">
                <span>Temperature</span>
                <span className="text-indigo-400 font-mono">0.7</span>
              </label>
              <input type="range" min="0" max="100" defaultValue="70" className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer" />
              <p className="text-[11px] text-gray-500 mt-2">Higher values make output more random, lower values make it more focused.</p>
            </div>
            
            <div>
              <label className="flex justify-between text-sm font-medium text-gray-300 mb-3">
                <span>Max Generation Tokens</span>
                <span className="text-indigo-400 font-mono">512</span>
              </label>
              <input type="range" min="128" max="2048" defaultValue="512" className="w-full h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer" />
            </div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel p-6 rounded-2xl">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/5">
            <Shield className="text-cyan-400" size={20} />
            <h3 className="text-lg font-bold">System Directive</h3>
          </div>
          
          <div>
            <textarea 
              defaultValue="You are ARIA, an advanced local runtime intelligence architecture. You provide direct, expert-level coding assistance without unnecessary disclaimers."
              className="w-full h-32 bg-[#0A0D14] border border-white/10 rounded-xl p-4 text-sm text-gray-300 focus:border-indigo-500/50 outline-none transition-colors"
            />
            <div className="mt-4 flex justify-end">
              <button onClick={() => alert("Preferences saved in Session memory")} className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors border border-indigo-400/30">
                Save Directive
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
export default SettingsView;
