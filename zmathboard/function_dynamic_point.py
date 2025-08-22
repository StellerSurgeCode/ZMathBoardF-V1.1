#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QTextEdit, QGroupBox, QFormLayout,
    QDoubleSpinBox, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QMessageBox, QSlider, QCheckBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush

from .function_plotter import FunctionExpression

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class DynamicPoint(QObject):
    """动点类 - 可以沿着函数轨迹或自定义路径移动"""
    
    position_changed = pyqtSignal(float, float)  # 位置改变信号
    
    def __init__(self, name: str, color: QColor = None):
        super().__init__()
        self.name = name
        self.color = color or QColor(255, 0, 0)
        self.x = 0.0
        self.y = 0.0
        self.visible = True
        self.size = 8
        
        # 动画参数
        self.is_animating = False
        self.animation_type = "function"  # "function", "linear", "circular"
        self.target_function = None
        self.parameter_min = -10.0
        self.parameter_max = 10.0
        self.current_parameter = 0.0
        self.animation_speed = 1.0  # 参数变化速度
        self.animation_direction = 1  # 1为正向，-1为反向
        self.loop_animation = True
        
        # 轨迹记录
        self.trail_points = []
        self.max_trail_length = 100
        self.show_trail = False
        
        # 测量功能
        self.distance_to_origin = 0.0
        self.distance_to_point = None
        self.measurement_target = None
        
        # 数据记录
        self.record_data = False
        self.position_history = []  # (x, y, time)
        self.distance_history = []  # 距离历史
        self.speed_history = []     # 速度历史
        self.parameter_history = []  # 参数历史
    
    def set_function_trajectory(self, function: FunctionExpression, t_min: float = -10, t_max: float = 10):
        """设置函数轨迹"""
        self.animation_type = "function"
        self.target_function = function
        self.parameter_min = t_min
        self.parameter_max = t_max
        self.current_parameter = t_min
    
    def set_linear_trajectory(self, start_point: Tuple[float, float], end_point: Tuple[float, float]):
        """设置线性轨迹"""
        self.animation_type = "linear"
        self.start_point = start_point
        self.end_point = end_point
        self.parameter_min = 0.0
        self.parameter_max = 1.0
        self.current_parameter = 0.0
    
    def set_circular_trajectory(self, center: Tuple[float, float], radius: float):
        """设置圆形轨迹"""
        self.animation_type = "circular"
        self.center = center
        self.radius = radius
        self.parameter_min = 0.0
        self.parameter_max = 2 * math.pi
        self.current_parameter = 0.0
    
    def update_position(self):
        """根据当前参数更新位置"""
        try:
            if self.animation_type == "function" and self.target_function:
                self.x = self.current_parameter
                self.y = self.target_function.evaluate(self.x)
                
            elif self.animation_type == "linear":
                t = self.current_parameter
                self.x = self.start_point[0] + t * (self.end_point[0] - self.start_point[0])
                self.y = self.start_point[1] + t * (self.end_point[1] - self.start_point[1])
                
            elif self.animation_type == "circular":
                t = self.current_parameter
                self.x = self.center[0] + self.radius * math.cos(t)
                self.y = self.center[1] + self.radius * math.sin(t)
            
            # 更新轨迹
            if self.show_trail:
                self.trail_points.append((self.x, self.y))
                if len(self.trail_points) > self.max_trail_length:
                    self.trail_points.pop(0)
            
            # 更新测量值
            self.update_measurements()
            
            # 发出位置变化信号
            self.position_changed.emit(self.x, self.y)
            
        except Exception as e:
            print(f"更新动点位置时出错: {e}")
    
    def update_measurements(self):
        """更新测量值"""
        # 到原点的距离
        self.distance_to_origin = math.sqrt(self.x**2 + self.y**2)
        
        # 到指定点的距离
        if self.measurement_target:
            dx = self.x - self.measurement_target[0]
            dy = self.y - self.measurement_target[1]
            self.distance_to_point = math.sqrt(dx**2 + dy**2)
    
    def animate_step(self, dt: float):
        """动画步进"""
        if not self.is_animating:
            return
        
        # 更新参数
        param_range = self.parameter_max - self.parameter_min
        step = self.animation_speed * dt * self.animation_direction
        
        self.current_parameter += step
        
        # 处理边界
        if self.loop_animation:
            if self.current_parameter > self.parameter_max:
                self.current_parameter = self.parameter_min
            elif self.current_parameter < self.parameter_min:
                self.current_parameter = self.parameter_max
        else:
            if self.current_parameter > self.parameter_max:
                self.current_parameter = self.parameter_max
                self.animation_direction = -1
            elif self.current_parameter < self.parameter_min:
                self.current_parameter = self.parameter_min
                self.animation_direction = 1
        
        # 更新位置
        old_x, old_y = self.x, self.y
        self.update_position()
        
        # 记录数据
        if self.record_data:
            import time
            current_time = time.time()
            
            # 记录位置
            self.position_history.append((self.x, self.y, current_time))
            
            # 记录参数
            self.parameter_history.append(self.current_parameter)
            
            # 计算并记录距离
            distance = math.sqrt(self.x**2 + self.y**2)  # 到原点距离
            self.distance_history.append(distance)
            
            # 计算并记录速度
            if len(self.position_history) > 1:
                dx = self.x - old_x
                dy = self.y - old_y
                dt_actual = current_time - self.position_history[-2][2] if len(self.position_history) > 1 else dt
                speed = math.sqrt(dx**2 + dy**2) / max(dt_actual, 0.001)  # 避免除零
                self.speed_history.append(speed)
            else:
                self.speed_history.append(0.0)
            
            # 限制历史记录长度
            max_history = 1000
            if len(self.position_history) > max_history:
                self.position_history = self.position_history[-max_history:]
                self.distance_history = self.distance_history[-max_history:]
                self.speed_history = self.speed_history[-max_history:]
                self.parameter_history = self.parameter_history[-max_history:]

