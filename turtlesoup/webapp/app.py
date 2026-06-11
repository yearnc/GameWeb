"""海龟汤 — FastAPI 路由"""

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import Config  # type: ignore[import-untyped]
from .game_runner import GameRunner

BASE_DIR = Path(__file__).parent

app = FastAPI(title="海龟汤")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="turtlesoup_static")

runner: GameRunner | None = None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/api/start")
async def start_game():
    global runner
    config = Config.load()
    errors = config.validate()
    if errors:
        return JSONResponse({"error": "; ".join(errors)}, status_code=400)
    runner = GameRunner(config)
    asyncio.create_task(runner.start_game())
    return {"status": "ok"}


@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request):
    return templates.TemplateResponse(request, "game.html")


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

        cur = runner.state.to_dict() if runner.state else {}
        yield f"data: {json.dumps(cur, ensure_ascii=False)}\n\n"
        last_gen = cur.get("generation", 0)

        async for state in runner.awaiter.state_queue_iter():
            gen = state.get("generation", 0)
            if state.get("waiting_for_human") or gen > last_gen:
                last_gen = max(last_gen, gen)
                yield f"data: {json.dumps(state, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/decision")
async def submit_decision(value: str = Form("")):
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
