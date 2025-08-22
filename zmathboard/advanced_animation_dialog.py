#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import sys
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QTextEdit, QGroupBox, QFormLayout,
    QDoubleSpinBox, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QMessageBox, QSlider, QCheckBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QScrollArea, QButtonGroup, QRadioButton, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject, QThread, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPixmap, QIcon

from .geometry import Point, Line
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

# 配置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class PointSelector(QWidget):
    """点选择器组件，用于选择画布上的点"""
    
    selection_changed = pyqtSignal(list)  # 选中的点列表变化信号
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.selected_points = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择移动点:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 点列表
        self.points_list = QListWidget()
        self.points_list.setSelectionMode(QListWidget.MultiSelection)
        self.points_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.points_list)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新点列表")
        refresh_btn.clicked.connect(self.refresh_points)
        layout.addWidget(refresh_btn)
        
        # 初始化点列表
        self.refresh_points()
        
    def refresh_points(self):
        """刷新画布上的点列表"""
        self.points_list.clear()
        self.selected_points.clear()
        
        # 遍历画布上的所有对象，找到点对象
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                item_text = f"点{i}: {obj.name if obj.name else f'({obj.x:.2f}, {obj.y:.2f})'}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (i, obj))  # 存储索引和对象引用
                self.points_list.addItem(item)
                
    def on_selection_changed(self):
        """处理选择变化"""
        self.selected_points.clear()
        for item in self.points_list.selectedItems():
            index, point = item.data(Qt.UserRole)
            self.selected_points.append((index, point))
        
        self.selection_changed.emit(self.selected_points)
        
    def get_selected_points(self):
        """获取选中的点列表"""
        return self.selected_points


