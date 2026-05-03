import random
from typing import List, Dict


class ConceptLinker:
    """Links new concepts to existing SWE knowledge and generates today's experiment."""

    CONCEPT_MAP = {
        "Embedding": ["HashMap", "Dictionary", "Lookup Table"],
        "Tokenizer": ["Lexer", "Parser", "Split"],
        "Attention": ["Pub-Sub", "Broadcast", "Query-Response"],
        "Transformer": ["Pipeline", "Map-Reduce", "Assembly Line"],
        "Vector DB": ["Index", "Search Engine", "B-Tree", "Hash Index"],
        "Linear": ["Function", "y = mx + b", "Matrix Multiply"],
        "Conv2d": ["Sliding Window", "Filter", "Kernel"],
        "LSTM": ["State Machine", "Tape Recorder", "Queue"],
        "GRU": ["Simpler State Machine", "LSTM Lite"],
        "Dropout": ["Random Disable", "Load Balancing"],
        "BatchNorm": ["Standardization", "Scale & Shift"],
        "Softmax": ["Probability Distribution", "Vote Tally"],
        "Optimizer": ["Feedback Loop", "PID Controller", "Hill Climbing"],
        "Loss": ["Error Metric", "Distance", "Score"],
        "Gradient": ["Slope", "Direction", "Derivative"],
        "Backbone": ["Framework", "Core Library", "Foundation"],
        "Retrieval": ["Search", "Query", "Lookup"],
        "Indexing": ["Catalog", "Table of Contents", "Hash Index"],
    }

    EXPERIMENT_TEMPLATES = {
        "Tokenizer": [
            "tokenizer로 'hello'와 'hello world'를 각각 넣고, 나오는 정수 리스트 길이를 비교핵심 키워드. 공백이 토큰에 어떤 영향을 주나요?"
        ],
        "Embedding": [
            "embedding 차원 128 vs 768로 바꿔서 메모리 사용량을 비교핵심 키워드. 리스트 길이가 용량에 어떤 영향을 주나요?"
        ],
        "Attention": [
            "3x3 숫자 행렬을 만들고, 각 행의 합이 1이 되도록 나누기. 이게 softmax의 직관입니다."
        ],
        "Linear": [
            "길이 4 리스트와 4x2 가중치 행렬을 손으로 곱해서 길이 2 리스트 만들기."
        ],
        "Vector DB": [
            "10개의 길이-3 리스트를 만들고, 가장 가까운 두 개를 찾기. 거리는 어떻게 측정할까요?"
        ],
        "Conv2d": [
            "5x5 숫자 격자 위에서 3x3 윈도우를 한 칸씩 움직이며 합 구하기. 출력 격자 크기는?"
        ],
        "Dropout": [
            "길이 10 리스트에서 무작위로 3개를 0으로 만들고 평균 내기. 나머지 값들은 어떻게 변하나요?"
        ],
        "Optimizer": [
            "x=10에서 시작해서 '목표는 0'이라고 할 때, x를 0.1씩 감소시키는 과정을 5번 반복하기."
        ],
        "Loss": [
            "예측값 [2, 3, 5]와 정답 [1, 3, 6]의 차이 리스트를 만들고 각 차이를 제곱한 뒤 평균 내기."
        ],
        "Softmax": [
            "[1.0, 2.0, 3.0]를 e의 거듭제곱으로 바꾸고, 전체 합으로 나누기. 결과 리스트의 합은?"
        ],
        "LSTM": [
            "1, 2, 3, 4를 순서대로 읽으면서 '지금까지 합'과 '지금 값' 두 가지를 동시에 기록하기."
        ],
    }

    def link(self, tracked_blocks: List[Dict]) -> List[Dict]:
        results = []
        for item in tracked_blocks:
            block = item["block"]
            block_type = block.get("block_type", "Unknown")
            linked = self.CONCEPT_MAP.get(block_type, ["No direct analogy yet"])
            gaps = self._infer_gaps(block, item)
            experiment = self._generate_experiment(block_type)
            results.append({
                "block": block,
                "concept": block_type,
                "linked_to": linked,
                "gaps": gaps,
                "experiment": experiment,
                "shape_info": item,
            })
        return results

    def _infer_gaps(self, block: Dict, shape_info: Dict) -> List[str]:
        gaps = []
        code = block.get("code", "")
        if "768" in code or "768" in str(shape_info.get("output_shape", [])):
            gaps.append("Why 768 dimensions?")
        if "encode" in code:
            gaps.append("Is the encoder trained or frozen?")
        if "last_hidden_state" in code:
            gaps.append("Difference between last_hidden_state and pooler_output")
        if not gaps:
            gaps.append("What does this block do inside?")
        return gaps

    def _generate_experiment(self, block_type: str) -> str:
        templates = self.EXPERIMENT_TEMPLATES.get(block_type, [
            "Print the shape of input and output for this block with a dummy example."
        ])
        return random.choice(templates)
