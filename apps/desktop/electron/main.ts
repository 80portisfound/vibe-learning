import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createBackendManager, resolveApiDir, resolveForkMetadataPath, waitForBackend } from './backendProcess.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const packagedResourcesPath = app.isPackaged ? process.resourcesPath : undefined;
const backend = createBackendManager({
  apiDir: resolveApiDir(__dirname, packagedResourcesPath),
  env: {
    ...process.env,
    ...(packagedResourcesPath
      ? {
          HERMES_VIBE_FORK_METADATA_PATH: resolveForkMetadataPath(packagedResourcesPath),
          HERMES_VIBE_PYTHON_RUNTIME_DIR: path.join(packagedResourcesPath, 'python-runtime'),
        }
      : {}),
  },
});

ipcMain.handle('backend:get-url', () => backend.url);
ipcMain.handle('backend:get-status', () => backend.status());
ipcMain.handle('backend:restart', async (_event, options?: { hermesHome?: string; bootstrapHermesHome?: boolean }) => {
  backend.stop();
  const hermesHome = options?.hermesHome?.trim();
  if (hermesHome) {
    backend.setHermesHome(hermesHome, Boolean(options?.bootstrapHermesHome));
  }
  await backend.start();
  try {
    await waitForBackend(backend.url);
  } catch (error) {
    console.error('[api] Backend restart readiness check failed', error);
  }
  return backend.status();
});

function createWindow() {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1100,
    minHeight: 760,
    backgroundColor: '#101214',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    void window.loadURL(devUrl);
  } else {
    void window.loadFile(path.join(__dirname, '../dist/index.html'));
  }
}

app.whenReady().then(async () => {
  await backend.start();
  try {
    await waitForBackend(backend.url);
  } catch (error) {
    console.error('[api] Backend readiness check failed', error);
  }
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  backend.stop();
});
