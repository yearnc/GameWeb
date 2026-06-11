"""AI 玩家 — 调用 LLM 生成描述和投票决策"""

import random
import re
from config import Config  # type: ignore[import-untyped]
from llm_client import LLMClient  # type: ignore[import-untyped]

from core.game import GameState, Player
from core.prompts import DESCRIBE_PROMPT, PLAYER_SYSTEM, VOTE_PROMPT


class AIPlayer:
    """单个 AI 玩家的 LLM 调用封装"""

    def __init__(self, config: Config, player: Player):
        self.config = config
        self.player = player
        api_key = config.get_key_for_player(player.id)
        self.client = LLMClient(config, api_key)

        # 所有人都用统一的提示词（不知道自己是不是卧底）
        self.system_prompt = PLAYER_SYSTEM.format(
            player_name=player.name, word=player.word
        )

    async def generate_description(self, state: GameState) -> str:
        """生成一句话描述"""
        prev = []
        for p in state.players:
            if p.id == self.player.id:
                continue
            if p.description:
                prev.append(f"玩家{p.id}（{p.name}）说：「{p.description}」")

        prev_text = "\n".join(prev) if prev else "（没有人描述过，你是第一个）"

        prompt = DESCRIBE_PROMPT.format(
            round_num=state.round_num, previous_descriptions=prev_text
        )

        result = await self.client.chat(self.system_prompt, prompt)
        if result:
            desc = result.strip().strip("「」\"\"''""")
            if len(desc) > 40:
                desc = desc[:40]
            return desc
        return "嗯…这个东西大家应该都知道"

    async def decide_vote(self, state: GameState) -> int:
        """决定投票目标"""
        alive = state.alive_players()
        alive_ids = [str(p.id) for p in alive if p.id != self.player.id]

        if not alive_ids:
            return alive[0].id if alive[0].id != self.player.id else alive[-1].id

        desc_lines = []
        for p in alive:
            desc_lines.append(
                f"玩家{p.id}（{p.name}）：「{p.description or '（还未描述）'}」"
            )
        all_descs = "\n".join(desc_lines)

        prompt = VOTE_PROMPT.format(
            round_num=state.round_num,
            all_descriptions=all_descs,
            alive_ids=", ".join(alive_ids),
        )

        result = await self.client.chat(self.system_prompt, prompt)
        if result:
            match = re.search(r"(\d+)", result.strip())
            if match:
                target = int(match.group(1))
                for p in alive:
                    if p.id == target and p.id != self.player.id:
                        return target

        candidates = [p for p in alive if p.id != self.player.id]
        if candidates:
            return random.choice(candidates).id
        return int(alive_ids[0])
