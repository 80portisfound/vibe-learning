import { spawn as defaultSpawn } from 'node:child_process';
import { EventEmitter } from 'node:events';
import fs from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';

export type ChildProcessLike = EventEmitter & {
  killed?: boolean;
  stdout?: EventEmitter | null;
  stderr?: EventEmitter | null;
  kill(signal?: NodeJS.Signals): boolean;
};

export type SpawnFn = (
  command: string,
  args: string[],
  options: { cwd: string; env: NodeJS.ProcessEnv; stdio: ['ignore', 'pipe', 'pipe'] },
) => ChildProcessLike;

export type BackendCommand = {
  command: string;
  args: string[];
  cwd: string;
  env: NodeJS.ProcessEnv;
  url: string;
};

export type BackendManager = {
  start(): Promise<ChildProcessLike>;
  stop(): void;
  setHermesHome(hermesHome: string, bootstrap?: boolean): void;
  status(): BackendStatus;
  url: string;
};

export type BackendStatus = {
  state: 'stopped' | 'starting' | 'running' | 'error';
  url: string;
  logs: string[];
  hermesHome: string;
  exitCode?: number | null;
};

export type BackendHealthFetch = (url: string) => Promise<{ ok: boolean }>;
export type PortAvailabilityCheck = (port: number) => Promise<boolean>;

export function resolveBackendPort(env: NodeJS.ProcessEnv): number {
  const rawPort = env.HERMES_VIBE_API_PORT;
  const parsed = rawPort ? Number.parseInt(rawPort, 10) : Number.NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 8000;
}

export function buildBackendCommand({
  apiDir,
  port,
  env = process.env,
}: {
  apiDir: string;
  port?: number;
  env?: NodeJS.ProcessEnv;
}): BackendCommand {
  const selectedPort = port ?? resolveBackendPort(env);
  return {
    command: resolvePythonExecutable(env),
    args: [
      '-m',
      'uvicorn',
      'hermes_vibe_api.app:create_app',
      '--factory',
      '--host',
      '127.0.0.1',
      '--port',
      String(selectedPort),
    ],
    cwd: apiDir,
    env: {
      ...process.env,
      ...env,
      HERMES_HOME: env.HERMES_HOME ?? path.join(os.homedir(), '.hermes'),
    },
    url: `http://127.0.0.1:${selectedPort}`,
  };
}

export async function chooseBackendPort(
  preferredPort: number,
  {
    attempts = 20,
    isPortAvailable: checkPort = isPortAvailable,
  }: {
    attempts?: number;
    isPortAvailable?: PortAvailabilityCheck;
  } = {},
): Promise<number> {
  for (let offset = 0; offset < attempts; offset += 1) {
    const candidate = preferredPort + offset;
    if (await checkPort(candidate)) return candidate;
  }
  throw new Error(`No available backend port found from ${preferredPort}`);
}

export function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', () => resolve(false));
    server.once('listening', () => {
      server.close(() => resolve(true));
    });
    server.listen(port, '127.0.0.1');
  });
}

export function createBackendManager({
  apiDir,
  env = process.env,
  spawn = defaultSpawn as SpawnFn,
  choosePort = chooseBackendPort,
}: {
  apiDir: string;
  env?: NodeJS.ProcessEnv;
  spawn?: SpawnFn;
  choosePort?: (preferredPort: number) => Promise<number>;
}): BackendManager {
  const runtimeEnv: NodeJS.ProcessEnv = { ...env };
  let command = buildBackendCommand({ apiDir, env: runtimeEnv });
  let child: ChildProcessLike | null = null;
  let state: BackendStatus['state'] = 'stopped';
  let exitCode: number | null | undefined;
  const logs: string[] = [];

  function appendLog(line: string): void {
    logs.push(line);
    if (logs.length > 200) logs.splice(0, logs.length - 200);
  }

  const manager: BackendManager = {
    get url() {
      return command.url;
    },
    async start() {
      if (child && !child.killed) return child;
      state = 'starting';
      exitCode = undefined;
      const port = await choosePort(resolveBackendPort(runtimeEnv));
      command = buildBackendCommand({ apiDir, env: runtimeEnv, port });
      child = spawn(command.command, command.args, {
        cwd: command.cwd,
        env: command.env,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      state = 'running';
      child.stdout?.on('data', (chunk) => {
        const line = String(chunk).trimEnd();
        appendLog(`[stdout] ${line}`);
        console.log(`[api] ${line}`);
      });
      child.stderr?.on('data', (chunk) => {
        const line = String(chunk).trimEnd();
        appendLog(`[stderr] ${line}`);
        console.error(`[api] ${line}`);
      });
      child.on('exit', (code) => {
        exitCode = code;
        state = code === 0 || code === null ? 'stopped' : 'error';
        child = null;
      });
      return child;
    },
    stop() {
      if (child && !child.killed) {
        child.kill('SIGTERM');
      }
      child = null;
      state = 'stopped';
    },
    setHermesHome(hermesHome: string, bootstrap = false) {
      runtimeEnv.HERMES_HOME = hermesHome;
      if (bootstrap) {
        runtimeEnv.HERMES_VIBE_BOOTSTRAP_HOME = '1';
      } else {
        delete runtimeEnv.HERMES_VIBE_BOOTSTRAP_HOME;
      }
      command = buildBackendCommand({ apiDir, env: runtimeEnv, port: resolveBackendPort(runtimeEnv) });
    },
    status() {
      return {
        state,
        url: command.url,
        logs: [...logs],
        hermesHome: String(command.env.HERMES_HOME ?? ''),
        exitCode,
      };
    },
  };
  return manager;
}

export function resolveApiDir(electronDir: string, resourcesPath?: string): string {
  if (resourcesPath) {
    return path.join(resourcesPath, 'api');
  }
  return path.resolve(electronDir, '..', '..', 'api');
}

export function resolveForkMetadataPath(resourcesPath: string): string {
  return path.join(resourcesPath, 'HERMES_VIBE_FORK.json');
}

export async function waitForBackend(
  baseUrl: string,
  {
    attempts = 40,
    delayMs = 250,
    fetch = globalThis.fetch as BackendHealthFetch,
  }: {
    attempts?: number;
    delayMs?: number;
    fetch?: BackendHealthFetch;
  } = {},
): Promise<void> {
  const healthUrl = `${baseUrl}/health`;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok) return;
    } catch {
      // Retry until the backend starts accepting connections.
    }
    if (attempt < attempts) {
      await delay(delayMs);
    }
  }
  throw new Error(`Backend did not become ready at ${healthUrl}`);
}

function resolvePythonExecutable(env: NodeJS.ProcessEnv): string {
  if (env.HERMES_VIBE_PYTHON) return env.HERMES_VIBE_PYTHON;
  if (env.HERMES_VIBE_PYTHON_RUNTIME_DIR) {
    return path.join(env.HERMES_VIBE_PYTHON_RUNTIME_DIR, 'bin', 'python');
  }
  const tempVenvPython = '/private/tmp/hermes-vibe-api-venv/bin/python';
  if (fs.existsSync(tempVenvPython)) return tempVenvPython;
  return 'python3';
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}
