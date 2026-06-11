"""你画我猜 — FastAPI"""

import asyncio, json
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import Config
from llm_client import LLMClient

BASE = Path(__file__).parent
app = FastAPI(title="你画我猜")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="drawguess_static")

class GameState:
    def __init__(self): self.events=[]; self.gen=0; self.over=False
    def to_dict(self): return {"events":self.events[-20:],"gen":self.gen,"over":self.over}
    def add_event(self,t,text): self.gen+=1; self.events.append({"type":t,"text":text,"gen":self.gen})

class GameRunner:
    def __init__(self, config):
        self.cfg = config; self.state = GameState()
        self.client = LLMClient(config, config.llm_api_keys[0] if config.llm_api_keys else "")
        self.queue = asyncio.Queue(); self._stop = False
        self._decision = asyncio.Event(); self._value = ""

    def push(self,waiting=False):
        d = self.state.to_dict()
        if waiting: d["waiting"] = True
        self.queue.put_nowait(d)

    async def wait(self):
        self._decision.clear(); await self._decision.wait(); return self._value

    def submit(self,v): self._value = v; self._decision.set()
    def stop(self): self._stop = True

    async def run(self):
        self.state.add_event("system", "请在画布上画一个东西，然后点击「让 AI 猜」")
        self.push(waiting=True)
        while not self._stop:
            ans = await self.wait()
            if self._stop: return
            self.state.add_event("player", "🎨 画好了，让 AI 猜…")
            self.push()
            prompt = f"一个人在画布上画了一些东西。画面描述如下：{ans[:500]}\n请你猜猜这个人画的是什么。只回复你的猜测（一句话），不要多余内容。"
            reply = await self.client.chat("你是一个猜画游戏的AI，根据画面描述猜测画的是什么。", prompt)
            if reply:
                self.state.add_event("ai", f"🤖 AI 猜：{reply.strip()}")
            else:
                self.state.add_event("ai", "🤖 AI 猜不出来…再试试？")
            self.push(waiting=True)

    async def queue_iter(self):
        while True:
            try: r = await asyncio.wait_for(self.queue.get(),0.5); yield r
            except asyncio.TimeoutError: yield {"heartbeat":True}

runner = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request): return templates.TemplateResponse(request, "index.html")

@app.post("/api/start")
async def start():
    global runner
    cfg = Config.load()
    if cfg.validate(): return {"error":"config error"}
    runner = GameRunner(cfg); asyncio.create_task(runner.run())
    return {"status":"ok"}

@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request): return templates.TemplateResponse(request, "game.html")

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
            if s.get("waiting") or g > lg: lg = max(lg,g); yield f"data: {json.dumps(s,ensure_ascii=False)}\n\n"
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
