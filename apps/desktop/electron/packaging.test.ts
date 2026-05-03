import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';

test('python runtime packaging installs runtime-only api requirements', () => {
  const desktopDir = process.cwd();
  const apiDir = path.resolve(desktopDir, '../api');
  const runtimeRequirementsPath = path.join(apiDir, 'requirements-runtime.txt');
  const devRequirementsPath = path.join(apiDir, 'requirements-dev.txt');
  const prepareScriptPath = path.join(desktopDir, 'scripts/prepare-python-runtime.sh');

  assert.equal(existsSync(runtimeRequirementsPath), true);
  assert.equal(existsSync(devRequirementsPath), true);

  const runtimeRequirements = readFileSync(runtimeRequirementsPath, 'utf8');
  assert.match(runtimeRequirements, /^fastapi/m);
  assert.match(runtimeRequirements, /^requests/m);
  assert.match(runtimeRequirements, /^httpx\[socks\]/m);
  assert.doesNotMatch(runtimeRequirements, /^pytest/m);

  const devRequirements = readFileSync(devRequirementsPath, 'utf8');
  assert.match(devRequirements, /^-r requirements-runtime\.txt/m);
  assert.match(devRequirements, /^pytest/m);

  const prepareScript = readFileSync(prepareScriptPath, 'utf8');
  assert.match(prepareScript, /requirements-runtime\.txt/);
  assert.doesNotMatch(prepareScript, /requirements\.txt/);
});

test('vite build uses relative assets for electron file loading', () => {
  const viteConfigPath = path.join(process.cwd(), 'vite.config.ts');
  const viteConfig = readFileSync(viteConfigPath, 'utf8');

  assert.match(viteConfig, /base:\s*['"]\.\/['"]/);
});
