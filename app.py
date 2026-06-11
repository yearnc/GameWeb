"""游戏小站 — 主页服务器（含狼人杀子应用）"""
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent

# 让狼人杀 / 谁是卧底模块能正确 import
# 注意：insert(0) 最后 insert 的在最前面
# undercover 必须在 turtlesoup 之前（两者都有 webapp 包，undercover 需要优先解析）
sys.path.insert(0, str(BASE_DIR / "werewolf"))
sys.path.insert(0, str(BASE_DIR / "werewolf" / "game"))
sys.path.insert(0, str(BASE_DIR / "turtlesoup"))
sys.path.insert(0, str(BASE_DIR / "undercover"))

# 主应用
app = FastAPI(title="游戏小站")
templates = Jinja2Templates(directory=str(BASE_DIR))
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")

# 挂载狼人杀子应用
from werewolf.web.app import app as werewolf_app
app.mount("/werewolf", werewolf_app)

# 挂载五子棋静态页面
app.mount("/gomoku", StaticFiles(directory=str(BASE_DIR / "gomoku"), html=True), name="gomoku")

# 挂载井字棋静态页面
app.mount("/tictactoe", StaticFiles(directory=str(BASE_DIR / "tictactoe"), html=True), name="tictactoe")

# 挂载围棋静态页面
app.mount("/go", StaticFiles(directory=str(BASE_DIR / "go"), html=True), name="go")

# 挂载谁是卧底子应用
from undercover.webapp.app import app as undercover_app

# 挂载休闲小游戏（静态）
app.mount("/tetris", StaticFiles(directory=str(BASE_DIR / "tetris"), html=True), name="tetris")
app.mount("/snake", StaticFiles(directory=str(BASE_DIR / "snake"), html=True), name="snake")
app.mount("/game2048", StaticFiles(directory=str(BASE_DIR / "game2048"), html=True), name="game2048")
app.mount("/minesweeper", StaticFiles(directory=str(BASE_DIR / "minesweeper"), html=True), name="minesweeper")
app.mount("/match3", StaticFiles(directory=str(BASE_DIR / "match3"), html=True), name="match3")

# 挂载海龟汤子应用
from turtlesoup.webapp.app import app as turtlesoup_app
app.mount("/undercover", undercover_app)
app.mount("/turtlesoup", turtlesoup_app)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request, "index.html")
