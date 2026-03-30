import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import Toast from './components/Toast';
import SplashScreen from './components/SplashScreen';
import LoadingOverlay from './components/LoadingOverlay';
import ChatView from './views/ChatView';
import MetricsView from './views/MetricsView';
import ModelsView from './views/ModelsView';
import SettingsView from './views/SettingsView';
import KnowledgeView from './views/KnowledgeView';
import AnalysisView from './views/AnalysisView';
import LogsView from './views/LogsView';
import LayerInspectorView from './views/LayerInspectorView';
import { checkHealth } from './api';

const App = () => {
  const [activeView, setActiveView] = useState('chat');
  const [health, setHealth] = useState({ status: 'offline', details: null });
  const [toast, setToast] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);
  const [isLoading, setIsLoading] = useState(false);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
  };

  useEffect(() => {
    // Initial loading sequence
    const timer = setTimeout(() => setIsInitializing(false), 2000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    const pingHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth({ status: 'online', details: data });
      } catch (e) {
        setHealth({ status: 'offline', details: null });
      }
    };
    pingHealth();
    const interval = setInterval(pingHealth, 3000);
    return () => clearInterval(interval);
  }, []);

  const renderView = () => {
    switch(activeView) {
      case 'chat': return <ChatView showToast={showToast} />;
      case 'knowledge': return <KnowledgeView showToast={showToast} />;
      case 'metrics': return <MetricsView health={health} />;
      case 'models': return <ModelsView health={health} showToast={showToast} />;
      case 'analysis': return <AnalysisView showToast={showToast} />;
      case 'logs': return <LogsView showToast={showToast} />;
      case 'inspector': return <LayerInspectorView showToast={showToast} />;
      case 'settings': return <SettingsView showToast={showToast} />;
      default: return <ChatView showToast={showToast} />;
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#05050A] text-gray-100 overflow-hidden font-sans">
      <SplashScreen isLoading={isInitializing} />
      <LoadingOverlay isVisible={isLoading} message="Processing inference..." />
      <Sidebar activeView={activeView} setActiveView={setActiveView} />
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <TopBar health={health} activeView={activeView} />
        <main className="flex-1 overflow-hidden relative">
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/5 via-[#05050A] to-cyan-900/5 pointer-events-none" />
          {renderView()}
        </main>
        {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      </div>
    </div>
  );
};

export default App;
