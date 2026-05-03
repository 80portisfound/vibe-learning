# Hermes Vibe Desktop Manual

이 문서는 Hermes Vibe Desktop을 실행하고, 다른 코딩 프로젝트에 연결하고, 대시보드와 주요 기능을 사용하는 방법을 설명한다.

## 1. 앱이 하는 일

Hermes Vibe Desktop은 Hermes Agent에 GUI와 학습/디버깅 대시보드를 붙인 데스크톱 워크벤치다.

핵심 흐름은 다음과 같다.

```text
React/Electron UI
  -> FastAPI backend
  -> vendored Hermes Agent CLI
  -> local Hermes Home
  -> SQLite event store
  -> Dashboard
```

사용자는 UI에서 에이전트를 만들고, 세션을 열고, Hermes와 채팅한다. backend는 Hermes CLI를 실행하고, 출력과 에러를 이벤트로 저장한다. 대시보드는 이 이벤트를 기반으로 구현 현황, 학습 개념, 디버깅 단서, 진행 요약을 보여준다.

## 2. 디렉터리 구조

```text
apps/api
  FastAPI backend, Hermes runtime adapter, SQLite 저장소, dashboard analyzer

apps/desktop
  Electron + React UI, desktop packaging 설정

packages/hermes
  hard-fork 형태로 vendoring 된 Hermes Agent 소스

docs
  설계 문서, 계획, 이 매뉴얼
```

중요 파일:

- `apps/api/hermes_vibe_api/app.py`: API 라우트와 앱 상태 관리
- `apps/api/hermes_vibe_api/hermes/runtime.py`: Hermes CLI 실행/stream 처리
- `apps/api/hermes_vibe_api/storage/sqlite_store.py`: agents, sessions, dashboard events 저장
- `apps/api/hermes_vibe_api/dashboard/analyzer.py`: Hermes 응답을 학습/구현/디버깅 이벤트로 변환
- `apps/desktop/src/App.tsx`: React 앱의 최상위 상태와 화면 구성
- `apps/desktop/electron/main.ts`: Electron main process와 backend 프로세스 관리

## 3. 실행 방법

### 3.1 패키지 앱 실행

이미 패키징된 앱이 있으면 repository root에서 실행한다.

```bash
open "apps/desktop/release/mac-arm64/Hermes Vibe.app"
```

macOS가 미공증 앱이라고 막으면 Finder에서 우클릭 후 Open을 사용하거나, System Settings의 Security & Privacy 허용 버튼을 사용한다. 현재 로컬 빌드는 개발/QA용이며, 공개 배포용은 Apple Developer ID signing과 notarization이 필요하다.

### 3.2 개발 모드 실행

터미널 1에서 backend를 실행한다.

```bash
cd /Users/songbongjune/vibe-learning/apps/api
/private/tmp/hermes-vibe-api-venv/bin/python -m uvicorn hermes_vibe_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

터미널 2에서 frontend dev server를 실행한다.

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run dev
```

브라우저에서 연다.

```text
http://127.0.0.1:5173/
```

### 3.3 Electron shell 실행

Electron 앱 형태로 개발 실행하려면 다음을 사용한다.

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run desktop
```

`npm run desktop`은 Electron main process를 빌드하고 앱을 실행한다. backend는 Electron main process가 같이 띄운다.

## 4. 다른 프로젝트에 적용하는 방법

Hermes Vibe repo는 "도구 앱"으로 두고, 실제 작업할 프로젝트를 backend workspace로 연결하는 방식이 가장 좋다.

```text
/Users/songbongjune/vibe-learning
  Hermes Vibe GUI와 backend 소스

/path/to/target-project
  실제 vibe coding 대상 프로젝트

~/.hermes
  Hermes memory, skills, honcho, sessions 공유 상태
```

### 4.1 기본 적용 방식

작업 대상 프로젝트에서 backend를 실행한다.

```bash
cd /path/to/target-project
HERMES_HOME=~/.hermes \
PYTHONPATH=/Users/songbongjune/vibe-learning/apps/api \
/private/tmp/hermes-vibe-api-venv/bin/python -m uvicorn hermes_vibe_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

