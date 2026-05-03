import React from 'react';
import { createRoot, type Root } from 'react-dom/client';
import {
  createAgent,
  createSession,
  archiveAgent,
  archiveSession,
  deleteAgent,
  deleteSession,
  deduplicateSessions,
  getBackendStatus,
  getDashboard,
  getHealth,
  getHermesHomeStatus,
  getHonchoStatus,
  getModelProviders,
  listAgents,
  listMemoryFiles,
  listSessionEvents,
  listSessions,
  listSkillFiles,
  readMemoryFile,
  readHermesConfig,
  readSkillFile,
  restartBackend,
  restoreAgent,
  restoreSession,
  saveMemoryFile,
  saveHermesConfig,
  saveSkillFile,
  setHermesHome,
  streamMessage,
  updateAgent,
  updateSession,
  type AgentProfile,
  type AgentProfileInput,
  type BackendStatus,
  type CodingSession,
  type CodingSessionInput,
  type DashboardEvent,
  type DashboardProjection,
  type HealthResponse,
  type HermesHomeStatus,
  type HonchoStatus,
  type MemoryFile,
  type ModelProvider,
  type RuntimeActivityItem,
  type SkillFile,
} from './api';
import { AgentsPanel } from './components/AgentsPanel';
import { ChatPanel, type ChatMessage } from './components/ChatPanel';
import { DashboardPanel } from './components/DashboardPanel';
import { HermesHomePanel } from './components/HermesHomePanel';
import { HermesSettingsPanel } from './components/HermesSettingsPanel';
import { HonchoPanel } from './components/HonchoPanel';
import { MemoryPanel } from './components/MemoryPanel';
import { ModelSelector } from './components/ModelSelector';
import { SessionPanel } from './components/SessionPanel';
import { SkillsPanel } from './components/SkillsPanel';
import './styles.css';

type MainView = 'chat' | 'agents' | 'sessions' | 'memory' | 'skills' | 'hermes' | 'honcho';

function selectedModelFromProviders(providers: ModelProvider[]): string {
  const firstProvider = providers[0];
  const firstModel = firstProvider?.models[0];
  return firstProvider && firstModel ? `${firstProvider.id}:${firstModel.id}` : '';
}

function assistantMessagesFromEvents(events: DashboardEvent[]): ChatMessage[] {
  return events
    .filter((event) => event.type === 'chat.message.completed' || event.type === 'chat.message.user')
    .map((event) => ({
      id: event.id,
      role: event.type === 'chat.message.user' ? 'user' as const : 'assistant' as const,
      content: String(event.payload.content ?? ''),
    }))
    .filter((message) => message.content.length > 0);
}

function chatMessageFromEvent(event: DashboardEvent): ChatMessage | null {
  if (event.type === 'chat.message.user') {
    const content = String(event.payload.content ?? '');
    return content ? { id: event.id, role: 'user', content } : null;
  }
  if (event.type === 'chat.message.completed') {
    const content = String(event.payload.content ?? '');
    return content ? { id: event.id, role: 'assistant', content } : null;
  }
  if (event.type === 'agent.log.chunk' && event.payload.stream === 'stderr') {
    return {
      id: event.id,
      role: 'system',
      content: String(event.payload.content ?? '').trim(),
    };
  }
  if (event.type === 'agent.tool.started') {
    return {
      id: event.id,
      role: 'system',
      content: `Started ${String(event.payload.tool ?? 'Hermes tool')}`,
    };
  }
  if (event.type === 'debug.error.detected') {
    return {
      id: event.id,
      role: 'system',
      content: `Error: ${String(event.payload.error_message ?? 'Hermes failed')}`,
    };
  }
  return null;
}

function applyAssistantDelta(messages: ChatMessage[], event: DashboardEvent): ChatMessage[] {
  const content = String(event.payload.content ?? '');
  if (!content) return messages;
  const draftId = `draft-${event.session_id}`;
  const existingIndex = messages.findIndex((message) => message.id === draftId);
  if (existingIndex === -1) {
    return [...messages, { id: draftId, role: 'assistant', content }];
  }
  return messages.map((message, index) => (
    index === existingIndex
      ? { ...message, content: `${message.content}${content}` }
      : message
  ));
}

