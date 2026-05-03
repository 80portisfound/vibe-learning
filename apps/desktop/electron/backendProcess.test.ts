import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import test from 'node:test';
import {
  buildBackendCommand,
  createBackendManager,
  chooseBackendPort,
  resolveApiDir,
  resolveBackendPort,
  resolveForkMetadataPath,
  waitForBackend,
  type ChildProcessLike,
  type SpawnFn,
} from './backendProcess.js';

test('resolveBackendPort uses default and env override', () => {
  assert.equal(resolveBackendPort({}), 8000);
  assert.equal(resolveBackendPort({ HERMES_VIBE_API_PORT: '8123' }), 8123);
});

test('chooseBackendPort falls back from occupied preferred ports', async () => {
  const occupied = new Set([8000, 8001]);

  const port = await chooseBackendPort(8000, {
    isPortAvailable: async (candidate) => !occupied.has(candidate),
  });

  assert.equal(port, 8002);
});

test('buildBackendCommand points uvicorn at the api app factory', () => {
  const command = buildBackendCommand({
    apiDir: '/repo/apps/api',
    port: 8123,
    env: {
      HERMES_VIBE_PYTHON: '/tmp/python',
    },
  });

  assert.equal(command.command, '/tmp/python');
  assert.deepEqual(command.args, [
    '-m',
    'uvicorn',
    'hermes_vibe_api.app:create_app',
    '--factory',
    '--host',
    '127.0.0.1',
    '--port',
    '8123',
  ]);
  assert.equal(command.cwd, '/repo/apps/api');
  assert.equal(command.env.HERMES_HOME?.endsWith('/.hermes'), true);
});

test('buildBackendCommand uses explicit hermes home override', () => {
  const command = buildBackendCommand({
    apiDir: '/repo/apps/api',
    port: 8123,
    env: {
      HERMES_HOME: '/tmp/custom-hermes',
      HERMES_VIBE_PYTHON: '/tmp/python',
    },
  });

  assert.equal(command.env.HERMES_HOME, '/tmp/custom-hermes');
});

test('buildBackendCommand prefers packaged python runtime directory', () => {
  const command = buildBackendCommand({
    apiDir: '/repo/apps/api',
    port: 8123,
    env: {
      HERMES_VIBE_PYTHON_RUNTIME_DIR: '/app/Resources/python-runtime',
    },
  });

  assert.equal(command.command, '/app/Resources/python-runtime/bin/python');
});

test('backend manager starts once and terminates the spawned process', async () => {
  const spawned: FakeProcess[] = [];
  const spawn: SpawnFn = (command, args, options) => {
    const child = new FakeProcess(command, args, options.cwd);
    spawned.push(child);
    return child;
  };
  const manager = createBackendManager({
    apiDir: '/repo/apps/api',
    env: { HERMES_VIBE_PYTHON: '/tmp/python' },
    spawn,
  });

  const first = await manager.start();
  const second = await manager.start();

  assert.equal(first, second);
  assert.equal(spawned.length, 1);
  manager.stop();
  assert.equal(spawned[0].killedWith, 'SIGTERM');
});

test('backend manager exposes fallback backend url after start', async () => {
  const manager = createBackendManager({
    apiDir: '/repo/apps/api',
    env: { HERMES_VIBE_PYTHON: '/tmp/python' },
    spawn: (command, args, options) => new FakeProcess(command, args, options.cwd),
    choosePort: async () => 8010,
  });

  await manager.start();

  assert.equal(manager.url, 'http://127.0.0.1:8010');
});

test('backend manager can repoint hermes home before restart', async () => {
  const spawned: FakeProcess[] = [];
  const spawn: SpawnFn = (command, args, options) => {
    const child = new FakeProcess(command, args, options.cwd, options.env);
    spawned.push(child);
    return child;
  };
  const manager = createBackendManager({
    apiDir: '/repo/apps/api',
    env: { HERMES_VIBE_PYTHON: '/tmp/python' },
    spawn,
  });

  await manager.start();
  manager.stop();
  manager.setHermesHome('/tmp/next-hermes', true);
  await manager.start();

  assert.equal(spawned.length, 2);
  assert.equal(spawned[1].env.HERMES_HOME, '/tmp/next-hermes');
  assert.equal(spawned[1].env.HERMES_VIBE_BOOTSTRAP_HOME, '1');
  assert.equal(manager.status().hermesHome, '/tmp/next-hermes');
});

test('backend manager tracks status and recent logs', async () => {
  const child = new FakeProcess('/tmp/python', [], '/repo/apps/api');
  const manager = createBackendManager({
    apiDir: '/repo/apps/api',
    env: { HERMES_VIBE_PYTHON: '/tmp/python' },
    spawn: () => child,
  });

  assert.equal(manager.status().state, 'stopped');
  await manager.start();
  child.stdout.emit('data', Buffer.from('ready\n'));
  child.stderr.emit('data', Buffer.from('warning\n'));
  assert.equal(manager.status().state, 'running');
  assert.deepEqual(manager.status().logs.slice(-2), ['[stdout] ready', '[stderr] warning']);
  child.emit('exit', 1, null);

  assert.equal(manager.status().state, 'error');
  assert.equal(manager.status().exitCode, 1);
});

test('waitForBackend retries until health endpoint is ready', async () => {
  let attempts = 0;

  await waitForBackend('http://127.0.0.1:8000', {
    attempts: 3,
    delayMs: 0,
    fetch: async (url) => {
      attempts += 1;
      assert.equal(url, 'http://127.0.0.1:8000/health');
      return { ok: attempts === 2 };
    },
  });

  assert.equal(attempts, 2);
});

test('waitForBackend throws when health endpoint never becomes ready', async () => {
  await assert.rejects(
    waitForBackend('http://127.0.0.1:8000', {
      attempts: 2,
      delayMs: 0,
      fetch: async () => ({ ok: false }),
    }),
    /Backend did not become ready/,
  );
});

test('resolveApiDir can point at packaged resources', () => {
  assert.equal(
    resolveApiDir('/app/Hermes Vibe.app/Contents/Resources/app.asar/dist-electron', '/app/Hermes Vibe.app/Contents/Resources'),
    '/app/Hermes Vibe.app/Contents/Resources/api',
  );
});

test('resolveForkMetadataPath can point at packaged resources', () => {
  assert.equal(
    resolveForkMetadataPath('/app/Hermes Vibe.app/Contents/Resources'),
    '/app/Hermes Vibe.app/Contents/Resources/HERMES_VIBE_FORK.json',
  );
});

class FakeProcess extends EventEmitter implements ChildProcessLike {
  killed = false;
  killedWith = '';
  stdout = new EventEmitter();
  stderr = new EventEmitter();

  constructor(
    public command: string,
    public args: string[],
    public cwd: string | undefined,
    public env: NodeJS.ProcessEnv = {},
  ) {
    super();
  }

  kill(signal?: NodeJS.Signals): boolean {
    this.killed = true;
    this.killedWith = signal ?? '';
    this.emit('exit', 0, signal);
    return true;
  }
}
