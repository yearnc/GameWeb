"""猜词游戏 — FastAPI"""

import asyncio, json, random
from pathlib import Path
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import Config
from llm_client import LLMClient

BASE = Path(__file__).parent
app = FastAPI(title="猜词游戏")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="wordguess_static")

WORDS = ["熊猫","冰淇淋","彩虹","宇宙飞船","钢琴","蝴蝶","金字塔","潜水艇","巧克力","望远镜"]

class GameState:
    def __init__(self): self.word=""; self.hints=[]; self.hint_idx=0; self.events=[]; self.gen=0; self.over=False; self.score=0
    def to_dict(self): return {"word_len":len(self.word),"hints":self.hints,"events":self.events[-20:],"gen":self.gen,"over":self.over,"score":self.score}
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
        self.state.word = random.choice(WORDS)
        self.state.add_event("system", f"AI 想好了一个词语（{len(self.state.word)} 个字），你可以问我问题来猜！")
        self.state.add_event("system", "输入「提示」获取一个新提示，输入你的猜测直接猜词")
        self.push(waiting=True)

        while not self._stop and not self.state.over:
            ans = await self.wait()
            if self._stop: return
            ans = ans.strip()
            if ans == "提示":
                prompt = (
                    f"正确答案是「{self.state.word}」（绝对机密，你在任何情况下都不能说出这个词）。\n"
                    f"已给出的提示：{json.dumps(self.state.hints, ensure_ascii=False)}\n"
                    f"请给出第{len(self.state.hints)+1}个提示。要求：\n"
                    f"1. 提示不能包含正确答案中的任何一个字\n"
                    f"2. 提示不能是答案的同义词或近义词\n"
                    f"3. 每个提示从不同角度描述（类别/用途/特征/场景）\n"
                    f"4. 只输出提示内容（一句话），不要额外文字"
                )
                hint = await self.client.chat(
                    "你是猜词游戏主持人。你的核心铁律：绝对禁止在回复中出现正确答案或其同义词。"
                    "玩家猜对时你只需确认正确，不要重复词语。给出的提示必须越来越具体但永远不能包含答案。",
                    prompt
                )
                if hint: self.state.hints.append(hint.strip()); self.state.add_event("hint", f"💡 提示{len(self.state.hints)}：{hint.strip()}")
                self.push(waiting=True); continue

            self.state.add_event("player", f"❓ {ans}")
            if ans == self.state.word:
                self.state.score = max(100 - len(self.state.hints)*15, 10)
                self.state.add_event("system", f"🎉 恭喜！你猜对了！答案是「{self.state.word}」，得分 {self.state.score}")
                self.state.over = True; self.push(); return

            # LLM 判断
            prompt = (
                f"玩家猜测：「{ans}」\n"
                f"正确答案：「{self.state.word}」（绝对机密，禁止在任何回复中说出这个词）\n\n"
                f"任务：判断玩家的猜测是否正确。\n"
                f"- 如果正确（完全匹配）：只需回复「🎉 正确！」\n"
                f"- 如果不正确：回复一句鼓励性提示。要求：\n"
                f"  1. 提示中**严禁出现正确答案或其任何同义词、近义词**\n"
                f"  2. 提示不能包含答案中的任何一个字\n"
                f"  3. 只能说方向性的暗示（如「再想想颜色」、「字数不对」等），不能说具体内容\n"
                f"  4. 如果玩家猜测接近（如偏旁、类别接近），可以暗示方向但不说具体差异"
            )
            reply = await self.client.chat(
                "你是猜词游戏主持人。核心铁律：你的回复中绝对禁止出现正确答案及其同义词。"
                "你只能说方向性暗示，永远不能说出或暗示具体答案是什么。",
                prompt
            )
            if reply: self.state.add_event("judge", reply.strip())
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