function applyCompletedAssistantMessage(messages: ChatMessage[], event: DashboardEvent): ChatMessage[] {
  const content = String(event.payload.content ?? '');
  if (!content) return messages;
  const draftId = `draft-${event.session_id}`;
  const withoutDraft = messages.filter((message) => message.id !== draftId);
  return [...withoutDraft, { id: event.id, role: 'assistant', content }];
}

function activityFromEvent(event: DashboardEvent): RuntimeActivityItem | null {
  if (event.type === 'agent.tool.started') {
    const tool = String(event.payload.tool ?? '');
    return {
      kind: 'tool.started',
      summary: `${tool} started`,
      stream: '',
      tool,
    };
  }
  if (event.type === 'agent.log.chunk') {
    const stream = String(event.payload.stream ?? '');
    return {
      kind: `log.${stream}`,
      summary: String(event.payload.content ?? '').trim(),
      stream,
      tool: String(event.payload.tool ?? ''),
    };
  }
  if (event.type === 'agent.tool.completed') {
    const tool = String(event.payload.tool ?? '');
    return {
      kind: 'tool.completed',
      summary: `${tool} completed with ${String(event.payload.returncode ?? '')}`,
      stream: '',
      tool,
    };
  }
  return null;
}

function appendActivity(dashboard: DashboardProjection | null, event: DashboardEvent): DashboardProjection | null {
  const activity = activityFromEvent(event);
  if (!dashboard || !activity || !activity.summary) return dashboard;
  return {
    ...dashboard,
    activity: [...dashboard.activity, activity],
  };
}

