#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QToolBar, QAction, QLabel, QStatusBar, QSystemTrayIcon,
    QMenu, QDockWidget, QFrame, QPushButton, QComboBox, 
    QSpinBox, QColorDialog, QMessageBox, QToolButton, QGroupBox,
    QApplication, QLineEdit, QCheckBox, QSizePolicy, QFileDialog,
    QInputDialog, QActionGroup, QDoubleSpinBox
)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette, QFont, QCursor, QPainter, QBrush
from PyQt5.QtCore import Qt, QSize, QPoint, QPointF, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QByteArray
from PyQt5.QtSvg import QSvgRenderer

from .canvas import Canvas
from .geometry import Point, Line, PathAnimation, ConnectAnimation
from .draw import show_draw_dialog
from .function_plotter import FunctionCanvas
from .function_dialog import FunctionInputDialog, FunctionManagerDialog
from .function_state_manager import FunctionStateManager, detect_state_type
from .ai_function_dialog import AIFunctionDialog
from .ai_function_chat_dialog import AIFunctionChatDialog
from .function_analyzer import FunctionQueryDialog
from .function_dynamic_point import DynamicPointDialog, DynamicPointManager, DynamicPointControlPanel
from .advanced_animation_dialog import AdvancedAnimationDialog
from .advanced_animation_manager import AdvancedAnimationManager, AnimationControlWidget

class StyleSheet:
    """应用程序样式表定义"""
    
    MAIN_STYLE = """
        * {
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QMainWindow {
            background-color: #f5f5f5;
            border: none;
        }
        
        QToolBar {
            background-color: #f5f5f5;
            border: none;
            spacing: 5px;
            padding: 5px;
        }
        
        QToolButton {
            background-color: transparent;
            border: none;
            color: black;
            padding: 5px;
            border-radius: 3px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QToolButton:hover {
            background-color: #e0e0e0;
        }
        
        QToolButton:checked {
            background-color: #d0d0d0;
        }
        
        QStatusBar {
            background-color: #f5f5f5;
            color: black;
        }
        
        QDockWidget {
            background-color: #f5f5f5;
            border: 1px solid #d0d0d0;
        }
        
        QDockWidget::title {
            background-color: #e0e0e0;
            color: black;
            padding: 5px;
            text-align: center;
        }
        
        QPushButton {
            background-color: #e0e0e0;
            color: black;
            border: none;
            border-radius: 3px;
            padding: 5px 10px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        
        QGroupBox {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            margin-top: 1ex;
            font-weight: bold;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QLabel {
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QSpinBox {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            padding: 2px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QComboBox {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            padding: 2px 10px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        QHeaderView::section {
            background-color: #e0e0e0;
            color: black;
            padding: 5px;
            border: none;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        /* 自定义窗口标题栏 */
        #titleBar {
            background-color: #f5f5f5;
            min-height: 30px;
            border-bottom: 1px solid #d0d0d0;
        }
        
        /* 工具栏标题样式 */
        #titleLabel {
            color: #2c3e50;
            font-weight: bold;
            font-size: 14px;
            font-family: "Microsoft YaHei", "微软雅黑", "Segoe UI", Arial, sans-serif;
            margin-left: 8px;
            padding: 0 10px;
            letter-spacing: 1px;
        }
        
        /* 窗口控制按钮样式 */
        QToolButton[text="－"], QToolButton[text="口"], QToolButton[text="回"], QToolButton[text="×"] {
            font-weight: bold;
            font-size: 14px;
            padding: 3px 8px;
            margin: 0 2px;
            border-radius: 0;
            min-width: 24px;
            min-height: 24px;
        }
        
        QToolButton[text="－"]:hover, QToolButton[text="口"]:hover, QToolButton[text="回"]:hover {
            background-color: #d0d0d0;
        }
        
        #closeButton:hover {
            background-color: #e81123;
            color: white;
        }
        
        QLineEdit {
            border: 1px solid #d0d0d0;
            border-radius: 3px;
            padding: 3px;
            font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
        }
        
        /* 最大化按钮 */
        #maxButton {
            font-family: "Segoe UI Symbol";
            font-size: 16px;
            padding: 4px 8px;
            border: none;
            background-color: transparent;
            color: #333;
        }
        
        #maxButton:hover {
            background-color: #eee;
        }
        
        /* 还原按钮 */
        #restoreButton {
            font-family: "Segoe UI Symbol";
            font-size: 16px;
            padding: 4px 8px;
            border: none;
            background-color: transparent;
            color: #333;
        }
        
        #restoreButton:hover {
            background-color: #eee;
        }
    """

