import sqlite3
import random
import os
import string
import json
import re
import calendar
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from PIL import Image, ImageTk, ImageDraw

BG_COLOR = "#4B342C"
CARD_HEX = "#D8B69F"
BTN_BG = "#9C7164"
BTN_PRIMARY = "#7C5244"
BTN_DANGER = "#5C3A31"
NAV_BG = "#2B1812"
NAV_ACTIVE_BG = "#7C5244"
ENTRY_BG = "#E8E1D1"
TEXT_COLOR = "#FFFFFF"
DARK_TEXT = "#2B150C"
LIGHT_GOLD = "#FFD2A6"
ALERT_RED = "#7C5244"

UI_FONT = "Segoe UI" if os.name == "nt" else "Arial"
MAX_CONTENT_W = 1000
CARD_BORDER = "#7C5244"

LOADING_IMAGE_PATH = r"C:\Users\owner\Desktop\проект\logo.png"
HOME_BANNER_PATH = r"C:\Users\owner\Desktop\проект\banner.png"
HOME_MENU_CARD_PATH = r"C:\Users\owner\Desktop\проект\menu_card.png"
HOME_NOVELTY_CARD_PATH = r"C:\Users\owner\Desktop\проект\novelty_card.png"

class _Modal(tk.Toplevel):
    def __init__(self, master=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        try:
            self.transient(master.winfo_toplevel())
        except Exception:
            pass
        self.after(15, self._center)

    def _center(self):
        try:
            if not self.winfo_exists():
                return
            self.update_idletasks()
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
            m = re.match(r"(\d+)x(\d+)", self.geometry())
            gw, gh = (int(m.group(1)), int(m.group(2))) if m else (1, 1)
            w = min(max(gw, self.winfo_reqwidth()), sw - 60)
            h = min(max(gh, self.winfo_reqheight()), sh - 100)
            top = self.master.winfo_toplevel()
            x = top.winfo_rootx() + (top.winfo_width() - w) // 2
            y = top.winfo_rooty() + (top.winfo_height() - h) // 2
            x = max(10, min(x, sw - w - 10))
            y = max(10, min(y, sh - h - 50))
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.minsize(min(w, 300), min(h, 200))
        except Exception:
            pass

tk.Toplevel = _Modal

class PlaceholderEntry(tk.Entry):
    def __init__(self, container, placeholder="", *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = "#888888"
        self.default_fg_color = kwargs.get("fg", DARK_TEXT)
        self.bind("<FocusIn>", self._focus_in)
        self.bind("<FocusOut>", self._focus_out)
        self._put_placeholder()

    def _put_placeholder(self):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg=self.placeholder_color)

    def _focus_in(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.config(fg=self.default_fg_color)

    def _focus_out(self, event):
        if not self.get():
            self._put_placeholder()

    def get_clean(self):
        val = self.get().strip()
        return "" if val == self.placeholder else val

def create_rounded_transparent_card(width, height, radius, hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    rgba = rgb + (alpha,)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, width, height), radius=radius, fill=rgba)
    return ImageTk.PhotoImage(image)

def generate_order_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=4))

def get_user_display_name(cursor, login):
    cursor.execute("SELECT имя, фамилия FROM пользователи WHERE логин = ?", (login,))
    res = cursor.fetchone()
    if res:
        fn, ln = res[0].strip(), res[1].strip()
        full_name = f"{fn} {ln}".strip()
        if full_name:
            return f"{full_name} ({login})"
    return f"*** ({login})"

def init_db():
    conn = sqlite3.connect("coffee_shop.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS пользователи (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            логин TEXT UNIQUE NOT NULL,
            телефон TEXT UNIQUE NOT NULL,
            пароль TEXT NOT NULL,
            роль TEXT NOT NULL DEFAULT 'клиент',
            имя TEXT DEFAULT '',
            фамилия TEXT DEFAULT '',
            дата_рождения TEXT DEFAULT '',
            дата_рождения_заблокирована INTEGER DEFAULT 0,
            бонусный_баланс REAL DEFAULT 0.0,
            штрихкод TEXT UNIQUE,
            дневная_ставка REAL DEFAULT 2000.0,
            выплачено_сумма REAL DEFAULT 0.0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS меню (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            название TEXT NOT NULL,
            описание TEXT,
            базовая_цена REAL NOT NULL,
            категория TEXT NOT NULL,
            путь_к_картинке TEXT,
            объемы_json TEXT DEFAULT '',
            дата_добавления TIMESTAMP
        )
    ''')

    cursor.execute("PRAGMA table_info(меню)")
    columns = [col[1] for col in cursor.fetchall()]
    if "дата_добавления" not in columns:
        cursor.execute("ALTER TABLE меню ADD COLUMN дата_добавления TIMESTAMP")
        cursor.execute("UPDATE меню SET дата_добавления = ? WHERE дата_добавления IS NULL", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS заказы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            код_заказа TEXT UNIQUE NOT NULL,
            логин_пользователя TEXT NOT NULL,
            роль_пользователя TEXT DEFAULT 'клиент',
            адрес TEXT NOT NULL,
            итоговая_цена REAL NOT NULL,
            баллы_использованы REAL DEFAULT 0,
            баллы_заработаны REAL DEFAULT 0,
            статус TEXT NOT NULL,
            создан_в TIMESTAMP,
            готов_в TIMESTAMP,
            отменен_в TIMESTAMP,
            завершен_в TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS элементы_заказа (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            код_заказа TEXT NOT NULL,
            название_товара TEXT NOT NULL,
            объем TEXT,
            цена REAL NOT NULL,
            количество INTEGER NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS график_работы (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            логин_пользователя TEXT NOT NULL,
            дата_работы TEXT NOT NULL,
            статус TEXT DEFAULT 'назначена'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS комментарии_к_графику (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            логин_пользователя TEXT NOT NULL,
            дата_работы TEXT NOT NULL,
            комментарий TEXT NOT NULL,
            запрошенная_дата TEXT,
            статус TEXT DEFAULT 'в ожидании',
            ответ_администратора TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS справочник_причин_переплаты (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            название TEXT UNIQUE NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS переплаты_сотрудников (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            логин_пользователя TEXT NOT NULL,
            период TEXT NOT NULL,
            причина TEXT NOT NULL
        )
    ''')

    cursor.execute("SELECT COUNT(*) FROM справочник_причин_переплаты")
    if cursor.fetchone()[0] == 0:
        default_reasons = ["Переработка", "Премия", "Просто молодец"]
        for r in default_reasons:
            try:
                cursor.execute("INSERT INTO справочник_причин_переплаты (название) VALUES (?)", (r,))
            except sqlite3.IntegrityError:
                pass

    default_users = [
        ('admin1', '1111111111', 'admin1', 'супер_администратор'),
        ('bar1', '2222222222', 'bar1', 'бариста'),
        ('klient', '3333333333', 'klient', 'клиент')
    ]
    for login, phone, pwd, role in default_users:
        cursor.execute("SELECT id FROM пользователи WHERE логин = ?", (login,))
        if not cursor.fetchone():
            bcode = "2000" + str(random.randint(10000000, 99999999))
            cursor.execute("INSERT INTO пользователи (логин, телефон, пароль, роль, штрихкод) VALUES (?, ?, ?, ?, ?)",
                           (login, phone, pwd, role, bcode))

    cursor.execute("SELECT COUNT(*) FROM меню")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample_menu = [
            ("Капучино", "Эспрессо, вспененное молоко, молочная пенка", 150.0, "напиток", "☕", '[{"vol":"300 мл","price":150},{"vol":"400 мл","price":200},{"vol":"500 мл","price":250}]', now_str),
            ("Латте", "Эспрессо, много молока, нежная пенка", 160.0, "напиток", "☕", '[{"vol":"300 мл","price":160},{"vol":"400 мл","price":210},{"vol":"500 мл","price":260}]', now_str),
            ("Американо", "Эспрессо, горячая вода", 120.0, "напиток", "☕", '[{"vol":"200 мл","price":120},{"vol":"300 мл","price":150},{"vol":"400 мл","price":180}]', now_str),
            ("Чизкейк Нью-Йорк", "Классический творожный десерт со сливочным вкусом", 220.0, "еда", "🍰", '[{"vol":"150 г","price":220},{"vol":"250 г","price":340}]', now_str),
            ("Круассан с шоколадом", "Свежая французская выпечка с шоколадной начинкой", 130.0, "еда", "🍰", '[{"vol":"100 г","price":130},{"vol":"200 г","price":240}]', now_str)
        ]
        cursor.executemany("INSERT INTO меню (название, описание, базовая_цена, категория, путь_к_картинке, объемы_json, дата_добавления) VALUES (?, ?, ?, ?, ?, ?, ?)", sample_menu)

    conn.commit()
    conn.close()

class CoffeeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Кофейня")
        self.configure(bg=BG_COLOR)
        
        self.is_fullscreen = True
        self.attributes('-fullscreen', self.is_fullscreen)
        self.geometry("1100x780")
        self.minsize(900, 640)
        self._apply_global_style()

        self.bind("<F11>", lambda event: self.toggle_fullscreen())
        self.bind("<Escape>", lambda event: self.set_fullscreen(False))

        self.current_user = None
        self.generated_code = None
        self.recovery_phone = None
        self.pending_registration_data = None
        self.cart = []

        self.top_bar = tk.Frame(self, bg=BG_COLOR)
        self.top_bar.pack(side="top", fill="x", padx=10, pady=5)

        self.btn_fullscreen = tk.Button(
            self.top_bar, 
            text="⛶ Оконный режим" if self.is_fullscreen else "⛶ Полноэкранный режим", 
            bg="#3D2923", fg=TEXT_COLOR, font=(UI_FONT, 9), relief="flat", cursor="hand2", padx=10, pady=3,
            command=self.toggle_fullscreen
        )
        self.btn_fullscreen.pack(side="left")

        self.container = tk.Frame(self, bg=BG_COLOR)
        self.container.pack(side="top", fill="both", expand=True)

        self.show_splash_screen()

    def _apply_global_style(self):
        self.option_add("*Button.relief", "flat")
        self.option_add("*Button.borderWidth", 0)
        self.option_add("*Button.cursor", "hand2")
        self.option_add("*Button.padx", 12)
        self.option_add("*Button.pady", 5)
        self.option_add("*Button.activeForeground", TEXT_COLOR)
        self.option_add("*Entry.relief", "flat")
        self.option_add("*Entry.borderWidth", 5)
        self.option_add("*Entry.highlightThickness", 1)
        self.option_add("*Entry.highlightBackground", ENTRY_BG)
        self.option_add("*Entry.highlightColor", BTN_BG)
        self.option_add("*Entry.insertBackground", DARK_TEXT)
        self.bind_class("Button", "<Enter>",
                        lambda e: e.widget.configure(activebackground=e.widget.cget("bg")), add="+")

        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("TCombobox", fieldbackground=ENTRY_BG, background=BTN_BG, foreground=DARK_TEXT,
                     arrowcolor=TEXT_COLOR, bordercolor=ENTRY_BG, lightcolor=ENTRY_BG,
                     darkcolor=ENTRY_BG, padding=4)
        st.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)],
               foreground=[("readonly", DARK_TEXT)], background=[("active", BTN_BG)])
        self.option_add("*TCombobox*Listbox.background", ENTRY_BG)
        self.option_add("*TCombobox*Listbox.foreground", DARK_TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", BTN_PRIMARY)
        self.option_add("*TCombobox*Listbox.selectForeground", TEXT_COLOR)
        self.option_add("*TCombobox*Listbox.font", (UI_FONT, 10))
        st.configure("TNotebook", background=BG_COLOR, borderwidth=0, tabmargins=(0, 4, 0, 0))
        st.configure("TNotebook.Tab", background=BTN_BG, foreground=TEXT_COLOR,
                     padding=(16, 8), font=(UI_FONT, 10, "bold"), borderwidth=0)
        st.map("TNotebook.Tab", background=[("selected", NAV_ACTIVE_BG)],
               foreground=[("selected", TEXT_COLOR)])
        st.configure("Vertical.TScrollbar", background=BTN_BG, troughcolor=BG_COLOR,
                     bordercolor=BG_COLOR, arrowcolor=TEXT_COLOR, lightcolor=BTN_BG,
                     darkcolor=BTN_BG, gripcount=0, arrowsize=14)
        st.map("Vertical.TScrollbar", background=[("active", NAV_ACTIVE_BG)])

    def _embed_scrollable(self, canvas, frame):
        win = canvas.create_window((0, 0), window=frame, anchor="nw")

        def _on_resize(event):
            inner = min(event.width, MAX_CONTENT_W)
            canvas.itemconfigure(win, width=inner)
            canvas.coords(win, (event.width - inner) // 2, 0)

        canvas.bind("<Configure>", _on_resize)
        return win

    def content_width(self, max_w=760):
        return max(320, min(max_w, self.winfo_width() - 140))

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.set_fullscreen(self.is_fullscreen)

    def set_fullscreen(self, state):
        self.is_fullscreen = state
        self.attributes('-fullscreen', self.is_fullscreen)
        if hasattr(self, 'btn_fullscreen'):
            self.btn_fullscreen.config(text="⛶ Оконный режим" if self.is_fullscreen else "⛶ Полноэкранный режим")

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def bind_mouse_scroll(self, widget, canvas):
        def _on_mousewheel(event):
            try:
                if not canvas.winfo_exists():
                    return
                sr = canvas.cget("scrollregion")
                if sr:
                    x1, y1, x2, y2 = map(int, sr.split())
                    if (y2 - y1) <= canvas.winfo_height():
                        return
            except Exception:
                return

            if event.delta:
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    def show_splash_screen(self):
        self.clear_container()
        self.photo_label = tk.Label(self.container, bg=BG_COLOR)
        self.photo_label.pack(expand=True)

        self.angle = 0
        self.rotation_running = True

        if os.path.exists(LOADING_IMAGE_PATH):
            self.original_image = Image.open(LOADING_IMAGE_PATH)
        else:
            self.original_image = Image.new("RGBA", (200, 200), color=(216, 182, 159, 255))

        self.original_image = self.original_image.resize((250, 250), Image.Resampling.LANCZOS)
        self.after(2000, self.stop_splash_and_open_main)
        self.rotate_photo()

    def rotate_photo(self):
        if not self.rotation_running:
            return
        rotated_img = self.original_image.rotate(-self.angle, resample=Image.Resampling.BICUBIC, expand=False)
        tk_img = ImageTk.PhotoImage(rotated_img)
        self.photo_label.configure(image=tk_img)
        self.photo_label.imgtk = tk_img
        self.angle = (self.angle + 12) % 360
        self.after(30, self.rotate_photo)

    def stop_splash_and_open_main(self):
        self.rotation_running = False
        self.show_welcome_screen()

    def show_welcome_screen(self):
        self.clear_container()
        w, h = 380, 260
        canvas = tk.Canvas(self.container, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        self.card_bg = create_rounded_transparent_card(w, h, radius=35, hex_color=CARD_HEX, alpha=150)
        canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

        canvas.create_text(w // 2, 50, text="Добро пожаловать!", font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)

        btn_login = tk.Button(canvas, text="Вход", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"),
                              relief="flat", cursor="hand2", command=self.show_login_screen)
        canvas.create_window(w // 2, 120, window=btn_login, width=280, height=42)

        btn_reg = tk.Button(canvas, text="Регистрация", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"),
                            relief="flat", cursor="hand2", command=self.show_register_screen)
        canvas.create_window(w // 2, 180, window=btn_reg, width=280, height=42)

    def show_login_screen(self, default_login=""):
        self.clear_container()
        w, h = 380, 420
        canvas = tk.Canvas(self.container, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        self.card_bg = create_rounded_transparent_card(w, h, radius=35, hex_color=CARD_HEX, alpha=150)
        canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

        canvas.create_text(w // 2, 45, text="Авторизация", font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)
        canvas.create_text(50, 85, text="Логин или номер телефона", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")

        entry_login = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), relief="flat")
        canvas.create_window(w // 2, 115, window=entry_login, width=280, height=32)
        if default_login:
            entry_login.insert(0, default_login)

        canvas.create_text(50, 155, text="Пароль", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")
        entry_pwd = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), show="*", relief="flat")
        canvas.create_window(w // 2, 185, window=entry_pwd, width=280, height=32)

        def handle_login():
            user_input = entry_login.get().strip()
            password = entry_pwd.get().strip()

            if not user_input or not password:
                messagebox.showwarning("Ошибка", "Все поля должны быть заполнены!")
                return

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT логин, роль FROM пользователи WHERE (логин = ? OR телефон = ?) AND пароль = ?",
                           (user_input, user_input, password))
            user = cursor.fetchone()
            conn.close()

            if user:
                self.current_user = {"login": user[0], "role": user[1]}
                is_admin_group = user[1] in ['администратор', 'супер_администратор']
                first_tab = "employees" if is_admin_group else ("orders" if user[1] == 'бариста' else "home")
                self.show_client_main_layout(active_tab=first_tab)
            else:
                messagebox.showerror("Ошибка", "Неверный логин/телефон или пароль!")

        def show_forgot_password_screen():
            self.clear_container()
            fw, fh = 380, 310
            f_canvas = tk.Canvas(self.container, width=fw, height=fh, bg=BG_COLOR, highlightthickness=0)
            f_canvas.place(relx=0.5, rely=0.5, anchor="center")

            self.card_bg = create_rounded_transparent_card(fw, fh, radius=35, hex_color=CARD_HEX, alpha=150)
            f_canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

            f_canvas.create_text(fw // 2, 35, text="Восстановление пароля", font=(UI_FONT, 15, "bold"), fill=DARK_TEXT)
            f_canvas.create_text(50, 75, text="Введите номер телефона", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")

            entry_f_phone = tk.Entry(f_canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), relief="flat")
            f_canvas.create_window(fw // 2, 115, window=entry_f_phone, width=280, height=32)

            def send_recovery_sms():
                ph = entry_f_phone.get().strip()
                if not ph:
                    messagebox.showwarning("Ошибка", "Введите номер телефона!")
                    return
                
                conn = sqlite3.connect("coffee_shop.db")
                cur = conn.cursor()
                cur.execute("SELECT логин FROM пользователи WHERE телефон = ?", (ph,))
                res = cur.fetchone()
                conn.close()

                if not res:
                    messagebox.showerror("Ошибка", "Пользователь с таким номером телефона не найден!")
                    return

                self.recovery_phone = ph
                self.generated_code = str(random.randint(100000, 999999))
                messagebox.showinfo("SMS Симуляция", f"Код подтверждения для восстановления: {self.generated_code}")
                show_recovery_code_screen()

            btn_send = tk.Button(f_canvas, text="Получить код", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"),
                                 relief="flat", cursor="hand2", command=send_recovery_sms)
            f_canvas.create_window(fw // 2, 185, window=btn_send, width=280, height=38)

            btn_back_l = tk.Button(f_canvas, text="Назад", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9),
                                 relief="flat", cursor="hand2", command=self.show_login_screen)
            f_canvas.create_window(fw // 2, 245, window=btn_back_l, width=100, height=28)

        def show_recovery_code_screen():
            self.clear_container()
            rw, rh = 380, 310
            r_canvas = tk.Canvas(self.container, width=rw, height=rh, bg=BG_COLOR, highlightthickness=0)
            r_canvas.place(relx=0.5, rely=0.5, anchor="center")

            self.card_bg = create_rounded_transparent_card(rw, rh, radius=35, hex_color=CARD_HEX, alpha=150)
            r_canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

            r_canvas.create_text(rw // 2, 35, text="Введите код из SMS", font=(UI_FONT, 15, "bold"), fill=DARK_TEXT)

            entry_r_code = tk.Entry(r_canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 14), justify="center", relief="flat")
            r_canvas.create_window(rw // 2, 95, window=entry_r_code, width=280, height=36)

            r_canvas.create_text(50, 135, text="Новый пароль", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")
            entry_new_pwd = tk.Entry(r_canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), show="*", relief="flat")
            r_canvas.create_window(rw // 2, 175, window=entry_new_pwd, width=280, height=32)

            def confirm_password_reset():
                code = entry_r_code.get().strip()
                npwd = entry_new_pwd.get().strip()

                if code != self.generated_code:
                    messagebox.showerror("Ошибка", "Неверный код из SMS!")
                    return
                if not npwd:
                    messagebox.showwarning("Ошибка", "Введите новый пароль!")
                    return

                conn = sqlite3.connect("coffee_shop.db")
                cur = conn.cursor()
                cur.execute("UPDATE пользователи SET пароль = ? WHERE телефон = ?", (npwd, self.recovery_phone))
                conn.commit()
                conn.close()

                messagebox.showinfo("Успех", "Пароль успешно изменен!")
                self.show_login_screen()

            btn_reset = tk.Button(r_canvas, text="Сохранить новый пароль", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"),
                                  relief="flat", cursor="hand2", command=confirm_password_reset)
            r_canvas.create_window(rw // 2, 235, window=btn_reset, width=280, height=38)

        forgot_id = canvas.create_text(330, 212, text="Забыли пароль?", font=(UI_FONT, 9, "underline"),
                                       fill=DARK_TEXT, anchor="e", activefill="#5D200A")
        canvas.tag_bind(forgot_id, "<Button-1>", lambda e: show_forgot_password_screen())
        canvas.tag_bind(forgot_id, "<Enter>", lambda e: canvas.config(cursor="hand2"))
        canvas.tag_bind(forgot_id, "<Leave>", lambda e: canvas.config(cursor=""))

        btn_submit = tk.Button(canvas, text="Вход", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"),
                               relief="flat", cursor="hand2", command=handle_login)
        canvas.create_window(w // 2, 265, window=btn_submit, width=280, height=42)

        btn_back = tk.Button(canvas, text="Назад", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9),
                             relief="flat", cursor="hand2", command=self.show_welcome_screen)
        canvas.create_window(w // 2, 330, window=btn_back, width=100, height=28)

    def show_register_screen(self):
        self.clear_container()
        w, h = 380, 420
        canvas = tk.Canvas(self.container, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        self.card_bg = create_rounded_transparent_card(w, h, radius=35, hex_color=CARD_HEX, alpha=150)
        canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

        canvas.create_text(w // 2, 35, text="Регистрация", font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)

        canvas.create_text(50, 65, text="Логин", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")
        entry_login = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), relief="flat")
        canvas.create_window(w // 2, 100, window=entry_login, width=280, height=32)

        canvas.create_text(50, 135, text="Номер телефона", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")
        entry_phone = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), relief="flat")
        canvas.create_window(w // 2, 170, window=entry_phone, width=280, height=32)

        canvas.create_text(50, 205, text="Пароль", font=(UI_FONT, 10), fill=DARK_TEXT, anchor="w")
        entry_pwd = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 11), show="*", relief="flat")
        canvas.create_window(w // 2, 240, window=entry_pwd, width=280, height=32)

        def initiate_register():
            login = entry_login.get().strip()
            phone = entry_phone.get().strip()
            password = entry_pwd.get().strip()

            if not login or not phone or not password:
                messagebox.showwarning("Ошибка", "Все поля должны быть заполнены!")
                return

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM пользователи WHERE логин = ?", (login,))
            if cursor.fetchone():
                conn.close()
                messagebox.showerror("Ошибка", "Данный логин уже занят!")
                return
            conn.close()

            self.pending_registration_data = {"login": login, "phone": phone, "password": password}
            self.generated_code = str(random.randint(100000, 999999))
            
            messagebox.showinfo("SMS Симуляция", f"Ваш код подтверждения: {self.generated_code}")
            self.show_reg_sms_code_screen()

        btn_submit = tk.Button(canvas, text="Зарегистрироваться", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"),
                               relief="flat", cursor="hand2", command=initiate_register)
        canvas.create_window(w // 2, 305, window=btn_submit, width=280, height=40)

        btn_back = tk.Button(canvas, text="Назад", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9),
                             relief="flat", cursor="hand2", command=self.show_welcome_screen)
        canvas.create_window(w // 2, 360, window=btn_back, width=100, height=28)

    def show_reg_sms_code_screen(self):
        self.clear_container()
        w, h = 380, 270
        canvas = tk.Canvas(self.container, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        self.card_bg = create_rounded_transparent_card(w, h, radius=35, hex_color=CARD_HEX, alpha=150)
        canvas.create_image(0, 0, anchor="nw", image=self.card_bg)

        canvas.create_text(w // 2, 45, text="Введите код подтверждения из SMS", 
                           font=(UI_FONT, 10, "bold"), fill=DARK_TEXT, width=320, justify="center")

        entry_code = tk.Entry(canvas, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 14), justify="center", relief="flat")
        canvas.create_window(w // 2, 115, window=entry_code, width=280, height=36)

        def verify_reg_code():
            code = entry_code.get().strip()
            if code == self.generated_code:
                data = self.pending_registration_data
                conn = sqlite3.connect("coffee_shop.db")
                cursor = conn.cursor()
                try:
                    bcode = "2000" + str(random.randint(10000000, 99999999))
                    cursor.execute("INSERT INTO пользователи (логин, телефон, пароль, роль, штрихкод) VALUES (?, ?, ?, 'клиент', ?)",
                                   (data["login"], data["phone"], data["password"], bcode))
                    conn.commit()
                    self.current_user = {"login": data["login"], "role": "клиент"}
                    messagebox.showinfo("Успех", "Регистрация завершена!")
                    self.show_client_main_layout("home")
                except sqlite3.IntegrityError:
                    messagebox.showerror("Ошибка", "Ошибка регистрации.")
                finally:
                    conn.close()
            else:
                messagebox.showerror("Ошибка", "Неверный код!")

        btn_verify = tk.Button(canvas, text="Подтвердить", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"),
                               relief="flat", cursor="hand2", command=verify_reg_code)
        canvas.create_window(w // 2, 185, window=btn_verify, width=280, height=40)

    def show_client_main_layout(self, active_tab="home"):
        self.clear_container()
        user_role = self.current_user['role']

        content_frame = tk.Frame(self.container, bg=BG_COLOR)
        content_frame.pack(side="top", fill="both", expand=True)

        nav_frame = tk.Frame(self.container, bg=NAV_BG, height=76)
        nav_frame.pack(side="bottom", fill="x")

        unread_comments_count = 0
        is_admin_group = user_role in ['администратор', 'супер_администратор']
        if is_admin_group:
            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM комментарии_к_графику WHERE статус = 'в ожидании'")
            unread_comments_count = cursor.fetchone()[0]
            conn.close()

        if is_admin_group:
            emp_tab_title = f"👥\nСотрудники ❗" if unread_comments_count > 0 else "👥\nСотрудники"
            tabs = [
                ("employees", emp_tab_title),
                ("menu", "📜\nМеню"),
                ("orders", "📋\nЗаказы"),
                ("loyalty", "💳\nКлубная карта"),
                ("cart", "🛒\nКорзина"),
                ("docs", "📁\nДокументы"),
                ("profile", "👤\nПрофиль")
            ]
        elif user_role == 'бариста':
            tabs = [
                ("orders", "📋\nЗаказы"),
                ("menu", "📜\nМеню"),
                ("loyalty", "💳\nКлубная карта"),
                ("cart", "🛒\nКорзина"),
                ("schedule", "📅\nГрафик работы"),
                ("history", "📜\nИстория заказов"),
                ("profile", "👤\nПрофиль")
            ]
        else:
            tabs = [
                ("home", "🏠\nГлавная"),
                ("menu", "📜\nМеню"),
                ("loyalty", "💳\nЛояльность"),
                ("cart", "🛒\nКорзина"),
                ("history", "📜\nИстория заказов"),
                ("profile", "👤\nПрофиль")
            ]

        for tab_id, tab_title in tabs:
            bg_c = NAV_ACTIVE_BG if tab_id == active_tab else NAV_BG
            holder = tk.Frame(nav_frame, bg=NAV_BG)
            holder.pack(side="left", fill="both", expand=True, padx=2, pady=(0, 3))
            tk.Frame(holder, bg=LIGHT_GOLD if tab_id == active_tab else NAV_BG, height=3).pack(fill="x")
            narrow = self.winfo_width() < 1150
            btn = tk.Button(
                holder, text=tab_title, bg=bg_c, fg=TEXT_COLOR,
                font=(UI_FONT, 9 if narrow else 10, "bold"), relief="flat", cursor="hand2", justify="center",
                padx=4, pady=6, command=lambda t=tab_id: self.show_client_main_layout(t)
            )
            btn.pack(fill="both", expand=True)

        if active_tab == "home":
            self.render_home_tab(content_frame)
        elif active_tab == "employees":
            self.render_admin_employees_tab(content_frame)
        elif active_tab == "orders":
            self.render_barista_orders_tab(content_frame)
        elif active_tab == "menu":
            self.render_menu_tab(content_frame)
        elif active_tab == "loyalty":
            self.render_loyalty_tab(content_frame)
        elif active_tab == "cart":
            self.render_cart_tab(content_frame)
        elif active_tab == "schedule":
            self.render_barista_schedule_tab(content_frame)
        elif active_tab == "history":
            self.render_history_tab(content_frame)
        elif active_tab == "docs":
            self.render_admin_docs_tab(content_frame)
        elif active_tab == "profile":
            self.render_profile_tab(content_frame)

    def render_home_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        cw = self.content_width(760)
        if os.path.exists(HOME_BANNER_PATH):
           banner_img = Image.open(HOME_BANNER_PATH).resize((cw, int(cw * 260 / 700)), Image.Resampling.LANCZOS)
           photo_banner = ImageTk.PhotoImage(banner_img)
           lbl_banner = tk.Label(scrollable_frame, image=photo_banner, bg=BG_COLOR)
           lbl_banner.image = photo_banner
           lbl_banner.pack(pady=(10, 15))
        else:
           banner_canvas = tk.Canvas(scrollable_frame, width=cw, height=int(cw * 260 / 700), bg=BG_COLOR, highlightthickness=0)
           banner_canvas.pack(pady=(10, 15))
           self.card_b = create_rounded_transparent_card(cw, int(cw * 260 / 700), 24, CARD_HEX, 150)
           banner_canvas.create_image(0, 0, anchor="nw", image=self.card_b)
           banner_canvas.create_text(cw // 2, int(cw * 260 / 700) // 2, text="[ Место для баннера главной страницы ]", font=(UI_FONT, 14, "bold"), fill=DARK_TEXT)

        if os.path.exists(HOME_NOVELTY_CARD_PATH):
            novelty_card_img = Image.open(HOME_NOVELTY_CARD_PATH).resize((cw, int(cw * 120 / 700)), Image.Resampling.LANCZOS)
            photo_novelty_card = ImageTk.PhotoImage(novelty_card_img)
            btn_novelty_card = tk.Button(scrollable_frame, image=photo_novelty_card, bg=BG_COLOR, relief="flat",
                                         cursor="hand2", command=lambda: self.show_client_main_layout("menu"))
            btn_novelty_card.image = photo_novelty_card
            btn_novelty_card.pack(pady=5)
        else:
            novelty_canvas = tk.Canvas(scrollable_frame, width=cw, height=100, bg=BG_COLOR, highlightthickness=0, cursor="hand2")
            novelty_canvas.pack(pady=5)
            self.card_n = create_rounded_transparent_card(cw, 100, 24, CARD_HEX, 180)
            novelty_canvas.create_image(0, 0, anchor="nw", image=self.card_n)
            novelty_canvas.create_text(cw // 2, 50, text="✨ Посмотреть Новинки ➔", font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)
            novelty_canvas.bind("<Button-1>", lambda e: self.show_client_main_layout("menu"))

        if os.path.exists(HOME_MENU_CARD_PATH):
            menu_card_img = Image.open(HOME_MENU_CARD_PATH).resize((cw, int(cw * 120 / 700)), Image.Resampling.LANCZOS)
            photo_menu_card = ImageTk.PhotoImage(menu_card_img)
            btn_menu_card = tk.Button(scrollable_frame, image=photo_menu_card, bg=BG_COLOR, relief="flat",
                                      cursor="hand2", command=lambda: self.show_client_main_layout("menu"))
            btn_menu_card.image = photo_menu_card
            btn_menu_card.pack(pady=5)
        else:
            menu_canvas = tk.Canvas(scrollable_frame, width=cw, height=100, bg=BG_COLOR, highlightthickness=0, cursor="hand2")
            menu_canvas.pack(pady=5)
            self.card_m = create_rounded_transparent_card(cw, 100, 24, CARD_HEX, 180)
            menu_canvas.create_image(0, 0, anchor="nw", image=self.card_m)
            menu_canvas.create_text(cw // 2, 50, text="☕ Перейти в Меню ➔", font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)
            menu_canvas.bind("<Button-1>", lambda e: self.show_client_main_layout("menu"))

    def render_admin_employees_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        tk.Label(scrollable_frame, text="Управление сотрудниками", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 10))

        emp_list_frame = tk.Frame(scrollable_frame, bg="#3D2923", bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=10, pady=10)
        emp_list_frame.pack(fill="x", pady=5)

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()
        cursor.execute("SELECT логин, роль, имя, фамилия FROM пользователи WHERE роль IN ('бариста', 'администратор', 'супер_администратор') AND логин != 'admin1'")
        employees = cursor.fetchall()

        current_login = self.current_user['login']
        is_main_admin = (current_login == 'admin1')
        is_super_admin = (self.current_user['role'] == 'супер_администратор')

        if not employees:
            tk.Label(emp_list_frame, text="Список сотрудников пуст", font=(UI_FONT, 11, "italic"), fg="#D8B69F", bg="#3D2923").pack(pady=10)
        else:
            for elogin, erole, efname, elname in employees:
                row_f = tk.Frame(emp_list_frame, bg="#3D2923")
                row_f.pack(fill="x", pady=4)

                display_name = get_user_display_name(cursor, elogin)
                role_str = "Супер-Администратор" if erole == 'супер_администратор' else ("Администратор" if erole == 'администратор' else "Сотрудник")
                
                tk.Label(row_f, text=f"{display_name} [{role_str}]", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(side="left")

                btns_f = tk.Frame(row_f, bg="#3D2923")
                btns_f.pack(side="right")

                def delete_emp(l=elogin, dn=display_name):
                    if messagebox.askyesno("Предупреждение", f"Вы уверены, что хотите удалить сотрудника {dn} из списка сотрудников?"):
                        c = sqlite3.connect("coffee_shop.db")
                        cur = c.cursor()
                        cur.execute("UPDATE пользователи SET роль = 'клиент' WHERE логин = ?", (l,))
                        c.commit()
                        c.close()
                        self.show_client_main_layout("employees")

                def promote_emp(l=elogin, dn=display_name):
                    if messagebox.askyesno("Предупреждение", f"Уверены ли вы, что хотите повысить пользователя {dn} до Администратора?"):
                        c = sqlite3.connect("coffee_shop.db")
                        cur = c.cursor()
                        cur.execute("UPDATE пользователи SET роль = 'администратор' WHERE логин = ?", (l,))
                        c.commit()
                        c.close()
                        self.show_client_main_layout("employees")

                def demote_emp(l=elogin, dn=display_name):
                    if messagebox.askyesno("Предупреждение", f"Уверены ли вы, что хотите понизить пользователя {dn} в правах до бариста?"):
                        c = sqlite3.connect("coffee_shop.db")
                        cur = c.cursor()
                        cur.execute("UPDATE пользователи SET роль = 'бариста' WHERE логин = ?", (l,))
                        c.commit()
                        c.close()
                        self.show_client_main_layout("employees")

                def demote_super_to_admin(l=elogin, dn=display_name):
                    if messagebox.askyesno("Предупреждение", f"Понизить супер-администратора {dn} до обычного Администратора?"):
                        c = sqlite3.connect("coffee_shop.db")
                        cur = c.cursor()
                        cur.execute("UPDATE пользователи SET роль = 'администратор' WHERE логин = ?", (l,))
                        c.commit()
                        c.close()
                        self.show_client_main_layout("employees")

                def make_super_emp(l=elogin, dn=display_name):
                    if messagebox.askyesno("Предупреждение", f"Повысить администратора {dn} до Супер-Администратора (полные права)?"):
                        c = sqlite3.connect("coffee_shop.db")
                        cur = c.cursor()
                        cur.execute("UPDATE пользователи SET роль = 'супер_администратор' WHERE логин = ?", (l,))
                        c.commit()
                        c.close()
                        self.show_client_main_layout("employees")

                can_manage_user = True
                if erole == 'супер_администратор' and not is_main_admin:
                    can_manage_user = False

                if is_main_admin or is_super_admin:
                    if can_manage_user:
                        btn_del = tk.Button(btns_f, text="✖", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), width=3, relief="flat", command=delete_emp)
                        btn_del.pack(side="left", padx=2)

                        if erole == 'бариста':
                            btn_up = tk.Button(btns_f, text="▲ Админ", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat", command=promote_emp)
                            btn_up.pack(side="left", padx=2)
                        elif erole == 'администратор':
                            btn_down = tk.Button(btns_f, text="▼ Бариста", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat", command=demote_emp)
                            btn_down.pack(side="left", padx=2)
                            btn_super = tk.Button(btns_f, text="★ Супер", bg=NAV_ACTIVE_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat", command=make_super_emp)
                            btn_super.pack(side="left", padx=2)
                        elif erole == 'супер_администратор' and is_main_admin:
                            btn_down_adm = tk.Button(btns_f, text="▼ Админ", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat", command=demote_super_to_admin)
                            btn_down_adm.pack(side="left", padx=2)
                            btn_down_bar = tk.Button(btns_f, text="▼ Бариста", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat", command=demote_emp)
                            btn_down_bar.pack(side="left", padx=2)

        conn.close()

        if is_main_admin or is_super_admin:
            btn_add_emp = tk.Button(scrollable_frame, text="Добавить сотрудника", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"), relief="flat", command=self.open_add_employee_modal)
            btn_add_emp.pack(anchor="w", pady=15)

        tk.Frame(scrollable_frame, bg="#D8B69F", height=2).pack(fill="x", pady=15)
        self.render_admin_schedule_module(scrollable_frame)

    def open_add_employee_modal(self):
        modal = tk.Toplevel(self)
        modal.title("Добавить сотрудника")
        modal.geometry("450x400")
        modal.configure(bg=BG_COLOR)
        modal.grab_set()

        btn_close = tk.Button(modal, text="✖", bg=BG_COLOR, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"), bd=0, command=modal.destroy)
        btn_close.place(x=415, y=10)

        tk.Label(modal, text="Поиск пользователя по логину", font=(UI_FONT, 12, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=(20, 10))

        search_entry = PlaceholderEntry(modal, placeholder="Введите логин...", font=(UI_FONT, 11), bg=ENTRY_BG, fg=DARK_TEXT)
        search_entry.pack(pady=5, padx=20, fill="x")

        results_frame = tk.Frame(modal, bg=BG_COLOR)
        results_frame.pack(fill="both", expand=True, padx=20, pady=10)

        def update_search(*args):
            for w in results_frame.winfo_children():
                w.destroy()
            query = search_entry.get_clean().lower()
            if not query:
                return

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT логин, имя, фамилия FROM пользователи WHERE роль = 'клиент' AND LOWER(логин) LIKE ?", (f"%{query}%",))
            matches = cursor.fetchall()

            for mlogin, mfn, mln in matches:
                r_line = tk.Frame(results_frame, bg="#3D2923", padx=5, pady=5)
                r_line.pack(fill="x", pady=2)

                dname = f"{mfn} {mln}".strip() if (mfn or mln) else "***"
                full_str = f"{mlogin} - {dname}"
                tk.Label(r_line, text=full_str, font=(UI_FONT, 10), fg=TEXT_COLOR, bg="#3D2923").pack(side="left")

                def add_emp_flow(l=mlogin, fs=full_str):
                    if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите добавить пользователя {fs} в список сотрудников?"):
                        role_win = tk.Toplevel(modal)
                        role_win.title("Выбор группы")
                        role_win.geometry("340x200")
                        role_win.configure(bg=BG_COLOR)
                        role_win.grab_set()

                        tk.Label(role_win, text="Добавить пользователя в группу:", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=15)

                        selected_role = tk.StringVar(value="бариста")

                        def set_group(r):
                            selected_role.set(r)
                            btn_sup.config(bg=NAV_ACTIVE_BG if r == 'супер_администратор' else BTN_BG)
                            btn_adm.config(bg=NAV_ACTIVE_BG if r == 'администратор' else BTN_BG)
                            btn_emp.config(bg=NAV_ACTIVE_BG if r == 'бариста' else BTN_BG)

                        btn_f = tk.Frame(role_win, bg=BG_COLOR)
                        btn_f.pack(pady=10)

                        current_login = self.current_user['login']
                        if current_login == 'admin1':
                            btn_sup = tk.Button(btn_f, text="Супер-Админ", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), command=lambda: set_group('супер_администратор'))
                            btn_sup.pack(side="left", padx=3)

                        btn_adm = tk.Button(btn_f, text="Администрация", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), command=lambda: set_group('администратор'))
                        btn_adm.pack(side="left", padx=3)

                        btn_emp = tk.Button(btn_f, text="Сотрудник", bg=NAV_ACTIVE_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), command=lambda: set_group('бариста'))
                        btn_emp.pack(side="left", padx=3)

                        def confirm_add():
                            c = sqlite3.connect("coffee_shop.db")
                            cur = c.cursor()
                            cur.execute("UPDATE пользователи SET роль = ? WHERE логин = ?", (selected_role.get(), l))
                            c.commit()
                            c.close()
                            role_win.destroy()
                            modal.destroy()
                            self.show_client_main_layout("employees")

                        tk.Button(role_win, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=10, command=confirm_add).pack(pady=10)

                btn_add = tk.Button(r_line, text="⊕", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"), relief="flat", command=lambda l=mlogin, fs=full_str: add_emp_flow(l, fs))
                btn_add.pack(side="right")

            conn.close()

        search_entry.bind("<KeyRelease>", update_search)

    def open_date_picker_modal(self, year_var, month_var, on_select_callback):
        modal = tk.Toplevel(self)
        modal.title("Выбор даты (Месяц и Год)")
        modal.geometry("320x220")
        modal.configure(bg=BG_COLOR)
        modal.grab_set()

        tk.Label(modal, text="Выберите год и месяц:", font=(UI_FONT, 12, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR).pack(pady=15)

        f_selectors = tk.Frame(modal, bg=BG_COLOR)
        f_selectors.pack(pady=10)

        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        cb_m = ttk.Combobox(f_selectors, values=months, state="readonly", width=12)
        cb_m.set(months[month_var.get() - 1])
        cb_m.pack(side="left", padx=5)

        years = [2026, 2027, 2028, 2029]
        cb_y = ttk.Combobox(f_selectors, values=years, state="readonly", width=8)
        cb_y.set(year_var.get())
        cb_y.pack(side="left", padx=5)

        def apply():
            m_idx = months.index(cb_m.get()) + 1
            y_val = int(cb_y.get())
            month_var.set(m_idx)
            year_var.set(y_val)
            modal.destroy()
            on_select_callback()

        tk.Button(modal, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=10, command=apply).pack(pady=15)

    def render_admin_schedule_module(self, parent_frame):
        tk.Label(parent_frame, text="График смен сотрудников", font=(UI_FONT, 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(10, 5))

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()
        
        current_login = self.current_user['login']
        is_main_admin = (current_login == 'admin1')
        is_super = (current_login == 'admin1' or self.current_user['role'] == 'супер_администратор')

        if is_main_admin:
            cursor.execute("SELECT логин, роль, имя, фамилия FROM пользователи WHERE роль IN ('бариста', 'администратор', 'супер_администратор') AND логин != 'admin1'")
        elif is_super:
            cursor.execute("SELECT логин, роль, имя, фамилия FROM пользователи WHERE роль IN ('бариста', 'администратор') AND логин != ?", (current_login,))
        else:
            cursor.execute("SELECT логин, роль, имя, фамилия FROM пользователи WHERE роль = 'бариста'")
        
        emp_rows = cursor.fetchall()

        emp_dict = {}
        for el, erol, ef, eln in emp_rows:
            dn = f"{ef} {eln}".strip() if (ef or eln) else "***"
            cursor.execute("SELECT COUNT(*) FROM комментарии_к_графику WHERE логин_пользователя = ? AND статус = 'в ожидании'", (el,))
            comm_cnt = cursor.fetchone()[0]
            cnt_str = " ❗" if comm_cnt > 0 else ""
            emp_dict[f"{el} - {dn}{cnt_str}"] = el

        conn.close()

        if not emp_dict:
            tk.Label(parent_frame, text="Нет доступных сотрудников для составления графика", font=(UI_FONT, 11, "italic"), fg="#D8B69F", bg=BG_COLOR).pack(pady=5)
            return

        now = datetime.now()
        year_var = tk.IntVar(value=now.year if now.year >= 2026 else 2026)
        month_var = tk.IntVar(value=now.month)

        ctrl_f = tk.Frame(parent_frame, bg=BG_COLOR)
        ctrl_f.pack(fill="x", pady=5)

        btn_cal_icon = tk.Button(ctrl_f, text="📅", font=(UI_FONT, 14), bg=BG_COLOR, fg=TEXT_COLOR, relief="flat", cursor="hand2")
        btn_cal_icon.pack(side="left", padx=(0, 5))

        lbl_date_info = tk.Label(ctrl_f, text="", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR)
        lbl_date_info.pack(side="left", padx=5)

        cb_emp = ttk.Combobox(ctrl_f, values=list(emp_dict.keys()), state="readonly", width=30)
        cb_emp.set(list(emp_dict.keys())[0])
        cb_emp.pack(side="left", padx=10)

        salary_frame = tk.Frame(parent_frame, bg="#3D2923", padx=10, pady=10)
        salary_frame.pack(fill="x", pady=10)

        lbl_salary_info = tk.Label(salary_frame, text="", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg="#3D2923")
        lbl_salary_info.pack(anchor="w")

        f_rate_edit = tk.Frame(salary_frame, bg="#3D2923")
        f_rate_edit.pack(anchor="w", pady=5)

        tk.Label(f_rate_edit, text="Ставка за смену (руб): ", fg=TEXT_COLOR, bg="#3D2923").pack(side="left")
        e_rate = tk.Entry(f_rate_edit, bg=ENTRY_BG, fg=DARK_TEXT, width=10)
        e_rate.pack(side="left", padx=5)

        tk.Label(f_rate_edit, text=" Выдано: ", fg=TEXT_COLOR, bg="#3D2923").pack(side="left")
        e_paid = tk.Entry(f_rate_edit, bg=ENTRY_BG, fg=DARK_TEXT, width=10)
        e_paid.pack(side="left", padx=5)

        reasons_frame = tk.Frame(salary_frame, bg="#3D2923")
        reasons_frame.pack(anchor="w", fill="x", pady=(5, 0))

        cal_frame = tk.Frame(parent_frame, bg="#3D2923", padx=10, pady=10)
        cal_frame.pack(anchor="w", pady=10)

        selected_dates = set()

        def render_overpayment_reasons_ui():
            for w in reasons_frame.winfo_children():
                w.destroy()

            tk.Label(reasons_frame, text="Причина переплаты:", font=(UI_FONT, 10, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w", pady=(5, 2))

            btns_container = tk.Frame(reasons_frame, bg="#3D2923")
            btns_container.pack(anchor="w", fill="x")

            target_login = emp_dict[cb_emp.get()]
            period_str = f"{year_var.get()}-{month_var.get():02d}"

            c_db = sqlite3.connect("coffee_shop.db")
            cur_db = c_db.cursor()
            cur_db.execute("SELECT причина FROM переплаты_сотрудников WHERE логин_пользователя = ? AND период = ?", (target_login, period_str))
            active_reasons_db = {r[0] for r in cur_db.fetchall()}

            cur_db.execute("SELECT название FROM справочник_причин_переплаты")
            all_reasons = [r[0] for r in cur_db.fetchall()]
            c_db.close()

            def save_active_reasons_to_db(act_set):
                c = sqlite3.connect("coffee_shop.db")
                cur = c.cursor()
                cur.execute("DELETE FROM переплаты_сотрудников WHERE логин_пользователя = ? AND период = ?", (target_login, period_str))
                for r_name in act_set:
                    cur.execute("INSERT INTO переплаты_сотрудников (логин_пользователя, период, причина) VALUES (?, ?, ?)", (target_login, period_str, r_name))
                c.commit()
                c.close()

            def build_reason_buttons():
                for w in btns_container.winfo_children():
                    if w != btn_add_new:
                        w.destroy()

                for r_text in all_reasons:
                    is_active = (r_text in active_reasons_db)
                    bg_col = NAV_ACTIVE_BG if is_active else BTN_BG
                    
                    r_btn = tk.Button(btns_container, text=r_text, bg=bg_col, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", cursor="hand2")
                    r_btn.pack(side="left", padx=3, pady=3)

                    def make_click_cmd(rt=r_text):
                        def on_single_click():
                            if rt in active_reasons_db:
                                active_reasons_db.remove(rt)
                            else:
                                active_reasons_db.add(rt)
                            save_active_reasons_to_db(active_reasons_db)
                            build_reason_buttons()
                        return on_single_click

                    def make_dbl_cmd(rt=r_text):
                        def on_dbl_click(event):
                            edit_win = tk.Toplevel(self)
                            edit_win.title("Редактировать причину")
                            edit_win.geometry("320x160")
                            edit_win.configure(bg=BG_COLOR)
                            edit_win.grab_set()

                            tk.Label(edit_win, text="Новое название причины:", font=(UI_FONT, 10, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=10)
                            e_edit = tk.Entry(edit_win, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 10))
                            e_edit.insert(0, rt)
                            e_edit.pack(pady=5, padx=20, fill="x")

                            def apply_edit():
                                new_v = e_edit.get().strip()
                                if new_v:
                                    c_conn = sqlite3.connect("coffee_shop.db")
                                    cur_c = c_conn.cursor()
                                    try:
                                        cur_c.execute("UPDATE справочник_причин_переплаты SET название = ? WHERE название = ?", (new_v, rt))
                                        cur_c.execute("UPDATE переплаты_сотрудников SET причина = ? WHERE причина = ?", (new_v, rt))
                                        c_conn.commit()
                                    except sqlite3.IntegrityError:
                                        messagebox.showerror("Ошибка", "Такая причина уже существует!")
                                    c_conn.close()
                                edit_win.destroy()
                                render_overpayment_reasons_ui()

                            tk.Button(edit_win, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=12, command=apply_edit).pack(pady=10)
                        return on_dbl_click

                    def make_right_click_cmd(rt=r_text):
                        def on_right_click(event):
                            if messagebox.askyesno("Удаление", f"Вы действительно хотите удалить причину '{rt}'?"):
                                c_conn = sqlite3.connect("coffee_shop.db")
                                cur_c = c_conn.cursor()
                                cur_c.execute("DELETE FROM справочник_причин_переплаты WHERE название = ?", (rt,))
                                cur_c.execute("DELETE FROM переплаты_сотрудников WHERE причина = ?", (rt,))
                                c_conn.commit()
                                c_conn.close()
                                render_overpayment_reasons_ui()
                        return on_right_click

                    r_btn.config(command=make_click_cmd(r_text))
                    r_btn.bind("<Double-Button-1>", make_dbl_cmd(r_text))
                    r_btn.bind("<Button-3>", make_right_click_cmd(r_text))

                btn_add_new.pack_forget()
                btn_add_new.pack(side="left", padx=3, pady=3)

            def add_new_reason_modal():
                add_win = tk.Toplevel(self)
                add_win.title("Добавить причину")
                add_win.geometry("320x160")
                add_win.configure(bg=BG_COLOR)
                add_win.grab_set()

                tk.Label(add_win, text="Название причины переплаты:", font=(UI_FONT, 10, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=10)
                e_new = tk.Entry(add_win, bg=ENTRY_BG, fg=DARK_TEXT, font=(UI_FONT, 10))
                e_new.pack(pady=5, padx=20, fill="x")
                e_new.focus_set()

                def confirm_new_reason():
                    val = e_new.get().strip()
                    if val:
                        c_conn = sqlite3.connect("coffee_shop.db")
                        cur_c = c_conn.cursor()
                        try:
                            cur_c.execute("INSERT INTO справочник_причин_переплаты (название) VALUES (?)", (val,))
                            c_conn.commit()
                        except sqlite3.IntegrityError:
                            messagebox.showerror("Ошибка", "Такая причина уже существует!")
                        c_conn.close()
                        add_win.destroy()
                        render_overpayment_reasons_ui()

                tk.Button(add_win, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=12, command=confirm_new_reason).pack(pady=10)

            btn_add_new = tk.Button(btns_container, text="+ добавить новую причину", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", cursor="hand2", command=add_new_reason_modal)
            build_reason_buttons()

        def update_salary_ui(target_login, num_shifts):
            c = sqlite3.connect("coffee_shop.db")
            cur = c.cursor()
            cur.execute("SELECT дневная_ставка, выплачено_сумма FROM пользователи WHERE логин = ?", (target_login,))
            d_rate, p_amt = cur.fetchone()
            c.close()

            e_rate.delete(0, tk.END)
            e_rate.insert(0, str(int(d_rate)))
            e_paid.delete(0, tk.END)
            e_paid.insert(0, str(int(p_amt)))

            total_due = num_shifts * d_rate
            remains = total_due - p_amt
            lbl_salary_info.config(text=f"Смен в месяце: {num_shifts} | К оплате: {total_due:.0f} руб. | Осталось: {remains:.0f} руб.")

            render_overpayment_reasons_ui()

        def save_salary_changes():
            target_login = emp_dict[cb_emp.get()]
            try:
                nr = float(e_rate.get().strip())
                np = float(e_paid.get().strip())
                c = sqlite3.connect("coffee_shop.db")
                cur = c.cursor()
                cur.execute("UPDATE пользователи SET дневная_ставка = ?, выплачено_сумма = ? WHERE логин = ?", (nr, np, target_login))
                c.commit()
                c.close()
                load_calendar()
            except ValueError:
                pass

        btn_save_sal = tk.Button(f_rate_edit, text="Сохранить", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), command=save_salary_changes)
        btn_save_sal.pack(side="left", padx=5)

        btn_max = tk.Button(f_rate_edit, text="Максимум", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), command=lambda: set_max_salary())
        btn_max.pack(side="left", padx=5)

        def set_max_salary():
            target_login = emp_dict[cb_emp.get()]
            c = sqlite3.connect("coffee_shop.db")
            cur = c.cursor()
            cur.execute("SELECT дневная_ставка FROM пользователи WHERE логин = ?", (target_login,))
            d_rate = cur.fetchone()[0]
            c.close()
            total_due = len(selected_dates) * d_rate
            e_paid.delete(0, tk.END)
            e_paid.insert(0, str(int(total_due)))
            save_salary_changes()

        def load_calendar():
            months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
            lbl_date_info.config(text=f"{months[month_var.get()-1]} {year_var.get()}")

            for w in cal_frame.winfo_children():
                w.destroy()

            sel_emp_str = cb_emp.get()
            if not sel_emp_str:
                return
            target_login = emp_dict[sel_emp_str]

            c_db = sqlite3.connect("coffee_shop.db")
            cur_db = c_db.cursor()
            cur_db.execute("SELECT дата_работы FROM график_работы WHERE логин_пользователя = ?", (target_login,))
            existing_dates = {r[0] for r in cur_db.fetchall() if r[0].startswith(f"{year_var.get()}-{month_var.get():02d}")}

            cur_db.execute("SELECT дата_работы, комментарий, запрошенная_дата, id FROM комментарии_к_графику WHERE логин_пользователя = ? AND статус = 'в ожидании'", (target_login,))
            comments_map = {r[0]: (r[1], r[2], r[3]) for r in cur_db.fetchall()}
            c_db.close()

            nonlocal selected_dates
            selected_dates = set(existing_dates)

            update_salary_ui(target_login, len(selected_dates))

            days_header = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            for i, h in enumerate(days_header):
                tk.Label(cal_frame, text=h, font=(UI_FONT, 9, "bold"), fg=LIGHT_GOLD, bg="#3D2923", width=4).grid(row=0, column=i, pady=2)

            cal = calendar.monthcalendar(year_var.get(), month_var.get())

            for r_idx, week in enumerate(cal, start=1):
                for c_idx, day in enumerate(week):
                    if day == 0:
                        continue
                    d_str = f"{year_var.get()}-{month_var.get():02d}-{day:02d}"
                    has_comment = d_str in comments_map
                    bg_c = NAV_ACTIVE_BG if d_str in selected_dates else "#2B1812"

                    btn_text = f"❗ {day}" if has_comment else (f"● {day}" if d_str in selected_dates else str(day))
                    if has_comment:
                        bg_c = ALERT_RED

                    btn = tk.Button(cal_frame, text=btn_text, bg=bg_c, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), width=6, relief="flat")
                    btn.grid(row=r_idx, column=c_idx, padx=2, pady=2)

                    btn.config(command=lambda ds=d_str, b=btn, comm=comments_map.get(d_str): show_comm_or_toggle(ds, b, comm, target_login))

        def show_comm_or_toggle(ds, b, comm, t_login):
            if comm:
                c_text, r_date, comm_id = comm
                m = tk.Toplevel(self)
                m.title("Запрос смены")
                m.geometry("400x320")
                m.configure(bg=BG_COLOR)
                m.grab_set()

                tk.Label(m, text=f"Запрос по дате: {ds}", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR).pack(pady=10)
                tk.Label(m, text=f"Причина: {c_text}", font=(UI_FONT, 10), fg=TEXT_COLOR, bg=BG_COLOR, wraplength=360).pack(pady=5)
                if r_date:
                    tk.Label(m, text=f"Предложенная дата замены: {r_date}", font=(UI_FONT, 10, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR).pack(pady=5)

                tk.Label(m, text="Ответ администратора:", font=(UI_FONT, 9), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", padx=20)
                entry_reply = tk.Entry(m, bg=ENTRY_BG, fg=DARK_TEXT)
                entry_reply.pack(fill="x", padx=20, pady=5)

                def handle_action(approved):
                    reply_t = entry_reply.get().strip()
                    c = sqlite3.connect("coffee_shop.db")
                    cur = c.cursor()
                    cur.execute("UPDATE комментарии_к_графику SET статус = ?, ответ_администратора = ? WHERE id = ?",
                                ('одобрено' if approved else 'отклонено', reply_t, comm_id))
                    if approved and r_date:
                        cur.execute("DELETE FROM график_работы WHERE логин_пользователя = ? AND дата_работы = ?", (t_login, ds))
                        cur.execute("INSERT OR REPLACE INTO график_работы (логин_пользователя, дата_работы) VALUES (?, ?)", (t_login, r_date))
                    c.commit()
                    c.close()
                    m.destroy()
                    self.show_client_main_layout("employees")

                btn_f = tk.Frame(m, bg=BG_COLOR)
                btn_f.pack(pady=15)

                tk.Button(btn_f, text="Поменять даты", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), command=lambda: handle_action(True)).pack(side="left", padx=5)
                tk.Button(btn_f, text="Отказать", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), command=lambda: handle_action(False)).pack(side="left", padx=5)
            else:
                if ds in selected_dates:
                    selected_dates.remove(ds)
                    b.config(bg="#2B1812", text=str(ds.split('-')[-1]))
                else:
                    selected_dates.add(ds)
                    b.config(bg=NAV_ACTIVE_BG, text=f"● {ds.split('-')[-1]}")
                btn_save_sched.pack(pady=10)

        def save_schedule():
            target_login = emp_dict[cb_emp.get()]
            c = sqlite3.connect("coffee_shop.db")
            cur = c.cursor()
            cur.execute("DELETE FROM график_работы WHERE логин_пользователя = ? AND дата_работы LIKE ?", (target_login, f"{year_var.get()}-{month_var.get():02d}-%"))
            for d in selected_dates:
                cur.execute("INSERT INTO график_работы (логин_пользователя, дата_работы) VALUES (?, ?)", (target_login, d))
            c.commit()
            c.close()
            messagebox.showinfo("Успех", "График смен сохранен!")
            self.show_client_main_layout("employees")

        btn_cal_icon.config(command=lambda: self.open_date_picker_modal(year_var, month_var, load_calendar))
        cb_emp.bind("<<ComboboxSelected>>", lambda e: load_calendar())

        btn_save_sched = tk.Button(parent_frame, text="Сохранить график", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"), relief="flat", command=save_schedule)
        load_calendar()

    def render_barista_schedule_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        tk.Label(scrollable_frame, text="Ваш график работы", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 10))

        now = datetime.now()
        year_var = tk.IntVar(value=now.year if now.year >= 2026 else 2026)
        month_var = tk.IntVar(value=now.month)

        ctrl_f = tk.Frame(scrollable_frame, bg=BG_COLOR)
        ctrl_f.pack(fill="x", pady=5)

        btn_cal_icon = tk.Button(ctrl_f, text="📅", font=(UI_FONT, 14), bg=BG_COLOR, fg=TEXT_COLOR, relief="flat", cursor="hand2")
        btn_cal_icon.pack(side="left", padx=(0, 5))

        lbl_date_info = tk.Label(ctrl_f, text="", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR)
        lbl_date_info.pack(side="left", padx=5)

        sal_card = tk.Frame(scrollable_frame, bg="#3D2923", padx=15, pady=10)
        sal_card.pack(fill="x", pady=10)

        lbl_sal_bar = tk.Label(sal_card, text="", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg="#3D2923")
        lbl_sal_bar.pack(anchor="w")

        lbl_barista_reasons = tk.Label(sal_card, text="", font=(UI_FONT, 10, "italic"), fg=LIGHT_GOLD, bg="#3D2923")
        lbl_barista_reasons.pack(anchor="w", pady=(3, 0))

        cal_frame = tk.Frame(scrollable_frame, bg="#3D2923", padx=10, pady=10)
        cal_frame.pack(anchor="w", pady=10)

        def load_barista_cal():
            months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
            lbl_date_info.config(text=f"{months[month_var.get()-1]} {year_var.get()}")

            for w in cal_frame.winfo_children():
                w.destroy()

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT дневная_ставка, выплачено_сумма FROM пользователи WHERE логин = ?", (self.current_user['login'],))
            d_rate, p_amt = cursor.fetchone()

            cursor.execute("SELECT дата_работы FROM график_работы WHERE логин_пользователя = ?", (self.current_user['login'],))
            work_dates = {r[0] for r in cursor.fetchall() if r[0].startswith(f"{year_var.get()}-{month_var.get():02d}")}

            period_str = f"{year_var.get()}-{month_var.get():02d}"
            cursor.execute("SELECT причина FROM переплаты_сотрудников WHERE логин_пользователя = ? AND период = ?", (self.current_user['login'], period_str))
            reasons_found = [r[0] for r in cursor.fetchall()]
            conn.close()

            num_shifts = len(work_dates)
            total_due = num_shifts * d_rate
            remains = total_due - p_amt
            lbl_sal_bar.config(text=f"Ставка за смену: {d_rate:.0f} руб. | Смен: {num_shifts} | К оплате: {total_due:.0f} руб. | Выдано: {p_amt:.0f} руб. | Осталось: {remains:.0f} руб.")

            if reasons_found:
                lbl_barista_reasons.config(text=f"Причина(ы) переплаты/доплаты: {', '.join(reasons_found)}")
            else:
                lbl_barista_reasons.config(text="")

            days_header = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            for i, h in enumerate(days_header):
                tk.Label(cal_frame, text=h, font=(UI_FONT, 9, "bold"), fg=LIGHT_GOLD, bg="#3D2923", width=4).grid(row=0, column=i, pady=2)

            cal = calendar.monthcalendar(year_var.get(), month_var.get())

            for r_idx, week in enumerate(cal, start=1):
                for c_idx, day in enumerate(week):
                    if day == 0:
                        continue
                    d_str = f"{year_var.get()}-{month_var.get():02d}-{day:02d}"
                    is_work = d_str in work_dates
                    bg_c = NAV_ACTIVE_BG if is_work else "#2B1812"

                    btn = tk.Button(cal_frame, text=f"● {day}" if is_work else str(day), bg=bg_c, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), width=5, relief="flat")
                    btn.grid(row=r_idx, column=c_idx, padx=2, pady=2)

                    if is_work:
                        def click_work_date(ds=d_str):
                            m = tk.Toplevel(self)
                            m.title("Запрос перенос смены")
                            m.geometry("380x300")
                            m.configure(bg=BG_COLOR)
                            m.grab_set()

                            tk.Label(m, text=f"Выбранная дата смены: {ds}", font=(UI_FONT, 10, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR).pack(pady=10)
                            tk.Label(m, text="Комментарий / причина:", font=(UI_FONT, 9), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", padx=20)

                            entry_c = tk.Entry(m, bg=ENTRY_BG, fg=DARK_TEXT)
                            entry_c.pack(fill="x", padx=20, pady=5)

                            tk.Label(m, text="Выберите свободную дату для замены:", font=(UI_FONT, 9), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", padx=20)
                            
                            num_days = calendar.monthrange(year_var.get(), month_var.get())[1]
                            free_dates = []
                            for d_num in range(1, num_days + 1):
                                f_d_str = f"{year_var.get()}-{month_var.get():02d}-{d_num:02d}"
                                if f_d_str not in work_dates:
                                    free_dates.append(f_d_str)

                            combo_free = ttk.Combobox(m, values=free_dates, state="readonly")
                            if free_dates:
                                combo_free.set(free_dates[0])
                            combo_free.pack(fill="x", padx=20, pady=5)

                            def send_comment():
                                txt = entry_c.get().strip()
                                req_d = combo_free.get().strip()
                                if not txt or not req_d:
                                    messagebox.showwarning("Ошибка", "Заполните поле и выберите дату!")
                                    return
                                c = sqlite3.connect("coffee_shop.db")
                                cur = c.cursor()
                                cur.execute("INSERT INTO комментарии_к_графику (логин_пользователя, дата_работы, комментарий, запрошенная_дата) VALUES (?, ?, ?, ?)",
                                            (self.current_user['login'], ds, txt, req_d))
                                c.commit()
                                c.close()
                                m.destroy()
                                messagebox.showinfo("Отправлено", "Запрос отправлен администратору!")

                            tk.Button(m, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=12, command=send_comment).pack(pady=15)

                        btn.config(command=click_work_date)

        btn_cal_icon.config(command=lambda: self.open_date_picker_modal(year_var, month_var, load_barista_cal))
        load_barista_cal()

    def render_barista_orders_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        tk.Label(scrollable_frame, text="Очередь заказов клиентов", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 15))

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()

        cursor.execute('''
            SELECT код_заказа, логин_пользователя, создан_в, итоговая_цена, статус, готов_в, отменен_в, роль_пользователя
            FROM заказы 
            WHERE статус IN ('создан', 'принят', 'готовится', 'готов', 'отменен')
            ORDER BY 
                CASE 
                    WHEN статус IN ('принят', 'готовится', 'готов') THEN 0
                    WHEN логин_пользователя = 'admin1' OR роль_пользователя IN ('администратор', 'супер_администратор') THEN 1
                    ELSE 2
                END ASC, id ASC
        ''')
        orders_list = cursor.fetchall()

        if not orders_list:
            tk.Label(scrollable_frame, text="Нет активных заказов в очереди", font=(UI_FONT, 14), fg="#D8B69F", bg=BG_COLOR).pack(pady=50)
            conn.close()
            return

        for o_code, u_login, c_time, t_price, status, ready_at, cancelled_at, u_role in orders_list:
            card_bg = "#3D2923"
            pin_symbol = ""

            if u_login == 'admin1' or u_role in ['администратор', 'супер_администратор']:
                card_bg = "#5A2A1E" 
                pin_symbol = "📌 "

            card = tk.Frame(scrollable_frame, bg=card_bg, bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=15, pady=15)
            card.pack(fill="x", expand=True, pady=10)

            top_line = tk.Frame(card, bg=card_bg)
            top_line.pack(fill="x")

            display_user = get_user_display_name(cursor, u_login)
            
            tk.Label(top_line, text=f"Заказ #{o_code}", font=(UI_FONT, 14, "bold"), fg=LIGHT_GOLD, bg=card_bg).pack(side="left")
            
            right_meta_str = f"Клиент: {display_user} | Время: {c_time} {pin_symbol}".strip()
            tk.Label(top_line, text=right_meta_str, font=(UI_FONT, 10, "bold" if pin_symbol else "normal"), fg=TEXT_COLOR, bg=card_bg).pack(side="right")

            cursor.execute("SELECT название_товара, объем, цена, количество FROM элементы_заказа WHERE код_заказа = ?", (o_code,))
            items = cursor.fetchall()

            items_frame = tk.Frame(card, bg="#2B1812", padx=10, pady=8)
            items_frame.pack(fill="x", pady=10)

            for i_name, i_vol, i_price, i_qty in items:
                vol_str = f" ({i_vol})" if i_vol else ""
                tk.Label(items_frame, text=f"• {i_name}{vol_str} — {i_qty} шт. x {i_price:.0f} руб.", font=(UI_FONT, 10), fg=TEXT_COLOR, bg="#2B1812").pack(anchor="w")

            tk.Label(card, text=f"Сумма: {t_price:.0f} руб.", font=(UI_FONT, 12, "bold"), fg=LIGHT_GOLD, bg=card_bg).pack(anchor="w")

            btn_frame = tk.Frame(card, bg=card_bg)
            btn_frame.pack(anchor="e", pady=(5, 0))

            def update_order_status(code=o_code, new_st='принят', u_log=u_login, tot_p=t_price):
                c_db = sqlite3.connect("coffee_shop.db")
                cur_db = c_db.cursor()
                now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if new_st == 'готов':
                    cur_db.execute("UPDATE заказы SET статус = ?, готов_в = ? WHERE код_заказа = ?", (new_st, now_s, code))
                elif new_st == 'завершен':
                    cur_db.execute("UPDATE заказы SET статус = ?, завершен_в = ? WHERE код_заказа = ?", (new_st, now_s, code))
                    cur_db.execute("SELECT баллы_использованы FROM заказы WHERE код_заказа = ?", (code,))
                    pts_u = cur_db.fetchone()[0]
                    
                    if pts_u == 0:
                        earned_pts = tot_p * 0.05
                        cur_db.execute("UPDATE пользователи SET бонусный_баланс = бонусный_баланс + ? WHERE логин = ?", (earned_pts, u_log))
                        cur_db.execute("UPDATE заказы SET баллы_заработаны = ? WHERE код_заказа = ?", (earned_pts, code))
                else:
                    cur_db.execute("UPDATE заказы SET статус = ? WHERE код_заказа = ?", (new_st, code))

                c_db.commit()
                c_db.close()
                self.show_client_main_layout("orders")

            if status == 'создан':
                btn = tk.Button(btn_frame, text="Принять заказ", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat",
                                command=lambda c=o_code, ul=u_login, tp=t_price: update_order_status(c, 'принят', ul, tp))
                btn.pack()
            elif status == 'принят':
                btn = tk.Button(btn_frame, text="Готовить", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat",
                                command=lambda c=o_code, ul=u_login, tp=t_price: update_order_status(c, 'готовится', ul, tp))
                btn.pack()
            elif status == 'готовится':
                btn = tk.Button(btn_frame, text="Заказ готов", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat",
                                command=lambda c=o_code, ul=u_login, tp=t_price: update_order_status(c, 'готов', ul, tp))
                btn.pack()
            elif status == 'готов':
                btn = tk.Button(btn_frame, text="Заказ выдан", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat",
                                command=lambda c=o_code, ul=u_login, tp=t_price: update_order_status(c, 'завершен', ul, tp))
                btn.pack()

        conn.close()

    def render_menu_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        user_role = self.current_user['role']
        is_admin_group = user_role in ['администратор', 'супер_администратор']

        tk.Label(scrollable_frame, text="Меню кофейни", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 10))

        search_entry = PlaceholderEntry(scrollable_frame, placeholder="Поиск по меню...", font=(UI_FONT, 11), bg=ENTRY_BG, fg=DARK_TEXT)
        search_entry.pack(fill="x", pady=(0, 10))

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()
        cursor.execute("SELECT дата_добавления FROM меню")
        all_dates = cursor.fetchall()
        conn.close()

        now_dt = datetime.now()
        thirty_days_ago = now_dt - timedelta(days=30)
        has_novelties = False
        for (d_str,) in all_dates:
            if d_str:
                try:
                    d_add = datetime.strptime(d_str, "%Y-%m-%d %H:%M:%S")
                    if d_add >= thirty_days_ago:
                        has_novelties = True
                        break
                except Exception:
                    pass

        cat_bar = tk.Frame(scrollable_frame, bg=BG_COLOR)
        cat_bar.pack(anchor="w", pady=(0, 10))

        selected_subcat = tk.StringVar(value="все")

        def filter_cat(scat):
            selected_subcat.set(scat)
            refresh_items_display()

        btn_all = tk.Button(cat_bar, text="Все", bg=NAV_ACTIVE_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", command=lambda: filter_cat("все"))
        btn_all.pack(side="left", padx=3)
        btn_drink = tk.Button(cat_bar, text="☕ Напитки", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", command=lambda: filter_cat("напиток"))
        btn_drink.pack(side="left", padx=3)
        btn_food = tk.Button(cat_bar, text="🍰 Десерты", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", command=lambda: filter_cat("еда"))
        btn_food.pack(side="left", padx=3)

        if has_novelties:
            btn_novelty = tk.Button(cat_bar, text="✨ Новинки", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", command=lambda: filter_cat("новинки"))
            btn_novelty.pack(side="left", padx=3)

        if is_admin_group:
            acw = self.content_width(760)
            add_card = tk.Canvas(scrollable_frame, width=acw, height=80, bg=BG_COLOR, highlightthickness=0, cursor="hand2")
            add_card.pack(pady=10)
            self.card_add = create_rounded_transparent_card(acw, 80, 18, CARD_HEX, 180)
            add_card.create_image(0, 0, anchor="nw", image=self.card_add)
            add_card.create_text(acw // 2, 40, text="[ + ]  Добавить новый товар", font=(UI_FONT, 14, "bold"), fill=DARK_TEXT)
            add_card.bind("<Button-1>", lambda e: self.open_product_modal())

        products_container = tk.Frame(scrollable_frame, bg=BG_COLOR)
        products_container.pack(fill="both", expand=True)

        def refresh_items_display(*args):
            for w in products_container.winfo_children():
                w.destroy()

            query_text = search_entry.get_clean().lower()
            subcat = selected_subcat.get()

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, название, описание, базовая_цена, категория, путь_к_картинке, объемы_json, дата_добавления FROM меню")
            items = cursor.fetchall()
            conn.close()

            filtered_items = []
            for item_id, name, desc, base_price, category, img_path, vols_json, date_added_str in items:
                is_novelty = False
                if date_added_str:
                    try:
                        d_add = datetime.strptime(date_added_str, "%Y-%m-%d %H:%M:%S")
                        if d_add >= thirty_days_ago:
                            is_novelty = True
                    except Exception:
                        pass

                if subcat == "новинки" and not is_novelty:
                    continue
                if subcat == "напиток" and category != "напиток":
                    continue
                if subcat == "еда" and category != "еда":
                    continue

                if query_text:
                    if query_text not in name.lower() and query_text not in (desc or "").lower():
                        continue

                filtered_items.append((item_id, name, desc, base_price, category, img_path, vols_json, is_novelty))

            if not filtered_items:
                tk.Label(products_container, text="Товары не найдены", font=(UI_FONT, 12, "italic"), fg="#D8B69F", bg=BG_COLOR).pack(pady=20)
                return

            for item_id, name, desc, base_price, category, img_path, vols_json, is_novelty in filtered_items:
                card_frame = tk.Frame(products_container, bg="#3D2923", bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=15, pady=15)
                card_frame.pack(fill="x", expand=True, pady=10)

                if is_admin_group:
                    top_btns = tk.Frame(card_frame, bg="#3D2923")
                    top_btns.pack(anchor="ne")

                    btn_edit = tk.Button(top_btns, text="✏", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), width=3, command=lambda i_id=item_id: self.open_product_modal(i_id))
                    btn_edit.pack(side="left", padx=2)

                    def delete_item_confirm(i_id=item_id, n=name):
                        if messagebox.askyesno("Удаление", f"Уверены ли вы, что хотите удалить позицию {n}?"):
                            c = sqlite3.connect("coffee_shop.db")
                            cur = c.cursor()
                            cur.execute("DELETE FROM меню WHERE id = ?", (i_id,))
                            c.commit()
                            c.close()
                            self.show_client_main_layout("menu")

                    btn_del = tk.Button(top_btns, text="✖", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), width=3, command=delete_item_confirm)
                    btn_del.pack(side="left", padx=2)

                if is_novelty:
                    tk.Label(card_frame, text="✨ НОВИНКА ✨", font=(UI_FONT, 9, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w", pady=(0, 2))

                if img_path and os.path.exists(img_path):
                    img = Image.open(img_path).resize((100, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    lbl_img = tk.Label(card_frame, image=photo, bg="#3D2923")
                    lbl_img.image = photo
                    lbl_img.pack(side="left", padx=(0, 15))
                else:
                    icon_symbol = img_path if img_path in ["☕", "🍰"] else ("☕" if category == "напиток" else "🍰")
                    lbl_img = tk.Label(card_frame, text=icon_symbol, font=(UI_FONT, 36), bg="#3D2923", fg=TEXT_COLOR)
                    lbl_img.pack(side="left", padx=(0, 15))

                info_frame = tk.Frame(card_frame, bg="#3D2923")
                info_frame.pack(side="left", fill="both", expand=True)

                tk.Label(info_frame, text=name, font=(UI_FONT, 14, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
                tk.Label(info_frame, text=f"Состав: {desc}", font=(UI_FONT, 9), fg="#D8B69F", bg="#3D2923", wraplength=max(260, min(self.winfo_width() - 360, 640)), justify="left").pack(anchor="w", pady=2)

                volumes_list = []
                if vols_json:
                    try:
                        volumes_list = json.loads(vols_json)
                    except Exception:
                        pass

                if not volumes_list:
                    default_vol = "300 мл" if category == "напиток" else "150 г"
                    volumes_list = [{"vol": default_vol, "price": base_price}]

                price_var = tk.DoubleVar(value=volumes_list[0]['price'])
                volume_var = tk.StringVar(value=volumes_list[0]['vol'])

                lbl_price = tk.Label(info_frame, text=f"Цена: {volumes_list[0]['price']:.0f} руб.", font=(UI_FONT, 12, "bold"), fg=LIGHT_GOLD, bg="#3D2923")
                lbl_price.pack(anchor="w", pady=2)

                if len(volumes_list) > 1:
                    vol_frame = tk.Frame(info_frame, bg="#3D2923")
                    vol_frame.pack(anchor="w", pady=5)

                    vol_label_txt = "Объем / Порция: "
                    tk.Label(vol_frame, text=vol_label_txt, font=(UI_FONT, 9), fg=TEXT_COLOR, bg="#3D2923").pack(side="left")

                    vol_options = [v['vol'] for v in volumes_list]
                    vol_cb = ttk.Combobox(vol_frame, values=vol_options, state="readonly", width=12)
                    vol_cb.set(vol_options[0])
                    vol_cb.pack(side="left")

                    def update_dynamic_price(event, cb=vol_cb, v_list=volumes_list, p_lbl=lbl_price, p_v=price_var, v_v=volume_var):
                        sel_v = cb.get()
                        v_v.set(sel_v)
                        for item_v in v_list:
                            if item_v['vol'] == sel_v:
                                p_v.set(item_v['price'])
                                p_lbl.config(text=f"Цена: {item_v['price']:.0f} руб.")
                                break

                    vol_cb.bind("<<ComboboxSelected>>", update_dynamic_price)

                def add_to_cart(i_id=item_id, n=name, v_var=volume_var, p_var=price_var):
                    vol = v_var.get()
                    price = p_var.get()
                    for c_item in self.cart:
                        if c_item['item_id'] == i_id and c_item['volume'] == vol:
                            c_item['quantity'] += 1
                            vol_str = f" ({vol})" if vol else ""
                            messagebox.showinfo("Корзина", f"Количество '{n}{vol_str}' увеличено!")
                            return
                    self.cart.append({'item_id': i_id, 'name': n, 'volume': vol, 'price': price, 'quantity': 1})
                    vol_str = f" ({vol})" if vol else ""
                    messagebox.showinfo("Корзина", f"'{n}{vol_str}' добавлено в корзину!")

                btn_add = tk.Button(info_frame, text="Добавить в корзину", bg=BTN_BG, fg=TEXT_COLOR,
                                    font=(UI_FONT, 10, "bold"), relief="flat", cursor="hand2", command=add_to_cart)
                btn_add.pack(anchor="w", pady=(5, 0))

        search_entry.bind("<KeyRelease>", refresh_items_display)
        refresh_items_display()

    def open_product_modal(self, product_id=None):
        modal = tk.Toplevel(self)
        modal.title("Редактирование товара" if product_id else "Добавить новый товар")
        modal.geometry("520x700")
        modal.configure(bg=BG_COLOR)
        modal.grab_set()

        icon_or_path = tk.StringVar(value="☕")
        category_var = tk.StringVar(value="напиток")

        btn_icon = tk.Button(modal, text="☕ Выбрать категорию или иконку", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"))
        btn_icon.pack(pady=10)

        def select_icon_menu():
            menu = tk.Menu(modal, tearoff=0)
            menu.add_command(label="Выбрать картинку из устройства", command=lambda: set_device_image())
            menu.add_command(label="☕ Напитки (чашка)", command=lambda: set_emoji("☕", "напиток"))
            menu.add_command(label="🍰 Десерты (торт)", command=lambda: set_emoji("🍰", "еда"))
            menu.post(btn_icon.winfo_rootx(), btn_icon.winfo_rooty() + btn_icon.winfo_height())

        def set_device_image():
            f_path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
            if f_path:
                icon_or_path.set(f_path)
                btn_icon.config(text=f"Картинка: {os.path.basename(f_path)}")

        def set_emoji(emoji, cat):
            icon_or_path.set(emoji)
            category_var.set(cat)
            btn_icon.config(text=f"Категория: { 'Напитки' if cat == 'напиток' else 'Десерты' } ({emoji})")

        btn_icon.config(command=select_icon_menu)

        entry_name = PlaceholderEntry(modal, placeholder="Добавить название", bg=ENTRY_BG, fg=DARK_TEXT)
        entry_name.pack(fill="x", padx=30, pady=5)

        entry_desc = PlaceholderEntry(modal, placeholder="Добавить состав товара", bg=ENTRY_BG, fg=DARK_TEXT)
        entry_desc.pack(fill="x", padx=30, pady=5)

        vols_container = tk.Frame(modal, bg=BG_COLOR)
        vols_container.pack(fill="x", padx=30, pady=10)

        vol_rows = []

        def add_vol_row(default_v="", default_p="", default_unit="мл"):
            r_frame = tk.Frame(vols_container, bg=BG_COLOR)
            r_frame.pack(fill="x", pady=3)

            e_p = PlaceholderEntry(r_frame, placeholder="Цена товара", bg=ENTRY_BG, fg=DARK_TEXT, width=12)
            e_p.pack(side="left", padx=2)
            if default_p:
                e_p.delete(0, tk.END)
                e_p.insert(0, str(default_p))
                e_p.config(fg=DARK_TEXT)

            e_v = PlaceholderEntry(r_frame, placeholder="Объем / Значение", bg=ENTRY_BG, fg=DARK_TEXT, width=14)
            e_v.pack(side="left", padx=2)
            if default_v:
                v_num = default_v.split()[0] if ' ' in default_v else default_v
                e_v.delete(0, tk.END)
                e_v.insert(0, v_num)
                e_v.config(fg=DARK_TEXT)

            unit_cb = ttk.Combobox(r_frame, values=["мл", "г", "мг", "шт"], state="readonly", width=5)
            unit_cb.set(default_unit)
            unit_cb.pack(side="left", padx=2)

            btn_del_r = tk.Button(r_frame, text="✖", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"))
            btn_del_r.pack(side="left", padx=5)

            vol_rows.append((r_frame, e_v, unit_cb, e_p, btn_del_r))

            def remove_row(rf=r_frame):
                for item in vol_rows:
                    if item[0] == rf:
                        vol_rows.remove(item)
                        rf.destroy()
                        break
                update_del_btns()

            btn_del_r.config(command=remove_row)
            update_del_btns()

        def update_del_btns():
            show = len(vol_rows) >= 2
            for rf, ev, ucb, ep, bd in vol_rows:
                if show:
                    bd.pack(side="left", padx=5)
                else:
                    bd.pack_forget()

        if product_id:
            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute("SELECT название, описание, базовая_цена, категория, путь_к_картинке, объемы_json FROM меню WHERE id = ?", (product_id,))
            pdata = cursor.fetchone()
            conn.close()
            if pdata:
                entry_name.delete(0, tk.END)
                entry_name.insert(0, pdata[0])
                entry_name.config(fg=DARK_TEXT)

                entry_desc.delete(0, tk.END)
                entry_desc.insert(0, pdata[1])
                entry_desc.config(fg=DARK_TEXT)

                category_var.set(pdata[3])
                icon_or_path.set(pdata[4])
                cat_name = "Напитки" if pdata[3] == "напиток" else "Десерты"
                btn_icon.config(text=f"Категория: {cat_name} ({pdata[4]})")
                
                v_list = []
                if pdata[5]:
                    try:
                        v_list = json.loads(pdata[5])
                    except Exception:
                        pass
                if v_list:
                    for vi in v_list:
                        v_str = vi['vol']
                        u_str = "мл"
                        for unit in ["мл", "г", "мг", "шт"]:
                            if unit in v_str:
                                u_str = unit
                                break
                        add_vol_row(v_str, vi['price'], u_str)
                else:
                    add_vol_row("300 мл", pdata[2], "мл")
        else:
            add_vol_row()

        btn_add_extra = tk.Button(modal, text="[ + ] Добавить дополнительный объем", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), command=lambda: add_vol_row())
        btn_add_extra.pack(pady=5)

        def save_product():
            p_name = entry_name.get_clean()
            p_desc = entry_desc.get_clean()

            if not p_name:
                messagebox.showwarning("Ошибка", "Заполните название товара!")
                return

            vols_data = []
            for rf, ev, ucb, ep, bd in vol_rows:
                v_val = ev.get_clean()
                p_val = ep.get_clean()
                unit_val = ucb.get()
                if v_val and p_val:
                    try:
                        p_num = float(p_val)
                        full_vol_str = f"{v_val} {unit_val}"
                        vols_data.append({"vol": full_vol_str, "price": p_num})
                    except ValueError:
                        pass

            if not vols_data:
                messagebox.showwarning("Ошибка", "Заполните хотя бы один объем и цену!")
                return

            base_price = vols_data[0]['price']
            vols_json_str = json.dumps(vols_data, ensure_ascii=False)
            current_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            if product_id:
                cursor.execute('''
                    UPDATE меню SET название = ?, описание = ?, базовая_цена = ?, категория = ?, путь_к_картинке = ?, объемы_json = ?
                    WHERE id = ?
                ''', (p_name, p_desc, base_price, category_var.get(), icon_or_path.get(), vols_json_str, product_id))
            else:
                cursor.execute('''
                    INSERT INTO меню (название, описание, базовая_цена, категория, путь_к_картинке, объемы_json, дата_добавления)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (p_name, p_desc, base_price, category_var.get(), icon_or_path.get(), vols_json_str, current_timestamp))
            conn.commit()
            conn.close()

            modal.destroy()
            self.show_client_main_layout("menu")

        btn_save = tk.Button(modal, text="ОК", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 11, "bold"), width=12, command=save_product)
        btn_save.pack(pady=15)

    def render_loyalty_tab(self, parent):
        w, h = 420, 450
        canvas = tk.Canvas(parent, width=w, height=h, bg=BG_COLOR, highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor="center")

        card_bg = create_rounded_transparent_card(w, h, radius=35, hex_color=CARD_HEX, alpha=220)
        canvas.create_image(0, 0, anchor="nw", image=card_bg)

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()
        cursor.execute("SELECT бонусный_баланс, штрихкод FROM пользователи WHERE логин = ?", (self.current_user['login'],))
        row = cursor.fetchone()
        conn.close()

        balance = row[0] if row else 0.0
        barcode_str = row[1] if row and row[1] else "200000000000"

        user_role = self.current_user['role']
        is_admin_group = user_role in ['администратор', 'супер_администратор']

        if is_admin_group:
            title_txt = "Клубная карта (Администратор)"
            status_txt = "Статус: Администрация (Скидка 100%)"
        elif user_role == 'бариста':
            title_txt = "Клубная карта (Сотрудник)"
            status_txt = "Статус: Сотрудник (Скидка 100%)"
        else:
            title_txt = "Карта лояльности"
            status_txt = f"Баланс баллов: {balance:.0f} B"

        canvas.create_text(w // 2, 40, text=title_txt, font=(UI_FONT, 16, "bold"), fill=DARK_TEXT)
        canvas.create_text(w // 2, 85, text=status_txt, font=(UI_FONT, 13, "bold"), fill=LIGHT_GOLD)

        bc_frame = tk.Frame(canvas, bg="#FFFFFF", width=340, height=150, bd=2, relief="solid")
        canvas.create_window(w // 2, 210, window=bc_frame)

        bc_canvas = tk.Canvas(bc_frame, bg="white", width=320, height=130, highlightthickness=0)
        bc_canvas.pack(expand=True, pady=5)
        
        random.seed(barcode_str)
        curr_x = 15
        bc_canvas.create_rectangle(curr_x, 10, curr_x + 2, 95, fill="black", outline="")
        curr_x += 4
        bc_canvas.create_rectangle(curr_x, 10, curr_x + 2, 95, fill="black", outline="")
        curr_x += 6

        while curr_x < 285:
            line_w = random.choice([1, 2, 3, 4])
            if random.choice([True, True, False]):
                bc_canvas.create_rectangle(curr_x, 10, curr_x + line_w, 95, fill="black", outline="")
            curr_x += line_w + random.choice([1, 2, 3])

        bc_canvas.create_rectangle(285, 10, 287, 95, fill="black", outline="")
        bc_canvas.create_rectangle(289, 10, 291, 95, fill="black", outline="")
        random.seed()

        bc_canvas.create_text(160, 112, text=barcode_str, font=("Courier", 13, "bold"), fill="black")
        canvas.create_text(w // 2, 315, text="Индивидуальный штрих-код", font=(UI_FONT, 10, "bold"), fill=DARK_TEXT)

        desc_str = "Штрих-код служебной карты дает 100% скидку." if user_role in ['бариста', 'администратор', 'супер_администратор'] else \
                   "Покажите штрих-код бариста при покупке вне приложения:\n• Кэшбек 5% на карту\n• В приложении баллы начисляются автоматически"
        canvas.create_text(w // 2, 375, text=desc_str, font=(UI_FONT, 9, "bold"), fill="#210D06", justify="center")

    def render_cart_tab(self, parent):
        user_role = self.current_user['role']

        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=(10, 0))
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        active_orders = []
        if user_role == 'клиент':
            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            cursor.execute('''
                SELECT код_заказа, статус, создан_в, готов_в, отменен_в 
                FROM заказы 
                WHERE логин_пользователя = ? AND статус NOT IN ('скрыт_истекший', 'завершен') 
                ORDER BY id DESC
            ''', (self.current_user['login'],))
            active_orders = cursor.fetchall()
            conn.close()

            if active_orders:
                tk.Label(scrollable_frame, text="Отслеживание ваших заказов", font=(UI_FONT, 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 10))
                for order_code, status, created_at, ready_at, cancelled_at in active_orders:
                    self.render_single_order_card(scrollable_frame, order_code, status)

                tk.Label(scrollable_frame, text="Содержимое корзины", font=(UI_FONT, 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(20, 10))

        if not self.cart:
            if user_role != 'клиент' or not active_orders:
                lbl_empty = tk.Label(scrollable_frame, text="В данный момент корзина пуста", font=(UI_FONT, 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR)
                lbl_empty.pack(pady=40)
            return

        total_sum = 0
        for idx, item in enumerate(self.cart):
            item_total = item['price'] * item['quantity']
            total_sum += item_total

            card = tk.Frame(scrollable_frame, bg="#3D2923", bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=15, pady=10)
            card.pack(fill="x", expand=True, pady=5)

            vol_str = f" ({item['volume']})" if item['volume'] else ""
            tk.Label(card, text=f"{item['name']}{vol_str}", font=(UI_FONT, 12, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
            tk.Label(card, text=f"Цена: {item_total:.0f} руб. ({item['price']:.0f} руб/шт)", font=(UI_FONT, 10), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w")

            ctrl_frame = tk.Frame(card, bg="#3D2923")
            ctrl_frame.pack(anchor="w", pady=5)

            def change_qty(index=idx, delta=1):
                self.cart[index]['quantity'] += delta
                if self.cart[index]['quantity'] <= 0:
                    self.cart.pop(index)
                self.show_client_main_layout("cart")

            def delete_entire_item(index=idx):
                self.cart.pop(index)
                self.show_client_main_layout("cart")

            btn_minus = tk.Button(ctrl_frame, text="-", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=3, command=lambda i=idx: change_qty(i, -1))
            btn_minus.pack(side="left")

            tk.Label(ctrl_frame, text=f"  {item['quantity']}  ", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(side="left")

            btn_plus = tk.Button(ctrl_frame, text="+", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), width=3, command=lambda i=idx: change_qty(i, 1))
            btn_plus.pack(side="left")

            btn_del = tk.Button(ctrl_frame, text="Удалить из корзины", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", command=lambda i=idx: delete_entire_item(i))
            btn_del.pack(side="left", padx=15)

        bottom_checkout = tk.Frame(parent, bg="#33211B", padx=10, pady=10)
        bottom_checkout.pack(side="bottom", fill="x")

        is_employee_group = user_role in ['бариста', 'администратор', 'супер_администратор']
        display_total = 0 if is_employee_group else total_sum
        sum_str = f"Итого к оплате: {display_total:.0f} руб. (Скидка 100%)" if is_employee_group else f"Итого к оплате: {total_sum:.0f} руб."

        lbl_total = tk.Label(bottom_checkout, text=sum_str, font=(UI_FONT, 14, "bold"), fg=LIGHT_GOLD, bg="#33211B")
        lbl_total.pack(pady=5)

        btn_checkout = tk.Button(bottom_checkout, text="Сделать заказ", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"),
                                 relief="flat", cursor="hand2", command=lambda: self.open_checkout_modal(total_sum))
        btn_checkout.pack(pady=5, fill="x")

    def render_single_order_card(self, parent_frame, order_code, status):
        card = tk.Frame(parent_frame, bg="#3D2923", bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=15, pady=10)
        card.pack(fill="x", expand=True, pady=5)

        status_text_map = {
            'создан': "Создан (Ожидает подтверждения)",
            'принят': "Заказ принят",
            'готовится': "Готовится",
            'готов': "Заказ готов!",
            'отменен': "Заказ отменен"
        }

        current_status_str = status_text_map.get(status, status)

        top_line = tk.Frame(card, bg="#3D2923")
        top_line.pack(fill="x")

        tk.Label(top_line, text=f"Заказ #{order_code}", font=(UI_FONT, 13, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(side="left")
        tk.Label(top_line, text=f"Статус: {current_status_str}", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(side="right")

    def open_checkout_modal(self, total_sum):
        user_role = self.current_user['role']
        is_employee_group = user_role in ['бариста', 'администратор', 'супер_администратор']

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()

        cursor.execute("SELECT бонусный_баланс FROM пользователи WHERE логин = ?", (self.current_user['login'],))
        row = cursor.fetchone()
        user_bonus = row[0] if row else 0.0

        cursor.execute('''
            SELECT COUNT(*) FROM заказы 
            WHERE роль_пользователя = 'клиент' 
            AND статус NOT IN ('отменен', 'скрыт_истекший', 'завершен')
        ''')
        client_active_orders_count = cursor.fetchone()[0]

        if client_active_orders_count > 15 and not is_employee_group:
            conn.close()
            messagebox.showerror("Ошибка", "Извините, кофейня перегружена (более 15 активных заказов у клиентов). Попробуйте позже!")
            return

        if client_active_orders_count <= 3:
            prep_time_text = "от 10 минут"
        elif client_active_orders_count <= 5:
            prep_time_text = "от 15 минут"
        elif client_active_orders_count <= 10:
            prep_time_text = "от 20 минут"
        else:
            prep_time_text = "от 30 минут"

        conn.close()

        points_to_use = 0.0
        final_price = 0.0 if is_employee_group else total_sum

        if not is_employee_group and user_bonus > 0:
            max_allowed_points = total_sum * 0.5
            max_can_use = min(user_bonus, max_allowed_points)
            
            if messagebox.askyesno("Списание баллов", f"У вас есть {user_bonus:.0f} B. Списать баллы? (Доступно к списанию максимум 50% от суммы: {max_can_use:.0f} B. При списании новые баллы не начисляются!)"):
                points_to_use = min(max_can_use, total_sum)
                final_price = total_sum - points_to_use

        modal = tk.Toplevel(self)
        modal.title("Оформление заказа")
        modal.geometry("450x420")
        modal.configure(bg=BG_COLOR)
        modal.grab_set()

        tk.Label(modal, text="Выберите адрес кофейни:", font=(UI_FONT, 11, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(pady=(15, 5))

        addresses = [
            "Россия, Московская область, г. Воскресенск, микрорайон Цемгигант, Ленинская ул., 1А",
            "Россия, Москва, ул. Арбат, 10",
            "Россия, Москва, Тверская ул., 4"
        ]

        combo_addr = ttk.Combobox(modal, values=addresses, width=50)
        combo_addr.set(addresses[0])
        combo_addr.pack(pady=5)

        tk.Label(modal, text=f"Приблизительное время приготовления: {prep_time_text}", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR).pack(pady=15)

        price_box = tk.Frame(modal, bg=BG_COLOR)
        price_box.pack(pady=5)

        if points_to_use > 0:
            lbl_old = tk.Label(price_box, text=f"Старая цена: {total_sum:.0f} руб.", font=(UI_FONT, 10, "overstrike"), fg="#A08070", bg=BG_COLOR)
            lbl_old.pack()
            lbl_new = tk.Label(price_box, text=f"Итого к оплате: {final_price:.0f} руб. (Списано {points_to_use:.0f} B)", font=(UI_FONT, 13, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR)
            lbl_new.pack()
        else:
            sum_label_txt = f"Сумма заказа: 0 руб. (Служебная скидка 100%)" if is_employee_group else f"Сумма заказа: {total_sum:.0f} руб."
            tk.Label(price_box, text=sum_label_txt, font=(UI_FONT, 12, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack()

        def confirm_order():
            addr = combo_addr.get().strip()
            if not addr:
                messagebox.showwarning("Ошибка", "Выберите или введите адрес!")
                return

            order_code = generate_order_code()
            conn_order = sqlite3.connect("coffee_shop.db")
            cur_o = conn_order.cursor()

            initial_status = 'создан'
            now_s = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if points_to_use > 0:
                cur_o.execute("UPDATE пользователи SET бонусный_баланс = бонусный_баланс - ? WHERE логин = ?", (points_to_use, self.current_user['login']))

            cur_o.execute('''
                INSERT INTO заказы (код_заказа, логин_пользователя, роль_пользователя, адрес, итоговая_цена, баллы_использованы, статус, создан_в)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_code, self.current_user['login'], user_role, addr, final_price, points_to_use, initial_status, now_s))

            for c_item in self.cart:
                cur_o.execute('''
                    INSERT INTO элементы_заказа (код_заказа, название_товара, объем, цена, количество)
                    VALUES (?, ?, ?, ?, ?)
                ''', (order_code, c_item['name'], c_item['volume'], c_item['price'], c_item['quantity']))

            conn_order.commit()
            conn_order.close()

            self.cart = []
            modal.destroy()
            msg = f"Заказ #{order_code} успешно оформлен!"
            messagebox.showinfo("Успех", msg)
            self.show_client_main_layout("orders" if is_employee_group else "cart")

        btn_txt = "Оплатить клубной картой" if is_employee_group else "Заказать"
        btn_confirm = tk.Button(modal, text=btn_txt, bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 12, "bold"),
                                relief="flat", cursor="hand2", command=confirm_order)
        btn_confirm.pack(pady=20, fill="x", padx=30)

    def render_history_tab(self, parent):
        tk.Label(parent, text="История заказов", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", padx=20, pady=(10, 5))
        
        user_role = self.current_user['role']
        is_admin_group = user_role in ['администратор', 'супер_администратор']

        if is_admin_group or user_role == 'бариста':
            now = datetime.now()
            year_var = tk.IntVar(value=now.year if now.year >= 2026 else 2026)
            month_var = tk.IntVar(value=now.month)

            ctrl_f = tk.Frame(parent, bg=BG_COLOR)
            ctrl_f.pack(anchor="w", padx=20, pady=5)

            btn_cal = tk.Button(ctrl_f, text="📅", font=(UI_FONT, 14), bg=BG_COLOR, fg=TEXT_COLOR, relief="flat", cursor="hand2")
            btn_cal.pack(side="left", padx=(0, 5))

            lbl_date_info = tk.Label(ctrl_f, text="", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR)
            lbl_date_info.pack(side="left", padx=5)

            months_list = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

            container_history = tk.Frame(parent, bg=BG_COLOR)
            container_history.pack(fill="both", expand=True, padx=20, pady=10)

            def load_filtered_history():
                lbl_date_info.config(text=f"Период: {months_list[month_var.get()-1]} {year_var.get()}")
                for w in container_history.winfo_children():
                    w.destroy()

                selected_pattern = f"{year_var.get()}-{month_var.get():02d}-%"

                notebook = ttk.Notebook(container_history)
                notebook.pack(fill="both", expand=True, pady=5)

                tab_gen = tk.Frame(notebook, bg=BG_COLOR)
                tab_emp = tk.Frame(notebook, bg=BG_COLOR)

                notebook.add(tab_gen, text="Общая история заказов")
                notebook.add(tab_emp, text="История заказов сотрудников")

                self.render_scrollable_history_list(tab_gen, role_filter="клиент", month_pattern=selected_pattern)
                self.render_scrollable_history_list(tab_emp, role_filter="employee", month_pattern=selected_pattern)

            btn_cal.config(command=lambda: self.open_date_picker_modal(year_var, month_var, load_filtered_history))
            load_filtered_history()
        else:
            self.render_scrollable_history_list(parent, role_filter="own")

    def render_admin_docs_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        tk.Label(scrollable_frame, text="Документы и отчетность", font=(UI_FONT, 18, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 10))

        now = datetime.now()
        year_var = tk.IntVar(value=now.year if now.year >= 2026 else 2026)
        month_var = tk.IntVar(value=now.month)

        top_filter = tk.Frame(scrollable_frame, bg=BG_COLOR)
        top_filter.pack(anchor="w", pady=5)

        btn_cal = tk.Button(top_filter, text="📅", font=(UI_FONT, 14), bg=BG_COLOR, fg=TEXT_COLOR, relief="flat", cursor="hand2")
        btn_cal.pack(side="left", padx=(0, 5))

        lbl_date_info = tk.Label(top_filter, text="", font=(UI_FONT, 11, "bold"), fg=LIGHT_GOLD, bg=BG_COLOR)
        lbl_date_info.pack(side="left", padx=5)

        notebook = ttk.Notebook(scrollable_frame)
        notebook.pack(fill="both", expand=False, pady=10)
        notebook.config(height=260)

        tab_gen = tk.Frame(notebook, bg=BG_COLOR)
        tab_emp = tk.Frame(notebook, bg=BG_COLOR)

        notebook.add(tab_gen, text="Общая история заказов")
        notebook.add(tab_emp, text="История заказов сотрудников")

        rep_frame = tk.Frame(scrollable_frame, bg="#3D2923", padx=15, pady=15)
        rep_frame.pack(fill="x", pady=15)

        months_list = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

        def load_docs_data():
            selected_pattern = f"{year_var.get()}-{month_var.get():02d}-%"
            lbl_date_info.config(text=f"{months_list[month_var.get()-1]} {year_var.get()}")

            for w in tab_gen.winfo_children():
                w.destroy()
            for w in tab_emp.winfo_children():
                w.destroy()

            self.render_scrollable_history_list(tab_gen, role_filter="клиент", month_pattern=selected_pattern)
            self.render_scrollable_history_list(tab_emp, role_filter="employee", month_pattern=selected_pattern)

            for w in rep_frame.winfo_children():
                w.destroy()

            tk.Label(rep_frame, text=f"Отчетность по продажам за {year_var.get()} год", font=(UI_FONT, 14, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w", pady=(0, 10))

            conn = sqlite3.connect("coffee_shop.db")
            cursor = conn.cursor()
            year_total = 0.0

            for m_idx, m_name in enumerate(months_list, start=1):
                pattern = f"{year_var.get()}-{m_idx:02d}-%"
                cursor.execute("SELECT SUM(итоговая_цена) FROM заказы WHERE статус = 'завершен' AND создан_в LIKE ?", (pattern,))
                m_sum = cursor.fetchone()[0]

                m_box = tk.Frame(rep_frame, bg="#3D2923")
                m_box.pack(fill="x", pady=3)

                sum_str = f"{m_sum:.0f} руб." if m_sum else "-"
                if m_sum:
                    year_total += m_sum

                tk.Label(m_box, text=f"{m_name}: {sum_str}", font=(UI_FONT, 10, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(side="left")

                if m_sum:
                    det_f = tk.Frame(rep_frame, bg="#2B1812", padx=10, pady=5)

                    cursor.execute('''
                        SELECT название_товара, объем, SUM(количество), SUM(цена * количество)
                        FROM элементы_заказа
                        WHERE код_заказа IN (SELECT код_заказа FROM заказы WHERE статус = 'завершен' AND создан_в LIKE ?)
                        GROUP BY название_товара, объем
                    ''', (pattern,))
                    det_items = cursor.fetchall()

                    for iname, ivol, sqty, stotal in det_items:
                        vol_s = f" ({ivol})" if ivol else ""
                        tk.Label(det_f, text=f"{iname}{vol_s} ...... {sqty} шт. , {stotal:.0f} руб.", font=("Courier", 9), fg=TEXT_COLOR, bg="#2B1812").pack(anchor="w")

                    def make_toggle(df=det_f):
                        def toggle():
                            if df.winfo_viewable():
                                df.pack_forget()
                                btn_t.config(text="▼ Развернуть")
                            else:
                                df.pack(fill="x", pady=2, after=m_box)
                                btn_t.config(text="▲ Свернуть")
                        return toggle

                    btn_t = tk.Button(m_box, text="▼ Развернуть", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 8, "bold"), relief="flat")
                    btn_t.config(command=make_toggle(det_f))
                    btn_t.pack(side="right")

            tk.Label(rep_frame, text=f"Всего заработано в {year_var.get()} году: {year_total:.0f} руб.", font=(UI_FONT, 12, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w", pady=(15, 5))

            year_pattern = f"{year_var.get()}-%"
            year_det_f = tk.Frame(rep_frame, bg="#2B1812", padx=10, pady=5)

            cursor.execute('''
                SELECT название_товара, объем, SUM(количество), SUM(цена * количество)
                FROM элементы_заказа
                WHERE код_заказа IN (SELECT код_заказа FROM заказы WHERE статус = 'завершен' AND создан_в LIKE ?)
                GROUP BY название_товара, объем
            ''', (year_pattern,))
            year_items = cursor.fetchall()

            if year_items:
                for iname, ivol, sqty, stotal in year_items:
                    vol_s = f" ({ivol})" if ivol else ""
                    tk.Label(year_det_f, text=f"{iname}{vol_s} ...... {sqty} шт. , {stotal:.0f} руб.", font=("Courier", 9), fg=TEXT_COLOR, bg="#2B1812").pack(anchor="w")
            else:
                tk.Label(year_det_f, text="За данный год нет завершенных продаж", font=(UI_FONT, 9, "italic"), fg="#D8B69F", bg="#2B1812").pack(anchor="w")

            btn_year_toggle = tk.Button(rep_frame, text="▼ Развернуть сводку за весь год", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 9, "bold"), relief="flat", cursor="hand2")

            def toggle_year_summary():
                if year_det_f.winfo_viewable():
                    year_det_f.pack_forget()
                    btn_year_toggle.config(text="▼ Развернуть сводку за весь год")
                else:
                    year_det_f.pack(fill="x", pady=5)
                    btn_year_toggle.config(text="▲ Свернуть сводку за весь год")

            btn_year_toggle.config(command=toggle_year_summary)
            btn_year_toggle.pack(anchor="w", pady=(2, 5))

            conn.close()

        btn_cal.config(command=lambda: self.open_date_picker_modal(year_var, month_var, load_docs_data))
        load_docs_data()

    def render_profile_tab(self, parent):
        canvas = tk.Canvas(parent, bg=BG_COLOR, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._embed_scrollable(canvas, scrollable_frame)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")

        self.bind_mouse_scroll(canvas, canvas)

        conn = sqlite3.connect("coffee_shop.db")
        cursor = conn.cursor()
        cursor.execute("SELECT имя, фамилия, дата_рождения, дата_рождения_заблокирована, телефон FROM пользователи WHERE логин = ?", (self.current_user['login'],))
        u_data = cursor.fetchone()
        conn.close()

        f_name, l_name, b_date, b_locked, phone = u_data if u_data else ("", "", "", 0, "")

        tk.Label(scrollable_frame, text="Личный профиль", font=(UI_FONT, 16, "bold"), fg=TEXT_COLOR, bg=BG_COLOR).pack(anchor="w", pady=(0, 15))

        edit_frame = tk.Frame(scrollable_frame, bg="#3D2923", padx=15, pady=15)
        edit_frame.pack(fill="x", expand=True)

        tk.Label(edit_frame, text=f"Логин аккаунта: {self.current_user['login']}", font=(UI_FONT, 10, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w", pady=(0, 10))

        tk.Label(edit_frame, text="Имя:", fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
        entry_fname = tk.Entry(edit_frame, bg=ENTRY_BG, fg=DARK_TEXT)
        entry_fname.insert(0, f_name)
        entry_fname.pack(fill="x", pady=(0, 10))

        tk.Label(edit_frame, text="Фамилия:", fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
        entry_lname = tk.Entry(edit_frame, bg=ENTRY_BG, fg=DARK_TEXT)
        entry_lname.insert(0, l_name)
        entry_lname.pack(fill="x", pady=(0, 10))

        tk.Label(edit_frame, text="Номер телефона:", fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
        entry_phone = tk.Entry(edit_frame, bg=ENTRY_BG, fg=DARK_TEXT)
        entry_phone.insert(0, phone)
        entry_phone.pack(fill="x", pady=(0, 10))

        tk.Label(edit_frame, text="Дата рождения:", fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w")
        entry_bdate = tk.Entry(edit_frame, bg=ENTRY_BG, fg=DARK_TEXT)
        entry_bdate.insert(0, b_date)

        if b_locked and self.current_user['login'] != 'admin1':
            entry_bdate.config(state="disabled")

        entry_bdate.pack(fill="x", pady=(0, 10))

        def save_profile():
            new_fn = entry_fname.get().strip()
            new_ln = entry_lname.get().strip()
            new_ph = entry_phone.get().strip()
            new_bd = entry_bdate.get().strip()

            conn_p = sqlite3.connect("coffee_shop.db")
            cur_p = conn_p.cursor()

            lock_flag = b_locked
            if not b_locked and new_bd and self.current_user['login'] != 'admin1':
                lock_flag = 1

            try:
                cur_p.execute('''
                    UPDATE пользователи 
                    SET имя = ?, фамилия = ?, телефон = ?, дата_рождения = ?, дата_рождения_заблокирована = ?
                    WHERE логин = ?
                ''', (new_fn, new_ln, new_ph, new_bd, lock_flag, self.current_user['login']))
                conn_p.commit()
                messagebox.showinfo("Успех", "Данные профиля обновлены!")
                self.show_client_main_layout("profile")
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Номер телефона уже используется другим аккаунтом!")
            finally:
                conn_p.close()

        btn_save = tk.Button(edit_frame, text="Сохранить изменения", bg=BTN_PRIMARY, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat", command=save_profile)
        btn_save.pack(pady=10)

        btn_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
        btn_frame.pack(fill="x", pady=20)

        def logout():
            self.current_user = None
            self.cart = []
            self.show_welcome_screen()

        def delete_account():
            if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите удалить учетную запись? Это действие необратимо."):
                conn_d = sqlite3.connect("coffee_shop.db")
                cur_d = conn_d.cursor()
                cur_d.execute("DELETE FROM пользователи WHERE логин = ?", (self.current_user['login'],))
                conn_d.commit()
                conn_d.close()
                messagebox.showinfo("Удаление", "Учетная запись успешно удалена.")
                logout()

        btn_logout = tk.Button(btn_frame, text="Выйти из учетной записи", bg=BTN_BG, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat", command=logout)
        btn_logout.pack(side="left", padx=5)

        if self.current_user['login'] != 'admin1':
            btn_delete = tk.Button(btn_frame, text="Удалить учетную запись", bg=BTN_DANGER, fg=TEXT_COLOR, font=(UI_FONT, 10, "bold"), relief="flat", command=delete_account)
            btn_delete.pack(side="right", padx=5)

    def render_scrollable_history_list(self, parent_frame, role_filter="own", month_pattern=None):
        hist_canvas = tk.Canvas(parent_frame, bg=BG_COLOR, highlightthickness=0, height=220)
        hist_scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=hist_canvas.yview)
        hist_inner_frame = tk.Frame(hist_canvas, bg=BG_COLOR)

        hist_inner_frame.bind("<Configure>", lambda e: hist_canvas.configure(scrollregion=hist_canvas.bbox("all")))
        self._embed_scrollable(hist_canvas, hist_inner_frame)
        hist_canvas.configure(yscrollcommand=hist_scrollbar.set)

        hist_canvas.pack(side="left", fill="both", expand=True)
        hist_scrollbar.pack(side="right", fill="y")
        self.bind_mouse_scroll(hist_canvas, hist_canvas)

        conn_h = sqlite3.connect("coffee_shop.db")
        cur_h = conn_h.cursor()

        query_str = '''
            SELECT код_заказа, создан_в, итоговая_цена, баллы_использованы, баллы_заработаны, логин_пользователя 
            FROM заказы WHERE 1=1
        '''
        params = []

        if role_filter == "own":
            query_str += " AND логин_пользователя = ?"
            params.append(self.current_user['login'])
        elif role_filter == "клиент":
            query_str += " AND роль_пользователя = 'клиент'"
        elif role_filter == "employee":
            query_str += " AND роль_пользователя IN ('бариста', 'администратор', 'супер_администратор')"

        if month_pattern:
            query_str += " AND создан_в LIKE ?"
            params.append(month_pattern)

        query_str += " ORDER BY id DESC"

        cur_h.execute(query_str, params)
        history_orders = cur_h.fetchall()

        if not history_orders:
            tk.Label(hist_inner_frame, text="Заказов пока нет", font=(UI_FONT, 11, "italic"), fg="#D8B69F", bg=BG_COLOR).pack(pady=10)
            conn_h.close()
            return

        for o_code, o_date, o_total, p_used, p_earned, u_login in history_orders:
            h_card = tk.Frame(hist_inner_frame, bg="#3D2923", bd=0, relief="flat", highlightthickness=1, highlightbackground=CARD_BORDER, highlightcolor=CARD_BORDER, padx=10, pady=10)
            h_card.pack(fill="x", pady=5, padx=5)

            display_user = get_user_display_name(cur_h, u_login)
            tk.Label(h_card, text=f"Заказ #{o_code} от {o_date} ({display_user})", font=(UI_FONT, 10, "bold"), fg=LIGHT_GOLD, bg="#3D2923").pack(anchor="w")

            cur_h.execute("SELECT название_товара, объем, цена, количество FROM элементы_заказа WHERE код_заказа = ?", (o_code,))
            o_items = cur_h.fetchall()
            for i_name, i_vol, i_price, i_qty in o_items:
                vol_s = f" ({i_vol})" if i_vol else ""
                tk.Label(h_card, text=f"• {i_name}{vol_s} — {i_price:.0f} руб. x {i_qty} = {i_price*i_qty:.0f} руб.", 
                         font=(UI_FONT, 9), fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w", padx=10)

            tk.Label(h_card, text=f"Сумма заказа: {o_total:.0f} руб.", font=(UI_FONT, 10, "bold"), fg=TEXT_COLOR, bg="#3D2923").pack(anchor="w", pady=(3, 0))

            bonus_str = ""
            if p_used > 0:
                bonus_str += f"Баллы: -{p_used:.0f} B "
            if p_earned > 0:
                bonus_str += f"Баллы: +{p_earned:.0f} B"
            if bonus_str:
                tk.Label(h_card, text=bonus_str, font=(UI_FONT, 9, "italic"), fg="#D8B69F", bg="#3D2923").pack(anchor="w")

        conn_h.close()

if __name__ == "__main__":
    init_db()
    app = CoffeeApp()
    app.mainloop()