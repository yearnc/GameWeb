"""海龟汤 — 核心游戏逻辑"""

import random
from dataclasses import dataclass, field

from .stories import STORIES

MAX_QUESTIONS = 30


@dataclass
class GameState:
    title: str
    soup: str  # 汤面
    answer: str  # 汤底
    questions_asked: int = 0
    max_questions: int = MAX_QUESTIONS
    phase: str = "playing"  # playing | judging | over
    events: list[dict] = field(default_factory=list)
    generation: int = 0
    host_reply: str | None = None
    judge_result: str | None = None

    @property
    def remaining(self) -> int:
        return self.max_questions - self.questions_asked

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "soup": self.soup,
            "questions_asked": self.questions_asked,
            "max_questions": self.max_questions,
            "remaining": self.remaining,
            "phase": self.phase,
            "generation": self.generation,
            "events": self.events[-30:],
            "host_reply": self.host_reply,
            "judge_result": self.judge_result,
        }

    def add_event(self, event_type: str, text: str):
        self.generation += 1
        self.events.append({
            "type": event_type,
            "text": text,
            "generation": self.generation,
        })


def create_game() -> GameState:
    """随机选一个故事开始新游戏"""
    story = random.choice(STORIES)
    state = GameState(
        title=story["title"],
        soup=story["soup"],
        answer=story["answer"],
    )
    state.add_event("soup", f"【汤面】{story['soup']}")
    state.add_event("system", f"你有 {MAX_QUESTIONS} 次提问机会。请通过「是/不是」问题推理出完整故事，输入「提交」可提前提交答案。")
    return state
