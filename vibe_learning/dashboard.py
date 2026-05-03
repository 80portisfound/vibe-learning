"""
Dashboard generator: produces a self-contained HTML file from project data.
"""
import json
import os
from .dashboard_engine import DashboardEngine


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>바이브 러닝 대시보드</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --surface-2: #1c2128; --surface-3: #22272e;
    --border: #30363d; --border-light: #484f58;
    --text: #e6edf3; --text-muted: #8b949e; --text-dim: #6e7681;
    --accent: #58a6ff; --accent-soft: rgba(88,166,255,.12);
    --ok: #3fb950; --ok-soft: rgba(63,185,80,.12);
    --warn: #d29922; --warn-soft: rgba(210,153,34,.12);
    --danger: #f85149; --danger-soft: rgba(248,81,73,.12);
    --purple: #bc8cff; --purple-soft: rgba(188,140,255,.12);
    --cyan: #39c5cf; --cyan-soft: rgba(57,197,207,.12);
    --orange: #ff9e42; --orange-soft: rgba(255,158,66,.12);
  }
  * { box-sizing: border-box; }
  body { margin:0; padding:0; background:var(--bg); color:var(--text); font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,"Apple SD Gothic Neo","Malgun Gothic",sans-serif; line-height:1.6; }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 32px 20px; }

  h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.3px; }
  h2 { font-size: 14px; margin: 0 0 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }
  .subtitle { color: var(--text-dim); font-size: 13px; margin-bottom: 28px; }

  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 14px; padding: 20px; }
  .card + .card { margin-top: 16px; }

  /* Tabs */
  .tabs { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
  .tab { padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; background: transparent; border: 1px solid transparent; color: var(--text-muted); transition: all .15s; }
  .tab:hover { background: var(--surface-2); color: var(--text); }
  .tab.active { background: var(--accent-soft); color: var(--accent); border-color: rgba(88,166,255,.25); }

  .tab-panel { display: none; }
  .tab-panel.active { display: block; }

  /* Hero */
  .hero { display: grid; grid-template-columns: 1fr 280px; gap: 20px; align-items: start; }
  .hero-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }
  .hero-concept { font-size: 32px; font-weight: 800; letter-spacing: -0.8px; margin: 0 0 8px; }
  .hero-prompt { font-size: 14px; color: var(--text-muted); margin-bottom: 16px; }
  .hero-tags { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  .tag { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; background: var(--surface-2); border: 1px solid var(--border); }
  .tag.accent { background: var(--accent-soft); color: var(--accent); border-color: rgba(88,166,255,.25); }
  .tag.ok { background: var(--ok-soft); color: var(--ok); border-color: rgba(63,185,80,.25); }
  .tag.warn { background: var(--warn-soft); color: var(--warn); border-color: rgba(210,153,34,.25); }
  .tag.danger { background: var(--danger-soft); color: var(--danger); border-color: rgba(248,81,73,.25); }

  .confusion-box { background: var(--danger-soft); border: 1px solid rgba(248,81,73,.2); border-radius: 10px; padding: 12px 14px; font-size: 13px; }
  .confusion-box .head { color: var(--danger); font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .confusion-box .body { color: #ff9e9e; }

  .mood-box { background: var(--purple-soft); border: 1px solid rgba(188,140,255,.2); border-radius: 10px; padding: 12px 14px; font-size: 13px; margin-top: 10px; }
  .mood-box .head { color: var(--purple); font-weight: 700; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .mood-box .body { color: #d9c2ff; }

  .progress-wrap { margin-top: 18px; }
  .progress-meta { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
  .progress-bar { height: 8px; background: var(--surface-2); border-radius: 999px; overflow: hidden; border: 1px solid var(--border); }
  .progress-fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--purple)); border-radius: 999px; transition: width .6s ease; }

  .side-list { list-style: none; padding: 0; margin: 0; }
  .side-list li { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px; }
  .side-list li:last-child { border-bottom: none; }
  .side-list .k { color: var(--text-muted); }
  .side-list .v { color: var(--text); font-weight: 600; }

  /* Timeline */
  .timeline-wrap { display: flex; align-items: stretch; gap: 12px; overflow-x: auto; padding-bottom: 8px; }
  .tl-col { flex: 1; min-width: 200px; display: flex; flex-direction: column; gap: 10px; }
  .tl-header { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; padding: 6px 10px; border-radius: 8px; text-align: center; }
  .tl-header.past { background: var(--surface-2); color: var(--text-dim); }
  .tl-header.present { background: var(--accent-soft); color: var(--accent); border: 1px solid rgba(88,166,255,.25); }
  .tl-header.future { background: var(--purple-soft); color: var(--purple); border: 1px solid rgba(188,140,255,.25); }
  .tl-item { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 12px; font-size: 13px; }
  .tl-item.dim { opacity: .6; border-style: dashed; }
  .tl-item .tl-date { font-size: 11px; color: var(--text-dim); margin-bottom: 4px; }
  .tl-item .tl-concept { font-weight: 700; color: var(--text); margin-bottom: 4px; }
  .tl-item .tl-prompt { color: var(--text-muted); font-size: 12px; line-height: 1.4; }
  .tl-item .tl-exp { margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); font-size: 11px; color: var(--text-dim); }
  .tl-item .tl-exp::before { content: "실험: "; color: var(--warn); font-weight: 600; }
  .tl-empty { text-align: center; color: var(--text-dim); font-size: 12px; padding: 20px; border: 1px dashed var(--border); border-radius: 10px; }

  /* Concept Map */
  .concept-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
  .concept-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; transition: border-color .2s, transform .15s; }
  .concept-card:hover { border-color: var(--border-light); transform: translateY(-2px); }
  .concept-card.dim { opacity: .55; }
  .concept-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .concept-name { font-size: 16px; font-weight: 800; letter-spacing: -0.3px; }
  .concept-badge { font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 20px; }
  .badge-mastered { background: var(--ok-soft); color: var(--ok); }
  .badge-learning { background: var(--warn-soft); color: var(--warn); }
  .badge-exploring { background: var(--danger-soft); color: var(--danger); }

  .concept-bar-bg { height: 6px; background: var(--bg); border-radius: 999px; overflow: hidden; margin-bottom: 12px; }
  .concept-bar-fill { height: 100%; border-radius: 999px; }
  .bar-mastered { background: var(--ok); }
  .bar-learning { background: var(--warn); }
  .bar-exploring { background: var(--danger); }

  .concept-meta { display: flex; gap: 12px; font-size: 11px; color: var(--text-muted); margin-bottom: 10px; }
  .concept-shapes { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 12px; color: var(--accent); background: var(--bg); padding: 8px 10px; border-radius: 8px; margin-bottom: 10px; border: 1px solid var(--border); }
  .concept-links { display: flex; flex-wrap: wrap; gap: 6px; }
  .clink { font-size: 11px; padding: 2px 8px; border-radius: 20px; background: var(--surface); border: 1px solid var(--border); color: var(--text-muted); }

  /* Next Steps */
  .step-list { display: flex; flex-direction: column; gap: 10px; }
  .step-item { display: flex; align-items: flex-start; gap: 12px; background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
  .step-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; }
  .dot-high { background: var(--danger); box-shadow: 0 0 8px rgba(248,81,73,.4); }
  .dot-medium { background: var(--warn); }
  .dot-low { background: var(--text-dim); }
  .step-body { flex: 1; }
  .step-title { font-size: 13px; font-weight: 700; margin-bottom: 2px; }
  .step-desc { font-size: 12px; color: var(--text-muted); line-height: 1.5; }
  .step-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; padding: 2px 6px; border-radius: 4px; margin-left: auto; white-space: nowrap; }
  .tag-gap { background: var(--danger-soft); color: var(--danger); }
  .tag-exp { background: var(--accent-soft); color: var(--accent); }
  .tag-next { background: var(--purple-soft); color: var(--purple); }

  /* Agent Swarm Tab */
  .pipeline-flow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: 16px 0; padding: 16px; background: var(--bg); border: 1px solid var(--border); border-radius: 12px; }
  .p-step { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 14px; border-radius: 10px; background: var(--surface-2); border: 1px solid var(--border); min-width: 90px; text-align: center; }
  .p-step .p-name { font-size: 12px; font-weight: 700; }
  .p-step .p-file { font-size: 10px; color: var(--text-dim); font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }
  .p-arrow { color: var(--text-dim); font-size: 14px; }

  .agent-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }
  .agent-card { background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 16px; transition: border-color .2s; }
  .agent-card:hover { border-color: var(--border-light); }
  .agent-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .agent-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; flex-shrink: 0; }
  .agent-title { font-size: 15px; font-weight: 800; }
  .agent-role { font-size: 11px; color: var(--text-muted); }
  .agent-file { font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 11px; color: var(--accent); margin-bottom: 10px; }
  .agent-summary { font-size: 12px; color: var(--text-muted); line-height: 1.6; margin-bottom: 10px; }
  .agent-rules { list-style: none; padding: 0; margin: 0; }
  .agent-rules li { font-size: 11px; color: var(--text-dim); padding: 3px 0; border-bottom: 1px solid var(--border); }
  .agent-rules li:last-child { border-bottom: none; }
  .agent-rules li::before { content: "✓ "; color: var(--ok); font-weight: 700; }
  .agent-status { margin-top: 10px; display: flex; gap: 6px; }
  .astatus { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px; }

  .arch-card { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px; }
  .arch-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }
  .arch-layer { padding: 6px 12px; border-radius: 8px; font-size: 12px; font-weight: 700; }
  .arch-user { background: var(--accent-soft); color: var(--accent); border: 1px solid rgba(88,166,255,.25); }
  .arch-adapter { background: var(--warn-soft); color: var(--warn); border: 1px solid rgba(210,153,34,.25); }
  .arch-core { background: var(--ok-soft); color: var(--ok); border: 1px solid rgba(63,185,80,.25); }
  .arch-data { background: var(--purple-soft); color: var(--purple); border: 1px solid rgba(188,140,255,.25); }
  .arch-arrow { color: var(--text-dim); font-size: 12px; }

  /* Debug */
  .debug-toggle { display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none; padding: 4px 0; }
  .debug-toggle h2 { margin: 0; }
  .chevron { transition: transform .2s; color: var(--text-dim); font-size: 12px; }
  .debug-body { display: none; margin-top: 14px; }
  .debug-body.open { display: block; }
  .debug-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
  .debug-stat { background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 12px; text-align: center; }
  .debug-stat .n { font-size: 22px; font-weight: 800; color: var(--text); }
  .debug-stat .l { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
  .debug-log { margin-top: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 12px; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; font-size: 11px; color: var(--text-muted); max-height: 180px; overflow-y: auto; line-height: 1.6; }

  footer { margin-top: 40px; text-align: center; color: var(--text-dim); font-size: 12px; }

  @media (max-width: 720px) {
    .hero { grid-template-columns: 1fr; }
    .timeline-wrap { flex-direction: column; }
  }
</style>
</head>
<body>
<div class="wrap">
  <h1>🔮 바이브 러닝 대시보드</h1>
  <div class="subtitle">나의 코딩 여행 지도 / 과거에서 현재, 그리고 미래를 향해</div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('learner')">📚 학습 여행</div>
    <div class="tab" onclick="switchTab('agents')">🤖 에이전트 스웨어봐</div>
  </div>

  <!-- ==================== LEARNER TAB ==================== -->
  <div class="tab-panel active" id="tab-learner">
    <div class="card hero">
      <div class="hero-main">
        <div class="hero-label">현재 학습 영역</div>
        <div class="hero-concept" id="hero-concept">-</div>
        <div class="hero-prompt" id="hero-prompt">지금은 바이브 코딩 세션이 없습니다.</div>
        <div class="hero-tags" id="hero-tags"></div>
        <div class="confusion-box" id="confusion-box" style="display:none">
          <div class="head">현재 궁금증 (Confusion)</div>
          <div class="body" id="confusion-text"></div>
        </div>
        <div class="mood-box" id="mood-box" style="display:none">
          <div class="head">발견 순간 (Feeling)</div>
          <div class="body" id="mood-text"></div>
        </div>
        <div class="progress-wrap">
          <div class="progress-meta">
            <span>📊 타임라인 진행도</span>
            <span id="progress-text">0%</span>
          </div>
          <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width:0%"></div></div>
        </div>
      </div>
      <div>
        <h2>세션 정보</h2>
        <ul class="side-list">
          <li><span class="k">소스</span><span class="v" id="side-tool">-</span></li>
          <li><span class="k">Session ID</span><span class="v" id="side-id">-</span></li>
          <li><span class="k">노트 수</span><span class="v" id="side-notes">0</span></li>
          <li><span class="k">개념 수</span><span class="v" id="side-concepts">0</span></li>
          <li><span class="k">실험 수</span><span class="v" id="side-exps">0</span></li>
          <li><span class="k">범용 도구</span><span class="v" id="side-tools">-</span></li>
        </ul>
      </div>
    </div>

    <div class="card">
      <h2>📅 타임라인: 과거 → 현재 → 미래</h2>
      <div class="timeline-wrap" id="timeline"></div>
    </div>

    <div class="card">
      <h2>🧠 핵심 개념 지도</h2>
      <div class="concept-grid" id="concept-grid"></div>
    </div>

    <div class="card">
      <h2>🎯 다음 스텝 / 앞으로 할 일</h2>
      <div class="step-list" id="next-steps"></div>
    </div>

    <div class="card">
      <div class="debug-toggle" onclick="toggleDebug()">
        <h2>🔧 디버그 및 통계 (펼쳐보기)</h2>
        <span class="chevron" id="chevron">&#9654;</span>
      </div>
      <div class="debug-body" id="debug-body">
        <div class="debug-grid" id="debug-stats"></div>
        <div class="debug-log" id="debug-log"></div>
      </div>
    </div>
  </div>

  <!-- ==================== AGENT SWARM TAB ==================== -->
  <div class="tab-panel" id="tab-agents">
    <div class="card">
      <h2>🖼️ 아키템 개요</h2>
      <div class="arch-card">
        <div class="arch-row">
          <span class="arch-layer arch-user">사용자 (Any IDE)</span>
          <span class="arch-arrow">→</span>
          <span class="arch-layer arch-adapter">어댑터 레이어</span>
          <span class="arch-arrow">→</span>
          <span class="arch-layer arch-core">유니버셜 컨텍스 스키마</span>
          <span class="arch-arrow">→</span>
          <span class="arch-layer arch-core">오케스트레이터 → 6 Agents</span>
          <span class="arch-arrow">→</span>
          <span class="arch-layer arch-data">컬렉션 + ChromaDB</span>
        </div>
        <div style="font-size:12px;color:var(--text-muted);margin-top:4px;">
          핵심 처학: "에이전트는 IDE를 몰라야 한다. 오직 유니버셜 컨텍스 스키마만 알아야 한다."
        </div>
      </div>
    </div>

    <div class="card">
      <h2>⚡ 파이프라인 플로우</h2>
      <div class="pipeline-flow" id="pipeline-flow"></div>
    </div>

    <div class="card">
      <h2>💼 에이전트 상세 정보 & 구현 요약</h2>
      <div class="agent-grid" id="agent-grid"></div>
    </div>
  </div>

  <footer>
    Vibe Coding Learning Agent Swarm v3.0 / 나의 코드가 내 지식이 된다
  </footer>
</div>

<script>
const DATA = {{DATA_JSON}};

const AGENTS = [
  {
    name: "Orchestrator",
    icon: "🎭",
    color: "#58a6ff",
    bg: "rgba(88,166,255,.12)",
    file: "agents/orchestrator.py",
    func: "run()",
    role: "전체 파이프라인 흐름 제어. 실패 시 분기 처리.",
    summary: "6개 에이전트의 실행 순서를 관리한다. 각 에이전트가 실패해도 비어 있는 값을 다음 단계로 전달하여 파이프라인이 중단되지 않도록 보장한다. CodeScanner → ShapeTracker → ConceptLinker → NoteArchitect → RecallAgent 순으로 추진한다.",
    rules: ["파이프라인 중단 없이 빈 값으로 다음 단계 진행", "에이전트 간 데이터 흘림 제어", "실행 로그 출력"]
  },
  {
    name: "Code Scanner",
    icon: "🔍",
    color: "#ff9e42",
    bg: "rgba(255,158,66,.12)",
    file: "agents/code_scanner.py",
    func: "scan(), _analyze_call()",
    role: "모르는 코드 블록 추출, confusion_score 태깅.",
    summary: "AST(추상 구문 트리)를 파싱하여 코드 안의 Call 노드를 분석한다. diff 형식의 코드도 청소하여 AST 파싱 가능하게 만든다. 기본 키워드(for/if/class)는 무시하고, encoder/embedding/tokenizer 등 도메인 키워드만 추출하여 confusion_score을 부여한다.",
    rules: ["for/if/class 무시", "domain keyword 추출", "confusion_score 0~100 태깅", "diff 크리닝 후 AST 파싱"]
  },
  {
    name: "Shape Tracker",
    icon: "📊",
    color: "#3fb950",
    bg: "rgba(63,185,80,.12)",
    file: "agents/shape_tracker.py",
    func: "track(), llm_infer_shapes()",
    role: "테서/데이터 shape 변화 추적. Python 리스트 관점 설명.",
    summary: "코드 블록의 입력/출력 shape를 추적한다. 사전 정의된 SHAPE_HINTS 맵을 통해 정적 분석을 시도하고, 매칭되지 않으면 LLM fallback을 활성화한다. 수학 기호(ℝ, Σ) 없이 오직 Python 리스트 관점으로만 설명한다.",
    rules: ["수학 기호 금지", "Python 리스트 관점으로만 설명", "정적 분석 실패 시 LLM fallback", "encode → [N,768] 등 shape 히트 맵핑"]
  },
  {
    name: "Concept Linker",
    icon: "🔗",
    color: "#bc8cff",
    bg: "rgba(188,140,255,.12)",
    file: "agents/concept_linker.py",
    func: "link(), _infer_gaps(), _generate_experiment()",
    role: "새 개념을 SWE 지식과 연결 + 5분 실험 질문 생성.",
    summary: "새로운 등장한 개념을 기존 소프트웨어 공학 지식(HashMap, Pub-Sub, B-Tree 등)과 연결한다. 사용자의 궁금증(gap)을 추론하고, 5분이면 끝날 수 있는 실험 질문을 자동 생성한다. 깊은 의미의 비유(embedding=HashMap.get) 기반.",
    rules: ["딥러닝 고유 개념 격리 안 함", "HashMap, Pub-Sub, B-Tree 등 SWE 개념과 연결", "5분 실험 원칙", "gap 추론 및 등록"]
  },
  {
    name: "Note Architect",
    icon: "📝",
    color: "#39c5cf",
    bg: "rgba(57,197,207,.12)",
    file: "agents/note_architect.py",
    func: "build(), save()",
    role: "마크다운 노트 자동 생성 및 저장.",
    summary: "사용자가 직접 쓴 feeling과 confusion만 입력하면, 나머지 모든 필드(shapes, linked_concepts, AI 설계 추론, 오늘의 실험, 다음 실험)을 자동으로 채워 마크다운 노트를 생성한다. 프롬프트 내용을 분석하여 AI가 어떤 설계 선택을 했는지 추론한다.",
    rules: ["사용자는 feeling, confusion만 쓴다", "나머지는 자동 채움", "AI 설계 추론 필드 포함", "frontmatter + 마크다운 바디 자동 생성"]
  },
  {
    name: "Recall Agent",
    icon: "📖",
    color: "#f85149",
    bg: "rgba(248,81,73,.12)",
    file: "agents/recall_agent.py",
    func: "index_note(), recall()",
    role: "노트 벡터화 및 ChromaDB 저장, 유사도 검색.",
    summary: "sentence-transformers를 사용해 노트 내용을 벡터화하고 ChromaDB에 저장한다. 자연어 쿼리를 받으면 벡터 유사도를 기반으로 관련 노트를 검색해 반환한다. 이 에이전트 자체가 RAG(Retrieval-Augmented Generation)의 원리를 체험하도록 하는 구조다.",
    rules: ["ChromaDB 지속 저장", "sentence-transformers 임베딩", "자연어 쿼리 → 벡터 유사도 검색", "RAG 원리 체험"]
  }
];

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('tab-' + name).classList.add('active');
}

