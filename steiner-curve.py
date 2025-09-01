import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTabWidget, 
                            QSizePolicy, QSlider, QDoubleSpinBox, QGroupBox, 
                            QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from matplotlib.lines import Line2D

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class SteinerCurve:
    def __init__(self, R=3.0, r=1.0, d=1.0):
        self.set_parameters(R, r, d)
    
    def set_parameters(self, R, r, d):
        if R <= 0 or r <= 0 or d <= 0:
            raise ValueError("Все параметры должны быть положительными")
        if d > r:
            raise ValueError("Расстояние d не может быть больше радиуса r")
        
        self.R = R
        self.r = r
        self.d = d
    
    def calculate_cartesian(self, t_values):
        x = (self.R - self.r) * np.cos(t_values) + self.d * np.cos(((self.R - self.r)/self.r) * t_values)
        y = (self.R - self.r) * np.sin(t_values) - self.d * np.sin(((self.R - self.r)/self.r) * t_values)
        return [Point(x[i], y[i]) for i in range(len(t_values))]
    
    def calculate_polar(self, t_values):
        points = self.calculate_cartesian(t_values)
        r = [np.sqrt(p.x**2 + p.y**2) for p in points]
        theta = [np.arctan2(p.y, p.x) for p in points]
        return r, theta
    
    def calculate_rolling_circle(self, t_values):
        x = (self.R - self.r) * np.cos(t_values)
        y = (self.R - self.r) * np.sin(t_values)
        return x, y

class GraphCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.figure)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ax = None
        self.artists = []
        self.figure.set_facecolor('none')
    
    def setup_axes(self, polar=False):
        self.clear()
        if polar:
            self.ax = self.figure.add_subplot(111, projection='polar')
        else:
            self.ax = self.figure.add_subplot(111)
            self.ax.set_aspect('equal', 'box')
        self.ax.grid(True)
    
    def draw_curve(self, points, color='b', label=None, polar=False):
        if polar:
            theta = [np.arctan2(p.y, p.x) for p in points]
            r = [np.sqrt(p.x**2 + p.y**2) for p in points]
            artist, = self.ax.plot(theta, r, color=color, linewidth=2, label=label)
        else:
            x = [p.x for p in points]
            y = [p.y for p in points]
            artist, = self.ax.plot(x, y, color=color, linewidth=2, label=label)
        self.artists.append(artist)
        return artist
    
    def draw_circle(self, center, radius, **kwargs):
        circle = Circle(center, radius, **kwargs)
        self.ax.add_patch(circle)
        self.artists.append(circle)
        return circle
    
    def draw_point(self, x, y, color='r', markersize=8, label=None):
        artist = Line2D([x], [y], marker='o', 
                       color=color, markersize=markersize, 
                       label=label, linestyle='None')
        self.ax.add_line(artist)
        self.artists.append(artist)
        return artist
    
    def draw_line(self, x1, y1, x2, y2, color='g'):
        artist, = self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=1)
        self.artists.append(artist)
        return artist
    
    def clear(self):
        for artist in self.artists:
            try:
                artist.remove()
            except:
                pass
        self.artists = []
        
        if hasattr(self, 'ax') and self.ax:
            self.ax.clear()
            self.ax.grid(True)
            if not hasattr(self.ax, 'projection'):
                self.ax.set_aspect('equal', 'box')
    
    def set_title(self, title):
        if hasattr(self, 'ax') and self.ax:
            self.ax.set_title(title)
    
    def set_labels(self, xlabel, ylabel):
        if hasattr(self, 'ax') and self.ax and not hasattr(self.ax, 'projection'):
            self.ax.set_xlabel(xlabel)
            self.ax.set_ylabel(ylabel)
    
    def set_limits(self, limit):
        if hasattr(self, 'ax') and self.ax and not hasattr(self.ax, 'projection'):
            self.ax.set_xlim(-limit, limit)
            self.ax.set_ylim(-limit, limit)
    
    def show_legend(self):
        if hasattr(self, 'ax') and self.ax:
            self.ax.legend()

