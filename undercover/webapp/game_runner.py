"""游戏运行器 — 编排游戏流程，通过 awaitable 推送 SSE 事件"""

import asyncio
import json
import random
from dataclasses import dataclass

from config import Config  # type: ignore[import-untyped]

from core.ai_player import AIPlayer
from core.game import GameState, check_game_over, create_game, process_elimination


@dataclass
class SSEResult:
    """推送到 SSE 的事件"""
    state: dict
    waiting_for_human: bool = False
    decision_context: dict | None = None


class GameAwaiter:
    """异步事件队列 + 人类决策等待"""

    def __init__(self):
        self._queue: asyncio.Queue[SSEResult] = asyncio.Queue()
        self._pending_decision: dict | None = None
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

    def get_pending_decision(self) -> dict | None:
        return self._pending_decision

    async def wait_for_decision(self) -> str | None:
        self._decision_event.clear()
        await self._decision_event.wait()
        return self._decision_value

    def submit_decision(self, value: str):
        self._decision_value = value
        self._decision_event.set()

    def set_pending_decision(self, d: dict):
        self._pending_decision = d

    def clear_pending_decision(self):
        self._pending_decision = None


class GameRunner:
    """管理一局游戏的完整生命周期"""

    def __init__(self, config: Config, human_mode: bool = False):
        self.config = config
        self.human_mode = human_mode
        self.state: GameState | None = None
        self.awaiter: GameAwaiter | None = None
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    async def start_game(self):
        try:
            await self._run_game()
        except Exception as e:
            if self.state:
                self.state.add_event("system", f"游戏出错: {e}")
            if self.awaiter:
                d = self.state.to_dict() if self.state else {"error": str(e)}
                self.awaiter.push(SSEResult(state=d, waiting_for_human=False))
            import traceback
            traceback.print_exc()

    async def _run_game(self):
        self.awaiter = GameAwaiter()
        self.state = create_game(human_mode=self.human_mode)
        self._stop_flag = False

        ai_players: dict[int, AIPlayer] = {}
        for p in self.state.players:
            if not p.is_human:
                ai_players[p.id] = AIPlayer(self.config, p)

        self.state.add_event("phase", f"第 {self.state.round_num} 轮 — 词语已分发")
        self._push()
        await asyncio.sleep(1.0)

        while not self._stop_flag:
            winner = check_game_over(self.state)
            if winner:
                break

            # === 描述阶段 ===
            self.state.phase = "describing"
            self.state.add_event("phase", f"第 {self.state.round_num} 轮 · 描述阶段")
            self._push()
            await asyncio.sleep(1.0)

            for p in self.state.alive_players():
                if self._stop_flag:
                    return
                self.state.add_event("describe_turn", "", p.id)
                self._push()

                if p.is_human:
                    p.description = await self._get_human_input("describe", p)
                else:
                    p.description = await ai_players[p.id].generate_description(self.state)

                if self._stop_flag:
                    return

                self.state.add_event("description", p.description or "…", p.id)
                self._push()
                delay = self.config.game_speed_delay * random.uniform(0.8, 1.5)
                await asyncio.sleep(delay)

            # === 投票阶段 ===
            self.state.phase = "voting"
            for p in self.state.alive_players():
                p.voted_for = None
            self.state.add_event("phase", "投票阶段 · 你觉得谁是卧底？")
            self._push()
            await asyncio.sleep(1.5)

            # 并行收集所有 AI 投票
            self.state.add_event("phase", "AI 投票中…")
            self._push()

            async def ai_vote(player):
                target = await ai_players[player.id].decide_vote(self.state)
                return player.id, target

            ai_players_alive = [p for p in self.state.alive_players() if not p.is_human]
            human_player = next((p for p in self.state.alive_players() if p.is_human), None)

            # AI 并行投票
            ai_tasks = [ai_vote(p) for p in ai_players_alive]
            ai_results = await asyncio.gather(*ai_tasks) if ai_tasks else []

            # 记录 AI 投票结果
            for pid, target in ai_results:
                p = next((pp for pp in self.state.players if pp.id == pid), None)
                if p:
                    p.voted_for = target
                    target_name = next((pp.name for pp in self.state.players if pp.id == target), "?")
                    self.state.add_event("vote", f"{p.name} → {target_name}", p.id)

            self._push()

            # 人类玩家投票
            if human_player:
                self.state.add_event("vote_turn", "", human_player.id)
                self._push()
                raw = await self._get_human_input("vote", human_player) or "0"
                try:
                    target = int(raw)
                except (ValueError, TypeError):
                    target = 0
                human_player.voted_for = target
                target_name = next((pp.name for pp in self.state.players if pp.id == target), "?")
                self.state.add_event("vote", f"{human_player.name} → {target_name}", human_player.id)
                self._push()

            if self._stop_flag:
                return

            # === 计票 ===
            tally: dict[int, int] = {}
            for p in self.state.alive_players():
                if p.voted_for is not None:
                    tally[p.voted_for] = tally.get(p.voted_for, 0) + 1

            self.state.add_event("tally", json.dumps(tally, ensure_ascii=False))
            self._push()
            await asyncio.sleep(1.0)

            if tally:
                max_votes = max(tally.values())
                top = [pid for pid, cnt in tally.items() if cnt == max_votes]
                if len(top) > 1:
                    self.state.add_event("system", "平票，无人淘汰")
                else:
                    process_elimination(self.state, top[0])

            self._push()
            await asyncio.sleep(2.0)
            self.state.round_num += 1

        # ── 结束 ──
        self.state.phase = "over"
        winner = check_game_over(self.state)
        w = "平民" if winner == "civilian" else "卧底"
        self.state.add_event(
            "game_over",
            f"{w}胜利！平民词「{self.state.civilian_word}」卧底词「{self.state.spy_word}」"
        )
        self._push()

    def _push(self):
        if not self.awaiter or not self.state:
            return
        d = self.state.to_dict()
        human_needed = False
        ctx = None

        if self.state.phase == "describing":
            # 只有当最近的 describe_turn 事件指向人类玩家时，才需要等待
            for p in self.state.alive_players():
                if p.is_human and p.description is None:
                    # 检查最后的事件是否是针对该人类玩家的 describe_turn
                    if self.state.events and self.state.events[-1]["type"] == "describe_turn" and self.state.events[-1]["player_id"] == p.id:
                        human_needed = True
                        ctx = {"type": "describe", "player_id": p.id}
                        self.awaiter.set_pending_decision(ctx)
                    break

        if self.state.phase == "voting" and not human_needed:
            for p in self.state.alive_players():
                if p.is_human and p.voted_for is None:
                    # 只有当最近的 vote_turn 事件指向人类玩家时，才需要等待
                    if self.state.events and self.state.events[-1]["type"] == "vote_turn" and self.state.events[-1]["player_id"] == p.id:
                        human_needed = True
                        ctx = {
                            "type": "vote",
                            "player_id": p.id,
                            "alive_ids": [str(pp.id) for pp in self.state.alive_players() if pp.id != p.id],
                        }
                        self.awaiter.set_pending_decision(ctx)
                    break

        if not human_needed:
            self.awaiter.clear_pending_decision()

        # 将决策上下文嵌入 state dict，让前端能直接读取 type/player_id 等
        if human_needed:
            d["waiting_for_human"] = True
        if ctx:
            d.update(ctx)

        self.awaiter.push(SSEResult(state=d, waiting_for_human=human_needed, decision_context=ctx))

    async def _get_human_input(self, action: str, player) -> str:
        self.state.add_event("waiting", "", player.id)
        self._push()
        return await self.awaiter.wait_for_decision() or ""
