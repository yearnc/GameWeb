"""游戏小站 — 一键启动"""
import sys
import webbrowser
from pathlib import Path

# Windows 中文系统默认 GBK 不支持 emoji，先切换到 UTF-8
sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import uvicorn

PORT = 5000
URL = f"http://127.0.0.1:{PORT}"


def main():
    print(f"🎮 游戏小站")
    print(f"   🏠 主页:    {URL}")
    print(f"   🐺 狼人杀:  {URL}/werewolf")
    print()

    # 自动打开浏览器
    webbrowser.open(URL)

    uvicorn.run("app:app", host="127.0.0.1", port=PORT, reload=True)


if __name__ == "__main__":
    main()