class DynamicPointManager:
    """动点管理器"""
    
    def __init__(self):
        self.points = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate_all_points)
        self.animation_interval = 50  # 毫秒
        self.last_time = 0
        self.is_playing = False
        self.is_paused = False
    
    def add_point(self, point: DynamicPoint):
        """添加动点"""
        self.points.append(point)
    
    def remove_point(self, point: DynamicPoint):
        """移除动点"""
        if point in self.points:
            self.points.remove(point)
    
    def start_animation(self):
        """开始动画"""
        import time
        self.last_time = time.time()
        self.is_playing = True
        self.is_paused = False
        self.timer.start(self.animation_interval)
    
    def pause_animation(self):
        """暂停动画"""
        if self.is_playing and not self.is_paused:
            self.is_paused = True
            self.timer.stop()
    
    def resume_animation(self):
        """恢复动画"""
        if self.is_playing and self.is_paused:
            import time
            self.last_time = time.time()  # 重置时间以避免时间跳跃
            self.is_paused = False
            self.timer.start(self.animation_interval)
    
    def stop_animation(self):
        """停止动画"""
        self.is_playing = False
        self.is_paused = False
        self.timer.stop()
    
    def toggle_animation(self):
        """切换动画播放状态"""
        if self.is_playing:
            if self.is_paused:
                self.resume_animation()
            else:
                self.pause_animation()
        else:
            self.start_animation()
    
    def animate_all_points(self):
        """动画所有点"""
        import time
        current_time = time.time()
        dt = current_time - self.last_time
        self.last_time = current_time
        
        for point in self.points:
            if point.is_animating:
                point.animate_step(dt)