class Animator:
    def __init__(self, curve, cart_canvas, polar_canvas, slider):
        self.curve = curve
        self.cart_canvas = cart_canvas
        self.polar_canvas = polar_canvas
        self.slider = slider
        self.current_step = 0
        self.total_steps = 300
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.setInterval(10)
        self.animation_running = False
        self.points = []
        self.polar_r = []
        self.polar_theta = []
        self.rolling_circle_x = []
        self.rolling_circle_y = []
        self.current_artists = []
    
    def start_animation(self):
        if not self.points:
            if not self.generate_points():
                return False
        
        if not self.animation_running:
            self.animation_running = True
            self.timer.start()
            return True
        return False
    
    def stop_animation(self):
        if self.animation_running:
            self.animation_running = False
            self.timer.stop()
            return True
        return False
    
    def generate_points(self):
        try:
            t_values = np.linspace(0, 2*np.pi, self.total_steps)
            self.points = self.curve.calculate_cartesian(t_values)
            self.polar_r, self.polar_theta = self.curve.calculate_polar(t_values)
            self.rolling_circle_x, self.rolling_circle_y = self.curve.calculate_rolling_circle(t_values)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Ошибка", f"Не удалось рассчитать точки кривой: {str(e)}")
            return False
    
    def update_frame(self):
        if not self.animation_running:
            return
            
        self.current_step = (self.current_step + 1) % self.total_steps
        self.slider.setValue(self.current_step)
        self.draw_current_frame()
    
    def set_frame(self, step):
        self.current_step = step % self.total_steps
        self.draw_current_frame()
    
    def draw_current_frame(self):
        if not self.points or self.current_step >= len(self.points):
            return

        point = self.points[self.current_step]
        
        # Полностью пересоздаём декартов график
        self.cart_canvas.figure.clear()
        ax_cart = self.cart_canvas.figure.add_subplot(111)
        ax_cart.set_aspect('equal', 'box')
        ax_cart.grid(True)
        
        # Отрисовываем всё заново
        ax_cart.plot([p.x for p in self.points], [p.y for p in self.points], 
                    'b', linewidth=2, label='Кривая Штейнера')
        
        # Неподвижная окружность
        circle_fixed = Circle((0, 0), self.curve.R, fill=False, 
                            color='r', linestyle='--',
                            label=f'Неподвижная окружность (R={self.curve.R:.1f})')
        ax_cart.add_patch(circle_fixed)
        
        # Катящаяся окружность
        circle_rolling = Circle((self.rolling_circle_x[self.current_step], 
                               self.rolling_circle_y[self.current_step]),
                               self.curve.r, fill=False, 
                               color='g', linestyle=':',
                               label=f'Катящаяся окружность (r={self.curve.r:.1f})')
        ax_cart.add_patch(circle_rolling)
        
        # Текущая точка
        ax_cart.plot(point.x, point.y, 'ro', markersize=8, 
                    label=f'Текущая точка (d={self.curve.d:.1f})')
        
        # Линия от центра катящейся окружности до точки
        ax_cart.plot([self.rolling_circle_x[self.current_step], point.x],
                    [self.rolling_circle_y[self.current_step], point.y],
                    'g-', linewidth=1)
        
        ax_cart.set_title(f'Кривая Штейнера\nR={self.curve.R:.1f}, r={self.curve.r:.1f}, d={self.curve.d:.1f}')
        ax_cart.set_xlabel('X')
        ax_cart.set_ylabel('Y')
        max_dim = max(self.curve.R + self.curve.r + self.curve.d, 
                     max(abs(p.x) for p in self.points), 
                     max(abs(p.y) for p in self.points))
        ax_cart.set_xlim(-max_dim * 1.2, max_dim * 1.2)
        ax_cart.set_ylim(-max_dim * 1.2, max_dim * 1.2)
        ax_cart.legend()

        # Полностью пересоздаём полярный график
        self.polar_canvas.figure.clear()
        ax_polar = self.polar_canvas.figure.add_subplot(111, projection='polar')
        ax_polar.grid(True)
        
        # Отрисовываем полярный график
        theta = [np.arctan2(p.y, p.x) for p in self.points]
        r = [np.sqrt(p.x**2 + p.y**2) for p in self.points]
        ax_polar.plot(theta, r, 'b', linewidth=2, label='Кривая Штейнера')
        ax_polar.plot(self.polar_theta[self.current_step], 
                     self.polar_r[self.current_step], 
                     'ro', markersize=8, label='Текущая точка')
        ax_polar.set_title(f'Полярные координаты\nR={self.curve.R:.1f}, r={self.curve.r:.1f}, d={self.curve.d:.1f}')
        ax_polar.legend()

        # Обновляем отображение
        self.cart_canvas.draw()
        self.polar_canvas.draw()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Кривая Штейнера")
        self.setGeometry(100, 100, 1000, 800)
        
        # Инициализация компонентов
        self.steiner_curve = SteinerCurve()
        self.cartesian_canvas = GraphCanvas()
        self.polar_canvas = GraphCanvas()
        
        # Создаем слайдер перед созданием аниматора
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 299)  # 300 шагов (0-299)
        
        # Передаем слайдер в аниматор
        self.animator = Animator(self.steiner_curve, self.cartesian_canvas, self.polar_canvas, self.slider)
        
        self.init_ui()
    
    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Панель управления
        control_panel = QGroupBox("Управление")
        control_layout = QVBoxLayout()
        control_panel.setLayout(control_layout)
        control_panel.setMaximumWidth(300)
        
        # Группа параметров
        params_group = QGroupBox("Параметры кривой")
        params_layout = QVBoxLayout()
        params_group.setLayout(params_layout)
        
        # Параметры кривой
        self.R_spin = QDoubleSpinBox()
        self.R_spin.setRange(0.1, 10.0)
        self.R_spin.setValue(self.steiner_curve.R)
        self.R_spin.setSingleStep(0.1)
        self.R_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(QLabel("Радиус неподвижной окружности (R):"))
        params_layout.addWidget(self.R_spin)
        
        self.r_spin = QDoubleSpinBox()
        self.r_spin.setRange(0.1, 10.0)
        self.r_spin.setValue(self.steiner_curve.r)
        self.r_spin.setSingleStep(0.1)
        self.r_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(QLabel("Радиус катящейся окружности (r):"))
        params_layout.addWidget(self.r_spin)
        
        self.d_spin = QDoubleSpinBox()
        self.d_spin.setRange(0.1, 10.0)
        self.d_spin.setValue(self.steiner_curve.d)
        self.d_spin.setSingleStep(0.1)
        self.d_spin.valueChanged.connect(self.update_parameters)
        params_layout.addWidget(QLabel("Расстояние до точки (d):"))
        params_layout.addWidget(self.d_spin)
        
        # Кнопки управления
        self.plot_button = QPushButton("Построить график")
        self.plot_button.clicked.connect(self.plot_curve)
        
        self.animation_button = QPushButton("Старт анимации")
        self.animation_button.clicked.connect(self.toggle_animation)
        
        self.clear_button = QPushButton("Очистить графики")
        self.clear_button.clicked.connect(self.clear_plots)
        
        # Настройка слайдера (уже создан в __init__)
        self.slider.valueChanged.connect(self.animator.set_frame)
        
        # Добавление элементов на панель
        control_layout.addWidget(params_group)
        control_layout.addWidget(self.plot_button)
        control_layout.addWidget(self.animation_button)
        control_layout.addWidget(self.clear_button)
        control_layout.addWidget(QLabel("Ручное управление анимацией:"))
        control_layout.addWidget(self.slider)
        control_layout.addStretch()
        
        # Вкладки с графиками
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.cartesian_canvas, "Декартова система")
        self.tab_widget.addTab(self.polar_canvas, "Полярная система")
        
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.tab_widget)
    
    def update_parameters(self):
        try:
            R = self.R_spin.value()
            r = self.r_spin.value()
            d = self.d_spin.value()
            
            if d > r:
                QMessageBox.warning(self, "Ошибка", "Расстояние d не может быть больше радиуса r")
                self.d_spin.setValue(min(d, r))
                return
            
            self.steiner_curve.set_parameters(R, r, d)
            
            if self.animator.animation_running:
                was_running = self.animator.stop_animation()
                self.animation_button.setText("Старт анимации")
            
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
    
    def plot_curve(self):
        self.update_parameters()
        
        if self.animator.generate_points():
            self.animator.current_step = 0
            self.slider.setValue(0)
            self.animator.draw_current_frame()
    
    def toggle_animation(self):
        if not self.animator.points:
            if not self.animator.generate_points():
                return
            
        if self.animator.animation_running:
            if self.animator.stop_animation():
                self.animation_button.setText("Старт анимации")
        else:
            if self.animator.start_animation():
                self.animation_button.setText("Стоп анимации")
    
    def clear_plots(self):
        if self.animator.animation_running:
            self.animator.stop_animation()
            self.animation_button.setText("Старт анимации")
        
        self.animator.current_step = 0
        self.slider.setValue(0)
        
        # Полностью очищаем графики
        self.cartesian_canvas.figure.clear()
        self.polar_canvas.figure.clear()
        self.cartesian_canvas.draw()
        self.polar_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())