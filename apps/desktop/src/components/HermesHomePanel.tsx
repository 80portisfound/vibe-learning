import { HardDrive } from 'lucide-react';
import type { HealthResponse } from '../api';

export function HermesHomePanel({ health }: { health: HealthResponse | null }) {
  return (
    <section className="panel">
      <div className="panel-title"><HardDrive size={16} /> Hermes Home</div>
      <div className="mono">{health?.hermes_home.path ?? 'Not connected'}</div>
      <div className="muted">Linked mode uses local Hermes state directly.</div>
    </section>
  );
}
