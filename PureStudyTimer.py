import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import os
import winsound
import threading

class UltimateStudyTimer:
    def __init__(self, root):
        self.root = root
        self.root.title("순공 & 공놀 & 여가 측정기")
        
        # --- 데이터 및 설정 초기화 ---
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

        # UI 프레임 구성
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True)
        self.mini_frame = tk.Frame(self.root, bg="#2c3e50")

        self.setup_main_ui()
        self.setup_mini_ui()
        
        # 레이아웃 최적화 창 크기
        self.root.geometry("340x530")
        self.root.resizable(False, False) 
        
        # --- 신규 기능: 메인 창 움직임 감지 이벤트 바인딩 ---
        self.root.bind("<Configure>", self.on_main_window_move)
        
        self.update_clock()

    # --- 신규 기능: 메인 창을 따라오는 자석 로직 ---
    def on_main_window_move(self, event):
        """메인 창이 움직일 때 실행되는 함수"""
        # 메인 창이 움직인 것인지 확인하고, 기록창이 열려있을 때만 위치 갱신
        if event.widget == self.root and not self.is_mini_mode:
            self.refresh_log_positions()

    def refresh_log_positions(self):
        """기록창들의 위치를 메인 창 옆으로 강제 이동"""
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        
        # 각 창이 존재할 때만 새 좌표(main_x + 345)로 업데이트
        if self.study_log_window and tk.Toplevel.winfo_exists(self.study_log_window):
            self.study_log_window.geometry(f"+{main_x + 345}+{main_y}")
            
        if self.ps_log_window and tk.Toplevel.winfo_exists(self.ps_log_window):
            self.ps_log_window.geometry(f"+{main_x + 345}+{main_y + 180}")
            
        if self.leisure_log_window and tk.Toplevel.winfo_exists(self.leisure_log_window):
            self.leisure_log_window.geometry(f"+{main_x + 345}+{main_y + 360}")

    def setup_main_ui(self):
        # 상단 컨트롤 바
        ctrl = tk.Frame(self.main_frame)
        ctrl.pack(fill="x", padx=10, pady=(2, 0))
        tk.Button(ctrl, text="미니미 모드", command=self.toggle_minimi, bg="#dfe4ea", font=("Helvetica", 8)).pack(side="right")
        self.always_on_top_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ctrl, text="항상 위", variable=self.always_on_top_var, command=self.toggle_always_on_top, font=("Helvetica", 8)).pack(side="left")
        self.show_log_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ctrl, text="기록창 표시", variable=self.show_log_var, command=self.toggle_log_windows, font=("Helvetica", 8)).pack(side="left", padx=2)

        # 시스템 설정
        set_f = tk.LabelFrame(self.main_frame, text=" 설정 ", font=("Helvetica", 8), padx=10, pady=0)
        set_f.pack(fill="x", padx=10, pady=(2, 5))
        tk.Label(set_f, text="하루 시작:", font=("Helvetica", 8)).grid(row=0, column=0)
        tk.Spinbox(set_f, from_=0, to=23, textvariable=self.day_start_hour, width=3, font=("Helvetica", 8)).grid(row=0, column=1)
        tk.Label(set_f, text="알림 주기:", font=("Helvetica", 8)).grid(row=0, column=2, padx=(10,0))
        self.alert_entry = tk.Entry(set_f, textvariable=self.alert_interval_input, width=5, font=("Helvetica", 8))
        self.alert_entry.grid(row=0, column=3)
        tk.Button(set_f, text="확인", command=self.apply_alert_settings, font=("Helvetica", 8), padx=2, pady=0).grid(row=0, column=4, padx=5)

        # 타이머 섹션
        self.create_timer_section(self.main_frame, "순공", "study", "blue", "#2ecc71", "#e74c3c")
        self.create_timer_section(self.main_frame, "공놀", "ps", "#8e44ad", "#9b59b6", "#f39c12")
        self.create_timer_section(self.main_frame, "여가", "leisure", "green", "#3498db", "#e67e22")

    def create_timer_section(self, parent, title, t_type, color, s_bg, st_bg):
        f = tk.LabelFrame(parent, text=f" {title} ", font=("Helvetica", 9, "bold"), fg=color, padx=10, pady=0)
        f.pack(fill="x", padx=10, pady=1)
        lbl = tk.Label(f, text="0:00:00", font=("Helvetica", 28, "bold"), fg="#2c3e50")
        lbl.pack(pady=0)
        setattr(self, f"main_{t_type}_lbl", lbl)
        if t_type == "study":
            ft_f = tk.Frame(f)
            ft_f.pack(pady=0)
            self.first_time_label = tk.Label(ft_f, text="최초: --:--:--", fg="blue", font=("Helvetica", 8))
            self.first_time_label.pack(side="left")
            tk.Button(ft_f, text="X", command=self.delete_first_start, width=1, font=("Helvetica", 7), bg="#f1f2f6", relief="flat", pady=0).pack(side="left", padx=2)
        btn_f = tk.Frame(f)
        btn_f.pack(pady=(0, 2))
        tk.Button(btn_f, text="시작", command=lambda: self.start_timer(t_type), width=8, bg=s_bg, fg="white", font=("Helvetica", 9, "bold")).grid(row=0, column=0, padx=2)
        tk.Button(btn_f, text="정지", command=self.stop_current_timer, width=8, bg=st_bg, fg="white", font=("Helvetica", 9, "bold")).grid(row=0, column=1, padx=2)
        tk.Button(f, text="초기화", command=lambda: self.reset_timer(t_type), width=18, bg="#95a5a6", fg="white", font=("Helvetica", 8), pady=0).pack(pady=(0, 2))

    def setup_mini_ui(self):
        self.mini_study_lbl = tk.Label(self.mini_frame, text="순 0:00:00", font=("Consolas", 10, "bold"), fg="#2ecc71", bg="#2c3e50")
        self.mini_study_lbl.pack(pady=0, fill="x")
        self.mini_ps_lbl = tk.Label(self.mini_frame, text="놀 0:00:00", font=("Consolas", 10, "bold"), fg="#9b59b6", bg="#2c3e50")
        self.mini_ps_lbl.pack(pady=0, fill="x")
        self.mini_leisure_lbl = tk.Label(self.mini_frame, text="여 0:00:00", font=("Consolas", 10, "bold"), fg="#3498db", bg="#2c3e50")
        self.mini_leisure_lbl.pack(pady=0, fill="x")
        tk.Button(self.mini_frame, text="↩", command=self.toggle_minimi, font=("Helvetica", 8), bg="#7f8c8d", fg="white", relief="flat", pady=0).pack(pady=1)
        for w in [self.mini_frame, self.mini_study_lbl, self.mini_ps_lbl, self.mini_leisure_lbl]:
            w.bind("<Button-1>", self.start_move); w.bind("<B1-Motion>", self.on_move)

    def start_move(self, event): self.offset_x, self.offset_y = event.x, event.y
    def on_move(self, event):
        x, y = self.root.winfo_x() + (event.x - self.offset_x), self.root.winfo_y() + (event.y - self.offset_y)
        self.root.geometry(f"+{x}+{y}")

    def toggle_minimi(self):
        self.root.withdraw()
        if not self.is_mini_mode:
            self.main_frame.pack_forget(); self.mini_frame.pack(fill="both", expand=True)
            self.root.overrideredirect(True); self.root.geometry("140x85"); self.is_mini_mode = True
        else:
            self.mini_frame.pack_forget(); self.main_frame.pack(fill="both", expand=True)
            self.root.overrideredirect(False); self.root.geometry("340x530"); self.is_mini_mode = False
        self.root.deiconify(); self.root.attributes("-topmost", self.always_on_top_var.get())

    def start_timer(self, t_type):
        if self.running_type: self.stop_current_timer()
        now = datetime.now()
        self.running_type = t_type
        self.session_start_time = now.strftime("%H:%M:%S")
        if t_type == "study" and self.first_start_time is None:
            self.first_start_time = now.strftime("%H:%M:%S")
            self.first_time_label.config(text=f"최초: {self.first_start_time}")
        self.lock_settings(True)

    def stop_current_timer(self):
        if not self.running_type: return
        now = datetime.now()
        log = f"{now.strftime('%Y-%m-%d %H:%M:%S')} | [{self.session_start_time} ~ {now.strftime('%H:%M:%S')}]\n"
        f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        with open(f_map[self.running_type], "a", encoding="utf-8") as f: f.write(log)
        self.refresh_log_windows_content(); self.running_type = None; self.lock_settings(False)

    def reset_timer(self, t_type):
        if self.running_type == t_type: self.stop_current_timer()
        setattr(self, f"{t_type}_seconds", 0); self.update_labels()

    def update_clock(self):
        if self.running_type == "study": self.study_seconds += 1
        elif self.running_type == "ps":
            self.ps_seconds += 1
            if self.applied_interval > 0 and self.ps_seconds % self.applied_interval == 0: self.play_alert_sound()
        elif self.running_type == "leisure":
            self.leisure_seconds += 1
            if self.applied_interval > 0 and self.leisure_seconds % self.applied_interval == 0: self.play_alert_sound()
        self.update_labels(); self.root.after(1000, self.update_clock)

    def update_labels(self):
        s, ps, l = str(timedelta(seconds=self.study_seconds)), str(timedelta(seconds=self.ps_seconds)), str(timedelta(seconds=self.leisure_seconds))
        self.main_study_lbl.config(text=s); self.main_ps_lbl.config(text=ps); self.main_leisure_lbl.config(text=l)
        self.mini_study_lbl.config(text=f"순 {s}"); self.mini_ps_lbl.config(text=f"놀 {ps}"); self.mini_leisure_lbl.config(text=f"여 {l}")

    def play_alert_sound(self): threading.Thread(target=lambda: winsound.Beep(1000, 100), daemon=True).start()

    def apply_alert_settings(self):
        try:
            self.applied_interval = int(self.alert_interval_input.get()); messagebox.showinfo("알림", f"{self.applied_interval}초 설정됨")
        except: messagebox.showerror("오류", "숫자 입력")

    def lock_settings(self, lock): self.alert_entry.config(state="disabled" if lock else "normal")

    def toggle_always_on_top(self): 
        self.root.attributes("-topmost", self.always_on_top_var.get())
        # 기록창들도 항상 위 상태 동기화
        for w in [self.study_log_window, self.ps_log_window, self.leisure_log_window]:
            if w and tk.Toplevel.winfo_exists(w):
                w.attributes("-topmost", self.always_on_top_var.get())

    def toggle_log_windows(self):
        if self.show_log_var.get():
            self.study_log_window = self.create_log_ui("study", "순공", "blue", 0)
            self.ps_log_window = self.create_log_ui("ps", "공놀", "#8e44ad", 180)
            self.leisure_log_window = self.create_log_ui("leisure", "여가", "green", 360)
            self.refresh_log_positions() # 창을 켤 때 즉시 위치 보정
        else:
            for w in [self.study_log_window, self.ps_log_window, self.leisure_log_window]:
                if w and tk.Toplevel.winfo_exists(w): w.destroy()
            self.study_log_window = self.ps_log_window = self.leisure_log_window = None

    def create_log_ui(self, l_type, title, color, y_off):
        w = tk.Toplevel(self.root); w.overrideredirect(True)
        w.config(highlightbackground=color, highlightthickness=2)
        tk.Label(w, text=f"[{title}]", font=("Helvetica", 8, "bold"), fg=color).pack(pady=2)
        f = tk.Frame(w); f.pack(padx=5, fill="both", expand=True)
        lb = tk.Listbox(f, font=("Consolas", 8), height=6); lb.pack(side="left", fill="both", expand=True)
        tk.Button(w, text="삭제", command=lambda: self.delete_log_item(l_type, lb), bg="#f1f2f6", font=("Helvetica", 7)).pack(pady=1)
        self.load_logs_to_ui(l_type, lb); w.attributes("-topmost", self.always_on_top_var.get())
        return w

    def load_logs_to_ui(self, l_type, lb):
        f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        lb.delete(0, tk.END)
        if os.path.exists(f_map[l_type]):
            with open(f_map[l_type], "r", encoding="utf-8") as f:
                for line in f: lb.insert(tk.END, line.strip())

    def refresh_log_windows_content(self):
        if self.study_log_window: self.load_logs_to_ui("study", self.study_log_window.winfo_children()[1].winfo_children()[0])
        if self.ps_log_window: self.load_logs_to_ui("ps", self.ps_log_window.winfo_children()[1].winfo_children()[0])
        if self.leisure_log_window: self.load_logs_to_ui("leisure", self.leisure_log_window.winfo_children()[1].winfo_children()[0])

    def delete_log_item(self, l_type, lb):
        if not lb.curselection(): return
        target = lb.get(lb.curselection())
        f_map = {"study": "study_log.txt", "ps": "play_study_log.txt", "leisure": "leisure_log.txt"}
        if messagebox.askyesno("삭제", "삭제?"):
            lines = open(f_map[l_type], "r", encoding="utf-8").readlines()
            with open(f_map[l_type], "w", encoding="utf-8") as f:
                for l in lines: 
                    if l.strip() != target: f.write(l)
            self.load_logs_to_ui(l_type, lb)

    def delete_first_start(self): self.first_start_time = None; self.first_time_label.config(text="최초: --:--:--")

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateStudyTimer(root)
    root.mainloop()