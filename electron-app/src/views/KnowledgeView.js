import React from 'react';
import { Database, UploadCloud, FileText, Search, Plus, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';

const KnowledgeView = ({ showToast }) => {
  const documents = [
    { name: 'System_Architecture_v2.pdf', size: '2.4 MB', date: 'Today, 2:40 PM', type: 'PDF' },
    { name: 'API_Documentation.md', size: '14 KB', date: 'Yesterday', type: 'Markdown' },
    { name: 'user_onboarding.docx', size: '1.1 MB', date: 'Mar 24', type: 'Word' }
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto h-full overflow-y-auto">
      <div className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-white mb-2 flex items-center gap-3">
            <Database className="text-cyan-400" />
            Knowledge Base
          </h2>
          <p className="text-gray-400">Upload documents to enable Retrieval-Augmented Generation (RAG).</p>
        </div>
        
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={16} />
            <input 
              type="text" 
              placeholder="Search index..." 
              className="bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:border-cyan-500/50 outline-none w-64 transition-colors"
            />
          </div>
        </div>
      </div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
        onClick={() => showToast('Indexing engine initializing...', 'info')}
        className="glass-panel border-2 border-dashed border-cyan-500/30 hover:border-cyan-500/60 rounded-2xl p-12 text-center cursor-pointer transition-colors duration-300 group bg-[#0A0D14]/50 mb-8 relative overflow-hidden"
      >
        <div className="absolute inset-0 bg-cyan-500/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
        <div className="w-16 h-16 rounded-full bg-cyan-500/10 flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-transform">
          <UploadCloud className="text-cyan-400" size={32} />
        </div>
        <h3 className="text-lg font-bold text-gray-200 mb-2">Drag and drop files to index</h3>
        <p className="text-sm text-gray-500 mb-6">Supports PDF, TXT, MD, CSV, DOCX (Max 50MB per file)</p>
        <button className="px-6 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium transition-colors text-gray-300">
          Browse Files
        </button>
      </motion.div>

      <div>
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4">Vectorized Documents</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {documents.map((doc, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.1 }}
              className="glass-panel p-5 rounded-xl border border-white/5 hover:border-white/10 flex flex-col gap-3 group"
            >
              <div className="flex items-start justify-between">
                <div className="p-2.5 bg-indigo-500/10 rounded-lg text-indigo-400">
                  <FileText size={20} />
                </div>
                <button className="text-gray-600 hover:text-rose-400 transition-colors opacity-0 group-hover:opacity-100">
                  <Trash2 size={14} />
                </button>
              </div>
              <div>
                <h4 className="font-semibold text-gray-200 text-sm truncate" title={doc.name}>{doc.name}</h4>
                <div className="flex items-center gap-2 text-xs mt-1 font-mono text-gray-500">
                  <span>{doc.type}</span>
                  <span>•</span>
                  <span>{doc.size}</span>
                </div>
              </div>
              <div className="text-[10px] text-gray-600 mt-2 flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]"></div>
                Indexed {doc.date}
              </div>
            </motion.div>
          ))}
          
          {/* Add New Placeholder Node */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="border border-dashed border-white/10 rounded-xl p-5 flex flex-col items-center justify-center text-gray-500 hover:text-gray-300 hover:border-white/30 transition-colors cursor-pointer min-h-[140px]"
            onClick={() => showToast('Select source connection', 'info')}
          >
            <Plus size={24} className="mb-2" />
            <span className="text-sm font-medium">Add Web Source</span>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeView;
