import sys
import os
import queue
import threading
import customtkinter as ctk
from tkinter import messagebox

# Ensure backend directory is importable
backend_dir = os.path.join(os.path.dirname(__file__), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from storage import StorageManager, get_config_dir, get_logs_dir
    from crawler_engine import CrawlerEngine
except ImportError:
    from backend.storage import StorageManager, get_config_dir, get_logs_dir
    from backend.crawler_engine import CrawlerEngine

# Set Light Appearance Mode & Blue Theme
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class FAQCheckerGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("FAQ 自動檢閱管理系統 - 臺北市政府網站整合平台 (單機版)")
        self.geometry("1180x780")
        self.minsize(960, 640)
        self.configure(fg_color="#f8fafc")

        # Backend components
        self.storage = StorageManager()
        self.msg_queue = queue.Queue()
        self.crawler = CrawlerEngine(log_callback=self._log_callback)

        self.nodes = self.storage.get_nodes()
        self.settings = self.storage.get_settings()

        # Build Layout
        self._build_header()
        self._build_tabs()

        # Periodic Queue Processor
        self.after(100, self._process_queue)

        # Load initial data
        self.refresh_nodes_list()
        self.load_settings_to_ui()

    # ------------------------------------------------------------------ #
    #  Header                                                              #
    # ------------------------------------------------------------------ #
    def _build_header(self):
        """Build the top header bar with title and status badge."""
        #header = ctk.CTkFrame(self, fg_color="#1e40af", corner_radius=0, height=64)
        header = ctk.CTkFrame(self, fg_color="#84C1FF", border_color="#E5E7EB", corner_radius=0, height=80)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=10)

        # App title
        ctk.CTkLabel(
            inner,
            text="🏛  FAQ 自動檢閱管理系統",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=18, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left", anchor="w")

        # Status badge (right side)
        self.status_badge = ctk.CTkFrame(inner, fg_color="#f1f5f9", corner_radius=8,
                                          border_width=1, border_color="#cbd5e1")
        self.status_badge.pack(side="right", anchor="e")

        self.status_lbl = ctk.CTkLabel(
            self.status_badge,
            text="● 準備就緒 (IDLE)",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#475569",
        )
        self.status_lbl.pack(padx=14, pady=6)

    # ------------------------------------------------------------------ #
    #  Tabs                                                                #
    # ------------------------------------------------------------------ #
    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="transparent",
            border_width=0,
            corner_radius=0,

            # ===== Tab 整體區域 =====
            segmented_button_fg_color="#FFFFFF",

            # ===== 選中的 Tab =====
            segmented_button_selected_color="#EAF4FF",
            segmented_button_selected_hover_color="#DDEEFF",

            # ===== 未選中的 Tab =====
            segmented_button_unselected_color="#FFFFFF",
            segmented_button_unselected_hover_color="#F1F5F9",

            # ===== Tab 文字 =====
            text_color="#334155",
            text_color_disabled="#94A3B8",
        )

        self.tabview.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(10, 12),
        )

        self.tab_nodes = self.tabview.add("📋 路徑節點")
        self.tab_dashboard = self.tabview.add("🚀 任務儀表板")
        self.tab_logs = self.tabview.add("📜 執行日誌")
        self.tab_settings = self.tabview.add("⚙️ 系統設定")

        self.tabview._segmented_button.configure(
            height=40,
            corner_radius=7,
            font=ctk.CTkFont(
                family="Microsoft JhengHei",
                size=13,
                weight="bold",
            ),
        )

        for tab in (
            self.tab_nodes,
            self.tab_dashboard,
            self.tab_logs,
            self.tab_settings,
        ):
            tab.configure(
                fg_color="#F8FAFC"
            )
        '''
        self.tabview = ctk.CTkTabview(
            self,
            #fg_color="#F8FAFC",
            fg_color="transparent",
            border_width=1,
            border_color="#E2E8F0",
            corner_radius=12,
            segmented_button_fg_color="#F1F5F9",
            segmented_button_selected_color="#DBEAFE",
            segmented_button_selected_hover_color="#BFDBFE",
            segmented_button_unselected_color="#E8EEF5",
            segmented_button_unselected_hover_color="#D9E3EE",
            #text_color="#1E3A8A",
            text_color="#0080FF",
            text_color_disabled="#94A3B8",
        )

        self.tabview.pack(
            fill="both",
            expand=True,
            padx=12,
            pady=(10, 12),
        )

        self.tab_nodes = self.tabview.add("📋 路徑節點")
        self.tab_dashboard = self.tabview.add("🚀 任務儀表板")
        self.tab_logs = self.tabview.add("📜 執行日誌")
        self.tab_settings = self.tabview.add("⚙️ 系統設定")

        self.tabview._segmented_button.configure(
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(
                family="Microsoft JhengHei",
                size=13,
                weight="bold",
            ),
        )
        

        for tab in (
            self.tab_nodes,
            self.tab_dashboard,
            self.tab_logs,
            self.tab_settings,
        ):
            tab.configure(fg_color="#F8FAFC")
        '''

        self._build_tab_nodes()
        self._build_tab_dashboard()
        self._build_tab_logs()
        self._build_tab_settings()
    
    def _build_tab_nodes(self):
        """Build the nodes management tab."""
        # Toolbar
        toolbar = ctk.CTkFrame(self.tab_nodes, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            toolbar,
            text="爬蟲路徑節點清單",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=15, weight="bold"),
            text_color="#0f172a",
        ).pack(side="left")
        '''
        btn_save = ctk.CTkButton(
            toolbar,
            text="💾 儲存變更至檔案",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            fg_color="#059669", hover_color="#047857",
            height=36, corner_radius=8,
            command=self.save_all_nodes,
        )
        btn_save.pack(side="right")

        btn_add = ctk.CTkButton(
            toolbar,
            text="＋ 新增路徑節點",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            fg_color="#2563eb", hover_color="#1d4ed8",
            height=36, corner_radius=8,
            command=self.open_add_node_modal,
        )
        btn_add.pack(side="right", padx=(0, 10))
        '''
        btn_add = ctk.CTkButton(
            toolbar,
            text="＋ 新增路徑節點",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            fg_color="#3B8ED0",
            hover_color="#2F7DBB",
            text_color="white",
            height=38,
            corner_radius=8,
            command=self.open_add_node_modal,
        )
        btn_add.pack(side="right", padx=(5,0))

        btn_save = ctk.CTkButton(
            toolbar,
            text="💾 儲存變更",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            fg_color="#f3f4f6",
            hover_color="#e5e7eb",
            text_color="#1f2328",
            border_width=1,
            border_color="#E2E8F0",
            height=38,
            corner_radius=8,
            command=self.save_all_nodes,
        )
        btn_save.pack(side="right")


        # Scrollable Frame for Node Cards
        self.nodes_scroll_frame = ctk.CTkScrollableFrame(
            self.tab_nodes,
            fg_color="#f8fafc",
            corner_radius=8,
            border_width=1,
            border_color="#e2e8f0",
        )
        self.nodes_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh_nodes_list(self):
        """Clear and re-render all node cards."""
        for widget in self.nodes_scroll_frame.winfo_children():
            widget.destroy()

        if not self.nodes:
            ctk.CTkLabel(
                self.nodes_scroll_frame,
                text="尚無任何路徑節點，請點選上方「新增路徑節點」開始建立。",
                font=ctk.CTkFont(family="Microsoft JhengHei", size=13),
                text_color="#94a3b8",
            ).pack(pady=40)
            return

        for node in self.nodes:
            self._render_node_card(node)

    def _render_node_card(self, node: dict):
        """Render a single node card."""
        card = ctk.CTkFrame(
            self.nodes_scroll_frame,
            fg_color="#ffffff",
            corner_radius=10,
            border_width=1,
            border_color="#e2e8f0",
        )
        card.pack(fill="x", padx=10, pady=8)

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="x", padx=16, pady=14)

        # Header Row: Path Badge + Edit/Delete Buttons
        top_row = ctk.CTkFrame(card_inner, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 10))

        #path_badge = ctk.CTkFrame(top_row, fg_color="#e0f2fe", corner_radius=6)
        path_badge = ctk.CTkFrame(top_row, fg_color="#ECFEFF", corner_radius=6)
        path_badge.pack(side="left")

        ctk.CTkLabel(
            path_badge,
            text=f" 📍  {node['path']} ",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            #text_color="#0369a1",
            text_color="#0891B2",
        ).pack(padx=10, pady=4)

        # Action buttons
        actions_box = ctk.CTkFrame(top_row, fg_color="transparent")
        actions_box.pack(side="right")

        ctk.CTkButton(
            actions_box,
            text="編輯",
            width=60, height=28,
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
            fg_color="#f1f5f9", text_color="#334155", hover_color="#e2e8f0",
            corner_radius=6,
            command=lambda n=node: self.open_edit_node_modal(n),
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            actions_box,
            text="刪除",
            width=60, height=28,
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
            fg_color="#ffe4e6", text_color="#e11d48", hover_color="#fecdd3",
            corner_radius=6,
            command=lambda n_id=node["id"]: self.delete_node(n_id),
        ).pack(side="left", padx=4)

        # Keywords Chip Tags
        ctk.CTkLabel(
            card_inner,
            text=f"問答搜尋關鍵字 ({len(node.get('keywords', []))} 項):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=11),
            text_color="#64748b",
        ).pack(anchor="w", pady=(0, 6))

        chips_frame = ctk.CTkFrame(card_inner, fg_color="transparent")
        chips_frame.pack(fill="x", anchor="w")

        for kw in node.get("keywords", []):
            #chip = ctk.CTkFrame(chips_frame, fg_color="#f3e8ff", corner_radius=6)
            chip = ctk.CTkFrame(chips_frame, fg_color="#EFF6FF", corner_radius=6)
            chip.pack(side="left", padx=3, pady=3)
            ctk.CTkLabel(
                chip,
                text=kw,
                font=ctk.CTkFont(family="Microsoft JhengHei", size=11),
                #text_color="#7e22ce",
                text_color="#42677F",
            ).pack(padx=8, pady=2)

    

    def open_add_node_modal(self):
        self._show_node_editor_modal(title="新增路徑節點")

    def open_edit_node_modal(self, node: dict):
        self._show_node_editor_modal(title="編輯路徑節點", node=node)

    def _show_node_editor_modal(self, title: str, node: dict = None):
        modal = ctk.CTkToplevel(self)
        modal.title(title)
        modal.geometry("560x520")
        modal.configure(fg_color="#ffffff")
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text=title,
            font=ctk.CTkFont(family="Microsoft JhengHei", size=16, weight="bold"),
            text_color="#0f172a",
        ).pack(anchor="w", padx=24, pady=(20, 10))

        # Path input
        ctk.CTkLabel(
            modal,
            text="目錄階層路徑 (請用 > 分隔):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", padx=24, pady=(5, 4))

        path_entry = ctk.CTkEntry(
            modal,
            placeholder_text="例如: 業務專區>地政問答>地價類",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
            height=36, corner_radius=8,
        )
        path_entry.pack(fill="x", padx=24, pady=(0, 15))
        if node:
            path_entry.insert(0, node["path"])

        # Keywords section
        ctk.CTkLabel(
            modal,
            text="新增問答關鍵字:",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", padx=24, pady=(0, 4))

        kw_input_frame = ctk.CTkFrame(modal, fg_color="transparent")
        kw_input_frame.pack(fill="x", padx=24, pady=(0, 10))

        kw_entry = ctk.CTkEntry(
            kw_input_frame,
            placeholder_text="輸入關鍵字按下新增",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
            height=36, corner_radius=8,
        )
        kw_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        keywords_list = list(node.get("keywords", [])) if node else []

        kw_chips_scroll = ctk.CTkScrollableFrame(
            modal, fg_color="#f8fafc", corner_radius=8, height=180
        )
        kw_chips_scroll.pack(fill="both", expand=True, padx=24, pady=5)

        def render_modal_chips():
            for w in kw_chips_scroll.winfo_children():
                w.destroy()
            for idx, item in enumerate(keywords_list):
                chip = ctk.CTkFrame(
                    kw_chips_scroll, fg_color="#ffffff",
                    corner_radius=6, border_width=1, border_color="#cbd5e1"
                )
                chip.pack(fill="x", padx=6, pady=4)
                ctk.CTkLabel(
                    chip, text=item,
                    font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
                    text_color="#1e293b",
                ).pack(side="left", padx=10, pady=4)

                def remove_item(i=idx):
                    keywords_list.pop(i)
                    render_modal_chips()

                ctk.CTkButton(
                    chip, text="✕", width=24, height=24,
                    fg_color="transparent", text_color="#ef4444", hover_color="#fee2e2",
                    command=remove_item,
                ).pack(side="right", padx=6)

        def add_keyword_item():
            val = kw_entry.get().strip()
            if val and val not in keywords_list:
                keywords_list.append(val)
                kw_entry.delete(0, "end")
                render_modal_chips()

        ctk.CTkButton(
            kw_input_frame, text="新增", width=70, height=36,
            fg_color="#2563eb", hover_color="#1d4ed8",
            command=add_keyword_item,
        ).pack(side="right")
        kw_entry.bind("<Return>", lambda e: add_keyword_item())

        render_modal_chips()

        def save_modal_data():
            p = path_entry.get().strip()
            if not p:
                messagebox.showerror("錯誤", "目錄路徑不可為空！", parent=modal)
                return
            if not keywords_list:
                messagebox.showerror("錯誤", "請至少新增一個問答關鍵字！", parent=modal)
                return

            if node:
                node["path"] = p
                node["keywords"] = keywords_list
            else:
                self.nodes.append({
                    "id": f"node_{len(self.nodes) + 1}",
                    "path": p,
                    "keywords": keywords_list,
                    "enabled": True,
                })

            self.refresh_nodes_list()
            modal.destroy()

        ctk.CTkButton(
            modal, text="確認儲存節點", height=38,
            #fg_color="#059669", hover_color="#047857",
            fg_color="#f3f4f6",
            hover_color="#e5e7eb",
            text_color="#1f2328",
            border_width=1,
            border_color="#E2E8F0",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            command=save_modal_data,
        ).pack(fill="x", padx=24, pady=16)

    def delete_node(self, node_id: str):
        if messagebox.askyesno("確認刪除", "確定要刪除此路徑節點嗎？"):
            self.nodes = [n for n in self.nodes if n["id"] != node_id]
            self.refresh_nodes_list()

    def save_all_nodes(self):
        current_data = self.storage.load()
        current_data["nodes"] = self.nodes
        if self.storage.save(current_data):
            messagebox.showinfo("成功", "所有爬蟲節點資料已成功寫入 nodes_config.json！")
        else:
            messagebox.showerror("錯誤", "儲存檔案失敗！")

    # ------------------------------------------------------------------ #
    #  TAB 2: Dashboard                                                    #
    # ------------------------------------------------------------------ #
    def _build_tab_dashboard(self):
        dashboard_frame = ctk.CTkFrame(self.tab_dashboard, fg_color="transparent")
        dashboard_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Control Card
        control_card = ctk.CTkFrame(
            dashboard_frame, fg_color="#ffffff",
            corner_radius=12, border_width=1, border_color="#e2e8f0"
        )
        control_card.pack(fill="x", pady=(0, 16))

        cc_inner = ctk.CTkFrame(control_card, fg_color="transparent")
        cc_inner.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(
            cc_inner,
            text="任務控制台",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=16, weight="bold"),
            text_color="#0f172a",
        ).pack(anchor="w", pady=(0, 14))

        btn_box = ctk.CTkFrame(cc_inner, fg_color="transparent")
        btn_box.pack(fill="x", pady=(0, 10))

        self.btn_start = ctk.CTkButton(
            btn_box,
            text="▶  啟動 FAQ 自動檢閱任務",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=14, weight="bold"),
            fg_color="#059669", #hover_color="#047857",
            width=210,
            height=44, corner_radius=10,
            command=self.start_crawler_task,
        )
        self.btn_start.pack(side="left", padx=(0, 12))

        self.btn_stop = ctk.CTkButton(
            btn_box,
            text="⏹  強制停止任務",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=14, weight="bold"),
            fg_color="#e11d48", hover_color="#be123c",
            height=44, corner_radius=10,
            command=self.stop_crawler_task,
        )
        self.btn_stop.pack(side="left")
        self.btn_stop.configure(state="disabled")

        # Progress Card
        prog_card = ctk.CTkFrame(
            dashboard_frame, fg_color="#ffffff",
            corner_radius=12, border_width=1, border_color="#e2e8f0"
        )
        prog_card.pack(fill="x", pady=(0, 16))

        pc_inner = ctk.CTkFrame(prog_card, fg_color="transparent")
        pc_inner.pack(fill="x", padx=20, pady=20)

        prog_header = ctk.CTkFrame(pc_inner, fg_color="transparent")
        prog_header.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            prog_header,
            text="全域執行進度",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=14, weight="bold"),
            text_color="#0f172a",
        ).pack(side="left")

        self.pct_label = ctk.CTkLabel(
            prog_header,
            text="0%",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=16, weight="bold"),
            text_color="#2563eb",
        )
        self.pct_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            pc_inner, height=12, corner_radius=6,
            progress_color="#2563eb", fg_color="#e2e8f0"
        )
        self.progress_bar.pack(fill="x", pady=6)
        self.progress_bar.set(0)

        self.stats_lbl = ctk.CTkLabel(
            pc_inner,
            text="已完成: 0 / 0 項目 ｜ 當前步驟: 等待中",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12),
            text_color="#64748b",
        )
        self.stats_lbl.pack(anchor="w", pady=(6, 0))

        # Current Item Box
        curr_box = ctk.CTkFrame(
            dashboard_frame, fg_color="#e0f2fe",
            corner_radius=10, border_width=1, border_color="#bae6fd"
        )
        curr_box.pack(fill="x")

        cb_inner = ctk.CTkFrame(curr_box, fg_color="transparent")
        cb_inner.pack(fill="x", padx=18, pady=14)

        ctk.CTkLabel(
            cb_inner,
            text="當前正在檢閱之目錄與關鍵字:",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=11),
            text_color="#0369a1",
        ).pack(anchor="w")

        self.curr_item_lbl = ctk.CTkLabel(
            cb_inner,
            text="無執行中的任務",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            text_color="#0c4a6e",
        )
        self.curr_item_lbl.pack(anchor="w", pady=(4, 0))

    def start_crawler_task(self):
        if self.crawler.is_running():
            messagebox.showwarning("提示", "任務已經在執行中！")
            return

        paths_dict = self.storage.get_paths_and_checklists_dict()
        if not paths_dict:
            messagebox.showwarning("提示", "沒有已啟用的路徑節點可以執行檢閱！")
            return

        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_lbl.configure(text="● 任務執行中 (RUNNING)", text_color="#2563eb")
        self.status_badge.configure(fg_color="#dbeafe", border_color="#93c5fd")

        thread = threading.Thread(
            target=self.crawler.run,
            args=(paths_dict, self.storage.get_settings()),
            daemon=True,
        )
        thread.start()

    def stop_crawler_task(self):
        if self.crawler.is_running():
            self.crawler.request_stop()
            messagebox.showinfo("提示", "已送出停止請求，請稍候...")

    # ------------------------------------------------------------------ #
    #  TAB 3: Logs                                                         #
    # ------------------------------------------------------------------ #
    def _build_tab_logs(self):
        log_frame = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        top = ctk.CTkFrame(log_frame, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(
            top, text="清空日誌", width=80, height=30,
            fg_color="#e2e8f0", text_color="#334155", hover_color="#cbd5e1",
            command=self.clear_logs,
        ).pack(side="right")

        ctk.CTkButton(
            top, text="📂 開啟 Log 資料夾", width=140, height=30,
            fg_color="#e2e8f0", text_color="#334155", hover_color="#cbd5e1",
            command=self.open_logs_dir,
        ).pack(side="right", padx=(0, 10))
        
        self.log_textbox = ctk.CTkTextbox(
            log_frame,
            fg_color="#F2F2F2",
            text_color="#333333",
            font=ctk.CTkFont(family="Microsoft Jhenghei", size=14),
            corner_radius=10,
            border_width=1,
            border_color="#E2E8F0",
        )
        self.log_textbox.pack(fill="both", expand=True)
        self.log_textbox.insert("end", "[SYSTEM] 系統初始化完成，等待啟動任務...\n")

    def clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def open_logs_dir(self):
        logs_dir = get_logs_dir()
        os.makedirs(logs_dir, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(logs_dir)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', logs_dir])
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟 Log 資料夾: {e}")

    def open_config_dir(self):
        config_dir = get_config_dir()
        os.makedirs(config_dir, exist_ok=True)
        try:
            if sys.platform == 'win32':
                os.startfile(config_dir)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', config_dir])
        except Exception as e:
            messagebox.showerror("錯誤", f"無法開啟設定檔資料夾: {e}")

    def append_log(self, message: str, level: str = "INFO"):
        prefix = f"[{level}] " if level else ""
        self.log_textbox.insert("end", f"{prefix}{message}\n")
        self.log_textbox.see("end")
        if "等待使用者輸入自然人憑證 PIN 碼" in message:
            self._prompt_pin_dialog()

    def _prompt_pin_dialog(self):
        def ask_pin():
            dialog = ctk.CTkInputDialog(
                text="請輸入自然人憑證 PIN 碼（一次性使用）:",
                title="自然人憑證登入",
            )
            dialog.entry.configure(show="•")
            pin = dialog.get_input()
            if pin:
                self.crawler.set_pin_code(pin)
        self.after(100, ask_pin)

    # ------------------------------------------------------------------ #
    #  TAB 4: Settings                                                     #
    # ------------------------------------------------------------------ #
    def _build_tab_settings(self):
        card = ctk.CTkFrame(
            self.tab_settings, fg_color="#ffffff",
            corner_radius=12, border_width=1, border_color="#e2e8f0"
        )
        card.pack(fill="none", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=30, pady=30)

        ctk.CTkLabel(
            inner, text="系統參數設定",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=16, weight="bold"),
            text_color="#0f172a",
        ).pack(anchor="w", pady=(0, 20))

        # Target URL
        ctk.CTkLabel(
            inner, text="目標登入網址 (Target Login URL):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", pady=(6, 2))
        self.entry_url = ctk.CTkEntry(inner, width=420, height=36, corner_radius=8)
        self.entry_url.pack(anchor="w", pady=(0, 14))

        # System Search Name
        ctk.CTkLabel(
            inner, text="系統搜尋關鍵字:",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", pady=(6, 2))
        self.entry_sys_name = ctk.CTkEntry(inner, width=420, height=36, corner_radius=8)
        self.entry_sys_name.pack(anchor="w", pady=(0, 14))

        # Wait Timeout
        ctk.CTkLabel(
            inner, text="元素尋找超時 (秒):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", pady=(6, 2))
        self.entry_wait = ctk.CTkEntry(inner, width=150, height=36, corner_radius=8)
        self.entry_wait.pack(anchor="w", pady=(0, 14))

        # Log Directory
        ctk.CTkLabel(
            inner, text="Log 儲存目錄 (Log Directory):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", pady=(6, 2))
        
        log_dir_frame = ctk.CTkFrame(inner, fg_color="transparent")
        log_dir_frame.pack(anchor="w", fill="x", pady=(0, 14))
        
        self.entry_log_dir = ctk.CTkEntry(log_dir_frame, width=320, height=36, corner_radius=8)
        self.entry_log_dir.pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            log_dir_frame, text="📂 開啟 Log", width=90, height=36, corner_radius=8,
            fg_color="#e2e8f0", text_color="#334155", hover_color="#cbd5e1",
            command=self.open_logs_dir,
        ).pack(side="left")

        # Config Directory Info
        ctk.CTkLabel(
            inner, text="設定檔目錄 (Config Directory):",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=12, weight="bold"),
            text_color="#334155",
        ).pack(anchor="w", pady=(6, 2))

        config_dir_frame = ctk.CTkFrame(inner, fg_color="transparent")
        config_dir_frame.pack(anchor="w", fill="x", pady=(0, 14))
        
        self.entry_config_dir = ctk.CTkEntry(config_dir_frame, width=320, height=36, corner_radius=8)
        self.entry_config_dir.pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            config_dir_frame, text="📂 開啟 Config", width=90, height=36, corner_radius=8,
            fg_color="#e2e8f0", text_color="#334155", hover_color="#cbd5e1",
            command=self.open_config_dir,
        ).pack(side="left")

        # Save Button
        ctk.CTkButton(
            inner, text="💾 儲存系統設定",
            font=ctk.CTkFont(family="Microsoft JhengHei", size=13, weight="bold"),
            fg_color="#f3f4f6",
            hover_color="#e5e7eb",
            text_color="#1f2328",
            border_width=1,
            border_color="#E2E8F0",
            height=38, corner_radius=8,
            command=self.save_settings,
        ).pack(anchor="e", pady=(20, 0))

    def load_settings_to_ui(self):
        s = self.settings
        self.entry_url.delete(0, "end")
        self.entry_url.insert(0, s.get("target_url", "https://login.gov.taipei/login.php"))

        self.entry_sys_name.delete(0, "end")
        self.entry_sys_name.insert(0, s.get("search_system_name", "網站整合平臺"))

        self.entry_wait.delete(0, "end")
        self.entry_wait.insert(0, str(s.get("implicit_wait", 10)))

        log_path = s.get("log_dir") or get_logs_dir()
        self.entry_log_dir.delete(0, "end")
        self.entry_log_dir.insert(0, log_path)

        self.entry_config_dir.configure(state="normal")
        self.entry_config_dir.delete(0, "end")
        self.entry_config_dir.insert(0, get_config_dir())
        self.entry_config_dir.configure(state="readonly")

    def save_settings(self):
        try:
            w = int(self.entry_wait.get().strip())
        except ValueError:
            w = 10

        new_settings = {
            "target_url": self.entry_url.get().strip(),
            "search_system_name": self.entry_sys_name.get().strip(),
            "implicit_wait": w,
            "log_dir": self.entry_log_dir.get().strip() or get_logs_dir(),
        }
        self.storage.update_settings(new_settings)
        self.settings = self.storage.get_settings()
        messagebox.showinfo("成功", "系統設定已更新！")

    # ------------------------------------------------------------------ #
    #  Queue Processor                                                     #
    # ------------------------------------------------------------------ #
    def _log_callback(self, message: str, level: str):
        self.msg_queue.put(("LOG", message, level))

    def _process_queue(self):
        try:
            while not self.msg_queue.empty():
                item = self.msg_queue.get_nowait()
                if item[0] == "LOG":
                    self.append_log(item[1], item[2])
        except Exception:
            pass

        if hasattr(self, "crawler"):
            status = self.crawler.get_status()
            is_running = status["is_running"]

            if is_running:
                self.btn_start.configure(state="disabled")
                self.btn_stop.configure(state="normal")
                self.status_lbl.configure(text="● 任務執行中 (RUNNING)", text_color="#2563eb")
                self.status_badge.configure(fg_color="#dbeafe", border_color="#93c5fd")
            else:
                self.btn_start.configure(state="normal")
                self.btn_stop.configure(state="disabled")

                if status["current_step"] == "FINISHED":
                    self.status_lbl.configure(text="● 任務已完成 (FINISHED)", text_color="#059669")
                    self.status_badge.configure(fg_color="#d1fae5", border_color="#6ee7b7")
                elif status["current_step"] in ["ERROR", "STOPPED"]:
                    self.status_lbl.configure(text="● 任務中斷 / 錯誤", text_color="#e11d48")
                    self.status_badge.configure(fg_color="#ffe4e6", border_color="#fecdd3")
                else:
                    self.status_lbl.configure(text="● 準備就緒 (IDLE)", text_color="#475569")
                    self.status_badge.configure(fg_color="#f1f5f9", border_color="#cbd5e1")

            pct = status.get("progress", 0)
            self.progress_bar.set(pct / 100.0)
            self.pct_label.configure(text=f"{pct}%")

            comp = status.get("completed_items", 0)
            tot = status.get("total_items", 0)
            step = status.get("current_step", "IDLE")
            self.stats_lbl.configure(text=f"已完成: {comp} / {tot} 項目 ｜ 當前步驟: {step}")

            curr = status.get("current_item", "")
            self.curr_item_lbl.configure(
                text=curr if (is_running and curr) else ("處理中..." if is_running else "無執行中的任務")
            )

        self.after(200, self._process_queue)