function App() {
  const [health, setHealth] = React.useState<HealthResponse | null>(null);
  const [providers, setProviders] = React.useState<ModelProvider[]>([]);
  const [agents, setAgents] = React.useState<AgentProfile[]>([]);
  const [selectedAgentId, setSelectedAgentId] = React.useState('');
  const [showArchivedAgents, setShowArchivedAgents] = React.useState(false);
  const [sessions, setSessions] = React.useState<CodingSession[]>([]);
  const [showArchivedSessions, setShowArchivedSessions] = React.useState(false);
  const [sessionCleanupSummary, setSessionCleanupSummary] = React.useState('');
  const [memoryFiles, setMemoryFiles] = React.useState<MemoryFile[]>([]);
  const [skillFiles, setSkillFiles] = React.useState<SkillFile[]>([]);
  const [hermesStatus, setHermesStatus] = React.useState<HermesHomeStatus | null>(null);
  const [honchoStatus, setHonchoStatus] = React.useState<HonchoStatus | null>(null);
  const [selectedMemoryPath, setSelectedMemoryPath] = React.useState('');
  const [selectedSkillPath, setSelectedSkillPath] = React.useState('');
  const [memoryContent, setMemoryContent] = React.useState('');
  const [skillContent, setSkillContent] = React.useState('');
  const [hermesConfigContent, setHermesConfigContent] = React.useState('');
  const [selectedSessionId, setSelectedSessionId] = React.useState('');
  const [selectedModel, setSelectedModel] = React.useState('');
  const [mainView, setMainView] = React.useState<MainView>('chat');
  const [messages, setMessages] = React.useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hermes runtime is connected. Ask for a code change, a concept summary, or a debugging trace.',
    },
  ]);
  const [dashboard, setDashboard] = React.useState<DashboardProjection | null>(null);
  const [error, setError] = React.useState<string>('');
  const [isSending, setIsSending] = React.useState(false);
  const [backendStatus, setBackendStatus] = React.useState<BackendStatus | null>(null);
  const [isRestartingBackend, setIsRestartingBackend] = React.useState(false);
  const [isSavingMemory, setIsSavingMemory] = React.useState(false);
  const [isSavingSkill, setIsSavingSkill] = React.useState(false);
  const [isSavingHermesConfig, setIsSavingHermesConfig] = React.useState(false);
  const initialLoadStarted = React.useRef(false);
  const activeRunController = React.useRef<AbortController | null>(null);

  React.useEffect(() => {
    if (initialLoadStarted.current) return;
    initialLoadStarted.current = true;
    void loadInitialData();
  }, []);

  async function refreshBackendStatus() {
    const status = await getBackendStatus();
    setBackendStatus(status);
    return status;
  }

  async function loadInitialData(options: { resetFileSelections?: boolean } = {}) {
    await refreshBackendStatus();
    try {
      const [
        healthResponse,
        providerResponse,
        agentResponse,
        sessionResponse,
        memoryResponse,
        skillResponse,
        hermesHomeResponse,
        hermesConfigResponse,
        honchoResponse,
      ] = await Promise.all([
        getHealth(),
        getModelProviders(),
        listAgents(showArchivedAgents),
        listSessions(showArchivedSessions),
        listMemoryFiles(),
        listSkillFiles(),
        getHermesHomeStatus(),
        readHermesConfig(),
        getHonchoStatus(),
      ]);
      let nextSessions = sessionResponse;
      let activeSessionId = selectedSessionId || nextSessions[0]?.id || '';
      if (!activeSessionId) {
        const created = await createSession({ title: 'First vibe session', goal: 'Build Hermes Vibe Desktop' });
        nextSessions = [created];
        activeSessionId = created.id;
      }
      setHealth(healthResponse);
      setProviders(providerResponse);
      setAgents(agentResponse);
      setSessions(nextSessions);
      setMemoryFiles(memoryResponse);
      setSkillFiles(skillResponse);
      setHermesStatus(hermesHomeResponse);
      setHonchoStatus(honchoResponse);
      setHermesConfigContent(hermesConfigResponse.content);
      if (options.resetFileSelections) {
        setSelectedMemoryPath('');
        setSelectedSkillPath('');
        setMemoryContent('');
        setSkillContent('');
      }
      if ((options.resetFileSelections || !selectedMemoryPath) && memoryResponse.length > 0) {
        await handleSelectMemoryFile(memoryResponse[0].path);
      }
      if ((options.resetFileSelections || !selectedSkillPath) && skillResponse.length > 0) {
        await handleSelectSkillFile(skillResponse[0].path);
      }
      setSelectedSessionId(activeSessionId);
      if (!selectedAgentId && agentResponse.length > 0) {
        setSelectedAgentId(agentResponse[0].id);
      }
      setSelectedModel(selectedModelFromProviders(providerResponse));
      await loadSessionData(activeSessionId);
      setError('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      await refreshBackendStatus();
    }
  }

  async function loadSessionData(sessionId: string) {
    const [dashboardResponse, eventResponse] = await Promise.all([
      getDashboard(sessionId),
      listSessionEvents(sessionId),
    ]);
    setDashboard(dashboardResponse);
    const restoredMessages = assistantMessagesFromEvents(eventResponse);
    setMessages(restoredMessages.length > 0 ? restoredMessages : [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Hermes runtime is connected. Ask for a code change, a concept summary, or a debugging trace.',
      },
    ]);
  }

  async function handleRestartBackend() {
    setIsRestartingBackend(true);
    setError('');
    try {
      const status = await restartBackend();
      setBackendStatus(status);
      await loadInitialData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      await refreshBackendStatus();
    } finally {
      setIsRestartingBackend(false);
    }
  }

  async function handleApplyHermesHome(path: string, bootstrap: boolean) {
    setIsRestartingBackend(true);
    setError('');
    try {
      if (window.hermesVibe?.restartBackend) {
        const status = await restartBackend({ hermesHome: path, bootstrapHermesHome: bootstrap });
        setBackendStatus(status);
      } else {
        await setHermesHome(path, bootstrap);
        await refreshBackendStatus();
      }
      await loadInitialData({ resetFileSelections: true });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      await refreshBackendStatus();
    } finally {
      setIsRestartingBackend(false);
    }
  }

  async function handleCreateAgent(input: AgentProfileInput) {
    const agent = await createAgent(input);
    setAgents((current) => [agent, ...current]);
    setSelectedAgentId(agent.id);
  }

  async function handleUpdateAgent(agentId: string, input: Partial<AgentProfileInput>) {
    const agent = await updateAgent(agentId, input);
    setAgents((current) => current.map((item) => (item.id === agent.id ? agent : item)));
    setSelectedAgentId(agent.id);
  }

  async function handleArchiveAgent(agentId: string) {
    await archiveAgent(agentId);
    const nextAgents = await listAgents(showArchivedAgents);
    setAgents(nextAgents);
    setSelectedAgentId(nextAgents[0]?.id ?? '');
  }

  async function handleRestoreAgent(agentId: string) {
    const restored = await restoreAgent(agentId);
    const nextAgents = await listAgents(showArchivedAgents);
    setAgents(nextAgents);
    setSelectedAgentId(restored.id);
  }

  async function handleDeleteAgent(agentId: string) {
    const agent = agents.find((item) => item.id === agentId);
    if (!window.confirm(`Delete agent "${agent?.name ?? agentId}"? This cannot be undone.`)) return;
    await deleteAgent(agentId);
    const nextAgents = await listAgents(showArchivedAgents);
    setAgents(nextAgents);
    setSelectedAgentId(nextAgents[0]?.id ?? '');
  }

  async function handleCreateSession(input: CodingSessionInput) {
    const session = await createSession(input);
    setSessions((current) => [session, ...current]);
    setSelectedSessionId(session.id);
    setSessionCleanupSummary('');
    setMainView('chat');
    await loadSessionData(session.id);
  }

  async function handleUpdateSession(sessionId: string, input: Partial<CodingSessionInput>) {
    const session = await updateSession(sessionId, input);
    setSessions((current) => current.map((item) => (item.id === session.id ? session : item)));
  }

  async function handleArchiveSession(sessionId: string) {
    await archiveSession(sessionId);
    const nextSessions = await listSessions(showArchivedSessions);
    setSessions(nextSessions);
    const nextSessionId = nextSessions[0]?.id ?? '';
    setSelectedSessionId(nextSessionId);
    if (nextSessionId) await loadSessionData(nextSessionId);
  }

  async function handleRestoreSession(sessionId: string) {
    const restored = await restoreSession(sessionId);
    const nextSessions = await listSessions(showArchivedSessions);
    setSessions(nextSessions);
    setSelectedSessionId(restored.id);
    await loadSessionData(restored.id);
  }

  async function handleDeleteSession(sessionId: string) {
    const session = sessions.find((item) => item.id === sessionId);
    if (!window.confirm(`Delete session "${session?.title ?? sessionId}" and its events? This cannot be undone.`)) return;
    await deleteSession(sessionId);
    const nextSessions = await listSessions(showArchivedSessions);
    setSessions(nextSessions);
    const nextSessionId = nextSessions[0]?.id ?? '';
    setSelectedSessionId(nextSessionId);
    if (nextSessionId) {
      await loadSessionData(nextSessionId);
    } else {
      setMessages([]);
      setDashboard(null);
    }
  }

  async function handleDeduplicateSessions() {
    const result = await deduplicateSessions();
    const nextSessions = await listSessions(showArchivedSessions);
    setSessions(nextSessions);
    setError('');
    if (result.archived_count === 0) {
      setSessionCleanupSummary('No duplicate sessions found.');
      return;
    }
    const currentStillActive = nextSessions.some((session) => session.id === selectedSessionId);
    const nextSessionId = currentStillActive ? selectedSessionId : nextSessions[0]?.id ?? '';
    setSelectedSessionId(nextSessionId);
    if (nextSessionId) await loadSessionData(nextSessionId);
    const groupText = result.groups
      .slice(0, 3)
      .map((group) => `${group.key.title || 'Untitled'} kept 1, archived ${group.archived_session_ids.length}`)
      .join('; ');
    setSessionCleanupSummary(`Archived ${result.archived_count} duplicate session${result.archived_count === 1 ? '' : 's'}. ${groupText}`);
  }

  async function handleShowArchivedAgentsChange(nextValue: boolean) {
    setShowArchivedAgents(nextValue);
    const nextAgents = await listAgents(nextValue);
    setAgents(nextAgents);
    setSelectedAgentId(nextAgents.some((agent) => agent.id === selectedAgentId) ? selectedAgentId : nextAgents[0]?.id ?? '');
  }

  async function handleShowArchivedSessionsChange(nextValue: boolean) {
    setShowArchivedSessions(nextValue);
    const nextSessions = await listSessions(nextValue);
    setSessions(nextSessions);
    const nextSessionId = nextSessions.some((session) => session.id === selectedSessionId)
      ? selectedSessionId
      : nextSessions[0]?.id ?? '';
    setSelectedSessionId(nextSessionId);
    if (nextSessionId) await loadSessionData(nextSessionId);
  }

  async function handleSelectSession(sessionId: string) {
    setSelectedSessionId(sessionId);
    await loadSessionData(sessionId);
  }

  async function handleSelectMemoryFile(path: string) {
    setSelectedMemoryPath(path);
    const file = await readMemoryFile(path);
    setMemoryContent(file.content);
  }

  async function handleSaveMemoryFile() {
    if (!selectedMemoryPath) return;
    setIsSavingMemory(true);
    setError('');
    try {
      await saveMemoryFile(selectedMemoryPath, memoryContent);
      setMemoryFiles(await listMemoryFiles());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSavingMemory(false);
    }
  }

  async function handleSelectSkillFile(path: string) {
    setSelectedSkillPath(path);
    const file = await readSkillFile(path);
    setSkillContent(file.content);
  }

  async function handleSaveSkillFile() {
    if (!selectedSkillPath) return;
    setIsSavingSkill(true);
    setError('');
    try {
      await saveSkillFile(selectedSkillPath, skillContent);
      setSkillFiles(await listSkillFiles());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSavingSkill(false);
    }
  }

  async function handleSaveHermesConfig() {
    setIsSavingHermesConfig(true);
    setError('');
    try {
      await saveHermesConfig(hermesConfigContent);
      const [status, config] = await Promise.all([getHermesHomeStatus(), readHermesConfig()]);
      setHermesStatus(status);
      setHermesConfigContent(config.content);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsSavingHermesConfig(false);
    }
  }

  async function handleRefreshHonchoStatus() {
    setHonchoStatus(await getHonchoStatus());
  }

  async function handleSend(content: string) {
    if (!selectedSessionId) return;
    const sessionId = selectedSessionId;
    const selectedSession = sessions.find((session) => session.id === sessionId);
    const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);
    if (selectedSession?.archived_at) {
      setError('Restore this archived session before chatting.');
      return;
    }
    if (selectedAgent?.archived_at) {
      setError('Restore this archived agent before chatting.');
      return;
    }
    const controller = new AbortController();
    activeRunController.current = controller;
    setError('');
    setIsSending(true);
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
    };
    setMessages((current) => [...current, userMessage]);

    const [defaultProvider, defaultModel] = selectedModel.split(':');
    const provider = selectedAgent?.provider ?? defaultProvider;
    const model = selectedAgent?.model ?? defaultModel;
    try {
      const streamedEvents: DashboardEvent[] = [];
      await streamMessage(
        sessionId,
        {
          role: 'user',
          content,
          provider,
          model,
          agent_id: selectedAgent?.id,
          agent_name: selectedAgent?.name,
          system_prompt: selectedAgent?.system_prompt,
        },
        async (event) => {
          streamedEvents.push(event);
          if (event.type === 'chat.message.delta') {
            setMessages((current) => applyAssistantDelta(current, event));
          } else if (event.type === 'chat.message.completed') {
            setMessages((current) => applyCompletedAssistantMessage(current, event));
          } else if (event.type !== 'chat.message.user') {
            const chatMessage = chatMessageFromEvent(event);
            if (chatMessage) {
              setMessages((current) => [...current, chatMessage]);
            }
          }
          if (event.type.startsWith('agent.')) {
            setDashboard((current) => appendActivity(current, event));
          }
          if (
            event.type.startsWith('implementation.') ||
            event.type.startsWith('concept.') ||
            event.type.startsWith('decision.') ||
            event.type.startsWith('error.')
          ) {
            setDashboard(await getDashboard(sessionId));
          }
        },
        controller.signal,
      );
      const assistantMessages = assistantMessagesFromEvents(streamedEvents);
      if (assistantMessages.length === 0) {
        setDashboard(await getDashboard(sessionId));
      }
      setSessions(await listSessions(showArchivedSessions));
    } catch (err: unknown) {
      if (isAbortError(err)) {
        setMessages((current) => [
          ...current.filter((message) => message.id !== `draft-${sessionId}`),
          {
            id: `cancelled-${Date.now()}`,
            role: 'system',
            content: 'Hermes run cancelled.',
          },
        ]);
      } else {
        setError(err instanceof Error ? err.message : String(err));
        await refreshBackendStatus();
      }
    } finally {
      setIsSending(false);
      activeRunController.current = null;
    }
  }

  function handleCancelRun() {
    activeRunController.current?.abort();
  }

  const selectedSession = sessions.find((session) => session.id === selectedSessionId) ?? null;
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? null;
  const chatDisabledReason = selectedSession?.archived_at
    ? 'Restore this archived session before chatting.'
    : selectedAgent?.archived_at
      ? 'Restore this archived agent before chatting.'
      : '';

  return (
    <main className="app">
      <nav className="rail">
        <div className="brand">Hermes Vibe</div>
        <button className={`rail-button ${mainView === 'chat' ? 'active' : ''}`} onClick={() => setMainView('chat')}>Chat</button>
        <button className={`rail-button ${mainView === 'agents' ? 'active' : ''}`} onClick={() => setMainView('agents')}>Agents</button>
        <button className="rail-button" onClick={() => setMainView('chat')}>Dashboard</button>
        <button className={`rail-button ${mainView === 'sessions' ? 'active' : ''}`} onClick={() => setMainView('sessions')}>Sessions</button>
        <button className={`rail-button ${mainView === 'memory' ? 'active' : ''}`} onClick={() => setMainView('memory')}>Memory</button>
        <button className={`rail-button ${mainView === 'skills' ? 'active' : ''}`} onClick={() => setMainView('skills')}>Skills</button>
        <button className={`rail-button ${mainView === 'hermes' ? 'active' : ''}`} onClick={() => setMainView('hermes')}>Hermes Home</button>
        <button className={`rail-button ${mainView === 'honcho' ? 'active' : ''}`} onClick={() => setMainView('honcho')}>Honcho</button>
      </nav>
      <section className="main">
        {error && <div className="error">{error}</div>}
        {(error || backendStatus?.state === 'error' || backendStatus?.state === 'stopped') && (
          <BackendStatusPanel
            status={backendStatus}
            isRestarting={isRestartingBackend}
            onRestart={handleRestartBackend}
          />
        )}
        <div className="topbar">
          <HermesHomePanel health={health} />
          <ModelSelector providers={providers} value={selectedModel} onChange={setSelectedModel} />
        </div>
        {mainView === 'chat' ? (
          <>
            <div className="context-strip">
              <span>{selectedSession?.title ?? 'No session'}</span>
              <button type="button" onClick={() => setMainView('sessions')}>Change</button>
            </div>
            {selectedAgentId && (
              <div className="active-agent-strip">
                Active agent: {selectedAgent?.name ?? 'Unknown'}
              </div>
            )}
            <ChatPanel
              messages={messages}
              isSending={isSending}
              disabledReason={chatDisabledReason}
              onSend={handleSend}
              onCancel={handleCancelRun}
            />
          </>
        ) : mainView === 'agents' ? (
          <AgentsPanel
            agents={agents}
            providers={providers}
            selectedAgentId={selectedAgentId}
            onSelectAgent={setSelectedAgentId}
            onCreateAgent={handleCreateAgent}
            onUpdateAgent={handleUpdateAgent}
            showArchived={showArchivedAgents}
            isRuntimeBusy={isSending}
            onShowArchivedChange={handleShowArchivedAgentsChange}
            onArchiveAgent={handleArchiveAgent}
            onRestoreAgent={handleRestoreAgent}
            onDeleteAgent={handleDeleteAgent}
          />
        ) : mainView === 'sessions' ? (
          <SessionPanel
            sessions={sessions}
            selectedSessionId={selectedSessionId}
            onSelectSession={handleSelectSession}
            onCreateSession={handleCreateSession}
            onUpdateSession={handleUpdateSession}
            onDeduplicateSessions={handleDeduplicateSessions}
            deduplicateSummary={sessionCleanupSummary}
            isRuntimeBusy={isSending}
            showArchived={showArchivedSessions}
            onShowArchivedChange={handleShowArchivedSessionsChange}
            onArchiveSession={handleArchiveSession}
            onRestoreSession={handleRestoreSession}
            onDeleteSession={handleDeleteSession}
          />
        ) : mainView === 'memory' ? (
          <MemoryPanel
            files={memoryFiles}
            selectedPath={selectedMemoryPath}
            content={memoryContent}
            isSaving={isSavingMemory}
            onSelectFile={handleSelectMemoryFile}
            onContentChange={setMemoryContent}
            onSave={handleSaveMemoryFile}
          />
        ) : mainView === 'skills' ? (
          <SkillsPanel
            files={skillFiles}
            selectedPath={selectedSkillPath}
            content={skillContent}
            isSaving={isSavingSkill}
            onSelectFile={handleSelectSkillFile}
            onContentChange={setSkillContent}
            onSave={handleSaveSkillFile}
          />
        ) : mainView === 'hermes' ? (
          <HermesSettingsPanel
            status={hermesStatus}
            configContent={hermesConfigContent}
            isSaving={isSavingHermesConfig}
            isRestarting={isRestartingBackend}
            onConfigChange={setHermesConfigContent}
            onSaveConfig={handleSaveHermesConfig}
            onApplyHermesHome={handleApplyHermesHome}
          />
        ) : mainView === 'honcho' ? (
          <HonchoPanel status={honchoStatus} onRefresh={handleRefreshHonchoStatus} />
        ) : null}
      </section>
      <DashboardPanel dashboard={dashboard} />
    </main>
  );
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function BackendStatusPanel({
  status,
  isRestarting,
  onRestart,
}: {
  status: BackendStatus | null;
  isRestarting: boolean;
  onRestart: () => void;
}) {
  const logs = status?.logs.slice(-8) ?? [];
  return (
    <section className="panel backend-status">
      <div className="panel-title">Backend</div>
      <div className="backend-status-row">
        <span className={`status-pill ${status?.state ?? 'unknown'}`}>{status?.state ?? 'unknown'}</span>
        <span className="mono">{status?.url ?? 'Electron backend status unavailable'}</span>
        <button type="button" onClick={onRestart} disabled={isRestarting}>
          {isRestarting ? 'Restarting...' : 'Restart'}
        </button>
      </div>
      {typeof status?.exitCode !== 'undefined' && (
        <div className="muted">Exit code: {status.exitCode ?? 'none'}</div>
      )}
      {logs.length > 0 && (
        <pre className="backend-log">{logs.join('\n')}</pre>
      )}
    </section>
  );
}

declare global {
  interface Window {
    __hermesVibeRoot?: Root;
  }
}

const rootElement = document.getElementById('root') as HTMLElement;
window.__hermesVibeRoot = window.__hermesVibeRoot ?? createRoot(rootElement);
window.__hermesVibeRoot.render(<App />);
