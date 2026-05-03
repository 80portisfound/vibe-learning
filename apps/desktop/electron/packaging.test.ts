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
  assert.doesNotMatch(runtimeRequirements, /^pytest/m);
  assert.doesNotMatch(runtimeRequirements, /^httpx/m);

  const devRequirements = readFileSync(devRequirementsPath, 'utf8');
  assert.match(devRequirements, /^-r requirements-runtime\.txt/m);
  assert.match(devRequirements, /^pytest/m);
  assert.match(devRequirements, /^httpx/m);

  const prepareScript = readFileSync(prepareScriptPath, 'utf8');
  assert.match(prepareScript, /requirements-runtime\.txt/);
  assert.doesNotMatch(prepareScript, /requirements\.txt/);
});
