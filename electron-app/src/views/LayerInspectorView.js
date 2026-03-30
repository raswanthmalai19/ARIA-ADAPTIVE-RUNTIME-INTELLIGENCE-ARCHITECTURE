import React, { useState } from 'react';
import { Eye, Layers, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

const LayerInspectorView = ({ showToast }) => {
  const [selectedLayer, setSelectedLayer] = useState(0);

  const layers = Array.from({ length: 24 }, (_, i) => ({
    id: i,
    name: `Transformer Block ${i + 1}`,
    active: i < 20,
    headCount: 12,
    activeHeads: Math.floor(12 * (0.7 + Math.random() * 0.3)),
    flops: Math.floor(Math.random() * 1000 + 500),
  }));

  const selectedLayerData = layers[selectedLayer];

  return (
    <div className="p-8 h-full flex gap-6 overflow-hidden">
      {/* Layer List */}
      <div className="w-64 bg-white/[0.02] border border-white/5 rounded-lg p-4 overflow-y-auto custom-scrollbar">
        <h3 className="text-sm font-bold text-gray-300 uppercase tracking-widest mb-3">Layers</h3>
        <div className="space-y-2">
          {layers.map(layer => (
            <motion.button
              key={layer.id}
              whileHover={{ x: 4 }}
              onClick={() => setSelectedLayer(layer.id)}
              className={`w-full text-left px-3 py-2 rounded-lg transition-all text-xs \${
                selectedLayer === layer.id
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono">{layer.name}</span>
                {layer.active ? (
                  <Zap size={10} className="text-cyan-400" />
                ) : (
                  <span className="text-gray-600">×</span>
                )}
              </div>
            </motion.button>
          ))}
        </div>
      </div>

      {/* Layer Details */}
      <div className="flex-1 space-y-6 overflow-y-auto custom-scrollbar pr-4">
        {selectedLayerData && (
          <>
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel p-6 rounded-xl border border-white/5"
            >
              <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
                <Layers className="text-cyan-400" />
                {selectedLayerData.name}
              </h2>
              <p className="text-gray-400 text-sm">
                Status: {selectedLayerData.active ? (
                  <span className="text-emerald-400 font-semibold">Active</span>
                ) : (
                  <span className="text-gray-500 font-semibold">Skipped</span>
                )}
              </p>
            </motion.div>

            {/* Attention Heads */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-panel p-6 rounded-xl border border-white/5"
            >
              <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Eye size={18} className="text-indigo-400" />
                Attention Heads
              </h3>
              <div className="grid grid-cols-6 gap-2">
                {Array.from({ length: selectedLayerData.headCount }).map((_, i) => (
                  <motion.div
                    key={i}
                    whileHover={{ scale: 1.1 }}
                    className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold cursor-pointer transition-all ${
                      i < selectedLayerData.activeHeads
                        ? 'bg-cyan-500/30 border border-cyan-500/60 text-cyan-300'
                        : 'bg-gray-800/30 border border-gray-700/60 text-gray-500'
                    }`}
                  >
                    {i + 1}
                  </motion.div>
                ))}
              </div>
              <div className="mt-4 text-sm text-gray-400">
                <span className="font-semibold text-cyan-400">{selectedLayerData.activeHeads}</span> / {selectedLayerData.headCount} heads active
              </div>
            </motion.div>

            {/* Computation */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="glass-panel p-6 rounded-xl border border-white/5"
            >
              <h3 className="text-lg font-bold text-white mb-4">Computation</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span className="text-gray-400">FLOPs</span>
                    <span className="text-cyan-400 font-bold">{selectedLayerData.flops}M</span>
                  </div>
                  <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(selectedLayerData.flops / 1000) * 100}%` }}
                      transition={{ duration: 0.8 }}
                      className="h-full bg-gradient-to-r from-indigo-500 to-cyan-500"
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
};

export default LayerInspectorView;
