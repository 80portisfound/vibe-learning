import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('hermesVibe', {
  platform: process.platform,
  getBackendUrl: () => ipcRenderer.invoke('backend:get-url') as Promise<string>,
  getBackendStatus: () => ipcRenderer.invoke('backend:get-status') as Promise<unknown>,
  restartBackend: (options?: { hermesHome?: string; bootstrapHermesHome?: boolean }) => (
    ipcRenderer.invoke('backend:restart', options) as Promise<unknown>
  ),
});
