"""海龟汤 AI 裁判"""

from config import Config  # type: ignore[import-untyped]
from llm_client import LLMClient  # type: ignore[import-untyped]

from .game import GameState
from .prompts import HOST_SYSTEM, JUDGE_ANSWER


class AIHost:
    """AI 裁判 —— 回答问题 + 评判答案"""

    def __init__(self, config: Config, state: GameState):
        self.config = config
        self.state = state
        api_key = config.llm_api_keys[0] if config.llm_api_keys else ""
        self.client = LLMClient(config, api_key)

    def _build_system(self) -> str:
        return HOST_SYSTEM.format(
            soup=self.state.soup,
            answer=self.state.answer,
            max_questions=self.state.max_questions,
            questions_asked=self.state.questions_asked,
            remaining=self.state.remaining,
        )

    async def answer_question(self, question: str) -> str:
        """回答玩家的问题"""
        system = self._build_system()
        prompt = f"玩家问：「{question}」\n请回答是/不是/是也不是/与此无关，并简短解释。"
        result = await self.client.chat(system, prompt)
        if result:
            return result.strip()
        return "是也不是（无法确定）"

    async def judge_answer(self, player_answer: str) -> str:
        """评判玩家的最终答案"""
        prompt = JUDGE_ANSWER.format(
            player_answer=player_answer,
            answer=self.state.answer,
        )
        system = "你是一个公正的裁判。请根据汤底判断玩家的答案是否正确。"
        result = await self.client.chat(system, prompt)
        if result:
            return result.strip()
        return "无法评判"
