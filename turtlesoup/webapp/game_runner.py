"""海龟汤 — 游戏运行器"""

import asyncio
from dataclasses import dataclass

from config import Config  # type: ignore[import-untyped]

from ..core.ai_host import AIHost
from ..core.game import GameState, create_game


@dataclass
class SSEResult:
    state: dict
    waiting_for_human: bool = False


class GameAwaiter:
    def __init__(self):
        self._queue: asyncio.Queue[SSEResult] = asyncio.Queue()
        self._decision_event = asyncio.Event()
        self._decision_value: str | None = None

    def push(self, result: SSEResult):
        self._queue.put_nowait(result)

    async def state_queue_iter(self):
        while True:
            try:
                result = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                yield result.state
            except asyncio.TimeoutError:
                yield {"heartbeat": True}

    async def wait_for_decision(self) -> str | None:
        self._decision_event.clear()
        await self._decision_event.wait()
        return self._decision_value

    def submit_decision(self, value: str):
        self._decision_value = value
        self._decision_event.set()


class GameRunner:
    def __init__(self, config: Config):
        self.config = config
        self.state: GameState | None = None
        self.awaiter: GameAwaiter | None = None
        self._stop_flag = False
        self._host: AIHost | None = None

    def stop(self):
        self._stop_flag = True

    async def start_game(self):
        self.awaiter = GameAwaiter()
        self.state = create_game()
        self._stop_flag = False
        self._host = AIHost(self.config, self.state)
        self._push()
        await self._game_loop()

    async def _game_loop(self):
        while not self._stop_flag and self.state.remaining > 0 and self.state.phase == "playing":
            self._push(waiting=True)
            question = await self.awaiter.wait_for_decision()
            if self._stop_flag:
                return
            if not question:
                continue

            q = question.strip()
            # 检查是否提交答案
            if q in ("提交", "submit", "结束"):
                await self._handle_submit()
                return

            # AI 回答
            self.state.add_event("question", f"❓ {q}")
            self.state.questions_asked += 1
            self._push()

            reply = await self._host.answer_question(q)
            self.state.host_reply = reply
            self.state.add_event("answer", f"🤖 {reply}")
            self._push()

        # 次数耗尽
        if self.state.phase == "playing":
            self.state.add_event("system", "⏰ 次数耗尽！请提交你的最终推理——你认为完整的故事是什么？")
            await self._handle_submit()

    async def _handle_submit(self):
        self.state.phase = "judging"
        self._push(waiting=True)
        submission = await self.awaiter.wait_for_decision()
        if self._stop_flag or not submission:
            return

        self.state.add_event("question", f"📝 提交答案：{submission.strip()}")
        self._push()

        self.state.add_event("system", "🤔 裁判正在评判你的答案…")
        self._push()

        result = await self._host.judge_answer(submission.strip())
        self.state.judge_result = result
        self.state.phase = "over"

        # 判定正确/接近/错误
        if "正确" in result:
            verdict = "🎉 恭喜！你的推理正确！"
        elif "接近" in result:
            verdict = "🤏 很接近了，但还不够完全准确。"
        else:
            verdict = "❌ 很遗憾，你的推理不太对。"

        self.state.add_event("judge", verdict)
        self.state.add_event("answer", f"📖 完整汤底：{self.state.answer}")
        self.state.add_event("system", f"裁判评语：{result}")
        self._push()

    def _push(self, waiting: bool = False):
        if not self.awaiter or not self.state:
            return
        d = self.state.to_dict()
        if waiting:
            d["waiting_for_human"] = True
        self.awaiter.push(SSEResult(state=d, waiting_for_human=waiting))