class DynamicPointDialog(QDialog):
    """动点设置对话框"""
    
    point_created = pyqtSignal(object)  # 动点创建信号
    
    def __init__(self, functions: List[FunctionExpression], parent=None):
        super().__init__(parent)
        self.functions = functions
        self.preview_point = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置user界面"""
        self.setWindowTitle("动点设置")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("动点设置")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 基本设置选项卡
        self.create_basic_settings_tab(tab_widget)
        
        # 轨迹设置选项卡
        self.create_trajectory_tab(tab_widget)
        
        # 动画设置选项卡
        self.create_animation_tab(tab_widget)
        
        # 测量设置选项卡
        self.create_measurement_tab(tab_widget)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        preview_button = QPushButton("预览")
        preview_button.clicked.connect(self.preview_point_settings)
        button_layout.addWidget(preview_button)
        
        create_button = QPushButton("创建动点")
        create_button.clicked.connect(self.create_dynamic_point)
        button_layout.addWidget(create_button)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: 楷体, KaiTi;
            }
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c3e50;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
    
    def create_basic_settings_tab(self, tab_widget):
        """创建基本设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 基本属性
        basic_group = QGroupBox("基本属性")
        basic_layout = QFormLayout(basic_group)
        
        self.name_input = QLineEdit("动点1")
        basic_layout.addRow("名称:", self.name_input)
        
        self.color_button = QPushButton("选择颜色")
        self.current_color = QColor(255, 0, 0)
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}")
        self.color_button.clicked.connect(self.choose_color)
        basic_layout.addRow("颜色:", self.color_button)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(4, 20)
        self.size_spin.setValue(8)
        basic_layout.addRow("大小:", self.size_spin)
        
        layout.addWidget(basic_group)
        
        # 轨迹显示
        trail_group = QGroupBox("轨迹设置")
        trail_layout = QFormLayout(trail_group)
        
        self.show_trail_check = QCheckBox("显示轨迹")
        trail_layout.addRow("", self.show_trail_check)
        
        self.trail_length_spin = QSpinBox()
        self.trail_length_spin.setRange(10, 500)
        self.trail_length_spin.setValue(100)
        trail_layout.addRow("轨迹长度:", self.trail_length_spin)
        
        layout.addWidget(trail_group)
        layout.addStretch()
        
        tab_widget.addTab(widget, "基本设置")
    
    def create_trajectory_tab(self, tab_widget):
        """创建轨迹设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 轨迹类型
        type_group = QGroupBox("轨迹类型")
        type_layout = QVBoxLayout(type_group)
        
        self.trajectory_combo = QComboBox()
        self.trajectory_combo.addItem("函数轨迹", "function")
        self.trajectory_combo.addItem("线性轨迹", "linear")
        self.trajectory_combo.addItem("圆形轨迹", "circular")
        self.trajectory_combo.currentTextChanged.connect(self.on_trajectory_type_changed)
        type_layout.addWidget(self.trajectory_combo)
        
        layout.addWidget(type_group)
        
        # 函数轨迹设置
        self.function_group = QGroupBox("函数轨迹设置")
        function_layout = QFormLayout(self.function_group)
        
        self.function_combo = QComboBox()
        for func in self.functions:
            self.function_combo.addItem(func.name, func)
        function_layout.addRow("选择函数:", self.function_combo)
        
        self.t_min_spin = QDoubleSpinBox()
        self.t_min_spin.setRange(-1000, 1000)
        self.t_min_spin.setValue(-10)
        function_layout.addRow("参数最小值:", self.t_min_spin)
        
        self.t_max_spin = QDoubleSpinBox()
        self.t_max_spin.setRange(-1000, 1000)
        self.t_max_spin.setValue(10)
        function_layout.addRow("参数最大值:", self.t_max_spin)
        
        layout.addWidget(self.function_group)
        
        # 线性轨迹设置
        self.linear_group = QGroupBox("线性轨迹设置")
        linear_layout = QFormLayout(self.linear_group)
        
        self.start_x_spin = QDoubleSpinBox()
        self.start_x_spin.setRange(-1000, 1000)
        linear_layout.addRow("起点X:", self.start_x_spin)
        
        self.start_y_spin = QDoubleSpinBox()
        self.start_y_spin.setRange(-1000, 1000)
        linear_layout.addRow("起点Y:", self.start_y_spin)
        
        self.end_x_spin = QDoubleSpinBox()
        self.end_x_spin.setRange(-1000, 1000)
        self.end_x_spin.setValue(10)
        linear_layout.addRow("终点X:", self.end_x_spin)
        
        self.end_y_spin = QDoubleSpinBox()
        self.end_y_spin.setRange(-1000, 1000)
        self.end_y_spin.setValue(10)
        linear_layout.addRow("终点Y:", self.end_y_spin)
        
        layout.addWidget(self.linear_group)
        
        # 圆形轨迹设置
        self.circular_group = QGroupBox("圆形轨迹设置")
        circular_layout = QFormLayout(self.circular_group)
        
        self.center_x_spin = QDoubleSpinBox()
        self.center_x_spin.setRange(-1000, 1000)
        circular_layout.addRow("圆心X:", self.center_x_spin)
        
        self.center_y_spin = QDoubleSpinBox()
        self.center_y_spin.setRange(-1000, 1000)
        circular_layout.addRow("圆心Y:", self.center_y_spin)
        
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.1, 1000)
        self.radius_spin.setValue(5)
        circular_layout.addRow("半径:", self.radius_spin)
        
        layout.addWidget(self.circular_group)
        layout.addStretch()
        
        # 初始显示
        self.on_trajectory_type_changed()
        
        tab_widget.addTab(widget, "轨迹设置")
    
    def create_animation_tab(self, tab_widget):
        """创建动画设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 动画参数
        anim_group = QGroupBox("动画参数")
        anim_layout = QFormLayout(anim_group)
        
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.1, 10.0)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setDecimals(2)
        anim_layout.addRow("动画速度:", self.speed_spin)
        
        self.loop_check = QCheckBox("循环动画")
        self.loop_check.setChecked(True)
        anim_layout.addRow("", self.loop_check)
        
        self.auto_start_check = QCheckBox("创建后自动开始")
        self.auto_start_check.setChecked(True)
        anim_layout.addRow("", self.auto_start_check)
        
        layout.addWidget(anim_group)
        layout.addStretch()
        
        tab_widget.addTab(widget, "动画设置")
    
    def create_measurement_tab(self, tab_widget):
        """创建测量设置选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 测量选项
        measure_group = QGroupBox("测量选项")
        measure_layout = QVBoxLayout(measure_group)
        
        self.measure_origin_check = QCheckBox("显示到原点的距离")
        self.measure_origin_check.setChecked(True)
        measure_layout.addWidget(self.measure_origin_check)
        
        self.measure_point_check = QCheckBox("显示到指定点的距离")
        measure_layout.addWidget(self.measure_point_check)
        
        # 目标点设置
        target_layout = QFormLayout()
        
        self.target_x_spin = QDoubleSpinBox()
        self.target_x_spin.setRange(-1000, 1000)
        target_layout.addRow("目标点X:", self.target_x_spin)
        
        self.target_y_spin = QDoubleSpinBox()
        self.target_y_spin.setRange(-1000, 1000)
        target_layout.addRow("目标点Y:", self.target_y_spin)
        
        measure_layout.addLayout(target_layout)
        
        layout.addWidget(measure_group)
        layout.addStretch()
        
        tab_widget.addTab(widget, "测量设置")
    
    def on_trajectory_type_changed(self):
        """轨迹类型改变时的处理"""
        trajectory_type = self.trajectory_combo.currentData()
        
        self.function_group.setVisible(trajectory_type == "function")
        self.linear_group.setVisible(trajectory_type == "linear")
        self.circular_group.setVisible(trajectory_type == "circular")
    
    def choose_color(self):
        """选择颜色"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()}")
    
    def preview_point_settings(self):
        """预览点设置"""
        # 这里可以实现预览功能
        QMessageBox.information(self, "预览", "预览功能将在画布上显示动点轨迹")
    
    def create_dynamic_point(self):
        """创建动点"""
        try:
            # 创建动点对象
            point = DynamicPoint(self.name_input.text(), self.current_color)
            point.size = self.size_spin.value()
            point.show_trail = self.show_trail_check.isChecked()
            point.max_trail_length = self.trail_length_spin.value()
            point.animation_speed = self.speed_spin.value()
            point.loop_animation = self.loop_check.isChecked()
            
            # 设置轨迹
            trajectory_type = self.trajectory_combo.currentData()
            
            if trajectory_type == "function":
                if not self.functions:
                    QMessageBox.warning(self, "错误", "没有可用的函数")
                    return
                
                selected_function = self.function_combo.currentData()
                if selected_function:
                    point.set_function_trajectory(
                        selected_function,
                        self.t_min_spin.value(),
                        self.t_max_spin.value()
                    )
                
            elif trajectory_type == "linear":
                point.set_linear_trajectory(
                    (self.start_x_spin.value(), self.start_y_spin.value()),
                    (self.end_x_spin.value(), self.end_y_spin.value())
                )
                
            elif trajectory_type == "circular":
                point.set_circular_trajectory(
                    (self.center_x_spin.value(), self.center_y_spin.value()),
                    self.radius_spin.value()
                )
            
            # 设置测量
            if self.measure_point_check.isChecked():
                point.measurement_target = (self.target_x_spin.value(), self.target_y_spin.value())
            
            # 初始化位置
            point.update_position()
            
            # 设置动画状态
            if self.auto_start_check.isChecked():
                point.is_animating = True
            
            # 发出创建信号
            self.point_created.emit(point)
            
            QMessageBox.information(self, "成功", f"动点 '{point.name}' 创建成功！")
            self.close()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建动点时出错: {str(e)}")