/* ====== Learner Tab Renderers ====== */
function renderHero() {
  const pos = DATA.current_position;
  document.getElementById('hero-concept').textContent = pos.active_concept || '-';
  document.getElementById('hero-prompt').textContent = pos.source_prompt || '지금은 바이브 코딩 세션이 없습니다.';
  const tags = document.getElementById('hero-tags');
  tags.innerHTML = '';
  const addTag = (text, cls) => { const s = document.createElement('span'); s.className = 'tag ' + cls; s.textContent = text; tags.appendChild(s); };
  addTag(pos.source_tool || '-', 'accent');
  if (pos.session_id && pos.session_id !== '-') addTag('#' + pos.session_id, '');
  const confusionBox = document.getElementById('confusion-box');
  if (pos.confusion) { confusionBox.style.display = 'block'; document.getElementById('confusion-text').textContent = pos.confusion; }
  const moodBox = document.getElementById('mood-box');
  if (pos.mood) { moodBox.style.display = 'block'; document.getElementById('mood-text').textContent = pos.mood; }
  document.getElementById('progress-text').textContent = (pos.progress_pct || 0) + '%';
  setTimeout(() => { document.getElementById('progress-fill').style.width = (pos.progress_pct || 0) + '%'; }, 100);
  document.getElementById('side-tool').textContent = pos.source_tool || '-';
  document.getElementById('side-id').textContent = pos.session_id || '-';
  document.getElementById('side-notes').textContent = DATA.stats.total_notes;
  document.getElementById('side-concepts').textContent = DATA.stats.total_concepts;
  document.getElementById('side-exps').textContent = DATA.stats.total_experiments;
  const tools = Object.entries(DATA.stats.tool_usage || {}).map(([k,v]) => `${k}(${v})`).join(', ');
  document.getElementById('side-tools').textContent = tools || '-';
}

