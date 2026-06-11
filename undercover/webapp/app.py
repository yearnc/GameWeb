"""谁是卧底 — FastAPI 路由"""

import asyncio
import json
import random
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import Config  # type: ignore[import-untyped]
from webapp.game_runner import GameRunner

BASE_DIR = Path(__file__).parent

app = FastAPI(title="谁是卧底")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="undercover_static")

runner: GameRunner | None = None
# 三款主题：0=线索板 1=终端机 2=档案室
THEME_NAMES = ["evidence_board", "spy_terminal", "briefing_room"]


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    theme = random.randint(0, 2)
    return templates.TemplateResponse(request, "index.html", {"theme": theme})


@app.post("/api/start")
async def start_game(request: Request, mode: str = Form(...)):
    global runner
    config = Config.load()
    errors = config.validate()
    if errors:
        return JSONResponse({"error": "; ".join(errors)}, status_code=400)

    runner = GameRunner(config, human_mode=(mode == "human"))
    asyncio.create_task(runner.start_game())
    return {"status": "ok"}


@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request, mode: str = "spectate"):
    return templates.TemplateResponse(request, "game.html", {"mode": mode})


@app.get("/api/stream")
async def event_stream():
    async def generate():
        for _ in range(50):
            if runner is not None and runner.awaiter is not None:
                break
            await asyncio.sleep(0.1)

        if runner is None or runner.awaiter is None:
            yield f"data: {json.dumps({'error': 'no game'}, ensure_ascii=False)}\n\n"
            return

        last_gen = 0

        # Send current state on connect (includes pending decision context)
        cur = runner.state.to_dict() if runner.state else {}
        # Merge decision context if waiting for human
        pending = runner.awaiter.get_pending_decision()
        if pending:
            cur["waiting_for_human"] = True
            cur.update(pending)
        last_gen = cur.get("generation", 0)
        yield f"data: {json.dumps(cur, ensure_ascii=False)}\n\n"

        async for state in runner.awaiter.state_queue_iter():
            gen = state.get("generation", 0)
            # Always forward states where human needs to act (for reconnection)
            if state.get("waiting_for_human") or gen > last_gen:
                if not state.get("waiting_for_human") and gen <= last_gen:
                    continue
                last_gen = max(last_gen, gen)
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/decision")
async def submit_decision(decision_id: str = Form(...), value: str = Form("")):
    if runner is None or runner.awaiter is None:
        return JSONResponse({"error": "No game running"}, status_code=400)
    runner.awaiter.submit_decision(value)
    return {"status": "ok"}


@app.post("/api/stop")
async def stop_game():
    global runner
    if runner is not None:
        runner.stop()
        runner = None
    return {"status": "ok"}
