# Hermes Vibe Desktop App Design

## Summary

Build a desktop-first app that hard-forks Hermes Agent and gives it a GUI for real-time vibe coding. The app lets the user chat with Hermes, create and edit agents, choose models, inspect memory and skills, and watch a live dashboard that explains coding context, implementation progress, learning concepts, and debugging signals.

The first implementation target is an Electron desktop app with a React renderer and a Python backend that embeds the hard-forked Hermes runtime.

## Goals

- Run Hermes Agent as the app's core coding/chat runtime.
- Provide a desktop GUI for Hermes chat, agent editing, model selection, memory, skills, honcho state, and workspace context.
- Link directly to the user's local Hermes home, normally `~/.hermes`, so the app and local Hermes share config, memory, skills, sessions, and honcho state.
- Stream Hermes runtime activity into a live dashboard.
- Help the user understand AI-generated code through concept notes, implementation summaries, decision traces, before/after explanations, and error learning logs.

## Non-Goals

- Do not build a cloud service in the MVP.
- Do not support multi-user collaboration in the MVP.
- Do not mirror or bidirectionally sync a separate app copy of Hermes state in the MVP.
- Do not include a question generator in the MVP.
- Do not preserve strict upstream Hermes compatibility at the expense of the app experience.

## Product Shape

The app is a local desktop companion for vibe coding with Hermes. It is a coding cockpit, not a generic chatbot. The user can open a workspace, pick or edit an agent, choose a model, chat with Hermes, and see a right-side live context panel that explains what is happening.

Primary screens:

- Chat: Hermes conversation with streaming output, tool activity, current agent, model, workspace context, important files, test/debug status, and learning concepts.
- Agents: create and edit agent profiles, tools, MCP servers, memory scope, skill scope, and default model.
- Dashboard: implementation status, debug timeline, learning concepts, decision traces, before/after explanations, and next actions.
- Memory: structured editor for Hermes memory files.
- Skills: browse, edit, and manage Hermes skills.
- Hermes Home: inspect linked local Hermes path, backups, snapshots, and change log.
- Settings: model providers, API keys, app preferences, workspace defaults.

## Architecture

Use Electron for the desktop shell, React for the UI, and Python for the backend/runtime host.

```text
Electron Main
- app lifecycle
- window management
- local backend process launch
- secure IPC bridge

React Renderer
- Hermes chat
- agent/profile editor
- model selector
- memory/skills editor
- honcho/user model view
- live dashboard
- workspace/debug panels

Python Backend
- FastAPI server
- hard-forked Hermes core
- session manager
- model/provider registry
- event bus
- dashboard engine
- workspace/code indexer
- knowledge store

Hermes Runtime
- AIAgent
- tools/MCP
- skills
- memory
- honcho user/project modeling
- subagents
- model providers

Storage
- linked local Hermes home: ~/.hermes by default
- SQLite app metadata database
- dashboard event cache
- code/workspace index
- concept notes
- ChromaDB embeddings/vector index
- backup/snapshot store
```

Hermes is the runtime. The dashboard is a projection of Hermes runtime events plus workspace analysis.

## Hermes Home Link Strategy

The app uses the user's local Hermes state directly instead of maintaining a separate mirrored copy.

Default linked path:

```text
~/.hermes
```

Expected linked state:

```text
~/.hermes/config.yaml
~/.hermes/memories/*
~/.hermes/skills/*
~/.hermes/sessions/*
~/.hermes/honcho/*
```

Safety rules:

- Detect and validate the Hermes home path on app startup.
- Take a snapshot before modifying config, memory, skills, or honcho state.
- Treat session logs as read-only by default.
- Use structured editors for normal config, memory, skill, and honcho edits.
- Put raw file editing behind an advanced mode.
- Record every app-initiated write in a change log.
- Provide rollback from snapshots.

## Model Selection

Model selection is available at both agent-profile and chat-session levels.

Agent default:

- provider
- model
- reasoning/options where supported
- temperature/options where supported
- context limits or known capability metadata

Session override:

- the user can temporarily switch model for the current chat
- subagents can use different models from the main agent

The dashboard must show which agent and model are currently handling each significant task.

## Core Data Model

Hermes source of truth:

- `config.yaml`
- memory files
- skill files
- session files
- honcho state

App source of truth:

- workspaces
- dashboard events
- UI sessions
- snapshots/backups
- code index
- concept notes
- implementation summaries
- vector embeddings
- model/provider metadata cache

Core app entities:

