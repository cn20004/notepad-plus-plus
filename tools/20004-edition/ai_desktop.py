#!/usr/bin/env python3
"""20004 AI desktop companion. Python 3.10+, tkinter, stdlib only."""
import datetime as dt
import json
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import urllib.request

APP_TITLE = "Notepad++ 20004 Edition - AI Assistant (Desktop Companion)"
DEFAULT_MODEL = "qwen2.5:7b"

class Assistant:
    def __init__(self, root):
        self.root = root
        root.title(APP_TITLE)
        root.geometry("780x680")
        root.minsize(500, 450)
        self.loaded_path = None
        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="本地 Ollama 模型").pack(side="left")
        self.model = tk.StringVar(value=DEFAULT_MODEL)
        ttk.Entry(top, textvariable=self.model, width=20).pack(side="left", padx=8)
        ttk.Button(top, text="读取文件", command=self.open_file).pack(side="left", padx=4)
        ttk.Button(top, text="保存结果", command=self.save_result).pack(side="left", padx=4)
        ttk.Label(root, text="待处理文本（可直接从 Notepad++ 粘贴，默认不上传云端）").pack(anchor="w", padx=10)
        self.input = scrolledtext.ScrolledText(root, height=12, wrap="word", undo=True)
        self.input.pack(fill="both", expand=True, padx=10, pady=5)
        actions = ttk.Frame(root, padding=(10, 2))
        actions.pack(fill="x")
        self.action = tk.StringVar(value="请用中文总结这份文本，区分事实、待办事项与未核实信息，不得编造。")
        ttk.Entry(actions, textvariable=self.action).pack(side="left", fill="x", expand=True)
        self.run_btn = ttk.Button(actions, text="发送给本地 AI", command=self.generate)
        self.run_btn.pack(side="left", padx=(6, 0))
        ttk.Label(root, text="AI 输出（检查后再保存）").pack(anchor="w", padx=10)
        self.output = scrolledtext.ScrolledText(root, height=12, wrap="word", undo=True)
        self.output.pack(fill="both", expand=True, padx=10, pady=5)
        self.status = tk.StringVar(value="就绪：只连接 http://127.0.0.1:11434")
        ttk.Label(root, textvariable=self.status).pack(fill="x", padx=10, pady=5)

    def open_file(self):
        name = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.md *.json *.csv *.log"), ("All", "*.*")])
        if not name:
            return
        try:
            from npp20004 import read
            text = read(name)
            if len(text) > 2_000_000:
                raise ValueError("文件超过 200 万字符，请先拆分后处理")
            self.loaded_path = name
            self.input.delete("1.0", "end")
            self.input.insert("1.0", text)
            self.status.set(f"已载入：{name}")
        except (OSError, ValueError) as error:
            messagebox.showerror("读取失败", str(error))

    def save_result(self):
        content = self.output.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("暂无结果", "请先生成文本")
            return
        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", "*.md"), ("Text", "*.txt")])
        if not path:
            return
        try:
            from npp20004 import safe_write
            safe_write(path, content + "\n", overwrite=False)
            self.status.set(f"已保存：{path}")
        except FileExistsError:
            messagebox.showwarning("保护已有文件", "目标文件已经存在，请选择另一个文件名")
        except OSError as error:
            messagebox.showerror("保存失败", str(error))

    def generate(self):
        text = self.input.get("1.0", "end-1c").strip()
        model = self.model.get().strip()
        prompt = self.action.get().strip()
        if not text or not model:
            messagebox.showinfo("缺少内容", "请输入文本和本地模型名称")
            return
        if len(text) > 120_000:
            messagebox.showwarning("文本过长", "请先拆分至 12 万字符以内")
            return
        self.run_btn.configure(state="disabled")
        self.status.set("正在调用本机 Ollama；不会自动发送到云端...")
        def worker():
            try:
                from npp20004 import ollama
                result = ollama(text, prompt, model, "http://127.0.0.1:11434")
            except Exception as e:
                self.root.after(0, lambda msg=str(e): self.finish(None, msg))
                return
            self.root.after(0, lambda value=result: self.finish(value, None))
        threading.Thread(target=worker, daemon=True).start()

    def finish(self, output, error):
        self.run_btn.configure(state="normal")
        if error:
            self.status.set("AI 请求失败，请确认 Ollama 已启动并下载对应模型")
            messagebox.showerror("AI 请求失败", error)
            return
        self.output.delete("1.0", "end")
        self.output.insert("1.0", output)
        self.status.set("生成完成：请校对内容，确认无误后保存")

if __name__ == "__main__":
    root = tk.Tk()
    Assistant(root)
    root.mainloop()
