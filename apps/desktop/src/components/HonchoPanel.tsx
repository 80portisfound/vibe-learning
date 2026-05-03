import { Database, RefreshCw } from 'lucide-react';
import type { HonchoStatus } from '../api';

export function HonchoPanel({
  status,
  onRefresh,
}: {
  status: HonchoStatus | null;
  onRefresh: () => Promise<void>;
}) {
  return (
    <section className="honcho-panel">
      <section className="panel honcho-summary">
        <div className="panel-title"><Database size={16} /> Honcho Storage</div>
        <div className="mono">{status?.path ?? 'Unknown'}</div>
        <div className="metric-grid">
          <Metric label="Status" value={status?.exists ? 'linked' : 'missing'} />
          <Metric label="Files" value={String(status?.file_count ?? 0)} />
          <Metric label="Size" value={`${status?.total_size ?? 0} bytes`} />
        </div>
        <div className="dashboard-field">
          <span>App database</span>
          <p>{status?.app_database_path ?? 'Unknown'}</p>
        </div>
        <button type="button" className="refresh-button" onClick={onRefresh}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </section>

      <section className="panel honcho-recent">
        <div className="panel-title">Recent Honcho Files</div>
        {status?.recent_files.length ? (
          <ul className="activity-list">
            {status.recent_files.map((file) => (
              <li className="activity-item" key={file.path}>
                <span>{new Date(file.modified_at * 1000).toLocaleString()}</span>
                {file.path} · {file.size} bytes
              </li>
            ))}
          </ul>
        ) : (
          <div className="muted">No Honcho files found yet.</div>
        )}
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