function renderTimeline() {
  const t = DATA.timeline;
  const wrap = document.getElementById('timeline');
  wrap.innerHTML = '';
  const makeCol = (items, label, cls) => {
    const col = document.createElement('div'); col.className = 'tl-col';
    const h = document.createElement('div'); h.className = 'tl-header ' + cls; h.textContent = label; col.appendChild(h);
    if (!items || items.length === 0) {
      const empty = document.createElement('div'); empty.className = 'tl-empty';
      empty.textContent = cls === 'future' ? '앞으로 확장될 실험이 여기에 작성됩니다.' : '아직 기록이 없습니다.';
      col.appendChild(empty);
    } else {
      items.forEach(it => {
        const el = document.createElement('div');
        const isDim = it.concept === 'Unknown';
        el.className = 'tl-item' + (isDim ? ' dim' : '');
        el.innerHTML = `
          <div class="tl-date">${it.date}</div>
          <div class="tl-concept">${it.concept}</div>
          <div class="tl-prompt">${it.prompt}</div>
          ${it.experiment && it.experiment !== '-' ? `<div class="tl-exp">${it.experiment}</div>` : ''}
        `;
        col.appendChild(el);
      });
    }
    return col;
  };
  wrap.appendChild(makeCol(t.past, '과거', 'past'));
  wrap.appendChild(makeCol(t.present, '현재', 'present'));
  wrap.appendChild(makeCol(t.future, '미래', 'future'));
}

