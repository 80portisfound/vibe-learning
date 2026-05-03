import React from 'react';
import { Archive, FolderPlus, GitMerge, RotateCcw, Save, Trash2 } from 'lucide-react';
import type { CodingSession, CodingSessionInput } from '../api';

export function SessionPanel({
  sessions,
  selectedSessionId,
  onSelectSession,
  onCreateSession,
  onUpdateSession,
  onDeduplicateSessions,
  deduplicateSummary,
  isRuntimeBusy,
  showArchived,
  onShowArchivedChange,
  onArchiveSession,
  onRestoreSession,
  onDeleteSession,
}: {
  sessions: CodingSession[];
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  onCreateSession: (input: CodingSessionInput) => Promise<void>;
  onUpdateSession: (sessionId: string, input: Partial<CodingSessionInput>) => Promise<void>;
  onDeduplicateSessions: () => Promise<void>;
  deduplicateSummary: string;
  isRuntimeBusy: boolean;
  showArchived: boolean;
  onShowArchivedChange: (showArchived: boolean) => void;
  onArchiveSession: (sessionId: string) => Promise<void>;
  onRestoreSession: (sessionId: string) => Promise<void>;
  onDeleteSession: (sessionId: string) => Promise<void>;
}) {
  const selectedSession = sessions.find((session) => session.id === selectedSessionId) ?? null;
  const [title, setTitle] = React.useState(selectedSession?.title ?? '');
  const [goal, setGoal] = React.useState(selectedSession?.goal ?? '');
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    setTitle(selectedSession?.title ?? '');
    setGoal(selectedSession?.goal ?? '');
  }, [selectedSession]);

  async function createNewSession() {
    await onCreateSession({ title: 'New vibe session', goal: '' });
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSession || !title.trim() || isSaving) return;
    setIsSaving(true);
    try {
      await onUpdateSession(selectedSession.id, { title: title.trim(), goal: goal.trim() });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="session-panel panel">
      <div className="panel-title">Sessions</div>
      <div className="session-toolbar">
        <button type="button" className="new-session-button" onClick={createNewSession} disabled={isRuntimeBusy}>
          <FolderPlus size={16} />
          New session
        </button>
        <button type="button" className="dedupe-session-button" onClick={onDeduplicateSessions} disabled={isRuntimeBusy}>
          <GitMerge size={16} />
          Clean duplicates
        </button>
        <label className="inline-toggle">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => onShowArchivedChange(event.target.checked)}
          />
          Show archived
        </label>
        {deduplicateSummary && <div className="cleanup-summary">{deduplicateSummary}</div>}
      </div>
      <div className="session-list">
        {sessions.map((session) => (
          <button
            type="button"
            className={`session-row ${session.id === selectedSessionId ? 'active' : ''}`}
            key={session.id}
            onClick={() => onSelectSession(session.id)}
            disabled={isRuntimeBusy}
          >
            <strong>{session.title}</strong>
            <span>{session.goal || 'No goal set'}</span>
            {session.archived_at && <small>Archived</small>}
          </button>
        ))}
      </div>
      <form className="session-editor" onSubmit={submit}>
        <label>
          Title
          <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={!selectedSession || isRuntimeBusy} />
        </label>
        <label>
          Goal
          <textarea value={goal} onChange={(event) => setGoal(event.target.value)} disabled={!selectedSession || isRuntimeBusy} />
        </label>
        <div className="editor-actions">
          <button type="submit" disabled={!selectedSession || !title.trim() || isSaving || isRuntimeBusy || Boolean(selectedSession.archived_at)}>
            <Save size={16} />
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          {selectedSession?.archived_at ? (
            <>
              <button className="restore-button" type="button" onClick={() => onRestoreSession(selectedSession.id)} disabled={isRuntimeBusy}>
                <RotateCcw size={16} />
                Restore
              </button>
              <button className="danger-button" type="button" onClick={() => onDeleteSession(selectedSession.id)} disabled={isRuntimeBusy}>
                <Trash2 size={16} />
                Delete
              </button>
            </>
          ) : selectedSession ? (
            <>
              <button className="archive-button" type="button" onClick={() => onArchiveSession(selectedSession.id)} disabled={isRuntimeBusy}>
                <Archive size={16} />
                Archive
              </button>
              <button className="danger-button" type="button" onClick={() => onDeleteSession(selectedSession.id)} disabled={isRuntimeBusy}>
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
