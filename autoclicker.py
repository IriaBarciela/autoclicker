import customtkinter as ctk
import threading
import time
from pynput.mouse import Button, Controller
from pynput.keyboard import Listener, Key

mouse = Controller()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG     = "#0f0f1a"
CARD   = "#1a1a2e"
CARD2  = "#16213e"
ACCENT = "#4f8ef7"
GREEN  = "#2ecc71"
RED    = "#e74c3c"
YELLOW = "#f39c12"

BUTTON_MAP = {
    "Izquierdo": Button.left,
    "Derecho":   Button.right,
    "Central":   Button.middle,
}
SPECIAL_KEYS = {
    Key.f1:"F1", Key.f2:"F2", Key.f3:"F3", Key.f4:"F4",
    Key.f5:"F5", Key.f6:"F6", Key.f7:"F7", Key.f8:"F8",
    Key.f9:"F9", Key.f10:"F10", Key.f11:"F11", Key.f12:"F12",
    Key.space:"Espacio", Key.enter:"Enter", Key.tab:"Tab", Key.esc:"Escape",
}


class AutoClickerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AutoClicker Pro")
        self.geometry("430x545")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self.running       = False
        self.counting_down = False
        self._thread       = None
        self._hotkey       = Key.f6
        self._hotkey_label = "F6"
        self._capturing    = False
        self._last_toggle  = 0.0
        self._last_ui_upd  = 0.0

        self._build()
        self._start_kb_listener()

    # ─── BUILD ───────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ──────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=CARD2, corner_radius=0, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="🖱  AutoClicker Pro",
                     font=ctk.CTkFont("Segoe UI", 20, "bold"),
                     text_color="white").pack(expand=True)

        # ── Main body (no scroll) ────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color=BG)
        body.pack(fill="both", expand=True, padx=14, pady=8)

        # ── Row 1: Intervalo ────────────────────────────────────────────
        iv_card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
        iv_card.pack(fill="x", pady=(0, 6))

        iv_top = ctk.CTkFrame(iv_card, fg_color="transparent")
        iv_top.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(iv_top, text="⏱  Intervalo entre clics",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color="#718096").pack(side="left")
        self.warn_lbl = ctk.CTkLabel(iv_top, text="",
                                      font=ctk.CTkFont("Segoe UI", 10),
                                      text_color=YELLOW)
        self.warn_lbl.pack(side="right")

        iv_entries = ctk.CTkFrame(iv_card, fg_color="transparent")
        iv_entries.pack(fill="x", padx=10, pady=(0, 10))

        self.h_var  = ctk.StringVar(value="0")
        self.m_var  = ctk.StringVar(value="0")
        self.s_var  = ctk.StringVar(value="0")
        self.ms_var = ctk.StringVar(value="100")

        for col, (lbl, var) in enumerate([
            ("Horas", self.h_var), ("Minutos", self.m_var),
            ("Segundos", self.s_var), ("Miliseg.", self.ms_var),
        ]):
            iv_entries.columnconfigure(col, weight=1)
            cell = ctk.CTkFrame(iv_entries, fg_color="transparent")
            cell.grid(row=0, column=col, padx=4)
            ctk.CTkLabel(cell, text=lbl, font=ctk.CTkFont("Segoe UI", 10),
                         text_color="#a0aec0").pack()
            ctk.CTkEntry(cell, textvariable=var, width=72, justify="center",
                         font=ctk.CTkFont("Segoe UI", 16, "bold"),
                         fg_color=CARD2, border_color=ACCENT,
                         border_width=1).pack()

        for v in [self.h_var, self.m_var, self.s_var, self.ms_var]:
            v.trace_add("write", self._check_interval)

        # ── Row 2: Countdown (left) + Opciones de clic (right) ──────────
        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        # Countdown card
        cd_card = ctk.CTkFrame(row2, fg_color=CARD, corner_radius=12)
        cd_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        ctk.CTkLabel(cd_card, text="⏳  Countdown",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color="#718096").pack(anchor="w", padx=12, pady=(8, 2))

        cd_row = ctk.CTkFrame(cd_card, fg_color="transparent")
        cd_row.pack(fill="x", padx=12, pady=(0, 10))

        self.cd_var = ctk.IntVar(value=3)
        self.cd_lbl = ctk.CTkLabel(cd_row,
                                    text="3 s",
                                    font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                    text_color=ACCENT, width=36)
        self.cd_lbl.pack(side="right")
        ctk.CTkSlider(cd_row, from_=0, to=10, number_of_steps=10,
                      variable=self.cd_var, command=self._on_cd_change,
                      button_color=ACCENT, progress_color=ACCENT,
                      height=16).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkLabel(cd_card, text="Segundos antes de iniciar",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color="#4a5568").pack(padx=12, pady=(0, 8))

        # Opciones de clic card
        opt_card = ctk.CTkFrame(row2, fg_color=CARD, corner_radius=12)
        opt_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        ctk.CTkLabel(opt_card, text="🖱  Opciones de clic",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color="#718096").pack(anchor="w", padx=12, pady=(8, 4))

        opt_inner = ctk.CTkFrame(opt_card, fg_color="transparent")
        opt_inner.pack(fill="x", padx=10, pady=(0, 8))

        ctk.CTkLabel(opt_inner, text="Botón",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color="#a0aec0").pack(anchor="w")
        self.btn_var = ctk.StringVar(value="Izquierdo")
        ctk.CTkSegmentedButton(opt_inner,
                               values=["Izq.", "Der.", "Central"],
                               variable=self.btn_var,
                               font=ctk.CTkFont("Segoe UI", 10),
                               selected_color=ACCENT,
                               selected_hover_color=ACCENT,
                               height=28).pack(fill="x", pady=(2, 6))

        ctk.CTkLabel(opt_inner, text="Tipo",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color="#a0aec0").pack(anchor="w")
        self.type_var = ctk.StringVar(value="Simple")
        ctk.CTkSegmentedButton(opt_inner,
                               values=["Simple", "Doble"],
                               variable=self.type_var,
                               font=ctk.CTkFont("Segoe UI", 10),
                               selected_color=ACCENT,
                               selected_hover_color=ACCENT,
                               height=28).pack(fill="x", pady=(2, 0))

        # Fix btn_var values to match BUTTON_MAP
        self.btn_var_map = {"Izq.": Button.left, "Der.": Button.right, "Central": Button.middle}

        # ── Row 3: Repeticiones ─────────────────────────────────────────
        rep_card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
        rep_card.pack(fill="x", pady=(0, 6))

        rep_inner = ctk.CTkFrame(rep_card, fg_color="transparent")
        rep_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(rep_inner, text="🔁  Repeticiones",
                     font=ctk.CTkFont("Segoe UI", 11, "bold"),
                     text_color="#718096").pack(side="left")

        self.rep_var = ctk.StringVar(value="50")
        self.rep_entry = ctk.CTkEntry(rep_inner, textvariable=self.rep_var,
                                      width=72, justify="center",
                                      font=ctk.CTkFont("Segoe UI", 13, "bold"),
                                      fg_color=CARD2, border_color=ACCENT,
                                      border_width=1)
        self.rep_entry.pack(side="right")
        self.rep_entry.configure(state="disabled")

        self.rep_mode = ctk.StringVar(value="Infinito")
        ctk.CTkSegmentedButton(rep_inner,
                               values=["Infinito", "Cantidad fija"],
                               variable=self.rep_mode,
                               font=ctk.CTkFont("Segoe UI", 10),
                               selected_color=ACCENT,
                               selected_hover_color=ACCENT,
                               height=28,
                               command=self._toggle_rep).pack(
                               side="right", padx=(0, 8))

        # ── Row 4: Hotkey ───────────────────────────────────────────────
        hk_card = ctk.CTkFrame(body, fg_color=CARD, corner_radius=12)
        hk_card.pack(fill="x", pady=(0, 6))

        hk_inner = ctk.CTkFrame(hk_card, fg_color="transparent")
        hk_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(hk_inner, text="⌨",
                     font=ctk.CTkFont("Segoe UI", 14),
                     text_color="#718096").pack(side="left", padx=(0, 6))

        self.hk_display = ctk.CTkLabel(hk_inner,
                                        text=f"  {self._hotkey_label}  ",
                                        font=ctk.CTkFont("Segoe UI", 15, "bold"),
                                        fg_color=CARD2, corner_radius=8,
                                        text_color=GREEN, padx=6, pady=2)
        self.hk_display.pack(side="left")

        ctk.CTkLabel(hk_inner,
                     text="Activa / desactiva desde cualquier ventana",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color="#4a5568").pack(side="left", padx=10)

        self.hk_btn = ctk.CTkButton(hk_inner, text="Cambiar",
                                     width=80, height=28,
                                     font=ctk.CTkFont("Segoe UI", 11),
                                     fg_color=CARD2, hover_color=ACCENT,
                                     command=self._capture_hotkey)
        self.hk_btn.pack(side="right")

        # ── Footer ──────────────────────────────────────────────────────
        footer = ctk.CTkFrame(self, fg_color=CARD, corner_radius=0, height=118)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        info_row = ctk.CTkFrame(footer, fg_color="transparent")
        info_row.pack(fill="x", padx=18, pady=(10, 4))

        self.count_lbl = ctk.CTkLabel(info_row, text="Clics realizados: 0",
                                       font=ctk.CTkFont("Segoe UI", 11),
                                       text_color="#a0aec0")
        self.count_lbl.pack(side="left")

        self.status_lbl = ctk.CTkLabel(info_row, text="⬤  Detenido",
                                        font=ctk.CTkFont("Segoe UI", 12, "bold"),
                                        text_color=RED)
        self.status_lbl.pack(side="right")

        self.toggle_btn = ctk.CTkButton(footer,
                                         text=f"▶   INICIAR   [{self._hotkey_label}]",
                                         font=ctk.CTkFont("Segoe UI", 14, "bold"),
                                         height=48, corner_radius=12,
                                         fg_color=GREEN, hover_color="#27ae60",
                                         command=self.toggle)
        self.toggle_btn.pack(fill="x", padx=18, pady=(0, 12))

    # ─── HELPERS ─────────────────────────────────────────────────────────

    def _on_cd_change(self, val):
        self.cd_lbl.configure(text=f"{int(float(val))} s")

    def _check_interval(self, *_):
        try:
            iv = self._get_interval()
            self.warn_lbl.configure(
                text="⚠ mín. 10 ms" if iv < 0.05 else "")
        except Exception:
            pass

    def _get_interval(self):
        try:
            h  = max(0,  int(self.h_var.get()  or 0))
            m  = max(0,  int(self.m_var.get()  or 0))
            s  = max(0,  int(self.s_var.get()  or 0))
            ms = max(10, int(self.ms_var.get() or 10))
            return h * 3600 + m * 60 + s + ms / 1000
        except (ValueError, TypeError):
            return 0.1

    def _get_limit(self):
        if self.rep_mode.get() == "Infinito":
            return None
        try:
            return max(1, int(self.rep_var.get()))
        except (ValueError, TypeError):
            return 50

    def _toggle_rep(self, val):
        self.rep_entry.configure(
            state="normal" if val == "Cantidad fija" else "disabled")

    def _get_button(self):
        return self.btn_var_map.get(self.btn_var.get(), Button.left)

    # ─── COUNTDOWN + CLICK LOOP ──────────────────────────────────────────

    def _run(self):
        secs = self.cd_var.get()
        for i in range(secs, 0, -1):
            if not self.counting_down:
                return
            self.after(0, lambda n=i: self.status_lbl.configure(
                text=f"⏳  Iniciando en {n}...", text_color=YELLOW))
            time.sleep(1)

        if not self.counting_down:
            return

        self.running = True
        self.counting_down = False
        self.after(0, self._ui_running)

        btn      = self._get_button()
        clicks   = 2 if self.type_var.get() == "Doble" else 1
        interval = self._get_interval()
        limit    = self._get_limit()
        count    = 0

        while self.running:
            mouse.click(btn, clicks)
            count += 1
            now = time.monotonic()
            if now - self._last_ui_upd >= 0.1:
                self._last_ui_upd = now
                self.after(0, self.count_lbl.configure,
                           {"text": f"Clics realizados: {count}"})
            if limit is not None and count >= limit:
                self.after(0, self.count_lbl.configure,
                           {"text": f"Clics realizados: {count}"})
                self.after(0, self._auto_stop)
                break
            time.sleep(interval)

    def _auto_stop(self):
        self.running = False
        self._ui_stopped()

    # ─── TOGGLE ──────────────────────────────────────────────────────────

    def toggle(self):
        now = time.monotonic()
        if now - self._last_toggle < 0.8:
            return
        self._last_toggle = now

        if self.running:
            self.running = False
            self._ui_stopped()
        elif self.counting_down:
            self.counting_down = False
            self._ui_stopped()
        else:
            self.counting_down = True
            self.count_lbl.configure(text="Clics realizados: 0")
            self._ui_countdown()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # ─── UI STATES ───────────────────────────────────────────────────────

    def _ui_countdown(self):
        s = self.cd_var.get()
        self.status_lbl.configure(
            text=f"⏳  Iniciando en {s}..." if s > 0 else "⏳  Iniciando...",
            text_color=YELLOW)
        self.toggle_btn.configure(
            text=f"✕   CANCELAR   [{self._hotkey_label}]",
            fg_color=YELLOW, hover_color="#d68910", text_color="#0f0f1a")

    def _ui_running(self):
        self.status_lbl.configure(text="⬤  Activo", text_color=GREEN)
        self.toggle_btn.configure(
            text=f"■   DETENER   [{self._hotkey_label}]",
            fg_color=RED, hover_color="#c0392b", text_color="white")

    def _ui_stopped(self):
        self.status_lbl.configure(text="⬤  Detenido", text_color=RED)
        self.toggle_btn.configure(
            text=f"▶   INICIAR   [{self._hotkey_label}]",
            fg_color=GREEN, hover_color="#27ae60", text_color="white")

    # ─── HOTKEY ──────────────────────────────────────────────────────────

    def _start_kb_listener(self):
        def on_press(key):
            if not self._capturing and key == self._hotkey:
                self.after(0, self.toggle)
        self._kb = Listener(on_press=on_press, daemon=True)
        self._kb.start()

    def _capture_hotkey(self):
        if self._capturing:
            return
        self._capturing = True
        self.hk_btn.configure(text="Presiona...", state="disabled")
        self.hk_display.configure(text="  ...  ", text_color=YELLOW)

        def on_press(key):
            name = SPECIAL_KEYS.get(key, None)
            if name is None:
                try:
                    name = key.char.upper()
                except AttributeError:
                    name = str(key).replace("Key.", "").upper()
            self._hotkey = key
            self._hotkey_label = name
            self.after(0, self._finish_capture, name)
            return False

        Listener(on_press=on_press, daemon=True).start()

    def _finish_capture(self, name):
        self.hk_display.configure(text=f"  {name}  ", text_color=GREEN)
        self.hk_btn.configure(text="Cambiar", state="normal")
        self._capturing = False
        if self.running:
            self._ui_running()
        elif self.counting_down:
            self._ui_countdown()
        else:
            self._ui_stopped()


if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()