class FunctionAnimationChart(QWidget):
    """函数动画数据图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.points = []  # 监控的动点列表
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        if MATPLOTLIB_AVAILABLE:
            # 创建matplotlib图表
            self.figure = Figure(figsize=(10, 8), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            # 控制面板
            control_group = QGroupBox("图表控制")
            control_layout = QHBoxLayout(control_group)
            
            self.show_position_check = QCheckBox("显示位置轨迹")
            self.show_position_check.setChecked(True)
            self.show_position_check.stateChanged.connect(self.update_chart)
            control_layout.addWidget(self.show_position_check)
            
            self.show_distance_check = QCheckBox("显示距离")
            self.show_distance_check.setChecked(True)
            self.show_distance_check.stateChanged.connect(self.update_chart)
            control_layout.addWidget(self.show_distance_check)
            
            self.show_speed_check = QCheckBox("显示速度")
            self.show_speed_check.setChecked(True)
            self.show_speed_check.stateChanged.connect(self.update_chart)
            control_layout.addWidget(self.show_speed_check)
            
            self.show_parameter_check = QCheckBox("显示参数")
            self.show_parameter_check.setChecked(False)
            self.show_parameter_check.stateChanged.connect(self.update_chart)
            control_layout.addWidget(self.show_parameter_check)
            
            clear_btn = QPushButton("清除数据")
            clear_btn.clicked.connect(self.clear_data)
            control_layout.addWidget(clear_btn)
            
            layout.addWidget(control_group)
            
            # 更新定时器
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self.update_chart)
            self.update_timer.start(500)  # 每500ms更新一次
        else:
            # 没有matplotlib时显示提示
            label = QLabel("需要安装matplotlib才能显示图表\npip install matplotlib")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    
    def add_point(self, point: DynamicPoint):
        """添加要监控的动点"""
        if point not in self.points:
            self.points.append(point)
            point.record_data = True  # 启用数据记录
    
    def remove_point(self, point: DynamicPoint):
        """移除监控的动点"""
        if point in self.points:
            self.points.remove(point)
            point.record_data = False  # 禁用数据记录
    
    def clear_data(self):
        """清除所有数据"""
        for point in self.points:
            point.position_history.clear()
            point.distance_history.clear()
            point.speed_history.clear()
            point.parameter_history.clear()
        self.update_chart()
    
    def update_chart(self):
        """更新图表显示"""
        if not MATPLOTLIB_AVAILABLE:
            return
            
        self.figure.clear()
        
        # 检查是否有数据
        has_data = any(len(point.position_history) > 0 for point in self.points)
        if not has_data:
            return
        
        # 确定子图布局
        show_position = self.show_position_check.isChecked()
        show_distance = self.show_distance_check.isChecked()
        show_speed = self.show_speed_check.isChecked()
        show_parameter = self.show_parameter_check.isChecked()
        
        subplot_count = sum([show_position, show_distance, show_speed, show_parameter])
        if subplot_count == 0:
            return
        
        subplot_index = 1
        
        # 位置轨迹图 (XY散点图)
        if show_position:
            ax = self.figure.add_subplot(2, 2, subplot_index)
            for point in self.points:
                if len(point.position_history) > 0:
                    x_coords = [pos[0] for pos in point.position_history]
                    y_coords = [pos[1] for pos in point.position_history]
                    ax.plot(x_coords, y_coords, marker='o', markersize=2, 
                           label=f"{point.name} 轨迹", alpha=0.7)
                    # 标记起点和终点
                    if len(x_coords) > 0:
                        ax.plot(x_coords[0], y_coords[0], 'go', markersize=6, label=f"{point.name} 起点")
                        ax.plot(x_coords[-1], y_coords[-1], 'ro', markersize=6, label=f"{point.name} 当前")
            ax.set_title("位置轨迹")
            ax.set_xlabel("X 坐标")
            ax.set_ylabel("Y 坐标")
            ax.legend()
            ax.grid(True, alpha=0.3)
            ax.axis('equal')
            subplot_index += 1
        
        # 距离时间图
        if show_distance:
            ax = self.figure.add_subplot(2, 2, subplot_index)
            for point in self.points:
                if len(point.distance_history) > 0:
                    time_steps = list(range(len(point.distance_history)))
                    ax.plot(time_steps, point.distance_history, marker='o', markersize=2,
                           label=f"{point.name} 距离", linewidth=2)
            ax.set_title("距离变化 (到原点)")
            ax.set_xlabel("时间步")
            ax.set_ylabel("距离")
            ax.legend()
            ax.grid(True, alpha=0.3)
            subplot_index += 1
        
        # 速度时间图
        if show_speed:
            ax = self.figure.add_subplot(2, 2, subplot_index)
            for point in self.points:
                if len(point.speed_history) > 0:
                    time_steps = list(range(len(point.speed_history)))
                    ax.plot(time_steps, point.speed_history, marker='o', markersize=2,
                           label=f"{point.name} 速度", linewidth=2)
            ax.set_title("速度变化")
            ax.set_xlabel("时间步")
            ax.set_ylabel("速度")
            ax.legend()
            ax.grid(True, alpha=0.3)
            subplot_index += 1
        
        # 参数时间图
        if show_parameter:
            ax = self.figure.add_subplot(2, 2, subplot_index)
            for point in self.points:
                if len(point.parameter_history) > 0:
                    time_steps = list(range(len(point.parameter_history)))
                    ax.plot(time_steps, point.parameter_history, marker='o', markersize=2,
                           label=f"{point.name} 参数", linewidth=2)
            ax.set_title("参数变化")
            ax.set_xlabel("时间步")
            ax.set_ylabel("参数值")
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        self.figure.tight_layout()
        self.canvas.draw()


class DynamicPointControlPanel(QWidget):
    """动点控制面板"""
    
    def __init__(self, point_manager: DynamicPointManager, parent=None):
        super().__init__(parent)
        self.point_manager = point_manager
        self.chart_widget = None  # 图表窗口
        self.setup_ui()
    
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 动画控制
        control_group = QGroupBox("动画控制")
        control_layout = QHBoxLayout(control_group)
        
        self.play_button = QPushButton("播放")
        self.play_button.clicked.connect(self.toggle_animation)
        control_layout.addWidget(self.play_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_animation)
        control_layout.addWidget(self.stop_button)
        
        self.chart_button = QPushButton("显示图表")
        self.chart_button.clicked.connect(self.show_chart)
        control_layout.addWidget(self.chart_button)
        
        layout.addWidget(control_group)
        
        # 动点列表
        points_group = QGroupBox("动点列表")
        points_layout = QVBoxLayout(points_group)
        
        self.points_list = QListWidget()
        points_layout.addWidget(self.points_list)
        
        layout.addWidget(points_group)
        
        # 测量信息
        measure_group = QGroupBox("测量信息")
        measure_layout = QVBoxLayout(measure_group)
        
        self.measure_text = QTextEdit()
        self.measure_text.setReadOnly(True)
        self.measure_text.setMaximumHeight(100)
        measure_layout.addWidget(self.measure_text)
        
        layout.addWidget(measure_group)
        
        # 更新定时器
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(100)  # 每100ms更新一次
    
    def toggle_animation(self):
        """切换动画状态"""
        if self.point_manager.timer.isActive():
            self.point_manager.stop_animation()
            self.play_button.setText("播放")
        else:
            self.point_manager.start_animation()
            self.play_button.setText("暂停")
    
    def stop_animation(self):
        """停止动画"""
        self.point_manager.stop_animation()
        self.play_button.setText("播放")
    
    def show_chart(self):
        """显示数据图表"""
        if self.chart_widget is None:
            self.chart_widget = FunctionAnimationChart()
            self.chart_widget.setWindowTitle("函数动画数据图表")
            self.chart_widget.resize(1000, 800)
            
            # 添加所有动点到图表
            for point in self.point_manager.points:
                self.chart_widget.add_point(point)
        
        self.chart_widget.show()
        self.chart_widget.raise_()
        self.chart_widget.activateWindow()
    
    def update_display(self):
        """更新显示"""
        # 更新动点列表
        self.points_list.clear()
        for point in self.point_manager.points:
            status = "运行中" if point.is_animating else "已停止"
            item_text = f"{point.name} - {status}"
            self.points_list.addItem(item_text)
        
        # 更新测量信息
        measure_info = ""
        for point in self.point_manager.points:
            measure_info += f"{point.name}:\n"
            measure_info += f"  位置: ({point.x:.3f}, {point.y:.3f})\n"
            measure_info += f"  到原点距离: {point.distance_to_origin:.3f}\n"
            if point.distance_to_point is not None:
                measure_info += f"  到目标点距离: {point.distance_to_point:.3f}\n"
            measure_info += "\n"
        
        self.measure_text.setText(measure_info)
