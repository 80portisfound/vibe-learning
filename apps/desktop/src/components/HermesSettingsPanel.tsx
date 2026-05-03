import React from 'react';
import { CheckCircle2, RefreshCw, Save, XCircle } from 'lucide-react';
import type { HermesHomeStatus } from '../api';

export function HermesSettingsPanel({
  status,
  configContent,
  isSaving,
  isRestarting,
  onConfigChange,
  onSaveConfig,
  onApplyHermesHome,
}: {
  status: HermesHomeStatus | null;
  configContent: string;
  isSaving: boolean;
  isRestarting: boolean;
  onConfigChange: (content: string) => void;
  onSaveConfig: () => Promise<void>;
  onApplyHermesHome: (path: string, bootstrap: boolean) => Promise<void>;
}) {
  const pathEntries = Object.entries(status?.paths ?? {});
  const [homePath, setHomePath] = React.useState(status?.path ?? '');
  const [bootstrap, setBootstrap] = React.useState(false);

  React.useEffect(() => {
    setHomePath(status?.path ?? '');
  }, [status?.path]);

  async function submitHome(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPath = homePath.trim();
    if (!nextPath || isRestarting) return;
    await onApplyHermesHome(nextPath, bootstrap);
  }

  return (
    <section className="hermes-settings">
      <section className="panel hermes-paths">
        <div className="panel-title">Hermes Home</div>
        <form className="hermes-home-form" onSubmit={submitHome}>
          <label>
            Path
            <input value={homePath} onChange={(event) => setHomePath(event.target.value)} />
          </label>
          <label className="inline-toggle">
            <input
              type="checkbox"
              checked={bootstrap}
              onChange={(event) => setBootstrap(event.target.checked)}
            />
            Create missing structure
          </label>
          <button type="submit" disabled={!homePath.trim() || isRestarting}>
            <RefreshCw size={16} />
            {isRestarting ? 'Restarting...' : 'Apply & restart'}
          </button>
        </form>
        <div className="path-status-list">
          {pathEntries.map(([name, item]) => (
            <div className="path-status-row" key={name}>
              {item.exists ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
              <div>
                <strong>{name}</strong>
                <span>{item.kind} · {item.path}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="panel hermes-config-editor">
        <div className="panel-title">config.yaml</div>
        <textarea value={configContent} onChange={(event) => onConfigChange(event.target.value)} />
        <button type="button" onClick={onSaveConfig} disabled={isSaving}>
          <Save size={16} />
          {isSaving ? 'Saving...' : 'Save with snapshot'}
        </button>
      </section>
    </section>
  );
}