class PathSelector(QWidget):
    """路径选择器组件，用于选择移动路径"""
    
    path_changed = pyqtSignal(list)  # 路径变化信号
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.selected_path_points = []
        self.path_lines = []
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择移动路径:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 路径点选择
        path_group = QGroupBox("路径点选择")
        path_layout = QVBoxLayout(path_group)
        
        # 可用点列表
        self.available_points_list = QListWidget()
        self.available_points_list.setMaximumHeight(150)
        path_layout.addWidget(QLabel("可用的点:"))
        path_layout.addWidget(self.available_points_list)
        
        # 按钮组
        btn_layout = QHBoxLayout()
        self.add_to_path_btn = QPushButton("添加到路径")
        self.add_to_path_btn.clicked.connect(self.add_to_path)
        self.remove_from_path_btn = QPushButton("从路径移除")
        self.remove_from_path_btn.clicked.connect(self.remove_from_path)
        btn_layout.addWidget(self.add_to_path_btn)
        btn_layout.addWidget(self.remove_from_path_btn)
        path_layout.addLayout(btn_layout)
        
        # 路径点列表
        self.path_points_list = QListWidget()
        self.path_points_list.setMaximumHeight(150)
        path_layout.addWidget(QLabel("当前路径 (按顺序):"))
        path_layout.addWidget(self.path_points_list)
        
        # 调整顺序按钮
        order_layout = QHBoxLayout()
        self.move_up_btn = QPushButton("上移")
        self.move_up_btn.clicked.connect(self.move_up)
        self.move_down_btn = QPushButton("下移")
        self.move_down_btn.clicked.connect(self.move_down)
        order_layout.addWidget(self.move_up_btn)
        order_layout.addWidget(self.move_down_btn)
        path_layout.addLayout(order_layout)
        
        layout.addWidget(path_group)
        
        # 路径选项
        options_group = QGroupBox("路径选项")
        options_layout = QFormLayout(options_group)
        
        self.closed_path_check = QCheckBox("闭合路径")
        self.closed_path_check.stateChanged.connect(self.on_path_changed)
        options_layout.addRow("", self.closed_path_check)
        
        layout.addWidget(options_group)
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新可用点")
        refresh_btn.clicked.connect(self.refresh_available_points)
        layout.addWidget(refresh_btn)
        
        # 初始化
        self.refresh_available_points()
        
    def refresh_available_points(self):
        """刷新可用的点列表"""
        self.available_points_list.clear()
        
        # 遍历画布上的所有点对象
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                item_text = f"点{i}: {obj.name if obj.name else f'({obj.x:.2f}, {obj.y:.2f})'}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, (i, obj))
                self.available_points_list.addItem(item)
                
    def add_to_path(self):
        """添加点到路径"""
        current_item = self.available_points_list.currentItem()
        if current_item:
            index, point = current_item.data(Qt.UserRole)
            
            # 检查是否已经在路径中
            for existing_index, _ in self.selected_path_points:
                if existing_index == index:
                    QMessageBox.warning(self, "警告", "该点已在路径中")
                    return
            
            # 添加到路径
            self.selected_path_points.append((index, point))
            self.update_path_display()
            self.on_path_changed()
            
    def remove_from_path(self):
        """从路径中移除点"""
        current_row = self.path_points_list.currentRow()
        if current_row >= 0:
            self.selected_path_points.pop(current_row)
            self.update_path_display()
            self.on_path_changed()
            
    def move_up(self):
        """上移路径点"""
        current_row = self.path_points_list.currentRow()
        if current_row > 0:
            # 交换位置
            self.selected_path_points[current_row], self.selected_path_points[current_row-1] = \
                self.selected_path_points[current_row-1], self.selected_path_points[current_row]
            self.update_path_display()
            self.path_points_list.setCurrentRow(current_row - 1)
            self.on_path_changed()
            
    def move_down(self):
        """下移路径点"""
        current_row = self.path_points_list.currentRow()
        if current_row >= 0 and current_row < len(self.selected_path_points) - 1:
            # 交换位置
            self.selected_path_points[current_row], self.selected_path_points[current_row+1] = \
                self.selected_path_points[current_row+1], self.selected_path_points[current_row]
            self.update_path_display()
            self.path_points_list.setCurrentRow(current_row + 1)
            self.on_path_changed()
            
    def update_path_display(self):
        """更新路径显示"""
        self.path_points_list.clear()
        for i, (index, point) in enumerate(self.selected_path_points):
            item_text = f"{i+1}. 点{index}: {point.name if point.name else f'({point.x:.2f}, {point.y:.2f})'}"
            self.path_points_list.addItem(item_text)
            
    def on_path_changed(self):
        """路径改变时的处理"""
        # 生成路径线段
        self.path_lines.clear()
        if len(self.selected_path_points) >= 2:
            for i in range(len(self.selected_path_points) - 1):
                _, point1 = self.selected_path_points[i]
                _, point2 = self.selected_path_points[i + 1]
                # 确保点对象有效
                if hasattr(point1, 'x') and hasattr(point1, 'y') and \
                   hasattr(point2, 'x') and hasattr(point2, 'y'):
                    self.path_lines.append((point1, point2))
                
            # if是闭合路径，添加最后一条边
            if self.closed_path_check.isChecked() and len(self.selected_path_points) >= 3:
                _, first_point = self.selected_path_points[0]
                _, last_point = self.selected_path_points[-1]
                if hasattr(first_point, 'x') and hasattr(first_point, 'y') and \
                   hasattr(last_point, 'x') and hasattr(last_point, 'y'):
                    self.path_lines.append((last_point, first_point))
        
        self.path_changed.emit(self.path_lines)
        
    def get_path_lines(self):
        """获取路径线段列表"""
        return self.path_lines
        
    def get_path_points(self):
        """获取路径点列表"""
        return self.selected_path_points


