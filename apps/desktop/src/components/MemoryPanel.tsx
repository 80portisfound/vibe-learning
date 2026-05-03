import React from 'react';
import { Save } from 'lucide-react';
import type { MemoryFile } from '../api';

export function MemoryPanel({
  files,
  selectedPath,
  content,
  isSaving,
  onSelectFile,
  onContentChange,
  onSave,
}: {
  files: MemoryFile[];
  selectedPath: string;
  content: string;
  isSaving: boolean;
  onSelectFile: (path: string) => void;
  onContentChange: (content: string) => void;
  onSave: () => Promise<void>;
}) {
  return (
    <section className="memory-workbench">
      <div className="memory-list panel">
        <div className="panel-title">Memory</div>
        {files.length === 0 && <div className="muted">No memory files found.</div>}
        {files.map((file) => (
          <button
            type="button"
            key={file.path}
            className={`memory-row ${file.path === selectedPath ? 'active' : ''}`}
            onClick={() => onSelectFile(file.path)}
          >
            <strong>{file.path}</strong>
            <span>{file.size} bytes</span>
          </button>
        ))}
      </div>
      <section className="memory-editor panel">
        <div className="panel-title">{selectedPath || 'Select memory file'}</div>
        <textarea
          value={content}
          onChange={(event) => onContentChange(event.target.value)}
          disabled={!selectedPath}
        />
        <button type="button" onClick={onSave} disabled={!selectedPath || isSaving}>
          <Save size={16} />
          {isSaving ? 'Saving...' : 'Save with snapshot'}
        </button>
      </section>
    </section>
  );
}
