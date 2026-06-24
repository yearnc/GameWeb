"""成语接龙 — FastAPI"""

import asyncio, json, random
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import Config
from llm_client import LLMClient

BASE = Path(__file__).parent
app = FastAPI(title="成语接龙")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="idiom_static")

# 常见成语开头
STARTERS = ["一心一意","画龙点睛","马到成功","龙飞凤舞","虎头蛇尾","鸟语花香","山清水秀","风调雨顺","天长地久","花好月圆"]

class GameState:
    def __init__(self):
        self.last_idiom = ""
        self.last_char = ""
        self.score = 0
        self.streak = 0
        self.events = []
        self.gen = 0
        self.phase = "waiting"
        self.over = False

    def to_dict(self):
        return {"last_idiom":self.last_idiom,"last_char":self.last_char,"score":self.score,"streak":self.streak,"events":self.events[-20:],"phase":self.phase,"gen":self.gen,"over":self.over}

    def add_event(self,t,text):
        self.gen+=1;self.events.append({"type":t,"text":text,"gen":self.gen})

class GameRunner:
    def __init__(self, config):
        self.cfg = config
        self.state = GameState()
        self.client = LLMClient(config, config.llm_api_keys[0] if config.llm_api_keys else "")
        self.queue = asyncio.Queue()
        self._stop = False
        self._decision = asyncio.Event()
        self._value = ""

    def push(self,waiting=False):
        d = self.state.to_dict()
        if waiting: d["waiting"] = True
        self.queue.put_nowait(d)

    async def wait(self):
        self._decision.clear()
        await self._decision.wait()
        return self._value

    def submit(self,v):
        self._value = v; self._decision.set()

    def stop(self): self._stop = True

    async def run(self):
        # AI 先出题
        idiom = random.choice(STARTERS)
        self.state.last_idiom = idiom
        self.state.last_char = idiom[-1]
        self.state.add_event("ai", idiom)
        self.state.add_event("system", f"请以「{self.state.last_char}」开头接一个四字成语（同音字也可以哦~）")
        self.push(waiting=True)

        while not self._stop and not self.state.over:
            ans = await self.wait()
            if self._stop: return
            ans = ans.strip()
            self.state.add_event("player", ans)
            self.push()

            # AI 判断：是否以同音字开头 + 是否真实成语 + 给出下一个
            prompt = (
                f"上一个成语：「{self.state.last_idiom}」，结尾字「{self.state.last_char}」\n"
                f"玩家接了：「{ans}」\n\n"
                f"请判断：\n"
                f"1. 「{ans}」的第一个字是否与「{self.state.last_char}」**同音**（包括声调不同也算，如「画(huà)」接「花(huā)」）？\n"
                f"2. 「{ans}」是否为真实四字成语？\n\n"
                f"回复格式（严格）：\n"
                f"- 如果同音且是成语：[正确] 简短夸奖。我的成语：XXXX（用「{ans}」的最后一个字「{ans[-1]}」开头接新成语）\n"
                f"- 如果同音但不是成语：[错误] 不是成语\n"
                f"- 如果不同音：[错误] 不是同音字开头\n"
                f"- 如果接不出来：[认输] 我想不出来了，你赢了！"
            )
            system = (
                "你正在玩成语接龙，规则是同音字开头即可（声调不同也允许）。"
                "例如「画龙点睛(huà)」可以接「花好月圆(huā)」，因为画和花同音。"
                "严格只回复要求格式，不要多余内容。"
            )
            reply = await self.client.chat(system, prompt)
            if not reply:
                self.state.streak = 0
                self.state.add_event("judge", "无法判断，请重试")
                self.push(waiting=True)
                continue

            self.state.add_event("judge", reply.strip())
            if reply.startswith("[正确]") or reply.startswith("正确"):
                self.state.score += 10
                self.state.streak += 1
                import re
                m = re.search(r'我的成语[：:]\s*(.{4})', reply)
                if m:
                    new_idiom = m.group(1)
                    self.state.last_idiom = new_idiom
                    self.state.last_char = new_idiom[-1]
                    self.state.add_event("ai", new_idiom)
                    self.state.add_event("system", f"请接「{self.state.last_char}」开头的成语（同音字即可）")
                else:
                    self.state.add_event("system", "AI 接不出来了，你赢了！🎉")
                    self.state.score += 20; self.state.over = True
            elif reply.startswith("[认输]") or "认输" in reply:
                self.state.add_event("system", "AI 接不出来了，你赢了！🎉")
                self.state.score += 20; self.state.over = True
            else:
                self.state.streak = 0
                self.state.add_event("system", f"请重新接「{self.state.last_char}」开头的成语（同音字即可）")
            self.push(waiting=not self.state.over)

    async def queue_iter(self):
        while True:
            try:
                r = await asyncio.wait_for(self.queue.get(), 0.5)
                yield r
            except asyncio.TimeoutError:
                yield {"heartbeat": True}

runner = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/start")
async def start():
    global runner
    cfg = Config.load()
    if cfg.validate(): return {"error":"config error"}
    runner = GameRunner(cfg)
    asyncio.create_task(runner.run())
    return {"status":"ok"}

@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request):
    return templates.TemplateResponse(request, "game.html")

@app.get("/api/stream")
async def stream():
    async def gen():
        for _ in range(50):
            if runner and runner.queue: break
            await asyncio.sleep(0.1)
        if not runner: return
        cur = runner.state.to_dict(); yield f"data: {json.dumps(cur,ensure_ascii=False)}\n\n"
        lg = cur.get("gen",0)
        async for s in runner.queue_iter():
            g = s.get("gen",0)
            if s.get("waiting") or g > lg:
                lg = max(lg,g); yield f"data: {json.dumps(s,ensure_ascii=False)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.post("/api/decide")
async def decide(value: str = Form("")):
    if runner: runner.submit(value)
    return {"status":"ok"}

@app.post("/api/stop")
async def stop():
    global runner
    if runner: runner.stop(); runner = None
    return {"status":"ok"}
