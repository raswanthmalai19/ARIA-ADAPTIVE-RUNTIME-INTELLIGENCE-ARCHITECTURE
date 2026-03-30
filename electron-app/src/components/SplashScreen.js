import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';

const SplashScreen = ({ isLoading }) => {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isLoading) return;
    
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev;
        return prev + Math.random() * 30;
      });
    }, 300);

    return () => clearInterval(interval);
  }, [isLoading]);

  if (!isLoading) return null;

  return (
    <motion.div
      initial={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-[#05050A] z-50 flex flex-col items-center justify-center"
    >
      {/* Animated Logo Container */}
      <motion.div
        animate={{ scale: [1, 1.05, 1] }}
        transition={{ duration: 2, repeat: Infinity }}
        className="mb-8"
      >
        <div className="w-32 h-32 rounded-2xl bg-gradient-to-br from-indigo-900/30 to-cyan-900/30 border border-indigo-500/20 flex items-center justify-center shadow-2xl relative overflow-hidden">
          <div className="absolute inset-0 bg-indigo-500/10 animate-pulse"></div>
          <img src="/aria-logo.png" alt="ARIA" className="w-24 h-24 object-contain" />
        </div>
      </motion.div>

      {/* Branding */}
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="text-3xl font-bold text-white mb-2 tracking-wider"
      >
        ARIA
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="text-xs text-cyan-400 uppercase tracking-widest mb-12 font-mono"
      >
        Adaptive Runtime Intelligence Architecture
      </motion.p>

      {/* Progress Bar */}
      <div className="w-64 h-1.5 bg-gray-900/50 rounded-full border border-white/5 overflow-hidden shadow-lg">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
          className="h-full bg-gradient-to-r from-indigo-500 via-cyan-500 to-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.6)]"
        />
      </div>

      {/* Status Text */}
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="mt-6 text-xs text-gray-500 font-mono"
      >
        {progress < 30 && 'Initializing models...'}
        {progress >= 30 && progress < 60 && 'Loading inference engine...'}
        {progress >= 60 && progress < 85 && 'Preparing GPU resources...'}
        {progress >= 85 && 'Starting dashboard...'}
      </motion.p>

      {/* Animated Dots */}
      <div className="flex gap-2 mt-6">
        {[0, 1, 2].map(i => (
          <motion.div
            key={i}
            animate={{ scale: [1, 1.3, 1] }}
            transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
            className="w-2 h-2 rounded-full bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.8)]"
          />
        ))}
      </div>
    </motion.div>
  );
};

export default SplashScreen;
