"""谁是卧底 — 核心游戏逻辑"""

import random
from dataclasses import dataclass, field

from core.word_pairs import WORD_PAIRS

PLAYER_COUNT = 5

PLAYER_NAMES = ["玩家1号", "玩家2号", "玩家3号", "玩家4号", "玩家5号"]
PLAYER_AVATARS = ["①", "②", "③", "④", "⑤"]
PLAYER_PERSONAS = [
    "性格直率的上班族，说话爽快",
    "温柔细心的咖啡店店员，说话轻柔",
    "豪爽的运动爱好者，说话大大咧咧",
    "文静细腻的插画师，表达很有画面感",
    "谨慎稳重的中年教师，说话爱用书面语",
]


@dataclass
class Player:
    id: int
    name: str
    avatar: str
    persona: str
    role: str  # "civilian" | "spy"
    word: str
    is_human: bool = False
    alive: bool = True
    description: str | None = None
    voted_for: int | None = None


@dataclass
class GameState:
    players: list[Player] = field(default_factory=list)
    civilian_word: str = ""
    spy_word: str = ""
    round_num: int = 1
    phase: str = "setup"  # setup | describing | voting | result | over
    generation: int = 0   # monotonic counter for SSE dedup
    events: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "avatar": p.avatar,
                    "role": p.role,
                    "word": p.word,
                    "is_human": p.is_human,
                    "alive": p.alive,
                    "description": p.description,
                    "voted_for": p.voted_for,
                }
                for p in self.players
            ],
            "civilian_word": self.civilian_word,
            "spy_word": self.spy_word,
            "round_num": self.round_num,
            "phase": self.phase,
            "generation": self.generation,
            "events": self.events[-20:],  # last 20 events
        }

    def add_event(self, event_type: str, text: str, player_id: int | None = None):
        self.generation += 1
        self.events.append({
            "type": event_type,
            "text": text,
            "player_id": player_id,
            "generation": self.generation,
        })

    def alive_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def find_spy(self) -> Player | None:
        for p in self.players:
            if p.role == "spy":
                return p
        return None


def create_game(human_mode: bool = False) -> GameState:
    """初始化一局新游戏"""
    # 随机选词对
    pair = random.choice(WORD_PAIRS)

    # 随机决定卧底
    spy_idx = random.randint(0, PLAYER_COUNT - 1)

    # 随机决定人类玩家位置（如果参与模式）
    human_idx = random.randint(0, PLAYER_COUNT - 1) if human_mode else None

    players = []
    for i in range(PLAYER_COUNT):
        is_spy = (i == spy_idx)
        is_human = (human_idx is not None and i == human_idx)

        player = Player(
            id=i + 1,  # 1-indexed for display
            name="你" if is_human else PLAYER_NAMES[i],
            avatar="🙋" if is_human else PLAYER_AVATARS[i],
            persona=PLAYER_PERSONAS[i],
            role="spy" if is_spy else "civilian",
            word=pair["spy"] if is_spy else pair["civilian"],
            is_human=is_human,
        )
        players.append(player)

    state = GameState(
        players=players,
        civilian_word=pair["civilian"],
        spy_word=pair["spy"],
        round_num=1,
        phase="setup",
        generation=1,
    )

    return state


def check_game_over(state: GameState) -> str | None:
    """检查游戏是否结束。返回 'civilian' | 'spy' | None"""
    spy = state.find_spy()
    if spy is None:
        return None
    if not spy.alive:
        return "civilian"

    alive = state.alive_players()
    # 如果卧底存活且剩余 ≤ 2 人，卧底赢
    if len(alive) <= 2:
        return "spy"

    return None


def process_elimination(state: GameState, target_id: int) -> Player:
    """淘汰指定玩家"""
    for p in state.players:
        if p.id == target_id:
            p.alive = False
            state.add_event(
                "eliminate",
                f"{p.name}（{p.avatar}）被投票出局！" + ("TA 就是卧底！🕵️" if p.role == "spy" else "TA 是平民…"),
                p.id,
            )
            return p
    raise ValueError(f"Player {target_id} not found")