class MeasurementRecorder(QWidget):
    """测量记录器组件，用于记录长度和面积变化"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.length_measurements = []  # 长度测量配置
        self.area_measurements = []    # 面积测量配置
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 长度记录选项卡
        self.create_length_tab(tab_widget)
        
        # 面积记录选项卡
        self.create_area_tab(tab_widget)
        
        layout.addWidget(tab_widget)
        
    def create_length_tab(self, tab_widget):
        """创建长度记录选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("长度记录设置:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 添加长度测量
        add_group = QGroupBox("添加长度测量")
        add_layout = QVBoxLayout(add_group)
        
        # 点选择
        points_layout = QHBoxLayout()
        self.length_point1_combo = QComboBox()
        self.length_point2_combo = QComboBox()
        points_layout.addWidget(QLabel("起点:"))
        points_layout.addWidget(self.length_point1_combo)
        points_layout.addWidget(QLabel("终点:"))
        points_layout.addWidget(self.length_point2_combo)
        add_layout.addLayout(points_layout)
        
        # 测量名称
        name_layout = QHBoxLayout()
        self.length_name_edit = QLineEdit("长度测量1")
        name_layout.addWidget(QLabel("名称:"))
        name_layout.addWidget(self.length_name_edit)
        add_layout.addLayout(name_layout)
        
        # 添加按钮
        add_length_btn = QPushButton("添加长度测量")
        add_length_btn.clicked.connect(self.add_length_measurement)
        add_layout.addWidget(add_length_btn)
        
        layout.addWidget(add_group)
        
        # 当前测量列表
        current_group = QGroupBox("当前长度测量")
        current_layout = QVBoxLayout(current_group)
        
        self.length_list = QListWidget()
        current_layout.addWidget(self.length_list)
        
        # 删除按钮
        remove_length_btn = QPushButton("删除选中测量")
        remove_length_btn.clicked.connect(self.remove_length_measurement)
        current_layout.addWidget(remove_length_btn)
        
        layout.addWidget(current_group)
        
        # 刷新按钮
        refresh_length_btn = QPushButton("刷新点列表")
        refresh_length_btn.clicked.connect(self.refresh_length_points)
        layout.addWidget(refresh_length_btn)
        
        tab_widget.addTab(widget, "长度记录")
        
        # 初始化点列表
        self.refresh_length_points()
        
    def create_area_tab(self, tab_widget):
        """创建面积记录选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 标题
        title_label = QLabel("面积记录设置:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 添加面积测量
        add_group = QGroupBox("添加面积测量")
        add_layout = QVBoxLayout(add_group)
        
        # 点选择
        self.area_points_list = QListWidget()
        self.area_points_list.setSelectionMode(QListWidget.MultiSelection)
        self.area_points_list.setMaximumHeight(150)
        add_layout.addWidget(QLabel("选择构成多边形的点 (至少3个):"))
        add_layout.addWidget(self.area_points_list)
        
        # 测量名称
        name_layout = QHBoxLayout()
        self.area_name_edit = QLineEdit("面积测量1")
        name_layout.addWidget(QLabel("名称:"))
        name_layout.addWidget(self.area_name_edit)
        add_layout.addLayout(name_layout)
        
        # 添加按钮
        add_area_btn = QPushButton("添加面积测量")
        add_area_btn.clicked.connect(self.add_area_measurement)
        add_layout.addWidget(add_area_btn)
        
        layout.addWidget(add_group)
        
        # 当前测量列表
        current_group = QGroupBox("当前面积测量")
        current_layout = QVBoxLayout(current_group)
        
        self.area_list = QListWidget()
        current_layout.addWidget(self.area_list)
        
        # 删除按钮
        remove_area_btn = QPushButton("删除选中测量")
        remove_area_btn.clicked.connect(self.remove_area_measurement)
        current_layout.addWidget(remove_area_btn)
        
        layout.addWidget(current_group)
        
        # 刷新按钮
        refresh_area_btn = QPushButton("刷新点列表")
        refresh_area_btn.clicked.connect(self.refresh_area_points)
        layout.addWidget(refresh_area_btn)
        
        tab_widget.addTab(widget, "面积记录")
        
        # 初始化点列表
        self.refresh_area_points()
        
    def refresh_length_points(self):
        """刷新长度测量的点列表"""
        self.length_point1_combo.clear()
        self.length_point2_combo.clear()
        
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                text = f"点{i}: {obj.name if obj.name else f'({obj.x:.2f}, {obj.y:.2f})'}"
                self.length_point1_combo.addItem(text, (i, obj))
                self.length_point2_combo.addItem(text, (i, obj))
                
    def refresh_area_points(self):
        """刷新面积测量的点列表"""
        self.area_points_list.clear()
        
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                text = f"点{i}: {obj.name if obj.name else f'({obj.x:.2f}, {obj.y:.2f})'}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, (i, obj))
                self.area_points_list.addItem(item)
                
    def add_length_measurement(self):
        """添加长度测量"""
        if self.length_point1_combo.count() < 2:
            QMessageBox.warning(self, "错误", "至少需要2个点才能测量长度")
            return
            
        point1_data = self.length_point1_combo.currentData()
        point2_data = self.length_point2_combo.currentData()
        
        if not point1_data or not point2_data:
            QMessageBox.warning(self, "错误", "请选择有效的点")
            return
            
        if point1_data[0] == point2_data[0]:
            QMessageBox.warning(self, "错误", "起点和终点不能是同一个点")
            return
            
        measurement = {
            'name': self.length_name_edit.text().strip() or f"长度测量{len(self.length_measurements)+1}",
            'point1': point1_data,
            'point2': point2_data
        }
        
        self.length_measurements.append(measurement)
        self.update_length_list()
        
        # 自动生成下一个名称
        self.length_name_edit.setText(f"长度测量{len(self.length_measurements)+1}")
        
    def add_area_measurement(self):
        """添加面积测量"""
        selected_items = self.area_points_list.selectedItems()
        
        if len(selected_items) < 3:
            QMessageBox.warning(self, "错误", "至少需要选择3个点才能测量面积")
            return
            
        points = []
        for item in selected_items:
            points.append(item.data(Qt.UserRole))
            
        measurement = {
            'name': self.area_name_edit.text().strip() or f"面积测量{len(self.area_measurements)+1}",
            'points': points
        }
        
        self.area_measurements.append(measurement)
        self.update_area_list()
        
        # 自动生成下一个名称
        self.area_name_edit.setText(f"面积测量{len(self.area_measurements)+1}")
        
    def remove_length_measurement(self):
        """删除长度测量"""
        current_row = self.length_list.currentRow()
        if current_row >= 0:
            self.length_measurements.pop(current_row)
            self.update_length_list()
            
    def remove_area_measurement(self):
        """删除面积测量"""
        current_row = self.area_list.currentRow()
        if current_row >= 0:
            self.area_measurements.pop(current_row)
            self.update_area_list()
            
    def update_length_list(self):
        """更新长度测量列表显示"""
        self.length_list.clear()
        for measurement in self.length_measurements:
            _, point1 = measurement['point1']
            _, point2 = measurement['point2']
            text = f"{measurement['name']}: {point1.name or 'P1'} → {point2.name or 'P2'}"
            self.length_list.addItem(text)
            
    def update_area_list(self):
        """更新面积测量列表显示"""
        self.area_list.clear()
        for measurement in self.area_measurements:
            points_text = ', '.join([f"{point.name or f'P{i}'}" for i, (_, point) in enumerate(measurement['points'])])
            text = f"{measurement['name']}: [{points_text}]"
            self.area_list.addItem(text)
            
    def get_length_measurements(self):
        """获取长度测量配置"""
        return self.length_measurements
        
    def get_area_measurements(self):
        """获取面积测量配置"""
        return self.area_measurements


class MotionTypeSelector(QWidget):
    """运动类型选择器组件"""
    
    motion_type_changed = pyqtSignal(str)  # 运动类型变化信号
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("选择运动类型:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 运动类型选择
        self.motion_group = QButtonGroup()
        
        self.path_motion_radio = QRadioButton("路径运动")
        self.path_motion_radio.setChecked(True)
        self.path_motion_radio.toggled.connect(lambda: self.on_motion_type_changed("path"))
        self.motion_group.addButton(self.path_motion_radio)
        layout.addWidget(self.path_motion_radio)
        
        self.circular_motion_radio = QRadioButton("圆周运动")
        self.circular_motion_radio.toggled.connect(lambda: self.on_motion_type_changed("circular"))
        self.motion_group.addButton(self.circular_motion_radio)
        layout.addWidget(self.circular_motion_radio)
        
        # 说明文字
        info_label = QLabel(
            "• 路径运动: 点沿着指定的路径移动\n"
            "• 圆周运动: 点绕着指定圆心做圆周运动"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(info_label)
        
        layout.addStretch()
        
    def on_motion_type_changed(self, motion_type):
        """运动类型改变时的处理"""
        self.motion_type_changed.emit(motion_type)
        
    def get_motion_type(self):
        """获取当前选择的运动类型"""
        if self.path_motion_radio.isChecked():
            return "path"
        elif self.circular_motion_radio.isChecked():
            return "circular"
        return "path"


class CircularMotionSelector(QWidget):
    """圆周运动选择器组件"""
    
    settings_changed = pyqtSignal(dict)  # 圆周运动设置变化信号
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.selected_center = None
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("圆周运动设置:")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(title_label)
        
        # 圆心选择
        center_group = QGroupBox("选择圆心")
        center_layout = QVBoxLayout(center_group)
        
        # 可用点列表
        self.center_points_list = QListWidget()
        self.center_points_list.setMaximumHeight(150)
        self.center_points_list.itemSelectionChanged.connect(self.on_center_selected)
        center_layout.addWidget(QLabel("选择作为圆心的点:"))
        center_layout.addWidget(self.center_points_list)
        
        # 刷新按钮
        refresh_center_btn = QPushButton("刷新点列表")
        refresh_center_btn.clicked.connect(self.refresh_center_points)
        center_layout.addWidget(refresh_center_btn)
        
        layout.addWidget(center_group)
        
        # 运动参数
        params_group = QGroupBox("运动参数")
        params_layout = QFormLayout(params_group)
        
        # 半径显示（只读）
        self.radius_label = QLabel("未计算")
        params_layout.addRow("当前半径:", self.radius_label)
        
        # 角速度设置
        self.angular_speed_spin = QDoubleSpinBox()
        self.angular_speed_spin.setRange(0.1, 10.0)
        self.angular_speed_spin.setValue(1.0)
        self.angular_speed_spin.setDecimals(2)
        self.angular_speed_spin.setSuffix(" rad/s")
        self.angular_speed_spin.valueChanged.connect(self.on_settings_changed)
        params_layout.addRow("角速度:", self.angular_speed_spin)
        
        # 起始角度
        self.start_angle_spin = QDoubleSpinBox()
        self.start_angle_spin.setRange(0.0, 360.0)
        self.start_angle_spin.setValue(0.0)
        self.start_angle_spin.setSuffix("°")
        self.start_angle_spin.valueChanged.connect(self.on_settings_changed)
        params_layout.addRow("起始角度:", self.start_angle_spin)
        
        # 方向选择
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["顺时针", "逆时针"])
        self.direction_combo.currentTextChanged.connect(self.on_settings_changed)
        params_layout.addRow("旋转方向:", self.direction_combo)
        
        layout.addWidget(params_group)
        
        # 当前设置显示
        self.info_label = QLabel("请选择圆心点")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: blue; font-size: 11px; padding: 5px; background-color: #f0f8ff; border: 1px solid #add8e6;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
        # 初始化点列表
        self.refresh_center_points()
        
    def refresh_center_points(self):
        """刷新圆心点列表"""
        self.center_points_list.clear()
        
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                text = f"点{i}: {obj.name if obj.name else f'({obj.x:.1f}, {obj.y:.1f})'}"
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, (i, obj))
                self.center_points_list.addItem(item)
                
    def on_center_selected(self):
        """圆心选择改变时的处理"""
        current_item = self.center_points_list.currentItem()
        if current_item:
            index, point = current_item.data(Qt.UserRole)
            self.selected_center = (index, point)
            self.update_info_display()
            self.on_settings_changed()
        else:
            self.selected_center = None
            self.info_label.setText("请选择圆心点")
            
    def on_settings_changed(self):
        """设置改变时的处理"""
        self.update_info_display()
        
        if self.selected_center:
            settings = self.get_circular_motion_settings()
            self.settings_changed.emit(settings)
            
    def update_info_display(self):
        """更新信息显示"""
        if self.selected_center:
            index, point = self.selected_center
            angular_speed = self.angular_speed_spin.value()
            start_angle = self.start_angle_spin.value()
            direction = self.direction_combo.currentText()
            
            # 计算当前半径（需要在创建动画时提供移动点）
            radius_text = "将根据移动点距离计算"
            self.radius_label.setText(radius_text)
            
            info_text = (
                f"圆心: 点{index} ({point.x:.1f}, {point.y:.1f})\n"
                f"半径: {radius_text}\n"
                f"角速度: {angular_speed:.2f} rad/s\n"
                f"起始角度: {start_angle:.1f}°\n"
                f"方向: {direction}"
            )
            self.info_label.setText(info_text)
        else:
            self.info_label.setText("请选择圆心点")
            self.radius_label.setText("未计算")
            
    def get_circular_motion_settings(self):
        """获取圆周运动设置"""
        if not self.selected_center:
            return None
            
        return {
            'center_point': self.selected_center,
            'radius': None,  # 将在动画管理器中根据移动点计算
            'angular_speed': self.angular_speed_spin.value(),
            'start_angle': math.radians(self.start_angle_spin.value()),
            'direction': 1 if self.direction_combo.currentText() == "逆时针" else -1
        }


class ChartDisplay(QWidget):
    """图表显示组件，用于显示测量数据的折线图"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.length_data = {}  # 长度数据 {name: [values]}
        self.area_data = {}    # 面积数据 {name: [values]}
        self.time_steps = []   # 时间步长
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 创建matplotlib图表
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        # 控制面板
        control_group = QGroupBox("图表控制")
        control_layout = QHBoxLayout(control_group)
        
        self.show_length_check = QCheckBox("显示长度")
        self.show_length_check.setChecked(True)
        self.show_length_check.stateChanged.connect(self.update_chart)
        control_layout.addWidget(self.show_length_check)
        
        self.show_area_check = QCheckBox("显示面积")
        self.show_area_check.setChecked(True)
        self.show_area_check.stateChanged.connect(self.update_chart)
        control_layout.addWidget(self.show_area_check)
        
        clear_btn = QPushButton("清除数据")
        clear_btn.clicked.connect(self.clear_data)
        control_layout.addWidget(clear_btn)
        
        layout.addWidget(control_group)
        
    def add_data_point(self, length_values=None, area_values=None):
        """添加数据点"""
        self.time_steps.append(len(self.time_steps))
        
        if length_values:
            for name, value in length_values.items():
                if name not in self.length_data:
                    self.length_data[name] = []
                self.length_data[name].append(value)
                
        if area_values:
            for name, value in area_values.items():
                if name not in self.area_data:
                    self.area_data[name] = []
                self.area_data[name].append(value)
                
        self.update_chart()
        
    def update_chart(self):
        """更新图表显示"""
        self.figure.clear()
        
        # 决定子图布局
        show_length = self.show_length_check.isChecked() and self.length_data
        show_area = self.show_area_check.isChecked() and self.area_data
        
        if not show_length and not show_area:
            return
            
        if show_length and show_area:
            # 两个子图
            ax1 = self.figure.add_subplot(2, 1, 1)
            ax2 = self.figure.add_subplot(2, 1, 2)
            
            # 绘制长度数据
            for name, values in self.length_data.items():
                if len(values) == len(self.time_steps):
                    ax1.plot(self.time_steps, values, marker='o', label=name, linewidth=2)
            ax1.set_title("长度变化")
            ax1.set_xlabel("时间步")
            ax1.set_ylabel("长度")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 绘制面积数据
            for name, values in self.area_data.items():
                if len(values) == len(self.time_steps):
                    ax2.plot(self.time_steps, values, marker='s', label=name, linewidth=2)
            ax2.set_title("面积变化")
            ax2.set_xlabel("时间步")
            ax2.set_ylabel("面积")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
        elif show_length:
            # 只显示长度
            ax = self.figure.add_subplot(1, 1, 1)
            for name, values in self.length_data.items():
                if len(values) == len(self.time_steps):
                    ax.plot(self.time_steps, values, marker='o', label=name, linewidth=2)
            ax.set_title("长度变化")
            ax.set_xlabel("时间步")
            ax.set_ylabel("长度")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        elif show_area:
            # 只显示面积
            ax = self.figure.add_subplot(1, 1, 1)
            for name, values in self.area_data.items():
                if len(values) == len(self.time_steps):
                    ax.plot(self.time_steps, values, marker='s', label=name, linewidth=2)
            ax.set_title("面积变化")
            ax.set_xlabel("时间步")
            ax.set_ylabel("面积")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def clear_data(self):
        """清除所有数据"""
        self.length_data.clear()
        self.area_data.clear()
        self.time_steps.clear()
        self.update_chart()


class PlaybackControls(QWidget):
    """播放控制器组件"""
    
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    mode_changed = pyqtSignal(str)  # 播放模式变化
    speed_changed = pyqtSignal(float)  # 速度变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_playing = False
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 播放控制按钮
        button_group = QGroupBox("播放控制")
        button_layout = QHBoxLayout(button_group)
        
        self.play_pause_btn = QPushButton("播放")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_playback)
        button_layout.addWidget(self.stop_btn)
        
        layout.addWidget(button_group)
        
        # 播放模式
        mode_group = QGroupBox("播放模式")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_group = QButtonGroup()
        
        self.single_radio = QRadioButton("单次播放")
        self.single_radio.setChecked(True)
        self.single_radio.toggled.connect(lambda: self.on_mode_changed("single"))
        self.mode_group.addButton(self.single_radio)
        mode_layout.addWidget(self.single_radio)
        
        self.loop_radio = QRadioButton("循环播放")
        self.loop_radio.toggled.connect(lambda: self.on_mode_changed("loop"))
        self.mode_group.addButton(self.loop_radio)
        mode_layout.addWidget(self.loop_radio)
        
        self.pingpong_radio = QRadioButton("来回播放")
        self.pingpong_radio.toggled.connect(lambda: self.on_mode_changed("pingpong"))
        self.mode_group.addButton(self.pingpong_radio)
        mode_layout.addWidget(self.pingpong_radio)
        
        layout.addWidget(mode_group)
        
        # 播放参数
        params_group = QGroupBox("播放参数")
        params_layout = QFormLayout(params_group)
        
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 100)  # 0.1x 到 10x
        self.speed_slider.setValue(10)  # 默认1x
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        
        self.speed_label = QLabel("1.0x")
        
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        
        params_layout.addRow("播放速度:", speed_layout)
        
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(100, 10000)
        self.duration_spin.setValue(1000)
        self.duration_spin.setSuffix(" ms")
        params_layout.addRow("动画时长:", self.duration_spin)
        
        layout.addWidget(params_group)
        
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
            
    def start_playback(self):
        """开始播放"""
        self.is_playing = True
        self.play_pause_btn.setText("暂停")
        self.play_requested.emit()
        
    def pause_playback(self):
        """暂停播放"""
        self.is_playing = False
        self.play_pause_btn.setText("播放")
        self.pause_requested.emit()
        
    def stop_playback(self):
        """停止播放"""
        self.is_playing = False
        self.play_pause_btn.setText("播放")
        self.stop_requested.emit()
        
    def on_mode_changed(self, mode):
        """播放模式改变"""
        self.mode_changed.emit(mode)
        
    def on_speed_changed(self, value):
        """播放速度改变"""
        speed = value / 10.0  # 0.1x 到 10x
        self.speed_label.setText(f"{speed:.1f}x")
        self.speed_changed.emit(speed)
        
    def get_duration(self):
        """获取动画持续时间"""
        return self.duration_spin.value()
        
    def get_playback_mode(self):
        """获取播放模式"""
        if self.single_radio.isChecked():
            return "single"
        elif self.loop_radio.isChecked():
            return "loop"
        elif self.pingpong_radio.isChecked():
            return "pingpong"
        return "single"


