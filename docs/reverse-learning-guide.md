# Hermes Vibe Reverse Learning Guide

이 문서는 Hermes Vibe Desktop을 만들면서 구현한 내용을 바탕으로 역학습하는 방법을 정리한다.

역학습은 완성된 코드를 위에서 아래로 외우는 방식이 아니다. 작동 결과를 먼저 보고, 그 결과를 가능하게 만든 코드, 데이터 흐름, 설계 선택을 거꾸로 추적하는 방식이다.

## 1. 역학습 목표

이 프로젝트를 통해 배울 수 있는 핵심 주제는 다음과 같다.

- Electron + React desktop app 구조
- FastAPI backend 설계
- backend process를 Electron에서 띄우는 방식
- Hermes Agent CLI를 GUI 앱에 연결하는 방식
- streaming chat과 SSE 흐름
- agent/session CRUD
- local SQLite event store
- dashboard event projection
- memory/skills/config 파일 편집과 snapshot
- model/provider 선택 구조
- packaging, runtime dependency 분리, release artifact 생성
- Git repo 초기화와 GitHub push

## 2. 먼저 전체 그림 잡기

먼저 이 구조를 외운다.

```text
사용자
  -> React UI
  -> Electron main process
  -> FastAPI backend
  -> Hermes CLI
  -> stdout/stderr events
  -> SQLite 저장
  -> Dashboard projection
  -> React UI 표시
```

핵심 질문:

- 사용자가 메시지를 입력하면 어떤 API가 호출되는가?
- backend는 Hermes를 어떻게 실행하는가?
- Hermes 출력은 어디에 저장되는가?
- dashboard는 raw log를 그대로 보여주는가, 아니면 가공해서 보여주는가?
- agent profile은 runtime message에 어떻게 반영되는가?

## 3. 추천 학습 순서

### Step 1. 앱을 실행해보고 기능을 만져본다

개발 모드:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run dev
```

backend:

```bash
cd /Users/songbongjune/vibe-learning/apps/api
/private/tmp/hermes-vibe-api-venv/bin/python -m uvicorn hermes_vibe_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

브라우저:

```text
http://127.0.0.1:5173
```

관찰할 것:

- Agents 화면에서 agent 생성
- Sessions 화면에서 session 생성
- Chat에서 메시지 전송
- Dashboard 카드 변화 확인
- Hermes Home, Memory, Skills, Honcho 화면 확인

학습 질문:

- 어떤 화면이 어떤 backend endpoint를 호출하는가?
- 메시지 하나를 보냈을 때 event가 몇 개 생기는가?
- dashboard에는 어떤 종류의 카드가 생기는가?

### Step 2. frontend에서 API 호출을 추적한다

먼저 읽을 파일:

- `apps/desktop/src/App.tsx`
- `apps/desktop/src/api.ts`
- `apps/desktop/src/components/ChatPanel.tsx`
- `apps/desktop/src/components/DashboardPanel.tsx`
- `apps/desktop/src/components/AgentsPanel.tsx`
- `apps/desktop/src/components/SessionPanel.tsx`

추적 순서:

1. `ChatPanel`에서 submit이 발생한다.
2. `App.tsx`의 send handler로 올라간다.
3. `api.ts`의 stream/message API가 호출된다.
4. 응답 event를 React state에 반영한다.
5. Dashboard panel이 갱신된다.

학습 질문:

- Chat input은 언제 disabled 되는가?
- archived session/agent일 때 왜 메시지를 못 보내는가?
- cancel 버튼은 어떤 상태를 바꾸는가?
- dashboard는 직접 계산하는가, backend projection을 받는가?

실습:

- Chat placeholder 문구를 바꿔본다.
- Dashboard 카드 하나의 label을 바꿔본다.
- archived 상태의 disabled message를 더 명확하게 바꿔본다.

### Step 3. backend API를 추적한다

먼저 읽을 파일:

- `apps/api/hermes_vibe_api/app.py`
- `apps/api/hermes_vibe_api/agents.py`
- `apps/api/hermes_vibe_api/sessions.py`
- `apps/api/hermes_vibe_api/storage/sqlite_store.py`

핵심 endpoint:

- `GET /health`
- `GET /agents`
- `POST /agents`
- `GET /sessions`
- `POST /sessions`
- `POST /sessions/{session_id}/messages`
- `POST /sessions/{session_id}/messages/stream`
- `GET /sessions/{session_id}/dashboard`
- `GET /hermes/home`
- `PUT /hermes/home`

학습 질문:

- `create_app()`은 어떤 상태를 초기화하는가?
- `linked_home`, `active_runtime`, `store`는 각각 무엇인가?
- session이 없을 때 메시지를 보내면 어떤 일이 일어나는가?
- agent_id가 있는 메시지는 어떻게 보강되는가?

중요 흐름:

