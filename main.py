"""Offline desktop app: python main.py (Python 3.10+, Tk)."""
import bisect
import csv
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font
from physics import Parameters, RHO, MU, G, simulate, vacuum, vacuum_time, terminal_speed, terminal_reached_time

BG = '#f4f6fa'
INK = '#17263c'
BLUE = '#2563eb'
ORANGE = '#f59e0b'
SHAPES = {'구': 'sphere', '정육면체': 'cube', '유선형체': 'streamlined'}


class App:
    def __init__(self, root):
        self.root = root
        root.title('공기저항 시뮬레이션 - air resistance simulation')
        root.geometry('1180x820')
        root.minsize(940, 720)
        root.configure(bg=BG)
        families = set(font.families(root))
        self.font = next((name for name in ('Malgun Gothic', 'Apple SD Gothic Neo',
                         'Noto Sans CJK KR', 'NanumGothic') if name in families),
                         font.nametofont('TkDefaultFont').actual('family'))
        for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont'):
            font.nametofont(name).configure(family=self.font, size=10)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TLabel', background=BG, foreground=INK, font=(self.font, 11))
        style.configure('TButton', font=(self.font, 11), padding=8)
        style.configure('Title.TLabel', font=(self.font, 23, 'bold'))
        self.data = None
        self.playing = False
        self.animation = None
        self.mailbox = queue.Queue()
        header = ttk.Frame(root, padding=(24, 18))
        header.pack(fill='x')
        ttk.Label(header, text='공기저항 시뮬레이션', style='Title.TLabel').pack(anchor='w')
        body = ttk.Frame(root, padding=(24, 0, 24, 12))
        body.pack(fill='both', expand=True)
        left = ttk.Frame(body, width=240)
        left.pack(side='left', fill='y', padx=(0, 20))
        ttk.Label(left, text='실험 조건', font=(self.font, 14, 'bold')).pack(anchor='w', pady=(0, 12))
        self.shape = tk.StringVar(value='구')
        ttk.Label(left, text='물체 형상').pack(anchor='w')
        box = ttk.Combobox(left, textvariable=self.shape, values=list(SHAPES), state='readonly', width=24)
        box.pack(fill='x', pady=(4, 10))
        box.bind('<<ComboboxSelected>>', self.shape_changed)
        self.fields = {}
        for key, label, value in [('speed', '초기 속력 (m/s)', '25'), ('mass', '질량 (kg)', '0.2'),
                                  ('size', '지름 (m)', '0.1'), ('angle', '발사각 (°)', '45'),
                                  ('height', '발사 높이 (m)', '1.5')]:
            lab = ttk.Label(left, text=label)
            lab.pack(anchor='w')
            if key == 'size':
                self.size_label = lab
            var = tk.StringVar(value=value)
            self.fields[key] = var
            ttk.Entry(left, textvariable=var, width=25).pack(fill='x', pady=(4, 10))
        self.run_button = ttk.Button(left, text='시뮬레이션 실행 →', command=self.run)
        self.run_button.pack(fill='x', pady=(6, 8))
        self.export_button = ttk.Button(left, text='결과 CSV 저장', command=self.export, state='disabled')
        self.export_button.pack(fill='x')
        ttk.Label(left, text=f'건조 공기 · 298 K · 1 atm\nρ = {RHO:.4f} kg/m³\nμ = {MU:.3g} Pa·s\ng = {G} m/s²', justify='left').pack(anchor='w', pady=18)
        ttk.Button(left, text='모델과 가정 보기', command=self.about).pack(fill='x')
        right = ttk.Frame(body)
        right.pack(side='left', fill='both', expand=True)
        self.summary = ttk.Label(right, text='조건을 입력하고 실험을 시작하세요.', font=(self.font, 11, 'bold'), wraplength=780)
        self.summary.pack(anchor='w', pady=(0, 8))
        self.terminal_label = ttk.Label(right, text='', wraplength=780)
        self.terminal_label.pack(anchor='w', pady=(0, 8))
        self.chart = tk.Canvas(right, background='white', highlightthickness=0, height=340)
        self.chart.pack(fill='both', expand=True)
        self.chart.bind('<Configure>', lambda e: self.draw())
        controls = ttk.Frame(right)
        controls.pack(fill='x', pady=8)
        self.play_button = ttk.Button(controls, text='▶ 재생', command=self.toggle, state='disabled')
        self.play_button.pack(side='left')
        self.progress = tk.DoubleVar(value=100)
        ttk.Scale(controls, from_=0, to=100, variable=self.progress, command=lambda v: self.draw()).pack(side='left', fill='x', expand=True, padx=10)
        self.clock = ttk.Label(controls, text='0.00 s', width=18)
        self.clock.pack(side='left')
        ttk.Label(right, text='초기 역학적 에너지의 분배', font=(self.font, 13, 'bold')).pack(anchor='w', pady=(6, 4))
        self.energy = tk.Canvas(right, background='white', highlightthickness=0, height=143)
        self.energy.pack(fill='x')
        self.energy.bind('<Configure>', lambda e: self.draw())
        self.status = ttk.Label(root, text='오프라인 실행 · 외부 패키지 불필요', padding=(24, 8), wraplength=1100)
        self.status.pack(fill='x')
        root.after(100, self.poll)
        root.after(150, self.run)

    def shape_changed(self, event=None):
        self.size_label.configure(text={'구': '지름 (m)', '정육면체': '한 변의 길이 (m)', '유선형체': '장축 전체 길이 (m)'}[self.shape.get()])

    def stop(self):
        self.playing = False
        if self.animation is not None:
            self.root.after_cancel(self.animation)
            self.animation = None
        self.play_button.configure(text='▶ 재생')

    def run(self):
        if str(self.run_button['state']) == 'disabled':
            return
        try:
            p = Parameters(shape=SHAPES[self.shape.get()], **{k: float(v.get()) for k, v in self.fields.items()})
            p.validate()
        except ValueError as exc:
            messagebox.showerror('입력 확인', str(exc))
            return
        self.stop()
        self.play_button.configure(state='disabled')
        self.run_button.configure(state='disabled')
        self.export_button.configure(state='disabled')
        self.status.configure(text='계산 중…')
        def work():
            try:
                self.mailbox.put((p, simulate(p), None))
            except Exception as exc:
                self.mailbox.put((p, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        try:
            p, data, error = self.mailbox.get_nowait()
        except queue.Empty:
            pass
        else:
            self.run_button.configure(state='normal')
            if error:
                self.status.configure(text='계산 실패: ' + error)
                if self.data:
                    self.play_button.configure(state='normal')
                    self.export_button.configure(state='normal')
            else:
                self.p, self.data = p, data
                self.times = [q.t for q in data]
                end = data[-1]
                vt = vacuum_time(p)
                self.vacuum_data = [vacuum(p, vt*i/200) for i in range(201)]
                apex = max(q.y for q in data)
                self.summary.configure(text=f'궤적 비교   |   비행시간 {end.t:.2f} s   ·   사거리 {end.x:.2f} m   ·   최고 높이 {apex:.2f} m\n공기저항 없음: 비행시간 {vt:.2f} s · 사거리 {self.vacuum_data[-1].x:.2f} m')
                terminal = terminal_speed(p)
                reached = terminal_reached_time(data, terminal)
                arrival = f'{reached:.2f}초에 도달' if reached is not None else '도달하지 않음'
                self.terminal_label.configure(text=f'종단속도 {terminal:.3f} m/s · {arrival}\n판정 기준: 하강 속력이 종단속도의 ±1% 이내, 수평 속력이 종단속도의 1% 이하')
                self.progress.set(100)
                self.play_button.configure(state='normal')
                self.export_button.configure(state='normal')
                self.status.configure(text='계산 완료 · 결과는 실행 시 입력값 기준입니다. 파란색: 공기저항 있음 / 회색 점선: 공기저항 없음')
                self.draw()
        self.root.after(100, self.poll)

    def selected(self):
        t = self.data[-1].t * self.progress.get()/100
        i = min(bisect.bisect_left(self.times, t), len(self.data)-1)
        return self.data[i], i

    def draw(self):
        if not self.data:
            return
        c = self.chart
        c.delete('all')
        w, h = c.winfo_width(), c.winfo_height()
        if w < 100 or h < 100:
            return
        left, top, right, bottom = 66, 40, w-28, h-45
        xmax = max(self.data[-1].x, self.vacuum_data[-1].x, 1)*1.08
        ymax = max(max(q.y for q in self.data), max(q.y for q in self.vacuum_data), 1)*1.12
        def xy(q):
            return left+q.x/xmax*(right-left), bottom-q.y/ymax*(bottom-top)
        for i in range(6):
            x = left+(right-left)*i/5
            y = bottom-(bottom-top)*i/5
            c.create_line(x, top, x, bottom, fill='#edf0f5')
            c.create_line(left, y, right, y, fill='#edf0f5')
            c.create_text(x, bottom+16, text=f'{xmax*i/5:.1f}', fill=INK)
            c.create_text(left-9, y, text=f'{ymax*i/5:.1f}', anchor='e', fill=INK)
        c.create_text(left, 17, text='높이 (m)', anchor='w', fill=INK)
        c.create_text(right, h-10, text='수평 거리 (m)', anchor='e', fill=INK)
        c.create_text(right, 17, text='● 공기저항 있음    ┄ 공기저항 없음', anchor='e', fill=BLUE)
        c.create_line(left, top, left, bottom, right, bottom, fill='#8391a5')
        def line(points, color, dash=None, width=2):
            sampled = points[::max(1, len(points)//1500)]
            if sampled[-1] is not points[-1]:
                sampled.append(points[-1])
            if len(sampled) >= 2:
                c.create_line(*[v for q in sampled for v in xy(q)], fill=color, width=width, dash=dash)
        line(self.vacuum_data, '#94a3b8', (5, 4))
        line(self.data, '#c5d7ff')
        q, i = self.selected()
        line(self.data[:i+1], BLUE, width=3)
        x, y = xy(q)
        c.create_oval(x-6, y-6, x+6, y+6, fill=BLUE, outline='white', width=2)
        self.clock.configure(text=f'{q.t:.2f} / {self.data[-1].t:.2f} s')
        self.draw_energy(q)

    def draw_energy(self, q):
        c = self.energy
        c.delete('all')
        w = c.winfo_width()
        p = self.p
        initial = self.data[0].energy(p.mass)
        kinetic = p.mass*(q.vx*q.vx+q.vy*q.vy)/2
        potential = p.mass*G*q.y
        lost = max(0., initial-kinetic-potential)
        c.create_text(16, 17, text=f'초기 에너지 {initial:.3f} J   →   현재 남은 에너지 {kinetic+potential:.3f} J', anchor='w', fill=INK)
        x, width = 16, max(1, w-32)
        if initial > 0:
            for value, color in [(kinetic, BLUE), (potential, '#10b981'), (lost, ORANGE)]:
                span = width*value/initial
                c.create_rectangle(x, 38, x+span, 69, fill=color, outline='')
                x += span
        else:
            c.create_rectangle(x, 38, x+width, 69, fill='#e5e7eb', outline='')
        for i, (label, value, color) in enumerate([('운동', kinetic, BLUE), ('위치', potential, '#10b981'), ('공기저항 손실', lost, ORANGE)]):
            x = 16+i*(w-32)/3
            percent = 100*value/initial if initial else 0
            c.create_text(x, 87, text=f'● {label}', fill=color, anchor='w')
            c.create_text(x, 110, text=f'{value:.3f} J ({percent:.1f}%)', fill=INK, anchor='w')
        c.create_text(16, 133, text='위치에너지 기준: 지면 y=0 · 손실 = 초기 역학적 에너지 − 현재 역학적 에너지', anchor='w', fill='#64748b', font=(self.font, 9))

    def toggle(self):
        if not self.data:
            return
        if self.playing:
            self.stop()
            return
        self.playing = True
        self.play_button.configure(text='Ⅱ 일시정지')
        if self.progress.get() >= 100:
            self.progress.set(0)
        self.tick()

    def tick(self):
        self.animation = None
        if not self.playing:
            return
        self.progress.set(min(100, self.progress.get()+0.5))
        self.draw()
        if self.progress.get() >= 100:
            self.stop()
        else:
            self.animation = self.root.after(30, self.tick)

    def export(self):
        if not self.data:
            return
        path = filedialog.asksaveasfilename(defaultextension='.csv', initialfile='air_resistance_result.csv', filetypes=[('CSV', '*.csv')])
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['shape', 'size_m', 'mass_kg', 'initial_speed_m_s', 'angle_deg', 'height_m', 'air_density_kg_m3', 'viscosity_Pa_s'])
                p = self.p
                writer.writerow([p.shape, p.size, p.mass, p.speed, p.angle, p.height, RHO, MU])
                writer.writerow(['time_s', 'x_m', 'y_m', 'vx_m_s', 'vy_m_s', 'kinetic_J', 'potential_J', 'lost_J'])
                initial = self.data[0].energy(p.mass)
                for q in self.data:
                    writer.writerow([q.t, q.x, q.y, q.vx, q.vy, p.mass*(q.vx*q.vx+q.vy*q.vy)/2, p.mass*G*q.y, max(0, initial-q.energy(p.mass))])
            self.status.configure(text='CSV 저장 완료: ' + path)
        except OSError as exc:
            messagebox.showerror('저장 실패', str(exc))

    def about(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('모델과 가정')
        dialog.transient(self.root)
        dialog.resizable(False, False)
        panel = ttk.Frame(dialog, padding=20)
        panel.pack(fill='both', expand=True)
        ttk.Label(panel, text='중력과 속도 반대 방향 항력만 고려합니다. 바람·양력·회전·부력은 제외합니다.',
                  wraplength=700).pack(anchor='w', pady=(0, 14))
        equations = tk.Canvas(panel, width=700, height=390, bg='white', highlightthickness=0)
        equations.pack(fill='x')
        normal = font.Font(dialog, family=self.font, size=12)
        small = font.Font(dialog, family=self.font, size=9)
        # Keep font objects alive for the lifetime of the dialog.
        dialog.formula_fonts = (normal, small)

        def formula(y, *terms):
            x = 16
            for term in terms:
                if isinstance(term, str):
                    equations.create_text(x, y, text=term, font=normal, anchor='w', fill=INK)
                    x += normal.measure(term)
                elif term[0] == 'fraction':
                    numerator, denominator = term[1:]
                    width = max(small.measure(numerator), small.measure(denominator)) + 10
                    equations.create_text(x+width/2, y-11, text=numerator, font=small, fill=INK)
                    equations.create_line(x+2, y, x+width-2, y, fill=INK)
                    equations.create_text(x+width/2, y+12, text=denominator, font=small, fill=INK)
                    x += width+3
                elif term[0] in ('subscript', 'superscript'):
                    base, subscript = term[1:]
                    equations.create_text(x, y, text=base, font=normal, anchor='w', fill=INK)
                    x += normal.measure(base)
                    equations.create_text(x, y+(6 if term[0] == 'subscript' else -7), text=subscript, font=small, anchor='w', fill=INK)
                    x += small.measure(subscript)+2

        cd = ('subscript', 'C', 'd')
        fraction = lambda a, b: ('fraction', a, b)
        formula(30, ('subscript', 'F', 'd'), ' = ', fraction('1', '2'), 'ρ A ', cd,
                ' v²     Re = ', fraction('ρvL', 'μ'))
        formula(77, '구:  지름 d,  A = π (', fraction('d', '2'), ')²,  L = d')
        formula(124, 'Re < 1000:  ', cd, ' = ', fraction('24', 'Re'), '(1 + 0.15 ', ('superscript', 'Re', '0.687'), ')')
        formula(171, 'Re ≥ 1000:  ', cd, ' = 0.44')
        formula(218, '정육면체:  A = a²,  L = a,  ', cd, ' = ', fraction('24', 'Re'), ' + 1.05')
        formula(265, '유선형체:  장축 전체 길이 ℓ,  단축 지름 ', fraction('ℓ', '4'))
        formula(312, 'A = π (', fraction('ℓ', '8'), ')²,    L = ', fraction('ℓ', '4'))
        formula(359, cd, ' = ', fraction('24', 'Re'), ' + 0.10')
        ttk.Label(panel, text='허용 범위: 속력 0~100 m/s, 질량 0.0001~10000 kg, 크기 0.0001~10 m, '
                  '각도 −90~90°, 높이 0~10000 m. 극단적 조합은 계산 한도를 초과할 수 있습니다.',
                  wraplength=700).pack(anchor='w', pady=(14, 12))
        ttk.Button(panel, text='닫기', command=dialog.destroy).pack(anchor='e')
        dialog.bind('<Escape>', lambda event: dialog.destroy())
        dialog.grab_set()


if __name__ == '__main__':
    App(tk.Tk())
    tk.mainloop()