그 다음 Hermes Vibe frontend를 실행한다.

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run dev
```

이렇게 하면 Hermes CLI는 `/path/to/target-project`를 현재 작업 디렉터리로 보고 실행된다. 즉, Hermes와 채팅할 때 실제 수정/분석 대상이 target project가 된다.

### 4.2 Hermes Home 공유

기본 Hermes Home은 다음 경로다.

```text
~/.hermes
```

Hermes Vibe는 이 경로에서 다음을 읽고 관리한다.

- `config.yaml`
- `memories/`
- `skills/`
- `sessions/`
- `honcho/`

앱 안의 Hermes Home 화면에서 다른 Hermes Home 경로로 변경할 수 있다. 변경 시 backend가 새 경로를 감지하고 재시작/재연결한다.

### 4.3 현재 제한

현재 UI에는 "작업 프로젝트 경로 선택" 화면이 아직 없다. 그래서 다른 프로젝트에 적용하려면 backend를 해당 프로젝트 경로에서 직접 띄우는 방식이 필요하다.

향후 추가하면 좋은 기능:

- Workspace Path 선택 UI
- backend workspace repoint/restart
- 최근 연결 프로젝트 목록
- 프로젝트별 session/dashboard archive

## 5. 기본 사용 흐름

1. Hermes Home을 확인한다.
2. 필요한 agent를 만든다.
3. session을 만든다.
4. model/provider를 선택한다.
5. Chat에서 Hermes에게 작업을 요청한다.
6. Dashboard에서 구현 요약, 개념, 에러, 다음 단계를 확인한다.
7. Memory/Skills/Config가 필요하면 앱에서 수정한다.
8. 오래된 agent/session은 archive하거나 delete한다.

## 6. 주요 기능

### 6.1 Agents

Agent는 Hermes에게 전달할 작업 역할과 기본 모델 설정이다.

저장되는 항목:

- name
- role
- system_prompt
- provider
- model
- skills
- archived_at

채팅 요청에 `agent_id`가 포함되면 backend가 agent profile을 조회해서 runtime message에 자동 반영한다.

```text
agent_id
  -> agent_name
  -> system_prompt
  -> provider
  -> model
```

archived agent는 새 메시지를 받을 수 없다.

### 6.2 Sessions

Session은 하나의 vibe coding 작업 단위다.

기능:

- create
- edit
- archive
- restore
- delete
- duplicate cleanup

archived session에는 새 메시지를 보낼 수 없다. 중복 정리는 title과 goal을 정규화해서 같은 세션을 찾아 오래된 항목을 archive한다.

### 6.3 Chat

Chat은 Hermes CLI와 연결되는 실시간 작업 인터페이스다.

작동 흐름:

```text
사용자 메시지
  -> chat.message.user 저장
  -> Hermes CLI 실행
  -> stdout chunk를 chat.message.delta로 stream
  -> 완료 시 chat.message.completed 저장
  -> analyzer가 dashboard events 생성
```

실행 중에는 cancel 버튼으로 subprocess를 종료할 수 있다.

### 6.4 Model Selector

provider/model을 선택해서 메시지에 override로 전달한다.

현재 registry 기본값:

- OpenAI: `gpt-5.4`, `gpt-5.4-mini`
- Anthropic: `claude-sonnet-4.5`
- Local: `custom-local`

agent에 기본 provider/model이 있어도, 메시지에서 선택한 값이 있으면 메시지 override가 우선한다.

### 6.5 Hermes Home

Hermes Home은 Hermes의 로컬 상태 저장소다.

관리 대상:

- config
- memory files
- skills files
- sessions
- honcho data

Hermes Vibe는 Hermes Home을 수정하기 전에 snapshot을 남긴다. 잘못 수정했을 때 복구 근거를 남기기 위한 장치다.

### 6.6 Memory Editor

`~/.hermes/memories` 아래 파일을 조회하고 수정한다.

특징:

- 파일 목록 표시
- 파일 내용 읽기
- 파일 수정
- 수정 전 snapshot 저장
- lock file 제외

### 6.7 Skills Editor

`~/.hermes/skills` 아래 editable 파일을 조회하고 수정한다.

수정 가능한 확장자:

- `.md`
- `.txt`
- `.yaml`
- `.yml`
- `.json`

수정 전 snapshot이 저장된다.

### 6.8 Honcho Status

Honcho 상태 화면은 Hermes Home의 `honcho/` 폴더 상태를 보여준다.

표시 항목:

- honcho path
- 존재 여부
- 파일 개수
- 총 크기
- 최근 수정 파일
- app database path

## 7. Dashboard 설명

Dashboard는 단순 로그 뷰가 아니라, Hermes와의 작업을 학습/구현/디버깅 관점으로 다시 정리하는 화면이다.

backend는 Hermes 응답과 에러를 `DashboardEvent`로 저장하고, frontend는 그 이벤트를 카드 형태로 보여준다.

### 7.1 구현 현황

관련 event:

```text
implementation.summary.updated
```

보여주는 내용:

- 현재 목표
- 진행 중인 변경
- 다음 단계

용도:

- 지금 무엇을 만들고 있는지 빠르게 파악
- 다음에 이어서 할 작업 확인
- 긴 vibe coding 세션에서 맥락 회복

### 7.2 결정 기록

관련 event:

```text
decision.trace.created
```

보여주는 내용:

- 사용자 요청
- agent reasoning summary
- 사용된 tool
- 결과 파일
- outcome

용도:

- 왜 이 방향으로 구현했는지 추적
- 나중에 리팩토링/디버깅할 때 의사결정 근거 확인

### 7.3 학습 개념

관련 event:

```text
concept.detected
```

현재 analyzer는 메시지와 Hermes 응답에서 키워드를 찾아 개념 이벤트를 만든다.

예:

- CORS
- FastAPI
- React
- Electron
- pytest
- SSE
- SQLite
- honcho
- Hermes

용도:

- 오늘 작업에서 어떤 개념을 접했는지 확인
- 나중에 학습 노트로 확장할 재료 확보

### 7.4 디버깅/에러

관련 event:

```text
debug.error.detected
implementation.blocker.detected
error.learning_log.created
```

Hermes CLI가 실패하면 stderr/stdout을 모아 에러 이벤트를 만든다.

보여주는 내용:

- error message
- 어디서 발생했는지
- return code
- root cause summary
- fix summary
- prevention note

용도:

- 실패 원인 추적
- 반복되는 설정 문제 방지
- 에러를 학습 기록으로 전환

### 7.5 실시간 로그

관련 event:

```text
agent.tool.started
agent.log.chunk
agent.tool.completed
```

Hermes CLI 실행 명령, stdout/stderr chunk, 종료 코드를 기록한다.

용도:

- Hermes가 실제로 어떤 명령으로 실행됐는지 확인
- streaming 중 어디까지 진행됐는지 확인
- CLI 문제와 UI 문제를 분리해서 디버깅

## 8. 저장소와 데이터

앱 데이터는 SQLite에 저장된다.

기본 경로:

```text
~/.hermes-vibe/app.db
```

저장되는 데이터:

- dashboard events
- agent profiles
- coding sessions

Hermes 자체 상태는 Hermes Home에 저장된다.

기본 경로:

```text
~/.hermes
```

소스 repo에는 로컬 DB, 빌드 결과, release artifact, node_modules를 넣지 않는다. `.gitignore`가 이 파일들을 제외한다.

## 9. 테스트와 검증

backend 테스트:

```bash
cd /Users/songbongjune/vibe-learning/apps/api
/private/tmp/hermes-vibe-api-venv/bin/pytest -q
```

desktop build:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run build
```