```text
POST /sessions/{id}/messages/stream
  -> ensure_session_can_receive_message
  -> enrich_message_from_agent_profile
  -> touch_session
  -> user_message_event 저장
  -> active_runtime.send_message
  -> runtime event 저장
  -> SSE로 event 전송
```

실습:

- 없는 agent_id로 메시지를 보내고 404를 확인한다.
- archived agent로 메시지를 보내고 409를 확인한다.
- session title이 처음 메시지에서 어떻게 만들어지는지 확인한다.

### Step 4. Hermes runtime adapter를 읽는다

먼저 읽을 파일:

- `apps/api/hermes_vibe_api/hermes/runtime.py`
- `apps/api/hermes_vibe_api/tests/test_cli_runtime.py`

핵심 클래스:

- `RuntimeMessage`
- `RuntimeCommandEvent`
- `HermesRuntime`
- `InProcessHermesRuntime`
- `HermesCLIBackedRuntime`

핵심 함수:

- `build_command`
- `build_environment`
- `send_message`
- `_send_message_streaming`
- `stream_subprocess_command`

중요 흐름:

```text
RuntimeMessage
  -> build_command
  -> python packages/hermes/hermes -z prompt
  -> stdout/stderr streaming
  -> chat.message.delta
  -> chat.message.completed
  -> analyzer events
```

학습 질문:

- system_prompt는 command prompt에 어떻게 합쳐지는가?
- provider/model override 우선순위는 어떻게 되는가?
- stdout과 stderr는 각각 어떤 event로 바뀌는가?
- subprocess cancel은 어떻게 처리되는가?

실습:

- fake stream runner를 만들어 stdout/stderr event 순서를 테스트한다.
- model override가 command에 붙는지 테스트한다.
- 실패 returncode일 때 debug event가 생기는지 확인한다.

### Step 5. Dashboard event 모델을 이해한다

먼저 읽을 파일:

- `apps/api/hermes_vibe_api/dashboard/schemas.py`
- `apps/api/hermes_vibe_api/dashboard/analyzer.py`
- `apps/api/hermes_vibe_api/dashboard/projections.py`
- `apps/api/hermes_vibe_api/tests/test_dashboard_projections.py`

event 종류:

```text
chat.message.user
chat.message.delta
chat.message.completed
agent.tool.started
agent.log.chunk
agent.tool.completed
implementation.summary.updated
decision.trace.created
concept.detected
implementation.blocker.detected
error.learning_log.created
debug.error.detected
```

학습 질문:

- analyzer는 언제 successful turn으로 판단하는가?
- failed turn에서는 어떤 학습 로그가 만들어지는가?
- concept keyword는 어디에 정의되어 있는가?
- projection은 raw event를 어떻게 카드 데이터로 바꾸는가?

실습:

- `CONCEPT_KEYWORDS`에 새 개념을 추가한다.
- 특정 에러 메시지에 대해 prevention note를 더 구체적으로 바꾼다.
- Dashboard projection test를 하나 추가한다.

### Step 6. Hermes Home, Memory, Skills, Snapshot을 이해한다

먼저 읽을 파일:

- `apps/api/hermes_vibe_api/hermes/home.py`
- `apps/api/hermes_vibe_api/hermes/snapshots.py`
- `apps/api/hermes_vibe_api/tests/test_hermes_home.py`
- `apps/api/hermes_vibe_api/tests/test_memory_api.py`
- `apps/api/hermes_vibe_api/tests/test_skills_api.py`

핵심 개념:

- Hermes Home은 `~/.hermes`가 기본이다.
- 앱은 config/memory/skills 파일을 직접 편집할 수 있다.
- 편집 전 snapshot을 남긴다.
- path traversal을 막기 위해 scoped path resolve를 사용한다.

학습 질문:

- Hermes Home에 필요한 디렉터리는 무엇인가?
- bootstrap 옵션은 언제 필요한가?
- 파일 수정 전 snapshot은 어디에 저장되는가?
- skills editor는 어떤 확장자만 허용하는가?

실습:

- memory file 수정 API를 호출하고 snapshot 생성을 확인한다.
- skills editor가 `.py` 파일을 거부하는지 확인한다.
- 잘못된 relative path가 404/차단되는지 확인한다.

### Step 7. Electron backend process 관리를 이해한다

먼저 읽을 파일:

- `apps/desktop/electron/main.ts`
- `apps/desktop/electron/backendProcess.ts`
- `apps/desktop/electron/backendProcess.test.ts`

핵심 개념:

- Electron main process가 FastAPI backend를 subprocess로 띄운다.
- backend port는 기본 8000이고, 충돌 시 fallback port를 선택한다.
- packaged app에서는 `Resources/api`, `Resources/python-runtime`을 사용한다.
- backend status/restart IPC를 renderer에 노출한다.

학습 질문:

