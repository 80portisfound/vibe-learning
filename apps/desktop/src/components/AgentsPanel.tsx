import React from 'react';
import { Archive, Bot, RotateCcw, Save, Trash2 } from 'lucide-react';
import type { AgentProfile, AgentProfileInput, ModelProvider } from '../api';

const emptyForm: AgentProfileInput = {
  name: '',
  role: '',
  system_prompt: '',
  provider: null,
  model: null,
  skills: [],
};

export function AgentsPanel({
  agents,
  providers,
  selectedAgentId,
  onSelectAgent,
  onCreateAgent,
  onUpdateAgent,
  showArchived,
  isRuntimeBusy,
  onShowArchivedChange,
  onArchiveAgent,
  onRestoreAgent,
  onDeleteAgent,
}: {
  agents: AgentProfile[];
  providers: ModelProvider[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  onCreateAgent: (input: AgentProfileInput) => Promise<void>;
  onUpdateAgent: (agentId: string, input: Partial<AgentProfileInput>) => Promise<void>;
  showArchived: boolean;
  isRuntimeBusy: boolean;
  onShowArchivedChange: (showArchived: boolean) => void;
  onArchiveAgent: (agentId: string) => Promise<void>;
  onRestoreAgent: (agentId: string) => Promise<void>;
  onDeleteAgent: (agentId: string) => Promise<void>;
}) {
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? null;
  const [draft, setDraft] = React.useState<AgentProfileInput>(emptyForm);
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!selectedAgent) {
      setDraft(emptyForm);
      return;
    }
    setDraft({
      name: selectedAgent.name,
      role: selectedAgent.role,
      system_prompt: selectedAgent.system_prompt,
      provider: selectedAgent.provider,
      model: selectedAgent.model,
      skills: selectedAgent.skills,
    });
  }, [selectedAgent]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.name.trim() || isSaving) return;
    setIsSaving(true);
    try {
      if (selectedAgent) {
        await onUpdateAgent(selectedAgent.id, normalizeDraft(draft));
      } else {
        await onCreateAgent(normalizeDraft(draft));
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="agent-workbench">
      <div className="agent-list panel">
        <div className="panel-title"><Bot size={16} /> Agents</div>
        <label className="inline-toggle">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => onShowArchivedChange(event.target.checked)}
            disabled={isRuntimeBusy}
          />
          Show archived
        </label>
        <button
          type="button"
          className={`agent-row ${selectedAgentId ? '' : 'active'}`}
          onClick={() => onSelectAgent('')}
          disabled={isRuntimeBusy}
        >
          <strong>New agent</strong>
          <span>Create a Hermes profile</span>
        </button>
        {agents.map((agent) => (
          <button
            type="button"
            key={agent.id}
            className={`agent-row ${agent.id === selectedAgentId ? 'active' : ''}`}
            onClick={() => onSelectAgent(agent.id)}
            disabled={isRuntimeBusy}
          >
            <strong>{agent.name}</strong>
            <span>{agent.role || 'No role yet'}</span>
            {agent.archived_at && <small>Archived</small>}
          </button>
        ))}
      </div>

      <form className="agent-editor panel" onSubmit={submit}>
        <div className="panel-title">{selectedAgent ? 'Edit Agent' : 'Create Agent'}</div>
        <label>
          Name
          <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
        </label>
        <label>
          Role
          <input value={draft.role} onChange={(event) => setDraft({ ...draft, role: event.target.value })} />
        </label>
        <label>
          Model
          <select
            className="select"
            value={modelValue(draft)}
            onChange={(event) => {
              const [provider, model] = event.target.value.split(':');
              setDraft({ ...draft, provider: provider || null, model: model || null });
            }}
          >
            <option value="">Use chat default</option>
            {providers.map((provider) => provider.models.map((model) => (
              <option value={`${provider.id}:${model.id}`} key={`${provider.id}:${model.id}`}>
                {provider.display_name} / {model.display_name}
              </option>
            )))}
          </select>
        </label>
        <label>
          Skills
          <input
            value={draft.skills.join(', ')}
            onChange={(event) => setDraft({ ...draft, skills: splitSkills(event.target.value) })}
          />
        </label>
        <label>
          System prompt
          <textarea
            value={draft.system_prompt}
            onChange={(event) => setDraft({ ...draft, system_prompt: event.target.value })}
          />
        </label>
        <div className="editor-actions">
          <button
            className="save-agent"
            type="submit"
            disabled={isSaving || isRuntimeBusy || draft.name.trim().length === 0 || Boolean(selectedAgent?.archived_at)}
          >
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Save agent'}
          </button>
          {selectedAgent?.archived_at ? (
            <>
              <button className="restore-button" type="button" onClick={() => onRestoreAgent(selectedAgent.id)} disabled={isRuntimeBusy}>
                <RotateCcw size={16} />
                Restore
              </button>
              <button className="danger-button" type="button" onClick={() => onDeleteAgent(selectedAgent.id)} disabled={isRuntimeBusy}>
                <Trash2 size={16} />
                Delete
              </button>
            </>
          ) : selectedAgent ? (
            <>
              <button className="archive-button" type="button" onClick={() => onArchiveAgent(selectedAgent.id)} disabled={isRuntimeBusy}>
                <Archive size={16} />
                Archive
              </button>
              <button className="danger-button" type="button" onClick={() => onDeleteAgent(selectedAgent.id)} disabled={isRuntimeBusy}>
                <Trash2 size={16} />
                Delete
              </button>
            </>
          ) : null}
        </div>
      </form>
    </section>
  );
}

function modelValue(draft: AgentProfileInput): string {
  return draft.provider && draft.model ? `${draft.provider}:${draft.model}` : '';
}

function splitSkills(value: string): string[] {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function normalizeDraft(draft: AgentProfileInput): AgentProfileInput {
  return {
    ...draft,
    name: draft.name.trim(),
    role: draft.role.trim(),
    system_prompt: draft.system_prompt.trim(),
    provider: draft.provider || null,
    model: draft.model || null,
    skills: draft.skills.map((skill) => skill.trim()).filter(Boolean),
  };
}
