"""能源用量校核助手本地 HTML 应用

用途：
  启动本地校核服务和控制窗口。工作簿按 config.yaml 指定路径只读载入，
  根据能源类型复算标准煤和二氧化碳，并与表内登记结果核对。

配置文件：
  config.yaml 设置服务、输入工作簿、相对误差阈值、计算系数和展示顺序。
  AI.env 保存本机 AI 服务配置；当前校核流程不调用 AI。

可选参数：
  --host 覆盖本地服务监听地址。
  --port 覆盖本地服务端口。
  --no-browser 启动控制窗口但不自动打开浏览器。

示例：
  python energy_summit_assistant.py
  python energy_summit_assistant.py --port 8765

输出：
  启动服务控制窗口，可打开能耗统计页面或退出程序。默认在主显示器的
  Chrome 新窗口中打开 HTML 页面；输入工作簿不会被修改。
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from ctypes import wintypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from energy_submit_assistant.flows.energy_check import load_config, run_check

PAGE_TITLE = "能源用量校核工作台"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/api/results":
            try:
                config = load_config(ROOT / "config.yaml")
                workbook_path = Path(config["app"]["input_path"])
                if not workbook_path.is_absolute():
                    workbook_path = ROOT / workbook_path
                payload = run_check(workbook_path, config)
                configured_units = config.get("display", {}).get("unit_order", [])
                discovered_units = list(dict.fromkeys(
                    row.get("三级单位", "未填写")
                    for records in payload["sheets"].values()
                    for row in records
                ))
                payload["unit_order"] = configured_units or discovered_units
                payload["energy_type_order"] = config.get("display", {}).get(
                    "energy_type_order", []
                )
                payload["source_name"] = workbook_path.name
                data = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as exc:
                self.send_error(500, str(exc))
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        print("[web] " + fmt % args)


def _visible_windows() -> set[int]:
    """记录启动浏览器前已存在的 Windows 顶层窗口句柄。"""
    if sys.platform != "win32":
        return set()
    user32 = ctypes.windll.user32
    handles: set[int] = set()
    enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def collect(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            handles.add(int(hwnd))
        return True

    user32.EnumWindows(enum_callback(collect), 0)
    return handles


def _move_browser_window_to_primary(before: set[int], timeout: float = 15.0) -> bool:
    """定位本次新开的校核页面窗口，并移到主显示器后最大化。"""
    if sys.platform != "win32":
        return False
    user32 = ctypes.windll.user32
    enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    deadline = time.monotonic() + timeout
    target = None
    while time.monotonic() < deadline:
        candidates = []

        def collect(hwnd, _):
            if not user32.IsWindowVisible(hwnd) or int(hwnd) in before:
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            title = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title, length + 1)
            if PAGE_TITLE in title.value:
                candidates.append(hwnd)
            return True

        user32.EnumWindows(enum_callback(collect), 0)
        if candidates:
            target = candidates[0]
            break
        time.sleep(0.2)
    if target is None:
        return False

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                    ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

    monitor_enum = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR,
                                      wintypes.HDC, ctypes.POINTER(RECT), wintypes.LPARAM)
    primary = {"rect": None}

    def find_primary(monitor, _hdc, _rect, _data):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(monitor, ctypes.byref(info)) and info.dwFlags & 1:
            primary["rect"] = info.rcWork
            return False
        return True

    ctypes.windll.user32.EnumDisplayMonitors(None, None, monitor_enum(find_primary), 0)
    rect = primary["rect"]
    if rect is None:
        return False
    user32.SetWindowPos(target, 0, rect.left + 24, rect.top + 24, 1100, 760, 0x0004)
    user32.ShowWindow(target, 3)  # SW_MAXIMIZE
    user32.SetForegroundWindow(target)
    return True


def _open_browser(url: str) -> None:
    """创建浏览器新窗口；Windows Chrome 窗口移至主显示器并最大化。"""
    before = _visible_windows()
    if sys.platform == "win32":
        chrome = shutil.which("chrome")
        if chrome is None:
            candidates = [
                Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
                Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            ]
            chrome_path = next((candidate for candidate in candidates if candidate.is_file()), None)
            chrome = str(chrome_path) if chrome_path else None
        if chrome:
            subprocess.Popen([chrome, "--new-window", url])
        else:
            webbrowser.open_new(url)
        if not _move_browser_window_to_primary(before):
            print(f"浏览器已请求打开页面；如窗口未定位，请手动访问：{url}")
        return
    webbrowser.open_new(url)


def _run_control_window(server: ThreadingHTTPServer, url: str, auto_open: bool) -> None:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("能源用量校核助手")
    root.resizable(False, False)
    root.geometry("430x205")
    root.configure(bg="#f7f8f5")
    root.protocol("WM_DELETE_WINDOW", lambda: stop())

    tk.Label(root, text="能源用量校核助手", bg="#f7f8f5", fg="#183333",
             font=("Microsoft YaHei UI", 16, "bold")).pack(pady=(23, 4))
    tk.Label(root, text="本地校核服务已启动", bg="#f7f8f5", fg="#64756d",
             font=("Microsoft YaHei UI", 10)).pack(pady=(0, 6))
    tk.Label(root, text=url, bg="#f7f8f5", fg="#087b70",
             font=("Segoe UI", 9)).pack(pady=(0, 16))
    actions = tk.Frame(root, bg="#f7f8f5")
    actions.pack()
    stopping = False

    def open_page():
        try:
            _open_browser(url)
        except Exception as exc:
            messagebox.showerror("打开页面失败", f"无法打开能耗统计页面：{exc}\n\n可手动访问：{url}", parent=root)

    def stop():
        nonlocal stopping
        if stopping:
            return
        stopping = True
        open_button.configure(state="disabled")
        exit_button.configure(state="disabled", text="正在退出…")

        def shutdown():
            server.shutdown()
            server.server_close()
            root.after(0, root.destroy)

        threading.Thread(target=shutdown, daemon=True).start()

    open_button = tk.Button(actions, text="打开能耗统计页面", width=19, height=2,
                            command=open_page, bg="#087b70", fg="white",
                            activebackground="#06685f", activeforeground="white",
                            relief="flat", cursor="hand2")
    open_button.pack(side="left", padx=7)
    exit_button = tk.Button(actions, text="退出当前程序", width=16, height=2,
                            command=stop, relief="flat", cursor="hand2")
    exit_button.pack(side="left", padx=7)

    threading.Thread(target=server.serve_forever, daemon=True).start()
    if auto_open:
        root.after(400, open_page)
    root.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    config = load_config(ROOT / "config.yaml")
    host = args.host or os.environ.get("APP_HOST", config["app"].get("host", "127.0.0.1"))
    port = args.port or int(os.environ.get("APP_PORT", config["app"].get("port", 8765)))
    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_address[1]}"
    print(f"能源用量校核助手已启动：{url}")
    try:
        _run_control_window(server, url, auto_open=not args.no_browser)
    except Exception as exc:
        server.server_close()
        print(f"控制窗口启动失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