function renderConcepts() {
  const grid = document.getElementById('concept-grid');
  grid.innerHTML = '';
  DATA.concept_map.forEach(c => {
    const card = document.createElement('div');
    const isDim = c.name === 'Unknown';
    card.className = 'concept-card' + (isDim ? ' dim' : '');
    const badgeCls = c.status === '익숙함' ? 'badge-mastered' : c.status === '학습중' ? 'badge-learning' : 'badge-exploring';
    const barCls = c.status === '익숙함' ? 'bar-mastered' : c.status === '학습중' ? 'bar-learning' : 'bar-exploring';
    const links = (c.linked || []).map(l => `<span class="clink">${l}</span>`).join('');
    const shapes = (c.shapes || []).map(s => `<div class="concept-shapes">${s}</div>`).join('');
    card.innerHTML = `
      <div class="concept-head">
        <div class="concept-name">${c.name}</div>
        <div class="concept-badge ${badgeCls}">${c.status}</div>
      </div>
      <div class="concept-bar-bg"><div class="concept-bar-fill ${barCls}" style="width:${c.understanding}%"></div></div>
      <div class="concept-meta">
        <span>등장 ${c.mentions}회</span>
        <span>이해도 ${c.understanding}%</span>
        <span>${c.dates.join(', ')}</span>
      </div>
      ${shapes}
      <div class="concept-links">${links}</div>
    `;
    grid.appendChild(card);
  });
}