Electron tests:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run test:electron
```

audit:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm audit --omit=dev
npm audit
```

packaged app smoke test:

```bash
cd /Users/songbongjune/vibe-learning
HERMES_VIBE_API_PORT=8110 "./apps/desktop/release/mac-arm64/Hermes Vibe.app/Contents/MacOS/Hermes Vibe"
curl -fsS http://127.0.0.1:8110/health
curl -fsS http://127.0.0.1:8110/hermes/fork
```

## 10. 패키징

macOS app directory 생성:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run package:dir
```

DMG/ZIP 생성:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run package:mac
```

패키징 과정:

1. icon 생성
2. Vite production build
3. Electron TypeScript build
4. Python runtime 생성
5. runtime-only API requirements 설치
6. Electron Builder packaging

runtime-only requirements:

```text
apps/api/requirements-runtime.txt
```

dev/test requirements:

```text
apps/api/requirements-dev.txt
```

현재 macOS 산출물은 Apple Developer ID가 없으면 ad-hoc signing 상태가 된다. notarization은 Apple Developer credential 설정 전까지 스킵된다.

## 11. 자주 생기는 문제

### 11.1 앱이 backend에 연결하지 못함

확인:

```bash
curl -fsS http://127.0.0.1:8000/health
```

안 되면 backend가 안 떠 있거나 포트가 다를 수 있다. Electron 앱은 내부적으로 fallback port를 고를 수 있으므로 앱의 backend status UI를 확인한다.

### 11.2 Hermes Home이 잘못됨

확인:

```bash
curl -fsS http://127.0.0.1:8000/hermes/home
```

앱에서 Hermes Home 경로를 다시 지정하고 backend restart를 실행한다.

### 11.3 Hermes CLI 실행 실패

Dashboard의 error/debug 카드에서 다음을 확인한다.

- stderr
- returncode
- selected model/provider
- HERMES_HOME
- Hermes fork metadata

주로 model/provider 설정, credential, Hermes Home 구조 문제가 원인이다.

### 11.4 다른 프로젝트 코드 맥락을 못 봄

backend가 target project cwd에서 떠 있는지 확인한다.

잘못된 예:

```bash
cd /Users/songbongjune/vibe-learning/apps/api
uvicorn hermes_vibe_api.app:create_app --factory
```

이 경우 Hermes는 앱 repo를 작업 대상으로 본다.

올바른 예:

```bash
cd /path/to/target-project
PYTHONPATH=/Users/songbongjune/vibe-learning/apps/api \
/private/tmp/hermes-vibe-api-venv/bin/python -m uvicorn hermes_vibe_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

## 12. 추천 운영 방식

평소에는 다음 구조로 쓴다.

```text
Hermes Vibe repo
  GUI, backend, dashboard 개발

Target project
  실제 vibe coding 대상

~/.hermes
  Hermes의 공통 memory/skills/honcho
```

한 프로젝트를 오래 작업할 때는 session을 분리한다.

예:

- `auth refactor`
- `dashboard cards polish`
- `packaging signing`
- `Hermes adapter QA`

작업이 끝난 session과 agent는 archive한다. 삭제는 정말 필요할 때만 사용한다.

## 13. 다음에 추가하면 좋은 기능

- Workspace Path 선택 UI
- 프로젝트별 workspace archive
- dashboard event 필터/검색
- concept note 자동 markdown 생성
- error learning log export
- Hermes adapter deep integration
- Apple Developer ID signing/notarization
