#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QColorDialog, QDoubleSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QDialogButtonBox, QTextEdit, QSpinBox,
    QFrame, QScrollArea, QTabWidget, QFormLayout, QSlider
)
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
import math

from .function_plotter import FunctionExpression, FunctionCanvas

class FunctionInputDialog(QDialog):
    """函数输入对话框"""
    
    function_added = pyqtSignal(str, QColor, float, float)  # 表达式, 颜色, x_min, x_max
    
    def __init__(self, parent=None, existing_function=None):
        super().__init__(parent)
        self.existing_function = existing_function
        self.setup_ui()
        
        if existing_function:
            self.load_function(existing_function)
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("添加函数" if not self.existing_function else "编辑函数")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        
        # 函数表达式输入
        expr_group = QGroupBox("函数表达式")
        expr_layout = QVBoxLayout(expr_group)
        
        self.expr_label = QLabel("f(x) = ")
        self.expr_edit = QLineEdit()
        self.expr_edit.setPlaceholderText("例如: x**2, sin(x), exp(-x**2), ...")
        
        expr_input_layout = QHBoxLayout()
        expr_input_layout.addWidget(self.expr_label)
        expr_input_layout.addWidget(self.expr_edit)
        expr_layout.addLayout(expr_input_layout)
        
        # 添加帮助文本
        help_text = QLabel(
            "支持的函数和常数:\n"
            "• 基本运算: +, -, *, /, ** (幂运算)\n"
            "• 三角函数: sin, cos, tan, asin, acos, atan\n"
            "• 指数对数: exp, log, log10, sqrt\n"
            "• 常数: pi, e\n"
            "• 其他: abs, floor, ceil, round"
        )
        help_text.setStyleSheet("color: gray; font-size: 10px;")
        expr_layout.addWidget(help_text)
        
        layout.addWidget(expr_group)
        
        # 参数设置
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout(params_group)
        
        # X范围
        x_range_layout = QHBoxLayout()
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000, 1000)
        self.x_min_spin.setValue(-10)
        self.x_min_spin.setDecimals(2)
        
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000, 1000)
        self.x_max_spin.setValue(10)
        self.x_max_spin.setDecimals(2)
        
        x_range_layout.addWidget(QLabel("从"))
        x_range_layout.addWidget(self.x_min_spin)
        x_range_layout.addWidget(QLabel("到"))
        x_range_layout.addWidget(self.x_max_spin)
        
        params_layout.addRow("X范围:", x_range_layout)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 30)
        self.current_color = QColor(0, 100, 200)
        self.update_color_button()
        self.color_button.clicked.connect(self.choose_color)
        
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        
        params_layout.addRow("颜色:", color_layout)
        
        layout.addWidget(params_group)
        
        # 预览
        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_canvas = FunctionCanvas()
        self.preview_canvas.setFixedHeight(150)
        preview_layout.addWidget(self.preview_canvas)
        
        layout.addWidget(preview_group)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("预览")
        self.preview_button.clicked.connect(self.update_preview)
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.preview_button)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 连接信号
        self.expr_edit.textChanged.connect(self.on_expression_changed)
        
        # 设置默认值
        self.expr_edit.setText("x**2")
        self.update_preview()
    
    def load_function(self, func: FunctionExpression):
        """加载已有函数的数据"""
        self.expr_edit.setText(func.expression)
        self.x_min_spin.setValue(func.x_min)
        self.x_max_spin.setValue(func.x_max)
        self.current_color = func.color
        self.update_color_button()
        self.update_preview()
    
    def update_color_button(self):
        """更新颜色按钮显示"""
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()};")
    
    def choose_color(self):
        """选择颜色"""
        color = QColorDialog.getColor(self.current_color, self, "选择函数颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.update_preview()
    
    def on_expression_changed(self):
        """表达式改变时的处理"""
        # 延迟更新预览，避免频繁计算
        if hasattr(self, 'preview_timer'):
            self.preview_timer.stop()
        
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.preview_timer.start(500)  # 500ms延迟
    
    def update_preview(self):
        """更新预览"""
        try:
            expression = self.expr_edit.text().strip()
            if not expression:
                return
            
            x_min = self.x_min_spin.value()
            x_max = self.x_max_spin.value()
            
            if x_min >= x_max:
                QMessageBox.warning(self, "参数错误", "X范围的最小值必须小于最大值")
                return
            
            # 清除预览画布
            self.preview_canvas.clear_functions()
            
            # 添加函数到预览
            func = self.preview_canvas.add_function(expression, self.current_color, x_min, x_max)
            
            # 自动调整视图
            self.preview_canvas.zoom_to_fit()
            
        except Exception as e:
            # 显示错误但不阻止操作
            pass
    
    def accept(self):
        """确认添加函数"""
        try:
            expression = self.expr_edit.text().strip()
            if not expression:
                QMessageBox.warning(self, "输入错误", "请输入函数表达式")
                return
            
            x_min = self.x_min_spin.value()
            x_max = self.x_max_spin.value()
            
            if x_min >= x_max:
                QMessageBox.warning(self, "参数错误", "X范围的最小值必须小于最大值")
                return
            
            # 验证表达式
            test_func = FunctionExpression(expression, self.current_color, x_min, x_max)
            if not test_func.is_valid_expression():
                QMessageBox.warning(self, "表达式错误", "函数表达式无效，请检查语法")
                return
            
            # 发射信号
            self.function_added.emit(expression, self.current_color, x_min, x_max)
            super().accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加函数时出错: {str(e)}")

class FunctionManagerDialog(QDialog):
    """函数管理对话框"""
    
    def __init__(self, function_canvas: FunctionCanvas, parent=None):
        super().__init__(parent)
        self.function_canvas = function_canvas
        self.setup_ui()
        self.refresh_function_list()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("函数管理")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QHBoxLayout(self)
        
        # 左侧：函数列表
        left_layout = QVBoxLayout()
        
        list_group = QGroupBox("函数列表")
        list_layout = QVBoxLayout(list_group)
        
        self.function_list = QListWidget()
        self.function_list.currentItemChanged.connect(self.on_function_selected)
        list_layout.addWidget(self.function_list)
        
        # 函数列表操作按钮
        list_button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加")
        self.add_button.clicked.connect(self.add_function)
        
        self.edit_button = QPushButton("编辑")
        self.edit_button.clicked.connect(self.edit_function)
        
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_function)
        
        self.clear_button = QPushButton("清空")
        self.clear_button.clicked.connect(self.clear_functions)
        
        list_button_layout.addWidget(self.add_button)
        list_button_layout.addWidget(self.edit_button)
        list_button_layout.addWidget(self.delete_button)
        list_button_layout.addWidget(self.clear_button)
        
        list_layout.addLayout(list_button_layout)
        left_layout.addWidget(list_group)
        
        # 右侧：函数属性
        right_layout = QVBoxLayout()
        
        props_group = QGroupBox("函数属性")
        props_layout = QFormLayout(props_group)
        
        # 可见性
        self.visible_checkbox = QCheckBox("显示")
        self.visible_checkbox.toggled.connect(self.on_visibility_changed)
        props_layout.addRow("可见性:", self.visible_checkbox)
        
        # 颜色
        color_layout = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 30)
        self.color_button.clicked.connect(self.change_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        props_layout.addRow("颜色:", color_layout)
        
        # 线宽
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10)
        self.width_spin.valueChanged.connect(self.on_width_changed)
        props_layout.addRow("线宽:", self.width_spin)
        
        # X范围
        x_range_layout = QHBoxLayout()
        self.x_min_spin = QDoubleSpinBox()
        self.x_min_spin.setRange(-1000, 1000)
        self.x_min_spin.setDecimals(2)
        self.x_min_spin.valueChanged.connect(self.on_range_changed)
        
        self.x_max_spin = QDoubleSpinBox()
        self.x_max_spin.setRange(-1000, 1000)
        self.x_max_spin.setDecimals(2)
        self.x_max_spin.valueChanged.connect(self.on_range_changed)
        
        x_range_layout.addWidget(QLabel("从"))
        x_range_layout.addWidget(self.x_min_spin)
        x_range_layout.addWidget(QLabel("到"))
        x_range_layout.addWidget(self.x_max_spin)
        
        props_layout.addRow("X范围:", x_range_layout)
        
        right_layout.addWidget(props_group)
        
        # 视图控制
        view_group = QGroupBox("视图控制")
        view_layout = QVBoxLayout(view_group)
        
        view_button_layout = QHBoxLayout()
        
        self.zoom_fit_button = QPushButton("适应窗口")
        self.zoom_fit_button.clicked.connect(self.zoom_to_fit)
        
        self.reset_view_button = QPushButton("重置视图")
        self.reset_view_button.clicked.connect(self.reset_view)
        
        view_button_layout.addWidget(self.zoom_fit_button)
        view_button_layout.addWidget(self.reset_view_button)
        
        view_layout.addLayout(view_button_layout)
        
        # 网格和坐标轴
        grid_layout = QHBoxLayout()
        
        self.show_grid_checkbox = QCheckBox("显示网格")
        self.show_grid_checkbox.setChecked(True)
        self.show_grid_checkbox.toggled.connect(self.on_grid_toggled)
        
        self.show_axes_checkbox = QCheckBox("显示坐标轴")
        self.show_axes_checkbox.setChecked(True)
        self.show_axes_checkbox.toggled.connect(self.on_axes_toggled)
        
        grid_layout.addWidget(self.show_grid_checkbox)
        grid_layout.addWidget(self.show_axes_checkbox)
        
        view_layout.addLayout(grid_layout)
        
        right_layout.addWidget(view_group)
        right_layout.addStretch()
        
        # 组合布局
        layout.addLayout(left_layout)
        layout.addLayout(right_layout)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 初始状态
        self.selected_function = None
        self.update_property_controls()
    
    def refresh_function_list(self):
        """刷新函数列表"""
        self.function_list.clear()
        
        for i, func in enumerate(self.function_canvas.functions):
            item = QListWidgetItem(func.name)
            item.setData(Qt.UserRole, func)
            
            # 设置颜色指示器
            color_icon = QIcon()
            pixmap = QIcon().pixmap(16, 16)
            pixmap.fill(func.color)
            color_icon.addPixmap(pixmap)
            item.setIcon(color_icon)
            
            # 设置可见性
            if not func.visible:
                item.setText(f"[隐藏] {func.name}")
            
            self.function_list.addItem(item)
    
    def on_function_selected(self, current, previous):
        """函数选中时的处理"""
        if current:
            self.selected_function = current.data(Qt.UserRole)
            self.function_canvas.selected_function = self.selected_function
            self.function_canvas.update()
        else:
            self.selected_function = None
            self.function_canvas.selected_function = None
        
        self.update_property_controls()
    
    def update_property_controls(self):
        """更新属性控件"""
        enabled = self.selected_function is not None
        
        self.visible_checkbox.setEnabled(enabled)
        self.color_button.setEnabled(enabled)
        self.width_spin.setEnabled(enabled)
        self.x_min_spin.setEnabled(enabled)
        self.x_max_spin.setEnabled(enabled)
        
        if self.selected_function:
            # 阻止信号
            self.visible_checkbox.blockSignals(True)
            self.width_spin.blockSignals(True)
            self.x_min_spin.blockSignals(True)
            self.x_max_spin.blockSignals(True)
            
            self.visible_checkbox.setChecked(self.selected_function.visible)
            self.width_spin.setValue(self.selected_function.line_width)
            self.x_min_spin.setValue(self.selected_function.x_min)
            self.x_max_spin.setValue(self.selected_function.x_max)
            
            # 更新颜色按钮
            self.color_button.setStyleSheet(f"background-color: {self.selected_function.color.name()};")
            
            # 恢复信号
            self.visible_checkbox.blockSignals(False)
            self.width_spin.blockSignals(False)
            self.x_min_spin.blockSignals(False)
            self.x_max_spin.blockSignals(False)
    
    def add_function(self):
        """添加函数"""
        dialog = FunctionInputDialog(self)
        dialog.function_added.connect(self.on_function_added)
        dialog.exec_()
    
    def on_function_added(self, expression, color, x_min, x_max):
        """处理函数添加"""
        try:
            self.function_canvas.add_function(expression, color, x_min, x_max)
            self.refresh_function_list()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加函数失败: {str(e)}")
    
    def edit_function(self):
        """编辑函数"""
        if not self.selected_function:
            return
        
        dialog = FunctionInputDialog(self, self.selected_function)
        dialog.function_added.connect(self.on_function_edited)
        dialog.exec_()
    
    def on_function_edited(self, expression, color, x_min, x_max):
        """处理函数编辑"""
        if not self.selected_function:
            return
        
        try:
            # 更新函数属性
            self.selected_function.expression = expression
            self.selected_function.color = color
            self.selected_function.x_min = x_min
            self.selected_function.x_max = x_max
            self.selected_function.name = f"f(x) = {expression}"
            
            # 重新计算点
            self.selected_function.calculate_points()
            
            # 刷新界面
            self.refresh_function_list()
            self.function_canvas.update()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"编辑函数失败: {str(e)}")
    
    def delete_function(self):
        """删除函数"""
        if not self.selected_function:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除函数 {self.selected_function.name} 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.function_canvas.remove_function(self.selected_function)
            self.refresh_function_list()
    
    def clear_functions(self):
        """清空所有函数"""
        if not self.function_canvas.functions:
            return
        
        reply = QMessageBox.question(
            self, "确认清空", 
            "确定要清空所有函数吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.function_canvas.clear_functions()
            self.refresh_function_list()
    
    def on_visibility_changed(self, visible):
        """可见性改变"""
        if self.selected_function:
            self.selected_function.visible = visible
            self.function_canvas.update()
            self.refresh_function_list()
    
    def change_color(self):
        """改变颜色"""
        if not self.selected_function:
            return
        
        color = QColorDialog.getColor(self.selected_function.color, self, "选择函数颜色")
        if color.isValid():
            self.selected_function.color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()};")
            self.function_canvas.update()
            self.refresh_function_list()
    
    def on_width_changed(self, width):
        """线宽改变"""
        if self.selected_function:
            self.selected_function.line_width = width
            self.function_canvas.update()
    
    def on_range_changed(self):
        """范围改变"""
        if self.selected_function:
            x_min = self.x_min_spin.value()
            x_max = self.x_max_spin.value()
            
            if x_min < x_max:
                self.selected_function.x_min = x_min
                self.selected_function.x_max = x_max
                self.selected_function.calculate_points()
                self.function_canvas.update()
    
    def zoom_to_fit(self):
        """适应窗口"""
        self.function_canvas.zoom_to_fit()
    
    def reset_view(self):
        """重置视图"""
        self.function_canvas.set_view_range(-10, 10, -10, 10)
    
    def on_grid_toggled(self, show):
        """网格切换"""
        self.function_canvas.show_grid = show
        self.function_canvas.update()
    
    def on_axes_toggled(self, show):
        """坐标轴切换"""
        self.function_canvas.show_axes = show
        self.function_canvas.update()