class ZMathJBoardApp(QMainWindow):
    """ZMathJBoardF应用程序主窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 基本窗口设置
        self.setWindowTitle("ZMathJBoardF v1.1")
        self.setMinimumSize(1024, 768)
        self.setWindowFlags(Qt.FramelessWindowHint)  # 无边框窗口
        
        # 应用样式表
        self.setStyleSheet(StyleSheet.MAIN_STYLE)
        
        # 创建系统托盘图标
        self.setup_system_tray()
        
        # 创建主UI
        self.setup_ui()
        
        # 尝试从文件加载多边形属性
        # 多边形属性已通过UI状态管理器处理，无需单独加载
        
        # 拖动功能变量
        self.start = None
        self.pressing = False
        
    def setup_ui(self):
        """设置user界面"""
        # 创建中央部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 设置应用图标
        app_icon_path = os.path.join(os.path.dirname(__file__), 'img/mathb.jpg')
        if os.path.exists(app_icon_path):
            app_icon = QIcon(app_icon_path)
            self.setWindowIcon(app_icon)
            # 设置任务栏图标
            try:
                import ctypes
                myappid = 'ZMathJBoardF.v1.1'  # 应用程序ID
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception:
                pass  # if设置任务栏图标失败，不影响程序运行
        
        # 主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 工具栏（取代标题栏）
        self.create_toolbar()
        
        # 内容区域
        self.content_layout = QHBoxLayout()
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.addLayout(self.content_layout)
        
        # 创建几何画布
        self.geometry_canvas = Canvas()
        
        # 创建函数画布
        self.function_canvas = FunctionCanvas()
        
        # 当前活动画布
        self.current_canvas = self.geometry_canvas
        self.canvas_mode = "geometry"  # "geometry" 或 "function"
        
        # 添加当前画布到布局
        self.content_layout.addWidget(self.current_canvas)
        
        # 为兼容性保持canvas引用
        self.canvas = self.current_canvas
        
        # 创建属性面板
        self.create_properties_panel()
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 连接信号
        self.geometry_canvas.object_selected.connect(self.object_selected)
        self.function_canvas.function_selected.connect(self.function_selected)
        
        # 初始化状态管理器
        self.function_state_manager = FunctionStateManager(self.function_canvas)
        
        # 初始化动点管理器
        self.dynamic_point_manager = DynamicPointManager()
        self.dynamic_control_panel = None
        
        # 初始化高级动画管理器
        self.advanced_animation_manager = AdvancedAnimationManager(self.geometry_canvas)
        self.animation_control_widget = None
        self.current_animation_config = None
        
    def create_toolbar(self):
        """创建工具栏"""
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        # 添加应用图标到工具栏
        app_icon_path = os.path.join(os.path.dirname(__file__), 'img/mathb.jpg')
        if os.path.exists(app_icon_path):
            app_icon_label = QLabel()
            app_icon_pixmap = QPixmap(app_icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            app_icon_label.setPixmap(app_icon_pixmap)
            app_icon_label.setContentsMargins(5, 0, 5, 0)
            self.toolbar.addWidget(app_icon_label)
        
        # 添加应用名称标签
        self.title_label = QLabel("ZMathJBoardF v1.1")
        self.title_label.setObjectName("titleLabel")
        # 可选：直接设置字体
        title_font = QFont("Microsoft YaHei", 10)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.toolbar.addWidget(self.title_label)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        
        # 添加操作工具按钮
        self.tool_group = QActionGroup(self)
        self.tool_group.setExclusive(True)
        
        # 选择工具
        self.select_action = QAction("选择", self)
        self.select_action.setCheckable(True)
        self.select_action.setChecked(True)
        self.select_action.triggered.connect(lambda: self.set_tool("select"))
        self.tool_group.addAction(self.select_action)
        self.toolbar.addAction(self.select_action)
        
        # 点工具
        self.point_action = QAction("点", self)
        self.point_action.setCheckable(True)
        self.point_action.triggered.connect(lambda: self.set_tool("point"))
        self.tool_group.addAction(self.point_action)
        self.toolbar.addAction(self.point_action)
        
        # 线段工具
        self.line_action = QAction("线", self)
        self.line_action.setCheckable(True)
        self.line_action.triggered.connect(lambda: self.set_tool("line"))
        self.tool_group.addAction(self.line_action)
        self.toolbar.addAction(self.line_action)
        
        # 连接工具
        self.connect_action = QAction("连接", self)
        self.connect_action.setCheckable(True)
        self.connect_action.triggered.connect(lambda: self.set_tool("connect"))
        self.tool_group.addAction(self.connect_action)
        self.toolbar.addAction(self.connect_action)
        
        # 绘制工具
        self.draw_action = QAction("绘制", self)
        self.draw_action.triggered.connect(self.show_draw_dialog)
        self.toolbar.addAction(self.draw_action)
        
        # 角度工具
        self.angle_action = QAction("角度", self)
        self.angle_action.triggered.connect(self.show_angle_dialog)
        self.toolbar.addAction(self.angle_action)
        
        # AI绘图助手
        self.ai_action = QAction("AI助手", self)
        self.ai_action.triggered.connect(self.show_ai_dialog)
        self.toolbar.addAction(self.ai_action)
        
        self.toolbar.addSeparator()
        
        # 保存UI状态
        self.save_action = QAction("保存UI状态", self)
        self.save_action.triggered.connect(self.save_canvas)
        self.save_action.setShortcut("Ctrl+S")
        self.toolbar.addAction(self.save_action)
        
        # 加载UI状态
        self.load_action = QAction("加载UI状态", self)
        self.load_action.triggered.connect(self.load_canvas)
        self.load_action.setShortcut("Ctrl+O")
        self.toolbar.addAction(self.load_action)
        
        # 清空画布
        self.clear_action = QAction("清空画布", self)
        self.clear_action.triggered.connect(self.clear_canvas)
        self.clear_action.setShortcut("Ctrl+N")
        self.toolbar.addAction(self.clear_action)
        
        self.toolbar.addSeparator()
        
        # 显示设置菜单
        view_menu = QMenu("显示", self)
        
        # 网格显示控制
        self.grid_action = QAction("显示网格", self)
        self.grid_action.setCheckable(True)
        self.grid_action.setChecked(True)
        self.grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(self.grid_action)
        
        # 吸附控制
        self.snap_action = QAction("启用吸附", self)
        self.snap_action.setCheckable(True)
        self.snap_action.setChecked(True)
        self.snap_action.triggered.connect(self.toggle_snap)
        view_menu.addAction(self.snap_action)
        
        # 点名称显示控制
        self.point_names_action = QAction("显示点名称", self)
        self.point_names_action.setCheckable(True)
        self.point_names_action.setChecked(True)
        self.point_names_action.triggered.connect(self.toggle_point_names)
        view_menu.addAction(self.point_names_action)
        
        # 线段名称显示控制
        self.line_names_action = QAction("显示线段名称", self)
        self.line_names_action.setCheckable(True)
        self.line_names_action.setChecked(True)
        self.line_names_action.triggered.connect(self.toggle_line_names)
        view_menu.addAction(self.line_names_action)
        
        # 交点显示控制
        self.intersections_action = QAction("显示交点", self)
        self.intersections_action.setCheckable(True)
        self.intersections_action.setChecked(True)
        self.intersections_action.triggered.connect(self.toggle_intersections)
        view_menu.addAction(self.intersections_action)
        
        # 角度显示控制
        self.show_angles_action = QAction("显示角度", self)
        self.show_angles_action.setCheckable(True)
        self.show_angles_action.setChecked(True)
        self.show_angles_action.triggered.connect(self.toggle_angles)
        view_menu.addAction(self.show_angles_action)
        
        view_menu.addSeparator()
        
        # 几何检查控制
        self.geometry_check_action = QAction("启用几何检查", self)
        self.geometry_check_action.setCheckable(True)
        self.geometry_check_action.setChecked(True)
        self.geometry_check_action.triggered.connect(self.toggle_geometry_check)
        view_menu.addAction(self.geometry_check_action)
        
        # 自动修复异常
        self.auto_fix_action = QAction("自动修复异常", self)
        self.auto_fix_action.setCheckable(True)
        self.auto_fix_action.setChecked(True)
        self.auto_fix_action.triggered.connect(self.toggle_auto_fix)
        view_menu.addAction(self.auto_fix_action)
        
        # 手动修复所有异常
        self.manual_fix_action = QAction("手动修复所有异常", self)
        self.manual_fix_action.triggered.connect(self.manual_fix_all)
        view_menu.addAction(self.manual_fix_action)
        
        # 角度值显示控制
        self.show_angle_values_action = QAction("显示角度数值", self)
        self.show_angle_values_action.setCheckable(True)
        self.show_angle_values_action.setChecked(True)
        self.show_angle_values_action.triggered.connect(self.toggle_angle_values)
        view_menu.addAction(self.show_angle_values_action)
        
        view_menu.addSeparator()
        
        # 函数画布相关设置
        self.maintain_aspect_ratio_action = QAction("保持长宽比（函数画布）", self)
        self.maintain_aspect_ratio_action.setCheckable(True)
        self.maintain_aspect_ratio_action.setChecked(True)
        self.maintain_aspect_ratio_action.triggered.connect(self.toggle_maintain_aspect_ratio)
        view_menu.addAction(self.maintain_aspect_ratio_action)
        
        # 几何画布相关设置
        self.adaptive_line_scaling_action = QAction("线段长度自适应比例", self)
        self.adaptive_line_scaling_action.setCheckable(True)
        self.adaptive_line_scaling_action.setChecked(True)
        self.adaptive_line_scaling_action.triggered.connect(self.toggle_adaptive_line_scaling)
        view_menu.addAction(self.adaptive_line_scaling_action)
        
        # 添加显示设置按钮
        view_button = QToolButton()
        view_button.setText("显示")
        view_button.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'img/显示.png')))
        view_button.setPopupMode(QToolButton.InstantPopup)
        view_button.setMenu(view_menu)
        view_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toolbar.addWidget(view_button)
        
        self.toolbar.addSeparator()
        
        # 添加画布拖动按钮
        self.canvas_drag_action = QAction("画布拖动", self)
        self.canvas_drag_action.setCheckable(True)
        self.canvas_drag_action.setChecked(False)
        self.canvas_drag_action.triggered.connect(self.toggle_canvas_drag_mode)
        self.toolbar.addAction(self.canvas_drag_action)
        
        self.toolbar.addSeparator()
        
        # 动画控制
        self.play_action = QAction("播放", self)
        self.play_action.triggered.connect(self.play_animations)
        self.toolbar.addAction(self.play_action)
        
        self.stop_action = QAction("停止", self)
        self.stop_action.triggered.connect(self.stop_animations)
        self.toolbar.addAction(self.stop_action)
        
        # 添加弹性空间，将窗口控制按钮推到最右侧
        spacer2 = QWidget()
        spacer2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer2)
        
        # 添加窗口控制按钮到最右侧
        # 最小化按钮
        min_btn = QToolButton()
        min_btn.setText("－")
        min_btn.setToolTip("最小化")
        min_btn.clicked.connect(self.showMinimized)
        self.toolbar.addWidget(min_btn)
        
        # 最大化/还原按钮
        self.max_btn = QToolButton()
        self.max_btn.setObjectName("maxButton")
        # 创建最大化和还原SVG图标
        self.max_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
            <path fill="#333" d="M3 3v10h10V3H3zm1 1h8v8H4V4z"/>
        </svg>"""
        self.restore_svg = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
            <path fill="#333" d="M3 3v3h1V4h2V3H3zm7 0v1h2v2h1V3h-3zm-7 7v3h3v-1H4v-2H3zm10 0v2h-2v1h3v-3h-1z"/>
        </svg>"""
        
        # 设置最大化图标
        max_pixmap = QPixmap(16, 16)
        max_pixmap.fill(Qt.transparent)
        painter = QPainter(max_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer = QSvgRenderer(QByteArray(self.max_svg.encode()))
        renderer.render(painter)
        painter.end()
        self.max_icon = QIcon(max_pixmap)
        
        # 设置还原图标
        restore_pixmap = QPixmap(16, 16)
        restore_pixmap.fill(Qt.transparent)
        painter = QPainter(restore_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer = QSvgRenderer(QByteArray(self.restore_svg.encode()))
        renderer.render(painter)
        painter.end()
        self.restore_icon = QIcon(restore_pixmap)
        
        # 设置初始图标
        self.max_btn.setIcon(self.max_icon)
        self.max_btn.setIconSize(QSize(16, 16))
        self.max_btn.setToolTip("最大化")
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.toolbar.addWidget(self.max_btn)
        
        # 退出按钮
        close_btn = QToolButton()
        close_btn.setText("×")
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.hide)
        close_btn.setObjectName("closeButton")
        self.toolbar.addWidget(close_btn)
        
        # 工具动作组
        self.tool_actions = [self.select_action, self.point_action, self.line_action, self.connect_action]
        
    def create_properties_panel(self):
        """创建属性面板"""
        # 属性面板容器
        self.properties_widget = QWidget()
        self.properties_widget.setFixedWidth(280)
        self.properties_layout = QVBoxLayout(self.properties_widget)
        self.properties_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建属性组
        self.prop_group = QGroupBox("属性")
        self.prop_layout = QVBoxLayout(self.prop_group)
        
        # 对象名称
        self.name_layout = QHBoxLayout()
        self.name_label = QLabel("名称:")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入对象名称")
        self.name_edit.returnPressed.connect(self.update_object_name)
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_edit)
        self.prop_layout.addLayout(self.name_layout)
        
        # 对象类型
        self.type_layout = QHBoxLayout()
        self.type_label = QLabel("类型:")
        self.type_value = QLabel("")
        self.type_layout.addWidget(self.type_label)
        self.type_layout.addWidget(self.type_value)
        self.prop_layout.addLayout(self.type_layout)
        
        # 点属性 - 坐标
        self.point_props_widget = QWidget()
        self.point_props_layout = QVBoxLayout(self.point_props_widget)
        self.point_props_layout.setContentsMargins(0, 0, 0, 0)
        
        self.coord_layout = QHBoxLayout()
        self.x_label = QLabel("X:")
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.valueChanged.connect(self.update_point_position)
        
        self.y_label = QLabel("Y:")
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.valueChanged.connect(self.update_point_position)
        
        self.coord_layout.addWidget(self.x_label)
        self.coord_layout.addWidget(self.x_spin)
        self.coord_layout.addWidget(self.y_label)
        self.coord_layout.addWidget(self.y_spin)
        self.point_props_layout.addLayout(self.coord_layout)
        
        # 点固定选项
        self.point_fixed_cb = QCheckBox("固定位置")
        self.point_fixed_cb.toggled.connect(self.toggle_point_fixed_from_ui)
        self.point_props_layout.addWidget(self.point_fixed_cb)
        
        self.point_props_widget.setVisible(False)
        self.prop_layout.addWidget(self.point_props_widget)
        
        # 线属性
        self.line_props_widget = QWidget()
        self.line_props_layout = QVBoxLayout(self.line_props_widget)
        self.line_props_layout.setContentsMargins(0, 0, 0, 0)
        
        # 线段长度
        self.length_layout = QHBoxLayout()
        self.length_label = QLabel("长度:")
        self.length_value = QLabel("")
        self.length_layout.addWidget(self.length_label)
        self.length_layout.addWidget(self.length_value)
        self.line_props_layout.addLayout(self.length_layout)
        
        # 添加线段长度设置功能
        self.set_length_layout = QHBoxLayout()
        self.set_length_label = QLabel("设置长度:")
        self.set_length_input = QDoubleSpinBox()
        self.set_length_input.setRange(0.1, 2000.0)
        self.set_length_input.setDecimals(2)
        self.set_length_input.setValue(100.0)
        self.set_length_input.setSingleStep(1.0)
        self.set_length_button = QPushButton("应用")
        self.set_length_button.clicked.connect(self.apply_line_length)
        self.set_length_layout.addWidget(self.set_length_label)
        self.set_length_layout.addWidget(self.set_length_input)
        self.set_length_layout.addWidget(self.set_length_button)
        self.line_props_layout.addLayout(self.set_length_layout)
        
        # 线段固定长度选项
        self.line_fixed_cb = QCheckBox("固定长度")
        self.line_fixed_cb.toggled.connect(self.toggle_line_fixed_from_ui)
        self.line_props_layout.addWidget(self.line_fixed_cb)
        
        # 线段宽度
        self.width_layout = QHBoxLayout()
        self.width_label = QLabel("宽度:")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10)
        self.width_spin.setValue(2)
        self.width_spin.valueChanged.connect(self.update_line_width)
        self.width_layout.addWidget(self.width_label)
        self.width_layout.addWidget(self.width_spin)
        self.line_props_layout.addLayout(self.width_layout)
        
        # 线段样式
        self.style_layout = QHBoxLayout()
        self.style_label = QLabel("样式:")
        self.style_combo = QComboBox()
        self.style_combo.addItems(["实线", "虚线", "点线", "点划线"])
        self.style_combo.currentIndexChanged.connect(self.update_line_style)
        self.style_layout.addWidget(self.style_label)
        self.style_layout.addWidget(self.style_combo)
        self.line_props_layout.addLayout(self.style_layout)
        
        self.line_props_widget.setVisible(False)
        self.prop_layout.addWidget(self.line_props_widget)
        
        # 角度属性
        self.angle_props_widget = QWidget()
        self.angle_props_layout = QVBoxLayout(self.angle_props_widget)
        self.angle_props_layout.setContentsMargins(0, 0, 0, 0)
        
        # 角度值
        self.angle_value_layout = QHBoxLayout()
        self.angle_value_name = QLabel("角度值:")
        self.angle_value_label = QLabel("0.0°")
        self.angle_value_layout.addWidget(self.angle_value_name)
        self.angle_value_layout.addWidget(self.angle_value_label)
        self.angle_props_layout.addLayout(self.angle_value_layout)
        
        # 目标角度
        self.angle_target_layout = QHBoxLayout()
        self.angle_target_name = QLabel("目标角度:")
        self.angle_target_spin = QDoubleSpinBox()
        self.angle_target_spin.setRange(0, 360)
        self.angle_target_spin.setDecimals(1)
        self.angle_target_spin.setSuffix("°")
        self.angle_target_spin.setSingleStep(1)
        self.angle_target_button = QPushButton("应用")
        self.angle_target_button.clicked.connect(self.apply_angle_target)
        self.angle_target_layout.addWidget(self.angle_target_name)
        self.angle_target_layout.addWidget(self.angle_target_spin)
        self.angle_target_layout.addWidget(self.angle_target_button)
        self.angle_props_layout.addLayout(self.angle_target_layout)
        
        # 角度固定选项
        self.angle_fixed_cb = QCheckBox("固定角度")
        self.angle_fixed_cb.toggled.connect(self.toggle_angle_fixed_from_ui)
        self.angle_props_layout.addWidget(self.angle_fixed_cb)
        
        self.angle_props_widget.setVisible(False)
        self.prop_layout.addWidget(self.angle_props_widget)
        
        # 颜色选择按钮
        self.color_btn = QPushButton("颜色")
        self.color_btn.clicked.connect(self.change_color)
        self.prop_layout.addWidget(self.color_btn)
        
        # 添加到主布局
        self.properties_layout.addWidget(self.prop_group)
        
        # 画布切换组
        self.canvas_group = QGroupBox("画布模式")
        self.canvas_layout = QVBoxLayout(self.canvas_group)
        
        # 画布切换按钮
        self.canvas_switch_layout = QHBoxLayout()
        
        self.geometry_mode_btn = QPushButton("几何画板")
        self.geometry_mode_btn.setCheckable(True)
        self.geometry_mode_btn.setChecked(True)
        self.geometry_mode_btn.clicked.connect(lambda: self.switch_canvas_mode("geometry"))
        
        self.function_mode_btn = QPushButton("函数图像")
        self.function_mode_btn.setCheckable(True)
        self.function_mode_btn.clicked.connect(lambda: self.switch_canvas_mode("function"))
        
        self.canvas_switch_layout.addWidget(self.geometry_mode_btn)
        self.canvas_switch_layout.addWidget(self.function_mode_btn)
        self.canvas_layout.addLayout(self.canvas_switch_layout)
        
        # 函数相关按钮
        self.function_buttons_widget = QWidget()
        self.function_buttons_layout = QVBoxLayout(self.function_buttons_widget)
        
        self.add_function_btn = QPushButton("添加函数")
        self.add_function_btn.clicked.connect(self.add_function)
        
        self.manage_functions_btn = QPushButton("管理函数")
        self.manage_functions_btn.clicked.connect(self.manage_functions)
        
        self.ai_function_btn = QPushButton("AI助手")
        self.ai_function_btn.clicked.connect(self.show_ai_function_dialog)
        
        self.ai_chat_btn = QPushButton("AI对话")
        self.ai_chat_btn.clicked.connect(self.show_ai_function_chat_dialog)
        
        # 新增功能按钮
        self.query_function_btn = QPushButton("函数查询")
        self.query_function_btn.clicked.connect(self.show_function_query_dialog)
        
        self.dynamic_point_btn = QPushButton("创建动点")
        self.dynamic_point_btn.clicked.connect(self.show_dynamic_point_dialog)
        
        self.control_panel_btn = QPushButton("动点控制")
        self.control_panel_btn.clicked.connect(self.show_dynamic_point_control)
        
        self.function_buttons_layout.addWidget(self.add_function_btn)
        self.function_buttons_layout.addWidget(self.manage_functions_btn)
        self.function_buttons_layout.addWidget(self.ai_function_btn)
        self.function_buttons_layout.addWidget(self.ai_chat_btn)
        self.function_buttons_layout.addWidget(self.query_function_btn)
        self.function_buttons_layout.addWidget(self.dynamic_point_btn)
        self.function_buttons_layout.addWidget(self.control_panel_btn)
        
        self.canvas_layout.addWidget(self.function_buttons_widget)
        
        # 初始时隐藏函数按钮
        self.function_buttons_widget.setVisible(False)
        
        # 添加到主布局
        self.properties_layout.addWidget(self.canvas_group)
        
        # 动画控制组
        self.anim_group = QGroupBox("动画")
        self.anim_layout = QVBoxLayout(self.anim_group)
        
        # 高级动画按钮
        self.advanced_anim_btn = QPushButton("创建高级动画")
        self.advanced_anim_btn.clicked.connect(self.create_advanced_animation)
        self.anim_layout.addWidget(self.advanced_anim_btn)
        
        # 添加到主布局
        self.properties_layout.addWidget(self.anim_group)
        
        # 关于组
        self.about_group = QGroupBox("关于")
        self.about_layout = QVBoxLayout(self.about_group)
        
        self.about_text = QLabel(
            "ZMathJBoardF v1.1\n"
            "几何画板教学工具\n\n"
            "开发者: 顾俊辞"
        )
        self.about_layout.addWidget(self.about_text)
        
        # 添加到主布局
        self.properties_layout.addWidget(self.about_group)
        
        # 添加弹性空间
        self.properties_layout.addStretch()
        
        # 添加到主布局
        self.content_layout.addWidget(self.properties_widget)
        
    def setup_system_tray(self):
        """设置系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用jpg图片作为图标
        icon_path = os.path.join(os.path.dirname(__file__), 'img/mathb.jpg')
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # 创建临时图标作为备用
            icon_pixmap = QPixmap(16, 16)
            icon_pixmap.fill(QColor(52, 152, 219))  # 蓝色图标
            self.tray_icon.setIcon(QIcon(icon_pixmap))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        show_action = QAction("显示", self)
        quit_action = QAction("退出", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(self.quit_application)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 显示托盘图标
        self.tray_icon.show()
        
    def tray_icon_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()
                
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 隐藏窗口而不是退出
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "ZMathJBoardF",
            "程序已最小化到系统托盘。双击图标可重新打开窗口。",
            QSystemTrayIcon.Information,
            2000
        )
        
    def quit_application(self):
        """退出应用程序"""
        # 在退出前保存一次UI状态
        try:
            if hasattr(self.geometry_canvas, 'ui_state_manager'):
                self.geometry_canvas.ui_state_manager.auto_save_ui_state()
                print("程序退出时已保存几何画布UI状态")
                
            if hasattr(self, 'function_state_manager'):
                self.function_state_manager.auto_save_function_state()
                print("程序退出时已保存函数画布状态")
        except Exception as e:
            print(f"退出时保存UI状态出错: {str(e)}")
            
        self.tray_icon.hide()
        QApplication.quit()
        
    def set_tool(self, tool_name):
        """设置当前工具"""
        # 更新工具栏按钮状态
        for action in self.tool_actions:
            action.setChecked(False)
            
        if tool_name == "select":
            self.select_action.setChecked(True)
        elif tool_name == "point":
            self.point_action.setChecked(True)
        elif tool_name == "line":
            self.line_action.setChecked(True)
        elif tool_name == "connect":
            self.connect_action.setChecked(True)
            
        # 设置画布工具（只对几何画布有效）
        if self.canvas_mode == "geometry":
            self.current_canvas.set_tool(tool_name)
        
    def toggle_maximize(self):
        """切换最大化/还原状态"""
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setIcon(self.max_icon)
            self.max_btn.setObjectName("maxButton")
            self.max_btn.setToolTip("最大化")
        else:
            self.showMaximized()
            self.max_btn.setIcon(self.restore_icon)
            self.max_btn.setObjectName("restoreButton")
            self.max_btn.setToolTip("还原")
            
    def toggle_grid(self, checked=None):
        """切换网格显示状态"""
        if checked is None:
            # if没有传递状态，则切换当前状态
            self.current_canvas.show_grid = not self.current_canvas.show_grid
        else:
            self.current_canvas.show_grid = checked
        self.grid_action.setChecked(self.current_canvas.show_grid)
        self.current_canvas.update()
        
    def toggle_snap(self, checked=None):
        """切换吸附功能"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            if checked is None:
                # if没有传递状态，则切换当前状态
                self.geometry_canvas.snap_enabled = not self.geometry_canvas.snap_enabled
            else:
                self.geometry_canvas.snap_enabled = checked
            self.snap_action.setChecked(self.geometry_canvas.snap_enabled)
            self.geometry_canvas.update()
        
    def toggle_point_names(self, checked=None):
        """切换显示点名称"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            if checked is None:
                # if没有传递状态，则切换当前状态
                checked = not self.geometry_canvas.show_point_names
            
            self.geometry_canvas.toggle_show_point_names(checked)
            self.point_names_action.setChecked(checked)
    
    def toggle_line_names(self, checked=None):
        """切换显示线段名称"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            if checked is None:
                self.line_names_action.setChecked(not self.line_names_action.isChecked())
                checked = self.line_names_action.isChecked()
            else:
                self.line_names_action.setChecked(checked)
                
            self.geometry_canvas.toggle_show_line_names(checked)
        
    def toggle_intersections(self, checked=None):
        """切换是否显示交点"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            if checked is None:
                # 获取当前状态并取反
                current_state = self.geometry_canvas.get_intersection_state()
                new_state = self.geometry_canvas.toggle_show_intersections()
                self.intersections_action.setChecked(new_state)
            else:
                # 设置为指定状态
                self.intersections_action.setChecked(checked)
                if checked:
                    self.geometry_canvas.toggle_show_intersections(True)
                else:
                    self.geometry_canvas.toggle_show_intersections(False)
        
    def object_selected(self, obj):
        """对象被选中"""
        # 更新属性面板
        self.name_edit.setText(obj.name)
        self.type_value.setText(obj.__class__.__name__)
        
        # 隐藏所有属性特定面板
        self.point_props_widget.setVisible(False)
        self.line_props_widget.setVisible(False)
        self.angle_props_widget.setVisible(False)  # 添加角度属性面板的显示控制
        
        # 根据对象类型显示特定属性（只对几何画布对象有效）
        if self.canvas_mode == "geometry":
            if isinstance(obj, Point):
                self.point_props_widget.setVisible(True)
                self.x_spin.blockSignals(True)  # 阻止信号触发更新循环
                self.y_spin.blockSignals(True)
                self.x_spin.setValue(int(obj.x))
                self.y_spin.setValue(int(obj.y))
                self.x_spin.blockSignals(False)
                self.y_spin.blockSignals(False)
                self.point_fixed_cb.setChecked(obj.fixed)
            elif isinstance(obj, Line):
                self.line_props_widget.setVisible(True)
                line_length = round(obj.length(), 2)
                self.length_value.setText(str(line_length))
                # 更新长度输入框的值
                self.set_length_input.setValue(line_length)
                self.line_fixed_cb.setChecked(obj.fixed_length)
                self.width_spin.setValue(obj.width)
                
                # 设置线段样式
                styles = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine]
                style_index = styles.index(obj.style) if obj.style in styles else 0
                self.style_combo.setCurrentIndex(style_index)
            else:
                # 检查是否是角度对象
                try:
                    from .oangle import Angle
                    if isinstance(obj, Angle):
                        self.angle_props_widget.setVisible(True)
                        
                        # 显示角度值
                        angle_value = round(obj.calculate_angle(), 1)
                        self.angle_value_label.setText(f"{angle_value}°")
                        
                        # 显示是否固定
                        self.angle_fixed_cb.setChecked(obj.fixed)
                        
                        # 设置目标角度输入框的值
                        if obj.target_angle is not None:
                            self.angle_target_spin.setValue(obj.target_angle)
                        else:
                            self.angle_target_spin.setValue(angle_value)
                except (ImportError, AttributeError):
                    pass
        

        

                        
    def change_color(self):
        """更改对象颜色"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        obj = self.geometry_canvas.selected_object
        if not obj:
            return
            
        # 获取当前颜色
        current_color = obj.color if hasattr(obj, "color") else QColor(0, 0, 0)
        
        # 打开颜色对话框
        color = QColorDialog.getColor(current_color, self, "选择颜色")
        
        if color.isValid():
            # 设置对象颜色
            if hasattr(obj, "color"):
                obj.color = color
                self.geometry_canvas.update()
                

    def play_animations(self):
        """播放所有动画"""
        if self.canvas_mode == "geometry":
            # 优先播放高级动画
            if self.current_animation_config and self.advanced_animation_manager:
                if not self.advanced_animation_manager.is_playing:
                    self.advanced_animation_manager.start_animation()
                else:
                    self.advanced_animation_manager.pause_animation()
            else:
                # 播放传统动画
                for obj in self.geometry_canvas.objects:
                    for anim in obj.animations:
                        anim.start()
        elif self.canvas_mode == "function":
            # 函数画布动画控制
            if hasattr(self, 'dynamic_point_manager') and self.dynamic_point_manager:
                self.dynamic_point_manager.toggle_animation()
                
    def stop_animations(self):
        """停止所有动画"""
        if self.canvas_mode == "geometry":
            # 停止高级动画
            if self.advanced_animation_manager:
                self.advanced_animation_manager.stop_animation()
            
            # 停止传统动画
            for obj in self.geometry_canvas.objects:
                for anim in obj.animations:
                    anim.stop()
        elif self.canvas_mode == "function":
            # 停止函数画布动画
            if hasattr(self, 'dynamic_point_manager') and self.dynamic_point_manager:
                self.dynamic_point_manager.stop_animation()
    
    def create_advanced_animation(self):
        """创建高级动画"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            QMessageBox.warning(self, "错误", "高级动画功能仅在几何模式下可用")
            return
            
        # 检查是否有足够的对象来创建动画
        if len(self.geometry_canvas.objects) < 2:
            QMessageBox.warning(self, "错误", "至少需要2个几何对象才能创建动画")
            return
            
        # 创建高级动画对话框
        dialog = AdvancedAnimationDialog(self.geometry_canvas, self)
        dialog.animation_created.connect(self.on_advanced_animation_created)
        dialog.exec_()
    
    def on_advanced_animation_created(self, animation_config):
        """处理高级动画创建完成"""
        try:
            # 保存当前动画配置
            self.current_animation_config = animation_config
            
            # 设置动画管理器配置
            self.advanced_animation_manager.set_animation_config(animation_config)
            
            # 创建动画控制界面
            if self.animation_control_widget:
                self.animation_control_widget.close()
                
            chart_display = animation_config.get('chart_display')
            self.animation_control_widget = AnimationControlWidget(
                self.advanced_animation_manager, 
                chart_display,
                self
            )
            
            # 创建动画控制窗口
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            self.animation_control_dialog = QDialog(self)
            self.animation_control_dialog.setWindowTitle("动画控制")
            self.animation_control_dialog.setModal(False)
            self.animation_control_dialog.resize(800, 600)
            
            # 当对话框关闭时停止动画
            def on_dialog_close(event):
                try:
                    if self.advanced_animation_manager:
                        self.advanced_animation_manager.stop_animation()
                        print("动画控制窗口关闭，停止所有动画")
                except Exception as e:
                    print(f"关闭动画时出错: {e}")
                finally:
                    event.accept()
                    
            self.animation_control_dialog.closeEvent = on_dialog_close
            
            layout = QVBoxLayout(self.animation_control_dialog)
            layout.addWidget(self.animation_control_widget)
            
            # if有图表显示，添加到布局中
            if chart_display:
                layout.addWidget(chart_display)
            
            self.animation_control_dialog.show()
            
            # 连接播放控制信号
            playback_controls = animation_config.get('playback_controls')
            if hasattr(playback_controls, 'play_requested'):
                playback_controls.play_requested.connect(self.advanced_animation_manager.start_animation)
                playback_controls.pause_requested.connect(self.advanced_animation_manager.pause_animation)
                playback_controls.stop_requested.connect(self.advanced_animation_manager.stop_animation)
                playback_controls.speed_changed.connect(self.advanced_animation_manager.set_speed)
            
            QMessageBox.information(self, "成功", "高级动画已创建完成！\n使用动画控制窗口来播放和控制动画。")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建高级动画时出错: {str(e)}")
        
    def update_object_name(self):
        """更新对象名称"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry" and self.geometry_canvas.selected_object:
            self.geometry_canvas.selected_object.name = self.name_edit.text()
            self.geometry_canvas.update()
            
    def update_point_position(self):
        """更新点位置"""
        # 只对几何画布有效
        if (self.canvas_mode == "geometry" and 
            self.geometry_canvas.selected_object and 
            isinstance(self.geometry_canvas.selected_object, Point)):
            self.geometry_canvas.selected_object.x = float(self.x_spin.value())
            self.geometry_canvas.selected_object.y = float(self.y_spin.value())
            self.geometry_canvas.update()
            
    def toggle_point_fixed_from_ui(self, checked):
        """从UI触发固定点状态"""
        # 只对几何画布有效
        if (self.canvas_mode == "geometry" and 
            self.geometry_canvas.selected_object and 
            isinstance(self.geometry_canvas.selected_object, Point)):
            self.geometry_canvas.selected_object.fixed = checked
            self.geometry_canvas.update()
            
    def toggle_line_fixed_from_ui(self, checked):
        """从UI触发固定线段长度状态"""
        if (self.canvas_mode == "geometry" and 
            self.geometry_canvas.selected_object and 
            isinstance(self.geometry_canvas.selected_object, Line)):
            # 获取当前线段
            line = self.geometry_canvas.selected_object
            
            # 记录切换前的状态
            old_state = line.fixed_length
            old_length = line.length()
            
            # 强制设置状态而非切换，确保与UI保持一致
            if checked != line.fixed_length:
                line.fixed_length = checked
                # if启用固定长度，记录当前长度
                if line.fixed_length:
                    line._original_length = old_length
                    line._force_maintain_length = True
                    print(f"UI强制设置: 线段{line.name}设为固定长度, 长度={line._original_length}")
                    # 立即强制应用
                    line._enforce_fixed_length()
                else:
                    line._force_maintain_length = False
                    print(f"UI强制设置: 线段{line.name}取消固定长度, 长度={old_length}")
            
            # 确保UI勾选状态和实际状态一致
            if self.line_fixed_cb.isChecked() != line.fixed_length:
                self.line_fixed_cb.blockSignals(True)
                self.line_fixed_cb.setChecked(line.fixed_length)
                self.line_fixed_cb.blockSignals(False)
                
            # 更新UI显示
            current_length = line.length()
            self.length_value.setText(str(round(current_length, 2)))
            
            # 强制刷新画布
            self.geometry_canvas.update()
        
    def update_line_width(self, value):
        """更新线宽"""
        if (self.canvas_mode == "geometry" and 
            self.geometry_canvas.selected_object and 
            isinstance(self.geometry_canvas.selected_object, Line)):
            self.geometry_canvas.selected_object.width = value
            self.geometry_canvas.update()
            
    def update_line_style(self, index):
        """更新线段样式"""
        if (self.canvas_mode == "geometry" and 
            self.geometry_canvas.selected_object and 
            isinstance(self.geometry_canvas.selected_object, Line)):
            # 设置线段样式
            styles = [Qt.SolidLine, Qt.DashLine, Qt.DotLine, Qt.DashDotLine, Qt.DashDotDotLine]
            if 0 <= index < len(styles):
                self.geometry_canvas.selected_object.style = styles[index]
                self.geometry_canvas.update()
    
    def show_draw_dialog(self):
        """显示绘制封闭图形对话框"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            show_draw_dialog(self.geometry_canvas)
    
    def show_angle_dialog(self):
        """显示角度设置对话框"""
        # 只对几何画布有效
        if self.canvas_mode == "geometry":
            from .oangle import show_angle_dialog
            show_angle_dialog(self.geometry_canvas)
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件（用于拖拽标题栏）"""
        if event.button() == Qt.LeftButton:
            self.pressing = True
            self.start = event.globalPos()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件，实现窗口拖动功能"""
        if self.pressing and self.start:
            movement = event.globalPos() - self.start
            self.move(self.pos() + movement)
            self.start = event.globalPos()
            
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self.pressing = False
        
    def avoid_marker_overlaps(self):
        """避免元素名称重叠
        
        调用Canvas的名称位置管理器，自动调整各元素名称位置
        """
        # 只对几何画布有效
        if self.canvas_mode == "geometry" and hasattr(self.geometry_canvas, 'name_position_manager'):
            adjusted_count = self.geometry_canvas.name_position_manager.update_all_name_positions()
            self.status_bar.showMessage(f"名称位置调整完成，共调整了{adjusted_count}个名称位置")

    def apply_line_length(self):
        """应用线段长度设置"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        obj = self.geometry_canvas.selected_object
        if not obj or not isinstance(obj, Line):
            return
            
        new_length = self.set_length_input.value()
        if new_length <= 0:
            QMessageBox.warning(self, "长度错误", "线段长度必须为正数")
            return
            
        # 记录旧的长度值，以便可以检测是否有变化
        old_length = obj.length()
            
        # 应用新长度前先打印调试信息
        print(f"准备设置线段{obj.name}长度: 旧={old_length}, 新={new_length}, 固定状态={obj.fixed_length}")
            
        # 应用新长度
        obj.set_length(new_length)
        
        # 确保固定长度状态正确对应UI显示
        if not obj.fixed_length:  # 这种情况不应该发生，因为set_length会自动设置fixed_length=True
            obj.fixed_length = True
            print(f"警告: 在设置长度后fixed_length={obj.fixed_length}，强制设为True")
        
        # 更新UI勾选状态
        self.line_fixed_cb.setChecked(True)
            
        # 刷新显示
        final_length = obj.length()  # 获取实际设置后的长度
        self.length_value.setText(str(round(final_length, 2)))
        
        # if长度有实质性变化，通知user
        if abs(old_length - final_length) > 0.01:
            message = f"已将线段\"{obj.name}\"的长度从 {round(old_length, 2)} 设置为 {round(final_length, 2)}"
            self.status_bar.showMessage(message, 3000)
            QMessageBox.information(self, "设置成功", message)
            print(message)  # 同时打印到控制台
        
        # 强制刷新画布
        self.geometry_canvas.update() 

    def toggle_angle_fixed_from_ui(self, checked):
        """从UI触发固定角度状态"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        try:
            from .oangle import Angle
            if (self.geometry_canvas.selected_object and 
                isinstance(self.geometry_canvas.selected_object, Angle)):
                angle = self.geometry_canvas.selected_object
                angle.fixed = checked
                
                # if设置为固定状态，确保有目标角度值
                if angle.fixed and angle.target_angle is None:
                    angle.target_angle = angle.calculate_angle()
                    
                # if设置为固定状态，立即应用角度
                if angle.fixed:
                    angle.enforce_angle()
                    
                # 更新UI
                self.angle_value_label.setText(f"{round(angle.calculate_angle(), 1)}°")
                
                # 更新画布
                self.geometry_canvas.update()
        except (ImportError, AttributeError):
            pass
            
    def apply_angle_target(self):
        """应用目标角度值"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        try:
            from .oangle import Angle
            if (self.geometry_canvas.selected_object and 
                isinstance(self.geometry_canvas.selected_object, Angle)):
                angle = self.geometry_canvas.selected_object
                angle.target_angle = self.angle_target_spin.value()
                
                # 设置为固定状态并更新UI
                angle.fixed = True
                self.angle_fixed_cb.setChecked(True)
                
                # 立即应用角度
                angle.enforce_angle()
                
                # 更新UI
                self.angle_value_label.setText(f"{round(angle.calculate_angle(), 1)}°")
                
                # 更新画布
                self.geometry_canvas.update()
        except (ImportError, AttributeError):
            pass
            
    def toggle_angles(self, checked=None):
        """切换角度显示"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        if checked is None:
            # 切换当前状态
            checked = not getattr(self.geometry_canvas, 'show_angles', True)
            self.show_angles_action.setChecked(checked)
            
        # 设置画布上的角度显示属性
        self.geometry_canvas.show_angles = checked
        
        # 更新所有角度对象的可见性
        try:
            from .oangle import Angle
            for obj in self.geometry_canvas.objects:
                if isinstance(obj, Angle):
                    obj.visible = checked
        except (ImportError, AttributeError):
            pass
            
        # 更新画布
        self.geometry_canvas.update()
        
    def toggle_angle_values(self, checked=None):
        """切换角度数值显示"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        if checked is None:
            # 切换当前状态
            checked = not getattr(self.geometry_canvas, 'show_angle_values', True)
            self.show_angle_values_action.setChecked(checked)
            
        # 设置画布上的角度数值显示属性
        self.geometry_canvas.show_angle_values = checked
        
        # 更新画布
        self.geometry_canvas.update()
    
    def toggle_maintain_aspect_ratio(self, checked=None):
        """切换函数画布长宽比保持功能"""
        if checked is None:
            checked = not self.function_canvas.maintain_aspect_ratio
            self.maintain_aspect_ratio_action.setChecked(checked)
        
        self.function_canvas.set_maintain_aspect_ratio(checked)
    
    def toggle_adaptive_line_scaling(self, checked=None):
        """切换线段长度自适应比例功能"""
        if self.canvas_mode == "geometry":
            if checked is None:
                checked = not self.geometry_canvas.adaptive_line_scaling
                self.adaptive_line_scaling_action.setChecked(checked)
            
            self.geometry_canvas.toggle_adaptive_line_scaling(checked) 

    def toggle_canvas_drag_mode(self, checked=None):
        """切换画布拖动模式"""
        # 只对几何画布有效
        if self.canvas_mode != "geometry":
            return
            
        if checked is not None:
            self.geometry_canvas.drag_mode = checked
            self.geometry_canvas.is_canvas_drag_mode = checked
        else:
            self.geometry_canvas.drag_mode = not self.geometry_canvas.drag_mode
            self.geometry_canvas.is_canvas_drag_mode = self.geometry_canvas.drag_mode
            
        # 更新工具栏按钮状态
        self.canvas_drag_action.setChecked(self.geometry_canvas.drag_mode)
        
        # 更新鼠标光标
        if self.geometry_canvas.drag_mode:
            self.geometry_canvas.setCursor(Qt.OpenHandCursor)
        else:
            self.geometry_canvas.setCursor(Qt.ArrowCursor)
            
        # 更新画布
        self.geometry_canvas.update()
    
    def show_ai_dialog(self):
        """显示AI绘图助手对话框"""
        try:
            from .ai_dialog import AIDialog
            from .drawing_api import DrawingAPI
            
            # 创建AI对话框
            if not hasattr(self, 'ai_dialog') or self.ai_dialog is None:
                self.ai_dialog = AIDialog(self)
                
                # 设置画布引用
                self.ai_dialog.set_canvas(self.geometry_canvas)
                
                # 创建绘图API实例
                self.drawing_api = DrawingAPI(self.geometry_canvas)
                
                # 连接信号
                self.ai_dialog.execute_commands.connect(self.execute_ai_commands)
            
            # 显示对话框
            self.ai_dialog.show()
            self.ai_dialog.raise_()
            self.ai_dialog.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(self, "AI助手错误", f"无法启动AI助手：{str(e)}")
    
    def execute_ai_commands(self, commands):
        """执行AI生成的绘图命令"""
        try:
            if not hasattr(self, 'drawing_api'):
                from .drawing_api import DrawingAPI
                self.drawing_api = DrawingAPI(self.geometry_canvas)
            
            # 执行命令
            success = self.drawing_api.execute_commands(commands)
            
            if success:
                self.status_bar.showMessage("AI绘图命令执行成功", 3000)
                

            else:
                QMessageBox.warning(self, "执行失败", "部分或全部AI绘图命令执行失败，请检查命令格式")
                
        except Exception as e:
            QMessageBox.critical(self, "执行错误", f"执行AI绘图命令时出错：{str(e)}")
            print(f"AI命令执行错误: {str(e)}")
    

    
    def toggle_geometry_check(self, checked):
        """切换几何检查功能"""
        if self.canvas_mode == "geometry" and hasattr(self.geometry_canvas, 'geometry_checker'):
            self.geometry_canvas.geometry_checker.enable_checking(checked)
            status = "启用" if checked else "禁用"
            self.status_bar.showMessage(f"几何检查已{status}", 2000)
    
    def toggle_auto_fix(self, checked):
        """切换自动修复功能"""
        if self.canvas_mode == "geometry" and hasattr(self.geometry_canvas, 'geometry_checker'):
            self.geometry_canvas.geometry_checker.set_auto_fix(checked)
            status = "启用" if checked else "禁用"
            self.status_bar.showMessage(f"自动修复已{status}", 2000)
    
    def manual_fix_all(self):
        """手动修复所有异常"""
        try:
            if self.canvas_mode == "geometry" and hasattr(self.geometry_canvas, 'geometry_checker'):
                self.geometry_canvas.geometry_checker.manual_fix_all()
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "修复完成", "所有几何异常已修复")
                self.status_bar.showMessage("异常修复完成", 3000)
            
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "修复错误", f"修复异常时出错：{str(e)}")
            print(f"修复错误: {str(e)}")
    
    def switch_canvas_mode(self, mode):
        """切换画布模式"""
        if mode == self.canvas_mode:
            return
        
        try:
            # 保存当前画布状态
            if self.canvas_mode == "geometry":
                if hasattr(self.geometry_canvas, 'ui_state_manager'):
                    self.geometry_canvas.ui_state_manager.auto_save_ui_state()
            elif self.canvas_mode == "function":
                if hasattr(self, 'function_state_manager'):
                    self.function_state_manager.auto_save_function_state()
            
            # 移除当前画布
            self.content_layout.removeWidget(self.current_canvas)
            self.current_canvas.setParent(None)
            
            # 切换到新画布
            if mode == "geometry":
                self.current_canvas = self.geometry_canvas
                self.canvas_mode = "geometry"
                self.geometry_mode_btn.setChecked(True)
                self.function_mode_btn.setChecked(False)
                self.function_buttons_widget.setVisible(False)
                
                # 尝试加载几何画布状态
                if hasattr(self.geometry_canvas, 'ui_state_manager'):
                    self.geometry_canvas.ui_state_manager.auto_load_ui_state()
                
            elif mode == "function":
                self.current_canvas = self.function_canvas
                self.canvas_mode = "function"
                self.geometry_mode_btn.setChecked(False)
                self.function_mode_btn.setChecked(True)
                self.function_buttons_widget.setVisible(True)
                
                # 尝试加载函数画布状态
                if hasattr(self, 'function_state_manager'):
                    self.function_state_manager.auto_load_function_state()
            
            # 添加新画布到布局
            self.content_layout.insertWidget(0, self.current_canvas)
            
            # 更新canvas引用（为了兼容性）
            self.canvas = self.current_canvas
            
            # 清除选中状态
            self.selected_object = None
            
            # 更新状态栏
            mode_text = "几何画板" if mode == "geometry" else "函数图像"
            self.status_bar.showMessage(f"已切换到{mode_text}模式", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "切换错误", f"切换画布模式时出错：{str(e)}")
            print(f"切换画布模式错误: {str(e)}")
    
    def add_function(self):
        """添加函数"""
        try:
            dialog = FunctionInputDialog(self)
            dialog.function_added.connect(self.on_function_added)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开添加函数对话框时出错：{str(e)}")
    
    def on_function_added(self, expression, color, x_min, x_max):
        """处理函数添加"""
        try:
            self.function_canvas.add_function(expression, color, x_min, x_max)
            self.status_bar.showMessage("函数已添加", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加函数失败：{str(e)}")
    
    def manage_functions(self):
        """管理函数"""
        try:
            dialog = FunctionManagerDialog(self.function_canvas, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开函数管理对话框时出错：{str(e)}")
    
    def show_ai_function_dialog(self):
        """显示AI函数绘图对话框"""
        try:
            if not hasattr(self, 'ai_function_dialog') or self.ai_function_dialog is None:
                self.ai_function_dialog = AIFunctionDialog(self.function_canvas, self)
                self.ai_function_dialog.function_generated.connect(self.on_ai_function_generated)
            
            self.ai_function_dialog.show()
            self.ai_function_dialog.raise_()
            self.ai_function_dialog.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开AI函数绘图对话框时出错：{str(e)}")
    
    def on_ai_function_generated(self, expression, color, x_min, x_max):
        """处理AI生成的函数"""
        try:
            self.function_canvas.add_function(expression, color, x_min, x_max)
            self.status_bar.showMessage(f"AI生成的函数已添加: f(x) = {expression}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加AI生成的函数失败：{str(e)}")
    
    def show_ai_function_chat_dialog(self):
        """显示AI函数对话助手"""
        try:
            if not hasattr(self, 'ai_function_chat_dialog') or self.ai_function_chat_dialog is None:
                self.ai_function_chat_dialog = AIFunctionChatDialog(self.function_canvas, self)
                self.ai_function_chat_dialog.execute_function_commands.connect(self.on_ai_function_commands_executed)
            
            self.ai_function_chat_dialog.show()
            self.ai_function_chat_dialog.raise_()
            self.ai_function_chat_dialog.activateWindow()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开AI函数对话助手时出错：{str(e)}")
    
    def on_ai_function_commands_executed(self, commands):
        """处理AI对话生成的函数命令"""
        try:
            for cmd in commands:
                # 转换颜色
                if isinstance(cmd.color, str):
                    color = QColor(cmd.color)
                else:
                    color = cmd.color
                
                # 添加函数到画布
                self.function_canvas.add_function(
                    cmd.expression, 
                    color, 
                    cmd.x_min, 
                    cmd.x_max
                )
                
                # 设置线宽（if函数支持的话）
                if self.function_canvas.functions:
                    last_func = self.function_canvas.functions[-1]
                    last_func.line_width = cmd.line_width
            
            count = len(commands)
            self.status_bar.showMessage(f"AI对话生成的 {count} 个函数已添加", 5000)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"执行AI对话函数命令失败：{str(e)}")
            print(f"AI对话函数命令执行错误: {str(e)}")
    
    def function_selected(self, func):
        """函数被选中"""
        # 可以在这里更新属性面板显示函数属性
        if func:
            self.status_bar.showMessage(f"已选中函数: {func.name}", 3000)
    
    def save_canvas(self):
        """保存UI状态到文件"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            from datetime import datetime
            
            # 根据当前模式选择默认文件名
            if self.canvas_mode == "geometry":
                default_name = f"geometry_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            else:
                default_name = f"function_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            
            # 选择保存位置
            filepath, _ = QFileDialog.getSaveFileName(
                self, 
                "保存状态", 
                default_name,
                "状态文件 (*.pkl);;所有文件 (*)"
            )
            
            if filepath:
                success = False
                if self.canvas_mode == "geometry":
                    success = self.geometry_canvas.ui_state_manager.save_ui_state(filepath)
                else:
                    success = self.function_state_manager.save_function_state(filepath)
                
                if success:
                    QMessageBox.information(self, "保存成功", f"状态已保存到:\n{filepath}")
                    self.status_bar.showMessage(f"状态已保存: {filepath}", 5000)
                else:
                    QMessageBox.critical(self, "保存失败", "保存状态时出现错误")
                    
        except Exception as e:
            QMessageBox.critical(self, "保存错误", f"保存状态时出错：{str(e)}")
            print(f"保存错误: {str(e)}")
    
    def load_canvas(self):
        """从文件加载UI状态"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            
            # 选择文件
            filepath, _ = QFileDialog.getOpenFileName(
                self, 
                "加载状态", 
                "",
                "状态文件 (*.pkl);;所有文件 (*)"
            )
            
            if filepath:
                # 检测文件类型
                state_type = detect_state_type(filepath)
                
                if state_type is None:
                    QMessageBox.critical(self, "加载失败", "无法识别的状态文件格式")
                    return
                
                # 确认是否要覆盖当前状态
                current_has_content = False
                if state_type == "geometry":
                    current_has_content = bool(self.geometry_canvas.objects)
                elif state_type == "function":
                    current_has_content = bool(self.function_canvas.functions)
                
                if current_has_content:
                    reply = QMessageBox.question(
                        self, 
                        "确认加载", 
                        f"加载{('几何' if state_type == 'geometry' else '函数')}状态将清除当前内容，确定要继续吗？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply != QMessageBox.Yes:
                        return
                
                # 切换到对应模式
                if state_type != self.canvas_mode:
                    self.switch_canvas_mode(state_type)
                
                # 加载状态
                success = False
                if state_type == "geometry":
                    success = self.geometry_canvas.ui_state_manager.load_ui_state(filepath)
                elif state_type == "function":
                    success = self.function_state_manager.load_function_state(filepath)
                
                if success:
                    QMessageBox.information(self, "加载成功", f"状态已从以下位置加载:\n{filepath}")
                    self.status_bar.showMessage(f"状态已加载: {filepath}", 5000)
                    
                    # 强制刷新画布显示
                    self.current_canvas.update()
                else:
                    QMessageBox.critical(self, "加载失败", "加载状态时出现错误")
                    
        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载状态时出错：{str(e)}")
            print(f"加载错误: {str(e)}")
    
    def clear_canvas(self):
        """清空画布"""
        try:
            from PyQt5.QtWidgets import QMessageBox
            
            # 检查当前画布是否有内容
            has_content = False
            if self.canvas_mode == "geometry":
                has_content = bool(self.geometry_canvas.objects)
            else:
                has_content = bool(self.function_canvas.functions)
            
            # 确认清空操作
            if has_content:
                content_type = "几何图形" if self.canvas_mode == "geometry" else "函数"
                reply = QMessageBox.question(
                    self, 
                    "确认清空", 
                    f"确定要清空画布上的所有{content_type}吗？此操作不可撤销。",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # 执行清空
            if self.canvas_mode == "geometry":
                self.geometry_canvas.clear_canvas()
            else:
                self.function_canvas.clear_functions()
            
            QMessageBox.information(self, "清空完成", "画布已清空")
            self.status_bar.showMessage("画布已清空", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "清空错误", f"清空画布时出错：{str(e)}")
            print(f"清空错误: {str(e)}")
    
    def show_function_query_dialog(self):
        """显示函数查询对话框"""
        try:
            if not self.function_canvas.functions:
                QMessageBox.information(self, "提示", "请先添加函数再进行查询")
                return
            
            dialog = FunctionQueryDialog(self.function_canvas.functions, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开函数查询对话框时出错：{str(e)}")
    
    def show_dynamic_point_dialog(self):
        """显示动点创建对话框"""
        try:
            dialog = DynamicPointDialog(self.function_canvas.functions, self)
            dialog.point_created.connect(self.on_dynamic_point_created)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开动点创建对话框时出错：{str(e)}")
    
    def on_dynamic_point_created(self, point):
        """处理动点创建"""
        try:
            # 添加到管理器
            self.dynamic_point_manager.add_point(point)
            
            # 添加到画布
            self.function_canvas.add_dynamic_point(point)
            
            # if动点设置为自动开始，启动动画
            if point.is_animating and not self.dynamic_point_manager.timer.isActive():
                self.dynamic_point_manager.start_animation()
            
            self.status_bar.showMessage(f"动点 '{point.name}' 已创建", 3000)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建动点时出错：{str(e)}")
    
    def show_dynamic_point_control(self):
        """显示动点控制面板"""
        try:
            if not self.dynamic_point_manager.points:
                QMessageBox.information(self, "提示", "请先创建动点再打开控制面板")
                return
            
            if self.dynamic_control_panel is None:
                self.dynamic_control_panel = DynamicPointControlPanel(self.dynamic_point_manager)
                
                # 创建停靠窗口
                dock = QDockWidget("动点控制面板", self)
                dock.setWidget(self.dynamic_control_panel)
                dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
                self.addDockWidget(Qt.RightDockWidgetArea, dock)
                
                # 保存引用以便后续控制
                self.dynamic_control_dock = dock
            else:
                # if已存在，显示窗口
                if hasattr(self, 'dynamic_control_dock'):
                    self.dynamic_control_dock.show()
                    self.dynamic_control_dock.raise_()
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开动点控制面板时出错：{str(e)}") 