const { contextBridge, ipcRenderer } = require('electron');

/**
 * Secure IPC bridge between React and Electron main process
 * Exposes only specific APIs to the renderer process
 */

contextBridge.exposeInMainWorld('ariaAPI', {
  // Query endpoint
  query: (queryText, mode = 'adaptive') =>
    ipcRenderer.invoke('query', { query: queryText, mode }),

  // Analysis endpoint
  analyze: (queryText) =>
    ipcRenderer.invoke('analyze', { query: queryText }),

  // Health check
  health: () =>
    ipcRenderer.invoke('health'),

  // Metrics
  metrics: () =>
    ipcRenderer.invoke('metrics'),

  // Settings
  getSettings: () =>
    ipcRenderer.invoke('settings:get'),

  updateSettings: (settings) =>
    ipcRenderer.invoke('settings:update', settings),

  // History
  getHistory: () =>
    ipcRenderer.invoke('history:get'),
    
  saveHistory: (history) =>
    ipcRenderer.invoke('history:save', history),

  clearHistory: () =>
    ipcRenderer.invoke('history:clear'),
});

console.log('[Preload] Electron API bridge loaded');