function renderNextSteps() {
  const list = document.getElementById('next-steps');
  list.innerHTML = '';
  DATA.next_steps.forEach(s => {
    const el = document.createElement('div'); el.className = 'step-item';
    const dotCls = s.priority === 'high' ? 'dot-high' : s.priority === 'medium' ? 'dot-medium' : 'dot-low';
    const tagCls = s.type === 'gap' ? 'tag-gap' : s.type === 'experiment' ? 'tag-exp' : 'tag-next';
    const tagText = s.type === 'gap' ? 'GAPS' : s.type === 'experiment' ? 'EXPERIMENT' : 'NEXT';
    el.innerHTML = `
      <div class="step-dot ${dotCls}"></div>
      <div class="step-body">
        <div class="step-title">${s.title}</div>
        <div class="step-desc">${s.desc}</div>
      </div>
      <div class="step-tag ${tagCls}">${tagText}</div>
    `;
    list.appendChild(el);
  });
}

function renderDebug() {
  const stats = DATA.stats;
  const grid = document.getElementById('debug-stats');
  grid.innerHTML = '';
  const items = [
    {n: stats.total_notes, l: '총 노트'},
    {n: stats.total_concepts, l: '총 개념'},
    {n: stats.total_experiments, l: '실험 수'},
    {n: stats.total_gaps, l: '궁금증 수'},
  ];
  items.forEach(it => {
    const div = document.createElement('div'); div.className = 'debug-stat';
    div.innerHTML = `<div class="n">${it.n}</div><div class="l">${it.l}</div>`;
    grid.appendChild(div);
  });
  const log = document.getElementById('debug-log');
  log.innerHTML = `[Orchestrator] Pipeline started<br>` +
    `[Orchestrator] CodeScanner: ${stats.total_notes} blocks found<br>` +
    `[Orchestrator] ShapeTracker: ${stats.total_notes} tracked<br>` +
    `[Orchestrator] ConceptLinker: ${stats.total_concepts} linked<br>` +
    `[Orchestrator] NoteArchitect: saved to concepts/<br>` +
    `[Orchestrator] RecallAgent: indexed=True<br>` +
    `[Orchestrator] Pipeline finished`;
}