- packaged app과 dev app은 API 경로를 어떻게 다르게 찾는가?
- Python executable 우선순위는 무엇인가?
- backend restart 시 Hermes Home은 어떻게 전달되는가?
- recent logs는 어디서 수집되는가?

실습:

- `HERMES_VIBE_API_PORT=8110`으로 패키지 앱을 띄운다.
- `/health`를 호출해 backend가 뜬 것을 확인한다.
- 잘못된 Hermes Home을 설정했을 때 status UI가 어떻게 반응하는지 본다.

### Step 8. Packaging과 release 구조를 이해한다

먼저 읽을 파일:

- `apps/desktop/package.json`
- `apps/desktop/scripts/prepare-python-runtime.sh`
- `apps/desktop/scripts/generate-icon.py`
- `apps/desktop/electron/packaging.test.ts`
- `apps/desktop/README.md`

패키징 명령:

```bash
cd /Users/songbongjune/vibe-learning/apps/desktop
npm run package:dir
npm run package:mac
```

중요 설계:

- runtime-only Python requirements와 dev/test requirements를 분리했다.
- release artifact, build output, node_modules는 Git에 올리지 않는다.
- macOS notarization은 Apple Developer credential이 필요하다.

학습 질문:

- 왜 `requirements-runtime.txt`와 `requirements-dev.txt`를 분리했는가?
- packaged app은 backend source를 어디에 담는가?
- Hermes fork metadata는 어디에 포함되는가?
- signing과 notarization은 왜 아직 남은 작업인가?

실습:

- `npm run package:dir` 후 packaged app을 smoke test 한다.
- runtime에 `pytest`가 없는지 확인한다.
- `npm audit` 결과를 확인한다.

## 4. 역학습 루틴

한 기능을 배울 때마다 다음 순서를 반복한다.

```text
1. UI에서 기능을 실행한다.
2. Network/API endpoint를 추정한다.
3. frontend handler를 찾는다.
4. backend route를 찾는다.
5. storage/runtime/analyzer로 내려간다.
6. test를 읽는다.
7. 작은 실패 케이스를 하나 만든다.
8. test를 통과시키며 코드를 수정한다.
9. 배운 내용을 5줄로 요약한다.
```

예시: "archived agent는 메시지를 못 보내야 한다"

```text
UI 관찰
  archived agent 선택
  chat disabled 또는 API 409 확인

frontend
  App.tsx / AgentsPanel.tsx / ChatPanel.tsx

backend
  app.py enrich_message_from_agent_profile

test
  test_message_endpoint_rejects_archived_agent_profile

학습 요약
  agent profile은 UI만 막으면 안 되고 backend에서도 막아야 한다.
```

## 5. 하루 학습 플랜

### Day 1. 전체 실행과 구조

- 앱 실행
- Hermes Home 확인
- agent/session/chat/dashboard 사용
- `App.tsx`, `app.py` 훑기
- 전체 흐름 다이어그램 직접 그리기

### Day 2. Chat과 runtime

- `ChatPanel.tsx`
- `api.ts`
- `runtime.py`
- `test_cli_runtime.py`
- stdout/stderr streaming 테스트 읽기

### Day 3. Agents와 Sessions

- agent CRUD
- session CRUD
- archive/delete/restore
- duplicate cleanup
- 관련 API 테스트 읽기

### Day 4. Dashboard

- event schema
- analyzer
- projection
- dashboard UI
- concept keyword 하나 추가 실습

### Day 5. Hermes Home과 파일 편집

- home detection/bootstrap
- memory editor
- skills editor
- snapshots
- path safety

### Day 6. Electron과 Packaging

- Electron main process
- backend subprocess manager
- packaged resource path
- Python runtime packaging
- `package:dir` smoke test

### Day 7. 다른 프로젝트에 적용

- target project에서 backend 실행
- Hermes Vibe frontend 연결
- session 생성
- dashboard event 확인
- 적용 과정 문서화

## 6. 기능별 역질문 리스트

### Chat

- 메시지는 어디서 저장되는가?
- streaming과 non-streaming endpoint는 무엇이 다른가?
- cancel은 backend process까지 도달하는가?
- Hermes 실패는 어떻게 dashboard error가 되는가?

### Agent

- agent profile은 어느 테이블에 저장되는가?
- agent model보다 message model이 우선하는 이유는 무엇인가?
- archived agent를 backend에서도 막는 이유는 무엇인가?

### Session

- session은 언제 자동 생성되는가?
- title은 어떻게 만들어지는가?
- archive와 delete는 데이터 보존 관점에서 어떻게 다른가?
- duplicate cleanup 기준은 무엇인가?

### Dashboard

- raw event와 projection은 왜 분리했는가?
- concept.detected는 어떻게 만들어지는가?
- implementation summary는 얼마나 신뢰할 수 있는가?
- 에러를 learning log로 만드는 이유는 무엇인가?

