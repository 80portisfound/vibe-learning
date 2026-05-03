import React from 'react';
import { Save } from 'lucide-react';
import type { SkillFile } from '../api';

export function SkillsPanel({
  files,
  selectedPath,
  content,
  isSaving,
  onSelectFile,
  onContentChange,
  onSave,
}: {
  files: SkillFile[];
  selectedPath: string;
  content: string;
  isSaving: boolean;
  onSelectFile: (path: string) => void;
  onContentChange: (content: string) => void;
  onSave: () => Promise<void>;
}) {
  return (
    <section className="skills-workbench">
      <div className="skills-list panel">
        <div className="panel-title">Skills</div>
        {files.length === 0 && <div className="muted">No editable skill files found.</div>}
        {files.map((file) => (
          <button
            type="button"
            key={file.path}
            className={`skills-row ${file.path === selectedPath ? 'active' : ''}`}
            onClick={() => onSelectFile(file.path)}
          >
            <strong>{file.path}</strong>
            <span>{file.size} bytes</span>
          </button>
        ))}
      </div>
      <section className="skills-editor panel">
        <div className="panel-title">{selectedPath || 'Select skill file'}</div>
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
