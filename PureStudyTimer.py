import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import os
import winsound
import threading
import json

class UltimateStudyTimer:
    def __init__(self, root):
        self.root = root
        
        # --- [버전 업데이트] v1.3.0: 미니미 이동 핸들 시각화 ---
        self.version = "1.3.0" 
        self.root.title(f"순공 & 공놀 & 여가 측정기 v{self.version}")
        self.save_file = "save_data.json"
        
        self.is_mini_mode = False
        self.day_start_hour = tk.StringVar(value="6")
        self.alert_interval_input = tk.StringVar(value="300")
        self.applied_interval = 300
        
        self.running_type = None
        self.study_seconds = 0
        self.ps_seconds = 0
        self.leisure_seconds = 0
        self.first_start_time = None
        self.session_start_time = None

        self.study_log_window = None 
        self.ps_log_window = None
        self.leisure_log_window = None

        self.offset_x, self.offset_y = 0, 0

        self.load_data()

        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        self.mini_frame = tk.Frame(self.root, bg="#2c3e50")

        # Grip 핸들 생성
        self.grip = tk.Label(self.root, text="◢", font=("Helvetica", 8), fg="#95a5a6", bg="#2c3e50", cursor="size_nw_se")

        self.setup_main_ui()
        self.setup_mini_ui()
        
        self.root.geometry("340x530")
        self.root.resizable(False, False) 
        
        self.root.bind("<Configure>", self.on_main_window_move)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.update_clock()

    def save_data(self):
        """기록 및 설정 저장"""
        data = {
            "study_seconds": self.study_seconds, "ps_seconds": self.ps_seconds, "leisure_seconds": self.leisure_seconds,
            "first_start_time": self.first_start_time, "applied_interval": self.applied_interval,
            "day_start_hour": self.day_start_hour.get(), "last_saved_date": datetime.now().strftime("%Y-%m-%d")
        }
        with open(self.save_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_data(self):
        """저장된 데이터 불러오기"""
        if os.path.exists(self.save_file):
            try:
                with open(self.save_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.applied_interval = data.get("applied_interval", 300)
                self.alert_interval_input.set(str(self.applied_interval))
                self.day_start_hour.set(data.get("day_start_hour", "6"))
                if data.get("last_saved_date") == datetime.now().strftime("%Y-%m-%d"):
                    self.study_seconds = data.get("study_seconds", 0)
                    self.ps_seconds = data.get("ps_seconds", 0)
                    self.leisure_seconds = data.get("leisure_seconds", 0)
                    self.first_start_time = data.get("first_start_time")
            except Exception: pass

    def on_closing(self):
        if self.running_type: self.stop_current_timer()
        self.save_data(); self.root.destroy()

    def on_main_window_move(self, event):
        if event.widget == self.root and not self.is_mini_mode: self.refresh_log_positions()

    def refresh_log_positions(self):
        mx, my = self.root.winfo_x(), self.root.winfo_y()
        for w, off in [(self.study_log_window, 0), (self.ps_log_window, 180), (self.leisure_log_window, 360)]:
            if w and tk.Toplevel.winfo_exists(w): w.geometry(f"+{mx + 345}+{my + off}")

    def setup_main_ui(self):
        ctrl = tk.Frame(self.main_frame); ctrl.pack(fill="x", padx=10, pady=(2, 0))
        tk.Button(ctrl, text="미니미 모드", command=self.toggle_minimi, bg="#dfe4ea", font=("Helvetica", 8)).pack(side="right")
        self.always_on_top_var = tk.BooleanVar(value=False); tk.Checkbutton(ctrl, text="항상 위", variable=self.always_on_top_var, command=self.toggle_always_on_top, font=("Helvetica", 8)).pack(side="left")
        self.show_log_var = tk.BooleanVar(value=False); tk.Checkbutton(ctrl, text="기록창 표시", variable=self.show_log_var, command=self.toggle_log_windows, font=("Helvetica", 8)).pack(side="left", padx=2)

        set_f = tk.LabelFrame(self.main_frame, text=" 설정 ", font=("Helvetica", 8)); set_f.pack(fill="x", padx=10, pady=5)
        tk.Label(set_f, text="시작 시:", font=("Helvetica", 8)).grid(row=0, column=0)
        tk.Spinbox(set_f, from_=0, to=23, textvariable=self.day_start_hour, width=3).grid(row=0, column=1)
        tk.Label(set_f, text="알림(초):", font=("Helvetica", 8)).grid(row=0, column=2, padx=5)
        self.alert_entry = tk.Entry(set_f, textvariable=self.alert_interval_input, width=5); self.alert_entry.grid(row=0, column=3)
        tk.Button(set_f, text="확인", command=self.apply_alert_settings, font=("Helvetica", 8)).grid(row=0, column=4, padx=5)

        self.create_timer_section("순공", "study", "blue", "#2ecc71", "#e74c3c")
        self.create_timer_section("공놀", "ps", "#8e44ad", "#9b59b6", "#f39c12")
        self.create_timer_section("여가", "leisure", "green", "#3498db", "#e67e22")

    def create_timer_section(self, title, t_type, color, s_bg, st_bg):
        f = tk.LabelFrame(self.main_frame, text=f" {title} ", font=("Helvetica", 9, "bold"), fg=color, padx=10); f.pack(fill="x", padx=10, pady=1)
        lbl = tk.Label(f, text="0:00:00", font=("Helvetica", 28, "bold"), fg="#2c3e50"); lbl.pack(); setattr(self, f"main_{t_type}_lbl", lbl)
        if t_type == "study":
            ft_f = tk.Frame(f); ft_f.pack()
            st_val = self.first_start_time if self.first_start_time else "--:--:--"
            self.first_time_label = tk.Label(ft_f, text=f"최초: {st_val}", fg="blue", font=("Helvetica", 8)); self.first_time_label.pack(side="left")
            tk.Button(ft_f, text="X", command=self.delete_first_start, font=("Helvetica", 7)).pack(side="left", padx=2)
        btn_f = tk.Frame(f); btn_f.pack(pady=2)
        tk.Button(btn_f, text="시작", command=lambda: self.start_timer(t_type), width=8, bg=s_bg, fg="white").grid(row=0, column=0, padx=2)
        tk.Button(btn_f, text="정지", command=self.stop_current_timer, width=8, bg=st_bg, fg="white").grid(row=0, column=1, padx=2)
        tk.Button(f, text="초기화", command=lambda: self.reset_timer(t_type), width=18, bg="#95a5a6", fg="white", font=("Helvetica", 8)).pack(pady=2)

    def setup_mini_ui(self):
        """미니미 상단 드래그 핸들 추가"""
        self.mini_drag_bar = tk.Frame(self.mini_frame, bg="#34495e", height=10)
        self.mini_drag_bar.pack(side="top", fill="x")
        tk.Label(self.mini_drag_bar, text="⁝⁝⁝", font=("Helvetica", 6), fg="#bdc3c7", bg="#34495e").pack()

        self.mini_btn_f = tk.Frame(self.mini_frame, bg="#2c3e50")
        self.mini_btn_f.pack(side="bottom", fill="x", pady=2)
        tk.Button(self.mini_btn_f, text="복귀", command=self.toggle_minimi, 
                  font=("Helvetica", 9, "bold"), bg="#7f8c8d", fg="white", padx=5).pack(side="left", padx=10)
        
        for t, c in [("study", "#2ecc71"), ("ps", "#9b59b6"), ("leisure", "#3498db")]:
            lbl = tk.Label(self.mini_frame, text=f"{t[0].upper()} 0:00:00", font=("Consolas", 10, "bold"), fg=c, bg="#2c3e50")
            lbl.pack(fill="both", expand=True); setattr(self, f"mini_{t}_lbl", lbl)
        
        self.grip.bind("<Button-1>", self.start_resize); self.grip.bind("<B1-Motion>", self.on_resize)
        for w in [self.mini_frame, self.mini_btn_f, self.mini_drag_bar]:
            w.bind("<Button-1>", self.start_move); w.bind("<B1-Motion>", self.on_move)

    def start_move(self, event): self.offset_x, self.offset_y = event.x, event.y
    def on_move(self, event):
        x, y = self.root.winfo_x() + (event.x - self.offset_x), self.root.winfo_y() + (event.y - self.offset_y)
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.start_w, self.start_h = self.root.winfo_width(), self.root.winfo_height()
        self.start_mouse_x, self.start_mouse_y = event.x_root, event.y_root

    def on_resize(self, event):
        new_w, new_h = max(120, self.start_w + (event.x_root - self.start_mouse_x)), max(100, self.start_h + (event.y_root - self.start_mouse_y))
        self.root.geometry(f"{new_w}x{new_h}")
        new_font_size = max(8, int(new_w / 14))
        for t in ["study", "ps", "leisure"]: getattr(self, f"mini_{t}_lbl").config(font=("Consolas", new_font_size, "bold"))

    def toggle_minimi(self):
        self.root.withdraw()
        if not self.is_mini_mode:
            self.main_frame.pack_forget(); self.mini_frame.pack(fill="both", expand=True)
            self.root.overrideredirect(True); self.root.geometry("140x110"); self.is_mini_mode = True
            self.grip.place(relx=1.0, rely=1.0, anchor="se") 
        else:
            self.mini_frame.pack_forget(); self.main_frame.pack(fill="both", expand=True)
            self.root.overrideredirect(False); self.root.geometry("340x530"); self.is_mini_mode = False
            self.grip.place_forget() 
        self.root.deiconify(); self.root.attributes("-topmost", self.always_on_top_var.get())

    def start_timer(self, t_type):
        if self.running_type: self.stop_current_timer()
        now = datetime.now(); self.running_type = t_type; self.session_start_time = now.strftime("%H:%M:%S")
        if t_type == "study" and self.first_start_time is None:
            self.first_start_time = now.strftime("%H:%M:%S"); self.first_time_label.config(text=f"최초: {self.first_start_time}")
        self.save_data()

    def stop_current_timer(self):
        if not self.running_type: return
        now = datetime.now(); log = f"{now.strftime('%Y-%m-%d %H:%M:%S')} | [{self.session_start_time} ~ {now.strftime('%H:%M:%S')}]\n"
        f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        with open(f_map[self.running_type], "a", encoding="utf-8") as f: f.write(log)
        self.refresh_log_windows_content(); self.running_type = None; self.save_data()

    def reset_timer(self, t_type):
        if self.running_type == t_type: self.stop_current_timer()
        setattr(self, f"{t_type}_seconds", 0); self.update_labels(); self.save_data()

    def update_clock(self):
        if self.running_type == "study": self.study_seconds += 1
        elif self.running_type in ["ps", "leisure"]:
            val = getattr(self, f"{self.running_type}_seconds") + 1
            setattr(self, f"{self.running_type}_seconds", val)
            if self.applied_interval > 0 and val % self.applied_interval == 0:
                threading.Thread(target=lambda: winsound.Beep(2000, 500), daemon=True).start()
        if (self.study_seconds + self.ps_seconds + self.leisure_seconds) % 60 == 0: self.save_data()
        self.update_labels(); self.root.after(1000, self.update_clock)

    def update_labels(self):
        s, ps, l = str(timedelta(seconds=self.study_seconds)), str(timedelta(seconds=self.ps_seconds)), str(timedelta(seconds=self.leisure_seconds))
        self.main_study_lbl.config(text=s); self.main_ps_lbl.config(text=ps); self.main_leisure_lbl.config(text=l)
        self.mini_study_lbl.config(text=f"S {s}"); self.mini_ps_lbl.config(text=f"P {ps}"); self.mini_leisure_lbl.config(text=f"L {l}")

    def apply_alert_settings(self):
        try:
            self.applied_interval = int(self.alert_interval_input.get()); self.save_data()
            messagebox.showinfo("알림", f"{self.applied_interval}초마다 알림 설정됨")
        except: messagebox.showerror("오류", "숫자만 입력하세요.")

    def toggle_always_on_top(self): self.root.attributes("-topmost", self.always_on_top_var.get())

    def toggle_log_windows(self):
        if self.show_log_var.get():
            self.study_log_window = self.create_log_ui("study", "순공", "blue", 0)
            self.ps_log_window = self.create_log_ui("ps", "공놀", "#8e44ad", 180)
            self.leisure_log_window = self.create_log_ui("leisure", "여가", "green", 360)
            self.refresh_log_positions() 
        else:
            for w in [self.study_log_window, self.ps_log_window, self.leisure_log_window]:
                if w and tk.Toplevel.winfo_exists(w): w.destroy()
            self.study_log_window = self.ps_log_window = self.leisure_log_window = None

    def create_log_ui(self, l_type, title, color, y_off):
        w = tk.Toplevel(self.root); w.overrideredirect(True)
        w.config(highlightbackground=color, highlightthickness=2); w.geometry("320x170")
        tk.Label(w, text=f"[{title}]", font=("Helvetica", 8, "bold"), fg=color).pack(pady=2)
        f = tk.Frame(w); f.pack(padx=5, fill="both", expand=True)
        lb = tk.Listbox(f, font=("Consolas", 9), height=6); lb.pack(side="left", fill="both", expand=True)
        tk.Button(w, text="삭제", command=lambda: self.delete_log_item(l_type, lb), font=("Helvetica", 7)).pack(pady=1)
        self.load_logs_to_ui(l_type, lb); return w

    def load_logs_to_ui(self, l_type, lb):
        f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        lb.delete(0, tk.END)
        if os.path.exists(f_map[l_type]):
            with open(f_map[l_type], "r", encoding="utf-8") as f:
                for line in f: lb.insert(tk.END, line.strip())

    def refresh_log_windows_content(self):
        for l_type, win in [("study", self.study_log_window), ("ps", self.ps_log_window), ("leisure", self.leisure_log_window)]:
            if win: self.load_logs_to_ui(l_type, win.winfo_children()[1].winfo_children()[0])

    def delete_log_item(self, l_type, lb):
        if not lb.curselection(): return
        target = lb.get(lb.curselection()); f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        if messagebox.askyesno("삭제", "정말 삭제하시겠습니까?"):
            lines = open(f_map[l_type], "r", encoding="utf-8").readlines()
            with open(f_map[l_type], "w", encoding="utf-8") as f:
                for l in lines: 
                    if l.strip() != target: f.write(l)
            self.load_logs_to_ui(l_type, lb)

    def delete_first_start(self): 
        self.first_start_time = None; self.first_time_label.config(text="최초: --:--:--"); self.save_data()

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateStudyTimer(root)
    root.mainloop()