```text
AgentProfile
- id
- name
- description
- default_model
- tools
- mcp_servers
- memory_scope
- skill_scope

ChatSession
- id
- agent_id
- workspace_id
- model
- started_at
- status

Workspace
- id
- path
- name
- git_state
- indexed_at

DashboardEvent
- id
- session_id
- type
- payload
- source
- created_at

ConceptNote
- id
- session_id
- workspace_id
- concept
- short_summary
- detailed_note
- why_it_appeared
- related_code_files
- related_messages
- confusion_points
- experiment
- status
- created_at
- updated_at

ImplementationSummary
- id
- session_id
- workspace_id
- current_goal
- completed_changes
- in_progress_changes
- touched_files
- important_decisions
- blockers
- test_status
- next_steps
- generated_at

DecisionTrace
- id
- session_id
- user_request
- agent_reasoning_summary
- tool_calls
- code_changes
- resulting_files
- outcome

CodeChangeExplanation
- id
- session_id
- file_path
- before_summary
- after_summary
- behavior_change
- risk_level
- related_concepts

ErrorLearningLog
- id
- session_id
- error_message
- where_it_happened
- root_cause_summary
- fix_summary
- files_changed
- prevention_note
- related_concepts
```

## Event Schema

Hermes internal events must not be consumed directly by the React UI. The Python backend converts them into app-standard events.

Event flow:

```text
Hermes internal callback
-> HermesEventAdapter
-> DashboardEvent
-> WebSocket or SSE stream
-> Chat UI / Dashboard / Activity panel
-> App DB cache
```

Initial event types:

```text
chat.message.delta
chat.message.completed
agent.tool.started
agent.tool.completed
agent.subagent.started
agent.subagent.completed
workspace.file.changed
workspace.git.diff.updated
test.run.started
test.run.failed
test.run.passed
debug.error.detected
memory.updated
honcho.signal.observed
skill.used
concept.detected
concept.note.created
concept.note.updated
implementation.changed
implementation.summary.updated
implementation.milestone.detected
implementation.blocker.detected
implementation.file_grouped
implementation.test_status.updated
decision.trace.created
code.before_after.created
error.learning_log.created
summary.updated
```

## Learning And Debugging Features

The MVP includes five learning-oriented dashboard features.

### Concept Notes

Extract important concepts from Hermes chat, code diffs, tool calls, and error logs. Connect each concept to the code and session context where it appeared.

Dashboard output:

- today's concepts
- confusing concepts
- concepts linked to files
- 5-minute experiments
- links to previous related concepts

### Implementation Summary

Summarize what is being built and current implementation status.

Dashboard output:

- current goal
- completed changes
- in-progress changes
- touched files
- important decisions
- blockers
- test/debug status
- next actions

### Decision Trace

Explain why code exists by linking user requests, Hermes decisions, tool calls, code changes, and outcomes.

Dashboard output:

```text
request -> agent decision summary -> tool calls -> code changes -> result
```

### Before/After Explanation

For important file changes, show natural-language before/after behavior.

Dashboard output:

- before summary
- after summary
- behavior change
- why it matters
- risk level
- related concepts

### Error Learning Log

Turn errors into reusable learning records.

Dashboard output:

- error message
- where it happened
- root cause
- fix summary
- changed files
- prevention note
- related concepts

## Dashboard Analysis Pipeline

```text
Hermes events
-> Session Analyzer
-> Concept Extractor
-> Implementation Summarizer
-> Decision Tracer
-> Before/After Explainer
-> Error Learning Logger
-> Dashboard projections
-> App DB cache
```

The generated summaries are editable. Hermes drafts them, and the user can correct or pin important items.

## Safety And Error Handling

- Backend startup must fail visibly if the linked Hermes home is invalid.
- If the Python backend crashes, Electron shows recovery controls and logs.
- If a Hermes session fails, preserve the event log up to the failure.
- Writes to Hermes home require snapshots first.
- Raw edits require an advanced-mode confirmation.
- Destructive operations on memory, skills, config, or honcho state must be reversible through snapshots.
- Dashboard generation failures do not break chat.
- Chat failures do not corrupt Hermes state.

## Testing Strategy

Use focused tests around the runtime boundary and storage safety.

- Hermes home detection and validation tests.
- Snapshot-before-write tests for memory, skills, config, and honcho paths.
- Event adapter tests that convert Hermes events into app-standard events.
- Dashboard projection tests for implementation summaries, concept notes, decision traces, before/after explanations, and error learning logs.
- Model selection tests for profile defaults and session overrides.
- Electron smoke test that verifies the UI can start the backend and connect to the event stream.

## Implementation Defaults

- Backend framework: FastAPI.
- App metadata database: SQLite.
- Vector store: ChromaDB, matching the current project direction.
- Electron tooling: Electron + Vite + React.
- Hermes fork location: `packages/hermes`.
- Backend app location: `apps/api`.
- Renderer app location: `apps/desktop`.

The exact upstream Hermes commit is recorded when the hard fork is imported.
