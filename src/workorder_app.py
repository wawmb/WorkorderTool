# -*- coding: utf-8 -*-
"""
工单查询与导入工具
桌面应用：查询传票号产品型号信息，并自动/手动导入到ATE系统
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import urllib3
import hashlib
import json
import re
import threading
import os
import sys
import configparser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_app_dir():
    """获取应用所在目录，兼容 PyInstaller 打包和源码运行"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，exe 所在目录
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_config():
    """从config.ini读取配置，优先读取exe同目录，回退到打包内置"""
    config = configparser.ConfigParser()
    # 1. 先读 exe 同目录的 config.ini（用户可自定义修改）
    config_path = os.path.join(get_app_dir(), "config.ini")
    config.read(config_path, encoding="utf-8")
    # 2. 如果没读到，回退到打包内置的 config.ini
    if not config.has_section("login") and getattr(sys, "frozen", False):
        bundled_path = os.path.join(sys._MEIPASS, "config.ini")
        config.read(bundled_path, encoding="utf-8")
    return {
        "account": config.get("login", "account", fallback=""),
        "password": config.get("login", "password", fallback=""),
        "base_url": config.get("server", "base_url", fallback="https://192.168.96.248"),
    }


CONFIG = load_config()
BASE_URL = CONFIG["base_url"]


class WorkorderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("工单查询与导入工具")
        self.root.geometry("1100x820")
        self.root.resizable(True, True)
        self.root.minsize(900, 700)

        # 设置应用图标
        try:
            icon_path = os.path.join(get_app_dir(), "app_icon.ico")
            if not os.path.exists(icon_path) and getattr(sys, "frozen", False):
                # PyInstaller 打包后从资源目录读取
                icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass

        # 保存的会话和状态
        self.prod_session = None  # 生产管理系统session
        self.ate_session = None  # ATE系统session
        self.fproduct_options = []  # ATE系统所有可选产测属性 [(id, label), ...]
        self.current_chuanpiaohao = ""
        self.current_chanpinxinghao = ""
        self.current_fproduct_id = None

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        # 使用 clam 主题（扁平现代风格）
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # ===== 统一现代配色方案（蓝色系主色调）=====
        C_PRIMARY = "#1976D2"  # 主蓝
        C_PRIMARY_DARK = "#1565C0"  # 深蓝（悬停）
        C_PRIMARY_LIGHT = "#E3F2FD"  # 浅蓝（高亮/焦点）
        C_SUCCESS = "#43A047"  # 绿
        C_SUCCESS_DARK = "#2E7D32"
        C_WARN = "#FB8C00"  # 橙
        C_WARN_DARK = "#EF6C00"
        C_DANGER = "#E53935"  # 红
        C_BG = "#EEF2F7"  # 窗口背景（浅灰）
        C_SURFACE = "#FFFFFF"  # 面板背景（白）
        C_TEXT = "#263238"  # 主文字
        C_TEXT_SEC = "#607D8B"  # 次要文字
        C_BORDER = "#CFD8DC"  # 边框
        C_STATUS_BG = "#263238"  # 状态栏背景（深灰）

        # 统一字体
        FONT_UI = ("Microsoft YaHei", 10)
        FONT_BOLD = ("Microsoft YaHei", 10, "bold")
        FONT_TITLE = ("Microsoft YaHei", 11, "bold")
        FONT_SMALL = ("Microsoft YaHei", 9)
        FONT_MONO = ("Consolas", 9)

        # ===== 全局样式（卡片式：白底面板 + 灰底窗口）=====
        style.configure("TFrame", background=C_SURFACE)
        style.configure("TLabel", font=FONT_UI, background=C_SURFACE, foreground=C_TEXT)
        style.configure(
            "Info.TLabel", font=FONT_UI, background=C_SURFACE, foreground=C_TEXT
        )
        style.configure("TLabelframe", background=C_SURFACE, bordercolor=C_BORDER)
        style.configure(
            "TLabelframe.Label",
            font=FONT_TITLE,
            foreground=C_PRIMARY,
            background=C_SURFACE,
        )

        # 输入框
        style.configure(
            "TEntry",
            fieldbackground="white",
            bordercolor=C_BORDER,
            lightcolor=C_BORDER,
            darkcolor=C_BORDER,
            padding=4,
            insertcolor=C_PRIMARY,
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", C_PRIMARY)],
            lightcolor=[("focus", C_PRIMARY)],
            darkcolor=[("focus", C_PRIMARY)],
        )

        # 复选框
        style.configure(
            "TCheckbutton", background=C_SURFACE, foreground=C_TEXT, font=FONT_SMALL
        )

        # 滚动条
        style.configure(
            "TScrollbar",
            background=C_BORDER,
            troughcolor=C_SURFACE,
            bordercolor=C_SURFACE,
            arrowcolor=C_TEXT_SEC,
        )
        style.map("TScrollbar", background=[("active", C_PRIMARY_LIGHT)])

        # 通用按钮（扁平）
        style.configure(
            "TButton",
            font=FONT_BOLD,
            padding=(14, 7),
            background=C_SURFACE,
            foreground=C_TEXT,
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "TButton",
            background=[("active", C_PRIMARY_LIGHT)],
            foreground=[("active", C_PRIMARY)],
        )

        # 查询按钮：蓝色实心
        style.configure(
            "Query.TButton",
            font=FONT_BOLD,
            padding=(18, 8),
            background=C_PRIMARY,
            foreground="white",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Query.TButton",
            background=[
                ("active", C_PRIMARY_DARK),
                ("pressed", C_PRIMARY_DARK),
                ("disabled", "#B0BEC5"),
            ],
            foreground=[("disabled", "#ECEFF1")],
        )

        # 搜索匹配按钮：橙色实心
        style.configure(
            "Search.TButton",
            font=FONT_BOLD,
            padding=(18, 8),
            background=C_WARN,
            foreground="white",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Search.TButton",
            background=[
                ("active", C_WARN_DARK),
                ("pressed", C_WARN_DARK),
                ("disabled", "#B0BEC5"),
            ],
            foreground=[("disabled", "#ECEFF1")],
        )

        # 导入按钮：绿色实心
        style.configure(
            "Import.TButton",
            font=FONT_BOLD,
            padding=(18, 8),
            background=C_SUCCESS,
            foreground="white",
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Import.TButton",
            background=[
                ("active", C_SUCCESS_DARK),
                ("pressed", C_SUCCESS_DARK),
                ("disabled", "#B0BEC5"),
            ],
            foreground=[("disabled", "#ECEFF1")],
        )

        # 状态栏样式
        style.configure(
            "Status.TLabel",
            font=FONT_SMALL,
            background=C_STATUS_BG,
            foreground="white",
            padding=(12, 6),
        )

        # 设置窗口背景色
        self.root.configure(bg=C_BG)

        # ---- 顶部标题栏 ----
        header = tk.Frame(self.root, bg=C_PRIMARY, height=6)
        header.pack(fill=tk.X, side=tk.TOP)

        # ---- 顶部输入区 ----
        input_frame = ttk.LabelFrame(self.root, text="  登录信息  ", padding=14)
        input_frame.pack(fill=tk.X, padx=14, pady=(12, 6))

        row1 = ttk.Frame(input_frame)
        row1.pack(fill=tk.X, pady=5)
        ttk.Label(row1, text="账户:", width=8).pack(side=tk.LEFT)
        self.entry_account = ttk.Entry(row1, width=18, font=FONT_UI)
        self.entry_account.pack(side=tk.LEFT, padx=5)
        self.entry_account.insert(0, CONFIG["account"])

        ttk.Label(row1, text="密码:", width=8).pack(side=tk.LEFT, padx=(20, 0))
        self.entry_password = ttk.Entry(row1, width=18, show="*", font=FONT_UI)
        self.entry_password.pack(side=tk.LEFT, padx=5)
        self.entry_password.insert(0, CONFIG["password"])

        row2 = ttk.Frame(input_frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="传票号:", width=8).pack(side=tk.LEFT)
        self.entry_chuanpiaohao = ttk.Entry(row2, width=18, font=FONT_UI)
        self.entry_chuanpiaohao.pack(side=tk.LEFT, padx=5)

        ttk.Label(row2, text="匹配名称:", width=8).pack(side=tk.LEFT, padx=(20, 0))
        self.entry_match = ttk.Entry(row2, width=35, font=FONT_UI)
        self.entry_match.pack(side=tk.LEFT, padx=5)

        row3 = ttk.Frame(input_frame)
        row3.pack(fill=tk.X, pady=(10, 2))
        self.btn_query = ttk.Button(
            row3, text="🔍  查询", command=self.on_query, style="Query.TButton"
        )
        self.btn_query.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(row3, text="(Enter)", foreground=C_TEXT_SEC, font=FONT_SMALL).pack(
            side=tk.LEFT, padx=(0, 16)
        )
        self.btn_search_match = ttk.Button(
            row3,
            text="🔎  搜索匹配",
            command=self.on_search_match,
            state=tk.DISABLED,
            style="Search.TButton",
        )
        self.btn_search_match.pack(side=tk.LEFT, padx=8)
        ttk.Label(row3, text="(Ctrl+F)", foreground=C_TEXT_SEC, font=FONT_SMALL).pack(
            side=tk.LEFT, padx=(0, 16)
        )
        self.btn_import = ttk.Button(
            row3,
            text="📥  导入",
            command=self.on_import,
            state=tk.DISABLED,
            style="Import.TButton",
        )
        self.btn_import.pack(side=tk.LEFT, padx=8)
        ttk.Label(row3, text="(Ctrl+I)", foreground=C_TEXT_SEC, font=FONT_SMALL).pack(
            side=tk.LEFT, padx=(0, 0)
        )

        # ---- 中部：产品型号信息显示（较大区域）----
        info_frame = ttk.LabelFrame(self.root, text="  产品型号信息  ", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        self.text_info = scrolledtext.ScrolledText(
            info_frame,
            height=14,
            wrap=tk.WORD,
            font=FONT_UI,
            background=C_SURFACE,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_PRIMARY,
            padx=8,
            pady=8,
        )
        self.text_info.pack(fill=tk.BOTH, expand=True)
        # 设置文本标签颜色
        self.text_info.tag_config("label", foreground=C_PRIMARY, font=FONT_BOLD)
        self.text_info.tag_config("value", foreground=C_TEXT)
        self.text_info.tag_config(
            "header", foreground="#102027", font=FONT_TITLE, spacing1=4
        )
        self.text_info.tag_config("highlight", foreground=C_DANGER, font=FONT_TITLE)
        self.text_info.tag_config("success", foreground=C_SUCCESS, font=FONT_BOLD)

        # ---- 匹配选择区 ----
        match_frame = ttk.LabelFrame(
            self.root, text="  匹配选择（自动匹配失败时手动选择）  ", padding=10
        )
        match_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        match_top = ttk.Frame(match_frame)
        match_top.pack(fill=tk.X, pady=(0, 6))
        self.lbl_match_status = ttk.Label(
            match_top, text="", foreground=C_TEXT_SEC, font=FONT_SMALL
        )
        self.lbl_match_status.pack(side=tk.LEFT)

        self.var_nr01_only = tk.BooleanVar(value=False)
        self.chk_nr01 = ttk.Checkbutton(
            match_top,
            text="仅显示 NR01 开头",
            variable=self.var_nr01_only,
            command=self.on_filter_toggle,
        )
        self.chk_nr01.pack(side=tk.RIGHT, padx=(10, 0))

        # 用 Listbox + 滚动条替代 Combobox，支持完整显示长文本
        list_container = ttk.Frame(match_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        xscroll = ttk.Scrollbar(list_container, orient=tk.HORIZONTAL)
        yscroll = ttk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.listbox_match = tk.Listbox(
            list_container,
            font=FONT_MONO,
            height=6,
            selectmode=tk.SINGLE,
            activestyle="none",
            selectbackground=C_PRIMARY,
            selectforeground="white",
            background=C_SURFACE,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_PRIMARY,
            xscrollcommand=xscroll.set,
            yscrollcommand=yscroll.set,
        )
        xscroll.config(command=self.listbox_match.xview)
        yscroll.config(command=self.listbox_match.yview)
        self.listbox_match.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        # 选中项变化时显示完整描述
        self.listbox_match.bind("<<ListboxSelect>>", self.on_listbox_select)

        # 选中项完整描述
        self.lbl_selected = ttk.Label(
            match_frame,
            text="已选: 无",
            foreground=C_PRIMARY,
            wraplength=1050,
            justify=tk.LEFT,
            font=FONT_SMALL,
        )
        self.lbl_selected.pack(fill=tk.X, pady=(6, 0))

        # ---- 底部：导入结果（较小区域）----
        result_frame = ttk.LabelFrame(self.root, text="  导入结果  ", padding=10)
        result_frame.pack(fill=tk.BOTH, expand=False, padx=14, pady=(6, 12))

        self.text_result = scrolledtext.ScrolledText(
            result_frame,
            height=5,
            wrap=tk.WORD,
            font=FONT_MONO,
            background=C_SURFACE,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=C_BORDER,
            highlightcolor=C_PRIMARY,
            padx=8,
            pady=6,
        )
        self.text_result.pack(fill=tk.BOTH, expand=False)
        self.text_result.tag_config(
            "success", foreground=C_SUCCESS, font=("Consolas", 9, "bold")
        )
        self.text_result.tag_config(
            "fail", foreground=C_DANGER, font=("Consolas", 9, "bold")
        )
        self.text_result.tag_config("info", foreground=C_TEXT_SEC)

        # ---- 状态栏 ----
        self.status_var = tk.StringVar(value="就绪 — 请填写信息后点击查询")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, style="Status.TLabel", anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # ---- 键盘快捷键 ----
        self.root.bind("<Return>", lambda e: self.on_query())
        self.root.bind(
            "<Control-f>",
            lambda e: (
                self.on_search_match()
                if self.btn_search_match["state"] == tk.NORMAL
                else None
            ),
        )
        self.root.bind(
            "<Control-i>",
            lambda e: (
                self.on_import() if self.btn_import["state"] == tk.NORMAL else None
            ),
        )

    # ==================== 工具方法 ====================

    def log_info(self, msg):
        """写入产品型号信息区"""
        self.text_info.insert(tk.END, msg + "\n")
        self.text_info.see(tk.END)

    def log_result(self, msg, tag=None):
        """写入导入结果区，tag可选: success/fail/info"""
        if tag:
            self.text_result.insert(tk.END, msg + "\n", tag)
        else:
            self.text_result.insert(tk.END, msg + "\n")
        self.text_result.see(tk.END)

    def set_status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()

    def _save_config(self, account, password):
        """保存账户密码到 exe 同级目录的 config.ini"""
        try:
            config = configparser.ConfigParser()
            config["login"] = {"account": account, "password": password}
            config["server"] = {"base_url": BASE_URL}
            config_path = os.path.join(get_app_dir(), "config.ini")
            with open(config_path, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception:
            pass  # 保存失败不影响使用

    def run_async(self, func):
        """在后台线程中运行，避免阻塞UI"""
        self.set_status("处理中...")
        t = threading.Thread(target=func, daemon=True)
        t.start()

    def safe_json(self, r):
        """安全解析JSON响应，处理双重编码的JSON字符串"""
        try:
            data = r.json()
        except Exception:
            return {}
        # ATE系统可能返回双重编码的JSON字符串，如 "{\"success\":true}"
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return {}
        return data if isinstance(data, dict) else {}

    # ==================== 登录逻辑 ====================

    def login_prod(self, account, password):
        """登录生产管理系统，返回 requests.Session 或 None"""
        s = requests.Session()
        s.verify = False
        s.headers.update(
            {"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0"}
        )
        s.get(f"{BASE_URL}/Index/Login/index", timeout=10)
        md5_pwd = hashlib.md5(password.encode()).hexdigest()
        r = s.post(
            f"{BASE_URL}/index/login/check_login",
            data={
                "account": account,
                "password": md5_pwd,
                "SerialNum": "",
                "MacInfo": "",
            },
            timeout=10,
        )
        data = self.safe_json(r)
        if data.get("success"):
            return s
        return None

    def login_ate(self, account, password):
        """登录ATE系统，返回 requests.Session 或 None"""
        s = requests.Session()
        s.verify = False
        s.headers.update(
            {"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0"}
        )
        s.get(f"{BASE_URL}/ate/index/index", timeout=10)
        md5_pwd = hashlib.md5(password.encode()).hexdigest()
        r = s.post(
            f"{BASE_URL}/ate/login/check_login.html",
            data={"account": account, "password": md5_pwd},
            timeout=10,
        )
        data = self.safe_json(r)
        if data.get("success"):
            return s
        return None

    # ==================== 查询逻辑 ====================

    def query_workorder(self, session, chuanpiaohao):
        """查询生产管理系统整机工单，返回工单数据列表"""
        params = {
            "page": 1,
            "limit": 10,
            "query": 1,
            "chuanpiaohao": chuanpiaohao,
            "gongdantype": "",
            "status": "",
            "cpxh": "",
            "khdm": "",
            "chengpinliaohao": "",
            "check_man": "",
            "kaidan_start_time": "",
            "kaidan_end_time": "",
            "kaigong_start_time": "",
            "kaigong_end_time": "",
            "wangong_start_time": "",
            "wangong_end_time": "",
            "ruanjianyaoqiu": "",
            "xianti": "",
            "is_beyond_check": "",
            "unit": "",
            "process_num": "",
            "dev_software": "",
            "is_fauto": "",
        }
        r = session.get(
            f"{BASE_URL}/index/workorder/get_data", params=params, timeout=10
        )
        data = self.safe_json(r)
        return data.get("data", [])

    def ate_sel_product(self, session, chuanpiaohao):
        """查询ATE系统中该传票号对应的产品ID"""
        r = session.get(
            f"{BASE_URL}/ate/woimport/selProduct/chuanph/{chuanpiaohao}", timeout=10
        )
        return self.safe_json(r)

    def ate_get_fproduct_options(self, session):
        """从ATE正式工单导入页面解析所有可选产测属性"""
        r = session.get(f"{BASE_URL}/ate/Woimport/index", timeout=10)
        text = r.text
        if text.startswith('"'):
            text = json.loads(text)
        # 解析 <option value="123">描述</option>
        pattern = r'<option value="(\d+)">(.*?)</option>'
        matches = re.findall(pattern, text)
        options = []
        for val, label in matches:
            # 跳过空值选项
            if val:
                options.append((val, label))
        return options

    def ate_check_chuanph(self, session, chuanpiaohao):
        """检查传票号是否已经导入过"""
        r = session.post(
            f"{BASE_URL}/ate/woimport/check_chuanph",
            data={"chuanpiaohao": chuanpiaohao},
            timeout=10,
        )
        return self.safe_json(r)

    def ate_import(self, session, chuanpiaohao, fproduct, flag="0", node="1"):
        """执行正式工单导入"""
        r = session.post(
            f"{BASE_URL}/ate/woimport/import",
            data={
                "chuanpiaohao": chuanpiaohao,
                "fproduct": fproduct,
                "flag": flag,
                "node": node,
            },
            timeout=10,
        )
        return self.safe_json(r)

    # ==================== 提取HPC/SPC逻辑 ====================

    def extract_match_keywords(self, chanpinxinghao):
        """
        从产品型号信息中提取 HPC 开头和 SPC 开头的信息段。
        产品型号以 '-' 分隔，返回匹配到的段列表。
        """
        if not chanpinxinghao:
            return []
        parts = chanpinxinghao.split("-")
        keywords = []
        for part in parts:
            part = part.strip()
            if part.upper().startswith("HPC") or part.upper().startswith("SPC"):
                keywords.append(part)
        return keywords

    # ==================== 按钮事件 ====================

    def on_query(self):
        """查询按钮：登录 -> 查询工单 -> 提取匹配 -> 查询ATE -> 自动/手动导入"""
        account = self.entry_account.get().strip()
        password = self.entry_password.get().strip()
        chuanpiaohao = self.entry_chuanpiaohao.get().strip()

        if not account or not password or not chuanpiaohao:
            messagebox.showwarning("提示", "请填写账户、密码和传票号")
            return

        # 保存账户密码到 config.ini（exe 同级目录）
        self._save_config(account, password)

        # 清空显示区
        self.text_info.delete("1.0", tk.END)
        self.text_result.delete("1.0", tk.END)
        self.listbox_match.delete(0, tk.END)
        self.lbl_match_status.config(text="")
        self.lbl_selected.config(text="已选: 无")
        self.btn_import.config(state=tk.DISABLED)
        self.btn_search_match.config(state=tk.DISABLED)
        self.current_fproduct_id = None
        self.current_chuanpiaohao = chuanpiaohao
        # 重置ATE会话，确保用新账户登录
        self.ate_session = None

        self.run_async(lambda: self._do_query(account, password, chuanpiaohao))

    def _do_query(self, account, password, chuanpiaohao):
        """后台执行查询流程"""
        try:
            # Step 1: 登录生产管理系统
            self.set_status("正在登录生产管理系统...")
            self.prod_session = self.login_prod(account, password)
            if not self.prod_session:
                self.root.after(
                    0,
                    lambda: messagebox.showerror(
                        "错误", "登录生产管理系统失败，请检查账户密码"
                    ),
                )
                self.set_status("登录失败")
                return

            # Step 2: 查询整机工单
            self.set_status("正在查询整机工单...")
            orders = self.query_workorder(self.prod_session, chuanpiaohao)
            if not orders:
                self.root.after(
                    0,
                    lambda: self.log_info(
                        f"未找到传票号 {chuanpiaohao} 对应的整机工单"
                    ),
                )
                self.set_status("未找到工单")
                return

            # Step 3: 显示产品型号信息
            self.root.after(0, lambda: self._display_workorder(orders[0]))

            chanpinxinghao = orders[0].get("chanpinxinghao", "")
            self.current_chanpinxinghao = chanpinxinghao

            # Step 4: 提取HPC/SPC开头的信息（仅当匹配名称为空时自动填入，避免覆盖手动修改）
            keywords = self.extract_match_keywords(chanpinxinghao)
            current_match = self.entry_match.get().strip()
            if keywords and not current_match:
                match_str = " ".join(keywords)
                self.root.after(0, lambda: self.entry_match.delete(0, tk.END))
                self.root.after(0, lambda: self.entry_match.insert(0, match_str))
                self.root.after(
                    0, lambda: self.log_info(f"\n提取匹配关键词: {match_str}")
                )
            elif keywords:
                self.root.after(
                    0,
                    lambda: self.log_info(
                        f"\n提取匹配关键词: {' '.join(keywords)}（已保留手动修改的匹配名称）"
                    ),
                )
            else:
                self.root.after(
                    0, lambda: self.log_info("\n未在产品型号中找到HPC/SPC开头的信息")
                )

            # 查询完成，启用搜索匹配按钮
            self.root.after(0, lambda: self.btn_search_match.config(state=tk.NORMAL))
            self.set_status("查询完成，可修改匹配名称后点「搜索匹配」")

        except Exception as e:
            err_msg = str(e)
            self.root.after(
                0, lambda: messagebox.showerror("错误", f"查询过程中出错:\n{err_msg}")
            )
            self.set_status(f"错误: {err_msg}")

    def on_search_match(self):
        """搜索匹配按钮：用当前匹配名称去ATE系统过滤产测属性列表"""
        account = self.entry_account.get().strip()
        password = self.entry_password.get().strip()
        chuanpiaohao = self.current_chuanpiaohao
        if not chuanpiaohao:
            messagebox.showwarning("提示", "请先点「查询」获取产品信息")
            return

        # 清空列表和状态
        self.listbox_match.delete(0, tk.END)
        self.lbl_selected.config(text="已选: 无")
        self.btn_import.config(state=tk.DISABLED)
        self.current_fproduct_id = None

        self.run_async(lambda: self._do_search_match(account, password, chuanpiaohao))

    def _do_search_match(self, account, password, chuanpiaohao):
        """后台执行搜索匹配"""
        try:
            # 登录ATE系统（如尚未登录）
            if not self.ate_session:
                self.set_status("正在登录ATE系统...")
                self.ate_session = self.login_ate(account, password)
                if not self.ate_session:
                    self.root.after(
                        0, lambda: messagebox.showerror("错误", "登录ATE系统失败")
                    )
                    self.set_status("ATE登录失败")
                    return

            # 查询ATE中该传票号是否已有对应产品
            self.set_status("正在查询ATE产品匹配...")
            sel_result = self.ate_sel_product(self.ate_session, chuanpiaohao)

            if sel_result.get("success"):
                auto_matched_id = str(sel_result.get("msg"))
                self.root.after(
                    0,
                    lambda: self.lbl_match_status.config(
                        text=f"系统匹配到产品ID: {auto_matched_id}（仍需手动选择导入）",
                        foreground="green",
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.log_info(f"\nATE系统匹配到产品ID: {auto_matched_id}"),
                )
            else:
                self.root.after(
                    0,
                    lambda: self.lbl_match_status.config(
                        text="未自动匹配，请从列表选择", foreground="orange"
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.log_info(
                        f"\nATE系统未自动匹配到产品: {sel_result.get('msg', '')}"
                    ),
                )

            # 获取产测属性列表并按关键词过滤
            self.set_status("正在获取产测属性列表...")
            all_options = self.ate_get_fproduct_options(self.ate_session)
            self.fproduct_options = all_options

            match_text = self.entry_match.get().strip()
            filtered = []
            if match_text:
                for opt_id, opt_label in all_options:
                    if any(
                        kw.upper() in opt_label.upper() for kw in match_text.split()
                    ):
                        filtered.append((opt_id, opt_label))

            if not filtered:
                # 没找到匹配项，显示空列表
                self.root.after(
                    0,
                    lambda: self.log_info(
                        f"未找到包含「{match_text}」的匹配项，请修改匹配名称后重新搜索"
                    ),
                )
                self.root.after(
                    0,
                    lambda: self.lbl_match_status.config(
                        text=f"无匹配结果，请修改匹配名称", foreground="red"
                    ),
                )
            else:
                self.root.after(
                    0, lambda: self.log_info(f"找到 {len(filtered)} 个匹配项")
                )

            self._filtered_options = filtered

            # 填充Listbox，根据勾选框状态过滤显示
            self.root.after(0, lambda: self.on_filter_toggle())
            self.root.after(0, lambda: self.btn_import.config(state=tk.NORMAL))
            self.set_status("请从列表选择并点击导入")

        except Exception as e:
            err_msg = str(e)
            self.root.after(
                0, lambda: messagebox.showerror("错误", f"搜索匹配出错:\n{err_msg}")
            )
            self.set_status(f"错误: {err_msg}")

    def _display_workorder(self, order):
        """显示工单信息到信息区"""
        fields = [
            ("传票号", "chuanpiaohao"),
            ("产品型号", "chanpinxinghao"),
            ("产品类别", "chanpinleibie"),
            ("成品料号", "chengpinliaohao"),
            ("客户代码", "kehudaima"),
            ("工单类型", "gongdantype"),
            ("工单状态", "status"),
            ("投产总数", "touchannum"),
            ("线体", "xianti"),
            ("投产单位", "unit"),
            ("审核员", "check_man"),
            ("是否导入自动化", "is_fauto"),
        ]
        type_map = {
            1: "正常工单",
            2: "整改工单",
            5: "中试工单",
            4: "翻新工单",
            6: "样试工单",
            7: "CTO工单",
            8: "加工工单",
        }
        status_map = {
            0: "品管审核中",
            1: "工艺审核中",
            2: "进行中",
            3: "审核不通过",
            5: "已完成",
        }

        # 标题行
        self.text_info.insert(tk.END, "━" * 50 + "\n", "header")
        self.text_info.insert(tk.END, f"  传票号: ", "label")
        self.text_info.insert(tk.END, f"{order.get('chuanpiaohao', '')}\n", "highlight")
        self.text_info.insert(tk.END, "━" * 50 + "\n\n", "header")

        for label, key in fields:
            if key == "chuanpiaohao":
                continue  # 已经在标题显示了
            val = order.get(key, "")
            if key == "gongdantype" and val:
                val = type_map.get(val, str(val))
            if key == "status" and val != "":
                val = status_map.get(val, str(val))
            self.text_info.insert(tk.END, f"  {label}: ", "label")
            self.text_info.insert(tk.END, f"{val}\n", "value")
        self.text_info.see(tk.END)

    def on_listbox_select(self, event):
        """Listbox选中项变化时更新完整描述标签"""
        sel = self.listbox_match.curselection()
        if sel:
            self._update_selected_label(sel[0])

    def on_filter_toggle(self):
        """勾选框切换：仅显示NR01开头 或 显示全部"""
        if not hasattr(self, "_filtered_options") or not self._filtered_options:
            return
        nr01_only = self.var_nr01_only.get()
        self.listbox_match.delete(0, tk.END)
        self._displayed_options = []
        for oid, olabel in self._filtered_options:
            if nr01_only and not olabel.strip().upper().startswith("NR01"):
                continue
            self.listbox_match.insert(tk.END, f"[{oid}] {olabel}")
            self._displayed_options.append((oid, olabel))
        if self._displayed_options:
            self.listbox_match.selection_set(0)
            self._update_selected_label(0)
        else:
            self.lbl_selected.config(text="已选: 无（无匹配项）")

    def _update_selected_label(self, idx):
        """更新选中项的完整描述"""
        if hasattr(self, "_displayed_options") and idx < len(self._displayed_options):
            oid, olabel = self._displayed_options[idx]
            self.lbl_selected.config(text=f"已选: [{oid}] {olabel}")

    def on_import(self):
        """导入按钮：手动选择后执行导入"""
        if not self.ate_session:
            messagebox.showwarning("提示", "请先查询")
            return

        chuanpiaohao = self.current_chuanpiaohao
        if not chuanpiaohao:
            messagebox.showwarning("提示", "请先输入传票号并查询")
            return

        # 如果已有自动匹配的fproduct_id，直接用
        if self.current_fproduct_id:
            fproduct_id = self.current_fproduct_id
        else:
            # 从Listbox选择
            sel = self.listbox_match.curselection()
            if not sel:
                messagebox.showwarning("提示", "请从列表选择一个产测属性")
                return
            sel_idx = sel[0]
            if hasattr(self, "_displayed_options") and sel_idx < len(
                self._displayed_options
            ):
                fproduct_id = self._displayed_options[sel_idx][0]
            else:
                messagebox.showwarning("提示", "选择无效")
                return

        self.run_async(lambda: self._do_import(chuanpiaohao, fproduct_id))

    def _do_import(self, chuanpiaohao, fproduct_id):
        """后台执行导入"""
        try:
            self.set_status("正在导入...")
            self.root.after(0, lambda: self.log_result(f"\n{'=' * 50}"))
            self.root.after(0, lambda: self.log_result(f"传票号: {chuanpiaohao}"))
            self.root.after(0, lambda: self.log_result(f"产品ID: {fproduct_id}"))

            # 检查是否已导入
            check_result = self.ate_check_chuanph(self.ate_session, chuanpiaohao)
            self.root.after(
                0, lambda: self.log_result(f"[检查] {check_result.get('msg', '')}")
            )

            # 执行导入
            import_result = self.ate_import(self.ate_session, chuanpiaohao, fproduct_id)
            if import_result.get("success"):
                self.root.after(
                    0,
                    lambda: self.log_result(
                        f"[结果] ✓ 导入成功！{import_result.get('msg', '')}", "success"
                    ),
                )
            else:
                self.root.after(
                    0,
                    lambda: self.log_result(
                        f"[结果] ✗ 导入失败：{import_result.get('msg', '')}", "fail"
                    ),
                )

            self.set_status("导入完成")

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self.log_result(f"[错误] {err_msg}"))
            self.set_status(f"错误: {err_msg}")


if __name__ == "__main__":
    root = tk.Tk()
    app = WorkorderApp(root)
    root.mainloop()