function toggleDebug() {
  const body = document.getElementById('debug-body');
  const chev = document.getElementById('chevron');
  body.classList.toggle('open');
  chev.style.transform = body.classList.contains('open') ? 'rotate(90deg)' : 'rotate(0deg)';
}

/* ====== Agent Swarm Tab Renderers ====== */
function renderPipelineFlow() {
  const wrap = document.getElementById('pipeline-flow');
  wrap.innerHTML = '';
  AGENTS.forEach((a, i) => {
    const step = document.createElement('div');
    step.className = 'p-step';
    step.style.borderColor = a.color + '40';
    step.innerHTML = `
      <div class="p-name" style="color:${a.color}">${a.name}</div>
      <div class="p-file">${a.file}</div>
    `;
    wrap.appendChild(step);
    if (i < AGENTS.length - 1) {
      const arrow = document.createElement('span');
      arrow.className = 'p-arrow';
      arrow.innerHTML = '&#8594;';
      wrap.appendChild(arrow);
    }
  });
}

function renderAgentGrid() {
  const grid = document.getElementById('agent-grid');
  grid.innerHTML = '';
  AGENTS.forEach(a => {
    const card = document.createElement('div');
    card.className = 'agent-card';
    const rules = a.rules.map(r => `<li>${r}</li>`).join('');
    card.innerHTML = `
      <div class="agent-head">
        <div class="agent-icon" style="background:${a.bg};color:${a.color}">${a.icon}</div>
        <div>
          <div class="agent-title">${a.name}</div>
          <div class="agent-role">${a.role}</div>
        </div>
      </div>
      <div class="agent-file">${a.file} :: ${a.func}</div>
      <div class="agent-summary">${a.summary}</div>
      <ul class="agent-rules">${rules}</ul>
      <div class="agent-status">
        <span class="astatus" style="background:${a.bg};color:${a.color};border:1px solid ${a.color}40">운영 중</span>
        <span class="astatus" style="background:var(--surface-3);color:var(--text-dim);border:1px solid var(--border)">구현 완료</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

/* ====== Init ====== */
renderHero(); renderTimeline(); renderConcepts(); renderNextSteps(); renderDebug();
renderPipelineFlow(); renderAgentGrid();
</script>
</body>
</html>
'''


def generate_dashboard_html(project_root: str = ".") -> str:
    engine = DashboardEngine(project_root)
    data = engine.build()
    json_str = json.dumps(data, ensure_ascii=False)
    return HTML_TEMPLATE.replace("{{DATA_JSON}}", json_str)


def build_dashboard(project_root: str = ".", out_path: str = "dashboard.html") -> str:
    html = generate_dashboard_html(project_root)
    filepath = os.path.join(project_root, out_path)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    return os.path.abspath(filepath)


if __name__ == "__main__":
    import sys
    path = build_dashboard()
    print(f"Dashboard generated: {path}")
