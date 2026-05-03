import os
import re
from datetime import datetime
from typing import List, Dict


class NoteArchitect:
    """Generates markdown notes automatically.
    The user only writes 'feeling' and 'confusion'; the rest is auto-filled.
    """

    def build(
        self,
        linked_concepts: List[Dict],
        context: dict,
        user_feeling: str = "",
        user_confusion: str = "",
    ) -> str:
        session = context.get("session", {})
        prompt_ctx = context.get("prompt_context", {})
        meta = context.get("metadata", {})

        concept_names = [c["concept"] for c in linked_concepts]
        concept_name = concept_names[0] if concept_names else "Unknown"
        project_name = os.path.basename(os.getcwd())
        session_id = session.get("id", "unknown")
        source_tool = session.get("source_tool", "generic")
        source_prompt = (
            prompt_ctx.get("original_prompts", [""])[0]
            if prompt_ctx.get("original_prompts")
            else ""
        )

        shapes = []
        linked = []
        experiments = []
        gaps = []
        ai_design = self._infer_ai_design(source_prompt, meta)

        for c in linked_concepts:
            si = c.get("shape_info", {})
            if si.get("source") == "static_analysis":
                shapes.append(
                    f"[{', '.join(si.get('input_shape', []))}] -> [{', '.join(si.get('operations', []))}] -> [{', '.join(si.get('output_shape', []))}]"
                )
            elif "shape_flow" in si:
                shapes.append(si["shape_flow"])
            linked.extend(c.get("linked_to", []))
            experiments.append(c.get("experiment", ""))
            gaps.extend(c.get("gaps", []))

        shapes = list(dict.fromkeys(shapes))
        linked = list(dict.fromkeys(linked))
        experiments = list(dict.fromkeys(experiments))
        gaps = list(dict.fromkeys(gaps))

        today = datetime.now().strftime("%Y-%m-%d")

        note = f"""---
concept: "{concept_name}"
project: "{project_name}"
source_tool: "{source_tool}"
session_id: "{session_id}"
source_prompt: "{source_prompt}"
shapes: {shapes}
linked_concepts: {linked}
confusion: "{user_confusion or 'unknown yet'}"
---

## 발견 순간
{user_feeling or 'AI가 생성한 코드를 받고, 이 블록이 어떤 역할을 하는지 몰랐음.'}

## Shape 직관
"""
        if shapes:
            for s in shapes:
                note += f"- {s}\n"
        else:
            note += "- (아직 shape 분석이 완료되지 않음)\n"

        note += f"""
## 내 지식과의 연결
"""
        if linked:
            for l in linked:
                note += f'- "{concept_name}"는 "{l}"과 같음.\n'
        else:
            note += "- (아직 연결된 개념이 없음)\n"

        note += f"""
## AI 설계 추론
{ai_design}

## 오늘의 실험
"""
        if experiments:
            note += experiments[0] + "\n"
        else:
            note += "- (아직 실험 질문이 생성되지 않음)\n"

        note += f"""
## 다음 실험
"""
        if len(experiments) > 1:
            note += experiments[1] + "\n"
        else:
            note += "- 다음 사이클에서 shape 변화를 코드로 직접 찍어보기\n"

        if gaps:
            note += f"""
## 궁금한 점 (Gaps)
"""
            for g in gaps:
                note += f"- {g}\n"

        return note

    def save(self, note: str, out_dir: str = ".vibe-learning/concepts") -> str:
        os.makedirs(out_dir, exist_ok=True)
        # extract concept from frontmatter
        match = re.search(r'concept:\s*"([^"]+)"', note)
        concept = match.group(1) if match else "note"
        concept_slug = re.sub(r"[^\w\-]", "_", concept.lower())
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{concept_slug}.md"
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(note)
        return filepath

    def _infer_ai_design(self, prompt: str, meta: dict) -> str:
        if "벡터" in prompt or "vector" in prompt.lower():
            return (
                '프롬프트 "문서를 벡터로 만들어서 DB에 넣어줘" -> sentence-transformer 선택 (범용 문장 임베딩)\n'
                '대안: "코드 임베딩이 필요해" -> CodeBERT 선택했을 것'
            )
        if "챗봇" in prompt or "chat" in prompt.lower():
            return (
                '프롬프트 "RAG 챗봇 만들어줘" -> Retrieval-Augmented Generation 패턴 선택\n'
                '대안: "단순 키워드 검색" -> TF-IDF + cosine 유사도 선택했을 것'
            )
        if "속도" in prompt or "speed" in prompt.lower():
            return (
                '프롬프트 "속도 개선해줘" -> HNSW 인덱싱 또는 배치 처리 고려\n'
                '대안: "정확도 개선" -> 더 큰 모델 또는 fine-tuning 선택했을 것'
            )
        return "프롬프트 의도를 분석하여 AI가 선택한 설계를 추론 중..."
