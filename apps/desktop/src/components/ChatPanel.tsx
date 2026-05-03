import React from 'react';
import { MessageSquare, SendHorizontal, StopCircle } from 'lucide-react';

export type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
};

export function ChatPanel({
  messages,
  isSending,
  disabledReason,
  onSend,
  onCancel,
}: {
  messages: ChatMessage[];
  isSending: boolean;
  disabledReason?: string;
  onSend: (content: string) => Promise<void>;
  onCancel: () => void;
}) {
  const [draft, setDraft] = React.useState('');

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || isSending || disabledReason) return;
    setDraft('');
    await onSend(content);
  }

  return (
    <section className="chat">
      <div className="chat-title-row">
        <div className="panel-title"><MessageSquare size={16} /> Hermes Chat</div>
        {isSending && (
          <button type="button" className="cancel-run-button" onClick={onCancel}>
            <StopCircle size={16} />
            Cancel
          </button>
        )}
      </div>
      <div className="chat-log">
        {messages.map((message) => (
          <div className={`message ${message.role}`} key={message.id}>
            {message.content}
          </div>
        ))}
        {isSending && <div className="message assistant muted-message">Hermes is running...</div>}
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          placeholder={disabledReason || 'Message Hermes...'}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={isSending || Boolean(disabledReason)}
        />
        <button type="submit" disabled={isSending || Boolean(disabledReason) || draft.trim().length === 0} title="Send message">
          <SendHorizontal size={18} />
        </button>
      </form>
    </section>
  );
}
