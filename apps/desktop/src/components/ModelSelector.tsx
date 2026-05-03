import { Cpu } from 'lucide-react';
import type { ModelProvider } from '../api';

export function ModelSelector({
  providers,
  value,
  onChange,
}: {
  providers: ModelProvider[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <section className="panel">
      <div className="panel-title"><Cpu size={16} /> Model</div>
      <select className="select" value={value} onChange={(event) => onChange(event.target.value)}>
        {providers.flatMap((provider) =>
          provider.models.map((model) => (
            <option key={`${provider.id}:${model.id}`} value={`${provider.id}:${model.id}`}>
              {provider.display_name} / {model.display_name}
            </option>
          )),
        )}
      </select>
    </section>
  );
}
