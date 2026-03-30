const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const axios = require('axios');

// Check if in development mode
// In dev, we use npm start which sets NODE_ENV=development, or if running from npm run electron-dev
const isDev = process.env.NODE_ENV === 'development' || 
              process.env.NODE_ENV !== 'production' || 
              process.argv.some(arg => arg === '--dev') ||
              process.argv.some(arg => arg.includes('electron'));
let Store;

let mainWindow;
let backendProcess;
let store;

const BACKEND_URL = 'http://127.0.0.1:8000';
const BACKEND_PORT = 8000;

// Initialize electron-store asynchronously
async function initStore() {
  if (!Store) {
    Store = (await import('electron-store')).default;
    store = new Store({
      defaults: {
        settings: {
          theme: 'dark',
          fontSize: 'medium',
          maxTokens: 2048,
          model: 'qwen2.5-3b'
        },
        chatHistory: []
      }
    });
  }
}


/**
 * Launch FastAPI backend server
 */
function launchBackendServer() {
  return new Promise((resolve, reject) => {
    console.log('[Electron] Checking backend server...');
    
    // First check if backend is already running
    let retries = 0;
    const maxRetries = 5; // Try 5 times quickly
    
    const checkInterval = setInterval(async () => {
      try {
        const isHealthy = await checkBackendHealth();
        if (isHealthy) {
          clearInterval(checkInterval);
          console.log('[Electron] Backend already running');
          resolve();
          return;
        }
      } catch (err) {
        // Backend not running yet
      }
      
      retries++;
      if (retries >= maxRetries) {
        clearInterval(checkInterval);
        console.log('[Electron] Backend not found, attempting to launch...');
        
        // Try to launch backend
        const launchScript = path.join(__dirname, '..', 'scripts', 'launch-backend.sh');
        
        backendProcess = spawn('bash', [launchScript]);
        
        backendProcess.stdout.on('data', (data) => {
          console.log(`[Backend] ${data.toString()}`);
        });
        
        backendProcess.stderr.on('data', (data) => {
          console.warn(`[Backend Error] ${data.toString()}`);
        });
        
        backendProcess.on('error', (err) => {
          console.error('Failed to start backend:', err);
          reject(err);
        });
        
        // Poll health check until backend is ready
        let launchRetries = 0;
        const maxLaunchRetries = 20;
        
        const launchCheckInterval = setInterval(async () => {
          try {
            const isHealthy = await checkBackendHealth();
            if (isHealthy) {
              clearInterval(launchCheckInterval);
              console.log('[Electron] Backend launched successfully');
              resolve();
            }
          } catch (err) {
            launchRetries++;
            console.log(`[Electron] Waiting for backend... (${launchRetries}/${maxLaunchRetries})`);
            if (launchRetries >= maxLaunchRetries) {
              clearInterval(launchCheckInterval);
              console.error('[Electron] Backend startup timeout');
              resolve(); // Start anyway
            }
          }
        }, 500);
      }
    }, 500);
  });
}

/**
 * Check if backend is healthy
 */
async function checkBackendHealth() {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/v1/health`, { timeout: 5000 });
    return response.status === 200;
  } catch (error) {
    console.warn('[Electron] Backend not ready yet:', error.message);
    throw error;
  }
}

/**
 * Create main window
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      sandbox: true,
    },
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
  });

  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '..', 'build', 'index.html')}`;

  mainWindow.loadURL(startUrl);

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  return mainWindow;
}

/**
 * App event handlers
 */
app.on('ready', async () => {
  try {
    await initStore();
    // Launch backend first
    await launchBackendServer();
    
    // Then create window
    createWindow();
    
    // Create menu
    createMenu();
  } catch (error) {
    console.error('[Electron] Failed to start app:', error);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  // Cleanup backend process
  if (backendProcess) {
    console.log('[Electron] Killing backend process');
    backendProcess.kill();
  }
  
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

/**
 * Create application menu
 */
function createMenu() {
  const template = [
    {
      label: 'ARIA',
      submenu: [
        {
          label: 'About ARIA',
          click: () => {
            // Show about dialog
          },
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            app.quit();
          },
        },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

/**
 * IPC Handlers for React → Backend communication
 */

// Query endpoint
ipcMain.handle('query', async (event, { query, mode = 'adaptive' }) => {
  try {
    const payload = {
      query: query,
      mode: 'adaptive',
      execution_mode: mode === 'fast' ? 'cascade' : mode === 'deep' ? 'standard' : 'dynamic_layers'
    };
    
    const response = await axios.post(`${BACKEND_URL}/api/v1/query`, payload);
    return { success: true, data: response.data };
  } catch (error) {
    console.error('[IPC] Query error:', error.message);
    return {
      success: false,
      error: error.response?.data?.detail || error.message,
    };
  }
});

// Analysis endpoint
ipcMain.handle('analyze', async (event, { query }) => {
  try {
    const response = await axios.post(`${BACKEND_URL}/api/v1/analyze`, {
      query,
    });
    return { success: true, data: response.data };
  } catch (error) {
    console.error('[IPC] Analysis error:', error.message);
    return {
      success: false,
      error: error.response?.data?.detail || error.message,
    };
  }
});

// Health check
ipcMain.handle('health', async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/health`);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Metrics endpoint
ipcMain.handle('metrics', async () => {
  try {
    const response = await axios.get(`${BACKEND_URL}/api/v1/metrics`);
    return { success: true, data: response.data };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Settings get/update
ipcMain.handle('settings:get', async () => {
    await initStore();
    return { success: true, data: store.get('settings') };
});

ipcMain.handle('settings:update', async (event, settings) => {
    await initStore();
    store.set('settings', settings);
    return { success: true, data: settings };
});

// Chat History API
ipcMain.handle('history:get', async () => {
    await initStore();
    return { success: true, data: store.get('chatHistory') || [] };
});

ipcMain.handle('history:save', async (event, history) => {
    await initStore();
    store.set('chatHistory', history);
    return { success: true };
});

ipcMain.handle('history:clear', async () => {
    await initStore();
    store.set('chatHistory', []);
    return { success: true };
});

console.log('[Electron] App initialized');
