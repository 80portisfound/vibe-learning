"""
Dashboard Data Engine
- 학습자 중심의 데이터 모델링
- 과거/현재/미래 타임라인 생성
- 개념 이해 상태 트래킹
"""
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict


class DashboardEngine:
    def __init__(self, project_root: str = "."):
        self.project_root = project_root
        self.concepts_dir = os.path.join(project_root, ".vibe-learning", "concepts")
        self.processed_dir = os.path.join(project_root, ".vibe-learning", "processed")
        self.inbox_dir = os.path.join(project_root, ".vibe-learning", "inbox")

    def build(self) -> Dict:
        notes = self._load_notes()
        timeline = self._build_timeline(notes)
        concept_map = self._build_concept_map(notes)
        current_task = self._infer_current_task(notes, timeline)

        return {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "project": os.path.basename(os.path.abspath(self.project_root)),
                "version": "3.0.0",
            },
            # Layer 1: 나의 현재 위치 (Hero)
            "current_position": {
                "session_id": current_task.get("session_id", "-"),
                "source_tool": current_task.get("source_tool", "-"),
                "source_prompt": current_task.get("source_prompt", "지금은 바이브 코딩 세션이 없습니다."),
                "active_concept": current_task.get("concept", "-"),
                "confusion": current_task.get("confusion", ""),
                "progress_pct": self._calc_progress(timeline),
                "mood": current_task.get("feeling", ""),
            },
            # Layer 2: 핵심 개념 지도 (Concept Map)
            "concept_map": concept_map,
            # Layer 3: 타임라인 (과거 -> 현재 -> 미래)
            "timeline": timeline,
            # Layer 4: 다음 스텝 (미래)
            "next_steps": self._generate_next_steps(current_task, notes),
            # Layer 5: 통계 (하단)
            "stats": self._build_stats(notes),
        }

    def _load_notes(self) -> List[Dict]:
        notes = []
        if not os.path.isdir(self.concepts_dir):
            return notes
        for fname in sorted(os.listdir(self.concepts_dir)):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.concepts_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                meta = self._parse_frontmatter(content)
                meta["_filename"] = fname
                meta["_content"] = content
                notes.append(meta)
            except Exception:
                continue
        return notes

    def _parse_frontmatter(self, content: str) -> Dict:
        result = {}
        m = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not m:
            return result
        fm = m.group(1)
        for line in fm.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # list parsing
                if val.startswith("[") and val.endswith("]"):
                    try:
                        result[key] = json.loads(val.replace("'", '"'))
                    except Exception:
                        result[key] = val
                else:
                    result[key] = val
        # body sections
        result["feeling"] = self._extract_section(content, "발견 순간")
        result["shape_intuition"] = self._extract_section(content, "Shape 직관")
        result["linked_concepts"] = result.get("linked_concepts", [])
        result["gaps"] = self._extract_list(content, "궁금한 점")
        result["experiment"] = self._extract_section(content, "오늘의 실험")
        result["next_experiment"] = self._extract_section(content, "다음 실험")
        result["ai_design"] = self._extract_section(content, "AI 설계 추론")
        return result

    def _extract_section(self, content: str, heading: str) -> str:
        pattern = rf"## {re.escape(heading)}\n(.*?)(?=\n## |\Z)"
        m = re.search(pattern, content, re.DOTALL)
        if not m:
            return ""
        return m.group(1).strip()

    def _extract_list(self, content: str, heading: str) -> List[str]:
        section = self._extract_section(content, heading)
        items = []
        for line in section.splitlines():
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                items.append(line[1:].strip())
        return items

    def _build_timeline(self, notes: List[Dict]) -> Dict:
        past = []
        present = []
        future = []

        now = datetime.now()
        for note in notes:
            date_str = note.get("_filename", "")[:10]
            try:
                note_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                note_date = now

            item = {
                "date": date_str,
                "concept": note.get("concept", "Unknown"),
                "prompt": note.get("source_prompt", ""),
                "confusion": note.get("confusion", ""),
                "experiment": note.get("experiment", ""),
                "filename": note.get("_filename", ""),
            }

            if note_date.date() < now.date():
                past.append(item)
            elif note_date.date() == now.date():
                present.append(item)
            else:
                future.append(item)

        # If no present, treat latest note as present
        if not present and past:
            present.append(past[-1])
            past = past[:-1]

        # Future items from next_experiment fields
        for note in notes:
            nxt = note.get("next_experiment", "")
            if nxt and nxt.strip() and nxt.strip() != "-":
                future.append({
                    "date": "다음",
                    "concept": note.get("concept", ""),
                    "prompt": note.get("source_prompt", ""),
                    "experiment": nxt,
                    "from_note": note.get("_filename", ""),
                })

        return {
            "past": past,
            "present": present,
            "future": future,
        }

    def _infer_current_task(self, notes: List[Dict], timeline: Dict) -> Dict:
        # Prefer present items; skip "Unknown" fallback if possible
        candidates = timeline["present"] if timeline["present"] else notes
        if not candidates:
            return {}
        # If list of note dicts, pick the one with best concept
        if isinstance(candidates[0], dict) and "concept" in candidates[0]:
            non_unknown = [c for c in candidates if c.get("concept") != "Unknown"]
            return non_unknown[-1] if non_unknown else candidates[-1]
        # timeline items case
        for item in reversed(candidates):
            for note in notes:
                if note.get("_filename") == item.get("filename"):
                    if note.get("concept") != "Unknown":
                        return note
        # fallback to last
        for item in reversed(candidates):
            for note in notes:
                if note.get("_filename") == item.get("filename"):
                    return note
        return candidates[-1] if candidates else {}

    def _build_concept_map(self, notes: List[Dict]) -> List[Dict]:
        concepts = defaultdict(lambda: {
            "count": 0, "linked": set(), "confusions": [], "shapes": [], "dates": []
        })
        for note in notes:
            c = note.get("concept", "Unknown")
            concepts[c]["count"] += 1
            concepts[c]["dates"].append(note.get("_filename", "")[:10])
            for linked in note.get("linked_concepts", []):
                concepts[c]["linked"].add(linked)
            if note.get("confusion"):
                concepts[c]["confusions"].append(note["confusion"])
            if note.get("shapes"):
                if isinstance(note["shapes"], list):
                    concepts[c]["shapes"].extend(note["shapes"])
                else:
                    concepts[c]["shapes"].append(str(note["shapes"]))

        result = []
        for name, data in concepts.items():
            understanding = self._estimate_understanding(data)
            result.append({
                "name": name,
                "mentions": data["count"],
                "linked": sorted(list(data["linked"])),
                "confusions": data["confusions"][:3],
                "shapes": data["shapes"][:2],
                "dates": data["dates"],
                "understanding": understanding,
                "status": "익숙함" if understanding > 70 else "학습중" if understanding > 30 else "탐구중",
            })
        return sorted(result, key=lambda x: x["mentions"], reverse=True)

    def _estimate_understanding(self, data: Dict) -> int:
        score = 0
        if data["count"] > 0:
            score += min(data["count"] * 15, 40)
        if data["linked"]:
            score += min(len(data["linked"]) * 10, 30)
        if not data["confusions"]:
            score += 30
        else:
            score += max(0, 15 - len(data["confusions"]) * 5)
        return min(score, 100)

    def _calc_progress(self, timeline: Dict) -> int:
        total = len(timeline["past"]) + len(timeline["present"]) + len(timeline["future"])
        if total == 0:
            return 0
        done = len(timeline["past"]) + len(timeline["present"])
        return int((done / total) * 100)

    def _generate_next_steps(self, current: Dict, notes: List[Dict]) -> List[Dict]:
        steps = []
        # From current gaps
        for gap in current.get("gaps", [])[:2]:
            steps.append({
                "type": "gap",
                "title": f"궁금증 해결: {gap[:30]}...",
                "desc": gap,
                "priority": "high",
            })
        # From current experiment
        exp = current.get("experiment", "")
        if exp and exp.strip() and exp.strip() != "-":
            steps.append({
                "type": "experiment",
                "title": f"오늘의 실험: {exp[:30]}...",
                "desc": exp,
                "priority": "high",
            })
        # From next_experiment
        nxt = current.get("next_experiment", "")
        if nxt and nxt.strip() and nxt.strip() != "-":
            steps.append({
                "type": "next",
                "title": f"다음 실험: {nxt[:30]}...",
                "desc": nxt,
                "priority": "medium",
            })
        # Generic pipeline step if empty
        if not steps:
            steps.append({
                "type": "pipeline",
                "title": "새로운 바이브 코딩 세션 시작",
                "desc": "프롬프트를 입력하고 코드를 생성한 뒤, inbox에 세션을 덤프하세요.",
                "priority": "medium",
            })
        return steps

    def _build_stats(self, notes: List[Dict]) -> Dict:
        total = len(notes)
        concepts = set()
        gaps = 0
        experiments = 0
        tools = defaultdict(int)
        for note in notes:
            concepts.add(note.get("concept", "Unknown"))
            gaps += len(note.get("gaps", []))
            if note.get("experiment", "").strip() and note.get("experiment", "").strip() != "-":
                experiments += 1
            tools[note.get("source_tool", "unknown")] += 1
        return {
            "total_notes": total,
            "total_concepts": len(concepts),
            "total_gaps": gaps,
            "total_experiments": experiments,
            "tool_usage": dict(tools),
        }


def generate_dashboard_json(project_root: str = ".") -> str:
    engine = DashboardEngine(project_root)
    data = engine.build()
    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(generate_dashboard_json())