class AdvancedAnimationDialog(QDialog):
    """高级动画创建对话框"""
    
    animation_created = pyqtSignal(dict)  # 动画创建信号
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle("创建高级动画")
        self.setModal(True)
        self.resize(600, 650)  # 调整为更紧凑的尺寸
        self.setup_ui()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        
        # 点选择选项卡
        self.point_selector = PointSelector(self.canvas)
        tab_widget.addTab(self.point_selector, "选择移动点")
        
        # 运动类型选择选项卡
        self.motion_type_selector = MotionTypeSelector(self.canvas)
        tab_widget.addTab(self.motion_type_selector, "运动类型")
        
        # 路径选择选项卡
        self.path_selector = PathSelector(self.canvas)
        tab_widget.addTab(self.path_selector, "路径运动设置")
        
        # 圆周运动选项卡
        self.circular_motion_selector = CircularMotionSelector(self.canvas)
        tab_widget.addTab(self.circular_motion_selector, "圆周运动设置")
        
        # 测量记录选项卡
        self.measurement_recorder = MeasurementRecorder(self.canvas)
        tab_widget.addTab(self.measurement_recorder, "测量记录")
        
        # 播放控制选项卡
        self.playback_controls = PlaybackControls()
        tab_widget.addTab(self.playback_controls, "播放控制")
        
        layout.addWidget(tab_widget)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("创建动画")
        self.create_btn.clicked.connect(self.create_animation)
        button_layout.addWidget(self.create_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # 创建图表显示但不在主界面显示
        self.chart_display = ChartDisplay()
        
    def create_animation(self):
        """创建动画"""
        # 验证配置
        selected_points = self.point_selector.get_selected_points()
        if not selected_points:
            QMessageBox.warning(self, "错误", "请至少选择一个移动点")
            return
            
        # 获取运动类型
        motion_type = self.motion_type_selector.get_motion_type()
        
        # 根据运动类型验证配置
        if motion_type == "path":
            path_lines = self.path_selector.get_path_lines()
            if not path_lines:
                QMessageBox.warning(self, "错误", "请设置移动路径")
                return
        elif motion_type == "circular":
            circular_settings = self.circular_motion_selector.get_circular_motion_settings()
            if not circular_settings:
                QMessageBox.warning(self, "错误", "请设置圆周运动参数")
                return
            
        # 构建动画配置
        animation_config = {
            'motion_type': motion_type,
            'moving_points': selected_points,
            'length_measurements': self.measurement_recorder.get_length_measurements(),
            'area_measurements': self.measurement_recorder.get_area_measurements(),
            'playback_mode': self.playback_controls.get_playback_mode(),
            'duration': self.playback_controls.get_duration(),
            'chart_display': self.chart_display
        }
        
        # 根据运动类型添加特定配置
        if motion_type == "path":
            animation_config.update({
                'path_lines': self.path_selector.get_path_lines(),
                'path_points': self.path_selector.get_path_points()
            })
        elif motion_type == "circular":
            animation_config.update({
                'circular_settings': circular_settings
            })
        
        # 发送信号并关闭对话框
        self.animation_created.emit(animation_config)
        self.accept()
        
    def get_animation_config(self):
        """获取动画配置"""
        return {
            'moving_points': self.point_selector.get_selected_points(),
            'path_lines': self.path_selector.get_path_lines(),
            'path_points': self.path_selector.get_path_points(),
            'length_measurements': self.measurement_recorder.get_length_measurements(),
            'area_measurements': self.measurement_recorder.get_area_measurements(),
            'playback_mode': self.playback_controls.get_playback_mode(),
            'duration': self.playback_controls.get_duration()
        }