### Hermes Home

- 왜 `~/.hermes`를 공유 저장소로 쓰는가?
- 파일 수정 전 snapshot이 필요한 이유는 무엇인가?
- path traversal 방어는 어디서 하는가?

### Packaging

- 왜 Python runtime을 앱에 포함하는가?
- 왜 test dependency를 runtime에서 뺐는가?
- release artifact를 Git에 넣으면 안 되는 이유는 무엇인가?
- notarization이 필요한 이유는 무엇인가?

## 7. 직접 해볼 미니 과제

### 과제 1. 새 concept keyword 추가

목표:

- `zustand` 또는 `tailwind` 같은 새 개념을 dashboard에 감지시키기

수정 후보:

- `apps/api/hermes_vibe_api/dashboard/analyzer.py`
- `apps/api/hermes_vibe_api/tests/test_session_analyzer.py`

완료 조건:

- 관련 테스트 통과
- Chat 응답에 keyword가 있으면 dashboard concept 카드에 표시

### 과제 2. Workspace Path 선택 UI 설계

목표:

- 다른 프로젝트 적용을 UI에서 쉽게 만들기

생각할 항목:

- workspace path 저장 위치
- backend restart 필요 여부
- packaged app에서 권한 문제
- 최근 workspace 목록

수정 후보:

- `apps/desktop/src/components/HermesSettingsPanel.tsx`
- `apps/desktop/electron/backendProcess.ts`
- `apps/api/hermes_vibe_api/app.py`

### 과제 3. Error learning log 강화

목표:

- model credential error, Hermes Home error, CLI missing error를 더 구분하기

수정 후보:

- `apps/api/hermes_vibe_api/dashboard/analyzer.py`
- `apps/api/hermes_vibe_api/tests/test_session_analyzer.py`

완료 조건:

- error category 표시
- prevention note가 더 구체적

### 과제 4. Dashboard filter 추가

목표:

- concept/debug/implementation event를 필터링해서 보기

수정 후보:

- `apps/desktop/src/components/DashboardPanel.tsx`
- `apps/desktop/src/styles.css`

완료 조건:

- UI에서 event category 선택 가능
- 모바일/데스크톱 레이아웃 깨지지 않음

## 8. 학습 노트 템플릿

기능 하나를 공부한 뒤 아래 형식으로 정리한다.

```markdown
# 학습 주제

## 사용자가 보는 동작

## 관련 파일

## 데이터 흐름

## 핵심 코드

## 테스트가 보장하는 것

## 내가 헷갈린 점

## 5줄 요약

## 다음에 바꿔볼 것
```

예시:

```markdown
# Agent profile enrichment

## 사용자가 보는 동작
agent를 선택하고 메시지를 보내면 agent의 system prompt와 model이 자동 적용된다.

## 관련 파일
apps/api/hermes_vibe_api/app.py
apps/api/hermes_vibe_api/tests/test_message_api.py

## 데이터 흐름
agent_id -> store.get_agent -> RuntimeMessage.model_copy -> runtime.send_message

## 테스트가 보장하는 것
agent_name/system_prompt/provider/model이 runtime message에 들어간다.
archived agent는 409로 막힌다.

## 5줄 요약
UI 선택만 믿으면 안 된다.
backend가 agent_id를 기준으로 profile을 다시 조회해야 한다.
message override가 있으면 override가 우선한다.
archived agent는 backend에서 막아야 한다.
이 로직은 streaming/non-streaming 모두 동일해야 한다.
```

## 9. 역학습할 때 주의할 점

- 처음부터 모든 파일을 읽지 않는다.
- UI 동작 하나를 정하고 그 동작의 데이터 흐름만 따라간다.
- 테스트를 먼저 읽으면 설계 의도가 빨리 보인다.
- dashboard는 raw log가 아니라 event projection이라는 점을 기억한다.
- Hermes Vibe repo와 target project의 역할을 섞지 않는다.
- `node_modules`, `release`, local DB는 학습 대상이 아니라 생성물이다.

## 10. 최종 체크

이 프로젝트를 이해했다고 말하려면 다음 질문에 답할 수 있어야 한다.

- 다른 프로젝트를 target workspace로 연결하는 명령을 쓸 수 있는가?
- 메시지 하나가 dashboard card가 되기까지의 흐름을 설명할 수 있는가?
- agent profile이 runtime message에 적용되는 위치를 찾을 수 있는가?
- Hermes CLI 실패가 어떤 event로 저장되는지 설명할 수 있는가?
- Memory/Skills 수정 전 snapshot이 왜 필요한지 설명할 수 있는가?
- packaged app이 backend와 Python runtime을 어떻게 포함하는지 설명할 수 있는가?
- release artifact를 Git에 넣지 않는 이유를 설명할 수 있는가?
