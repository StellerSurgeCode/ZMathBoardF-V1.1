#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QPushButton, QLineEdit, QGroupBox, QScrollArea,
    QListWidget, QListWidgetItem, QMessageBox, QSplitter,
    QComboBox, QSpinBox, QCheckBox, QFrame, QWidget, QFormLayout
)
from PyQt5.QtGui import QFont, QColor, QTextCursor, QIcon
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer
import re
import random

from .function_plotter import FunctionCanvas

class AIFunctionDialog(QDialog):
    """AI函数绘图对话框"""
    
    function_generated = pyqtSignal(str, QColor, float, float)  # 表达式, 颜色, x_min, x_max
    
    def __init__(self, function_canvas: FunctionCanvas, parent=None):
        super().__init__(parent)
        self.function_canvas = function_canvas
        
        # AI建议的函数类型 - 先初始化模板
        self.function_templates = {
            "多项式函数": [
                ("线性函数", "2*x + 1", "y = ax + b"),
                ("二次函数", "x**2 - 2*x + 1", "y = ax² + bx + c"),
                ("三次函数", "x**3 - 3*x", "y = ax³ + bx² + cx + d"),
                ("四次函数", "x**4 - 2*x**2 + 1", "y = ax⁴ + bx³ + cx² + dx + e")
            ],
            "三角函数": [
                ("正弦函数", "sin(x)", "y = sin(x)"),
                ("余弦函数", "cos(x)", "y = cos(x)"),
                ("正切函数", "tan(x)", "y = tan(x)"),
                ("复合三角函数", "sin(2*x) + cos(x)", "y = sin(ax) + cos(bx)")
            ],
            "指数对数函数": [
                ("指数函数", "exp(x)", "y = eˣ"),
                ("对数函数", "log(x)", "y = ln(x)"),
                ("常用对数", "log10(x)", "y = log₁₀(x)"),
                ("指数衰减", "exp(-x)", "y = e⁻ˣ")
            ],
            "复合函数": [
                ("幂函数", "x**0.5", "y = x^n"),
                ("绝对值函数", "abs(x)", "y = |x|"),
                ("分段函数", "x if x > 0 else -x", "y = |x|的另一种写法"),
                ("复杂函数", "sin(x) * exp(-x/5)", "y = sin(x)·e^(-x/5)")
            ]
        }
        
        # 颜色预设
        self.color_presets = [
            QColor(255, 0, 0),    # 红色
            QColor(0, 255, 0),    # 绿色
            QColor(0, 0, 255),    # 蓝色
            QColor(255, 165, 0),  # 橙色
            QColor(128, 0, 128),  # 紫色
            QColor(255, 192, 203), # 粉色
            QColor(0, 255, 255),  # 青色
            QColor(165, 42, 42),  # 棕色
        ]
        
        # 设置UI
        self.setup_ui()
        
        # 设置模板
        self.setup_templates()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("AI函数绘图助手")
        self.setModal(False)
        self.resize(800, 600)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 左侧：AI建议和模板
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # AI建议组
        ai_group = QGroupBox("AI函数建议")
        ai_layout = QVBoxLayout(ai_group)
        
        # 函数类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("函数类型:"))
        
        self.function_type_combo = QComboBox()
        self.function_type_combo.addItems(list(self.function_templates.keys()))
        self.function_type_combo.currentTextChanged.connect(self.update_function_list)
        type_layout.addWidget(self.function_type_combo)
        
        ai_layout.addLayout(type_layout)
        
        # 函数列表
        self.function_list = QListWidget()
        self.function_list.itemClicked.connect(self.on_template_selected)
        ai_layout.addWidget(self.function_list)
        
        # 智能建议按钮
        suggest_layout = QHBoxLayout()
        
        self.smart_suggest_btn = QPushButton("智能建议")
        self.smart_suggest_btn.clicked.connect(self.smart_suggest)
        
        self.random_function_btn = QPushButton("随机函数")
        self.random_function_btn.clicked.connect(self.generate_random_function)
        
        suggest_layout.addWidget(self.smart_suggest_btn)
        suggest_layout.addWidget(self.random_function_btn)
        
        ai_layout.addLayout(suggest_layout)
        
        left_layout.addWidget(ai_group)
        
        # 快速设置组
        quick_group = QGroupBox("快速设置")
        quick_layout = QVBoxLayout(quick_group)
        
        # 函数属性设置
        attrs_layout = QVBoxLayout()
        
        # X范围快速设置
        x_range_layout = QHBoxLayout()
        x_range_layout.addWidget(QLabel("X范围:"))
        
        self.quick_x_combo = QComboBox()
        self.quick_x_combo.addItems([
            "[-10, 10]", "[-5, 5]", "[-π, π]", "[-2π, 2π]", 
            "[0, 10]", "[0, 2π]", "[-1, 1]", "自定义"
        ])
        self.quick_x_combo.currentTextChanged.connect(self.apply_quick_x_range)
        x_range_layout.addWidget(self.quick_x_combo)
        
        attrs_layout.addLayout(x_range_layout)
        
        # 颜色快速选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("颜色:"))
        
        self.current_color_index = 0
        self.color_preview = QPushButton()
        self.color_preview.setFixedSize(30, 20)
        self.update_color_preview()
        self.color_preview.clicked.connect(self.cycle_color)
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(QLabel("(点击切换)"))
        color_layout.addStretch()
        
        attrs_layout.addLayout(color_layout)
        
        # 叠加选项
        self.overlay_checkbox = QCheckBox("叠加到现有函数")
        self.overlay_checkbox.setChecked(True)
        attrs_layout.addWidget(self.overlay_checkbox)
        
        quick_layout.addLayout(attrs_layout)
        left_layout.addWidget(quick_group)
        
        splitter.addWidget(left_widget)
        
        # 右侧：输入和预览
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 输入组
        input_group = QGroupBox("函数输入")
        input_layout = QVBoxLayout(input_group)
        
        # 函数表达式输入
        expr_layout = QHBoxLayout()
        expr_layout.addWidget(QLabel("f(x) = "))
        
        self.expression_edit = QLineEdit()
        self.expression_edit.setPlaceholderText("输入函数表达式...")
        self.expression_edit.textChanged.connect(self.validate_expression)
        expr_layout.addWidget(self.expression_edit)
        
        input_layout.addLayout(expr_layout)
        
        # 参数设置
        params_layout = QHBoxLayout()
        
        params_layout.addWidget(QLabel("X范围:"))
        self.x_min_edit = QLineEdit("-10")
        self.x_min_edit.setFixedWidth(60)
        params_layout.addWidget(self.x_min_edit)
        
        params_layout.addWidget(QLabel("到"))
        self.x_max_edit = QLineEdit("10")
        self.x_max_edit.setFixedWidth(60)
        params_layout.addWidget(self.x_max_edit)
        
        params_layout.addStretch()
        
        input_layout.addLayout(params_layout)
        
        # 验证结果显示
        self.validation_label = QLabel("✓ 表达式有效")
        self.validation_label.setStyleSheet("color: green;")
        input_layout.addWidget(self.validation_label)
        
        right_layout.addWidget(input_group)
        
        # 预览组
        preview_group = QGroupBox("函数预览")
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_canvas = FunctionCanvas()
        self.preview_canvas.setFixedHeight(300)
        preview_layout.addWidget(self.preview_canvas)
        
        right_layout.addWidget(preview_group)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("预览")
        self.preview_btn.clicked.connect(self.preview_function)
        
        self.add_btn = QPushButton("添加到画布")
        self.add_btn.clicked.connect(self.add_function)
        
        self.clear_preview_btn = QPushButton("清除预览")
        self.clear_preview_btn.clicked.connect(self.clear_preview)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.clear_preview_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        
        right_layout.addLayout(button_layout)
        
        splitter.addWidget(right_widget)
        
        # 设置分割器比例
        splitter.setSizes([300, 500])
        
        # 默认函数
        self.expression_edit.setText("sin(x)")
        self.update_function_list()
    
    def setup_templates(self):
        """设置函数模板"""
        self.update_function_list()
    
    def update_function_list(self):
        """更新函数列表"""
        self.function_list.clear()
        
        current_type = self.function_type_combo.currentText()
        if current_type in self.function_templates:
            for name, expr, desc in self.function_templates[current_type]:
                item = QListWidgetItem(f"{name}\n{desc}")
                item.setData(Qt.UserRole, expr)
                self.function_list.addItem(item)
    
    def on_template_selected(self, item):
        """模板被选中"""
        expression = item.data(Qt.UserRole)
        self.expression_edit.setText(expression)
    
    def smart_suggest(self):
        """智能建议函数"""
        # 根据已有函数智能建议新函数
        existing_count = len(self.function_canvas.functions)
        
        suggestions = []
        
        if existing_count == 0:
            # 第一个函数建议基础函数
            suggestions = [
                ("基础二次函数", "x**2"),
                ("基础正弦函数", "sin(x)"),
                ("基础线性函数", "2*x + 1")
            ]
        elif existing_count <= 2:
            # 前几个函数建议互补的函数
            suggestions = [
                ("指数函数", "exp(x/2)"),
                ("对数函数", "log(abs(x) + 1)"),
                ("三角复合", "sin(x) + cos(x/2)")
            ]
        else:
            # 更多函数时建议复杂的组合
            suggestions = [
                ("波浪函数", "sin(x) * cos(x/2)"),
                ("衰减振荡", "exp(-x/10) * sin(x)"),
                ("抛物振荡", "x**2 * sin(x/2)")
            ]
        
        # 随机选择一个建议
        if suggestions:
            name, expr = random.choice(suggestions)
            self.expression_edit.setText(expr)
            self.validation_label.setText(f"✨ AI建议: {name}")
            self.validation_label.setStyleSheet("color: blue;")
    
    def generate_random_function(self):
        """生成随机函数"""
        # 随机选择函数类型和参数
        function_types = [
            lambda: f"{random.uniform(0.5, 3):.1f}*x**{random.randint(2, 4)}",
            lambda: f"sin({random.uniform(0.5, 3):.1f}*x)",
            lambda: f"cos({random.uniform(0.5, 3):.1f}*x)",
            lambda: f"exp({random.uniform(-1, 1):.1f}*x)",
            lambda: f"log(abs(x) + {random.uniform(0.1, 2):.1f})",
            lambda: f"abs(x)**{random.uniform(0.5, 2):.1f}",
        ]
        
        random_func = random.choice(function_types)()
        self.expression_edit.setText(random_func)
        
        # 随机选择颜色
        self.current_color_index = random.randint(0, len(self.color_presets) - 1)
        self.update_color_preview()
    
    def apply_quick_x_range(self, range_text):
        """应用快速X范围设置"""
        import math
        
        range_map = {
            "[-10, 10]": (-10, 10),
            "[-5, 5]": (-5, 5),
            "[-π, π]": (-math.pi, math.pi),
            "[-2π, 2π]": (-2*math.pi, 2*math.pi),
            "[0, 10]": (0, 10),
            "[0, 2π]": (0, 2*math.pi),
            "[-1, 1]": (-1, 1),
        }
        
        if range_text in range_map:
            x_min, x_max = range_map[range_text]
            self.x_min_edit.setText(f"{x_min:.2f}")
            self.x_max_edit.setText(f"{x_max:.2f}")
    
    def update_color_preview(self):
        """更新颜色预览"""
        color = self.color_presets[self.current_color_index]
        self.color_preview.setStyleSheet(f"background-color: {color.name()};")
    
    def cycle_color(self):
        """循环切换颜色"""
        self.current_color_index = (self.current_color_index + 1) % len(self.color_presets)
        self.update_color_preview()
    
    def validate_expression(self):
        """验证表达式"""
        expression = self.expression_edit.text().strip()
        
        if not expression:
            self.validation_label.setText("请输入函数表达式")
            self.validation_label.setStyleSheet("color: gray;")
            return False
        
        try:
            # 简单验证：尝试计算一个点
            from .function_plotter import FunctionExpression
            test_func = FunctionExpression(expression)
            test_value = test_func.evaluate(1.0)
            
            if not (hasattr(test_value, '__class__') and test_value.__class__.__name__ == 'float'):
                raise ValueError("表达式计算结果无效")
            
            self.validation_label.setText("✓ 表达式有效")
            self.validation_label.setStyleSheet("color: green;")
            return True
            
        except Exception as e:
            self.validation_label.setText(f"✗ 表达式错误: 请检查语法")
            self.validation_label.setStyleSheet("color: red;")
            return False
    
    def preview_function(self):
        """预览函数"""
        if not self.validate_expression():
            return
        
        try:
            expression = self.expression_edit.text().strip()
            x_min = float(self.x_min_edit.text())
            x_max = float(self.x_max_edit.text())
            
            if x_min >= x_max:
                QMessageBox.warning(self, "参数错误", "X范围的最小值必须小于最大值")
                return
            
            # 清除预览画布
            self.preview_canvas.clear_functions()
            
            # 添加函数到预览
            color = self.color_presets[self.current_color_index]
            func = self.preview_canvas.add_function(expression, color, x_min, x_max)
            
            # 自动调整视图
            self.preview_canvas.zoom_to_fit()
            
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", "请检查X范围参数是否为有效数字")
        except Exception as e:
            QMessageBox.critical(self, "预览错误", f"预览函数时出错：{str(e)}")
    
    def add_function(self):
        """添加函数到主画布"""
        if not self.validate_expression():
            return
        
        try:
            expression = self.expression_edit.text().strip()
            x_min = float(self.x_min_edit.text())
            x_max = float(self.x_max_edit.text())
            
            if x_min >= x_max:
                QMessageBox.warning(self, "参数错误", "X范围的最小值必须小于最大值")
                return
            
            # 获取颜色
            color = self.color_presets[self.current_color_index]
            
            # 检查是否清除现有函数
            if not self.overlay_checkbox.isChecked():
                self.function_canvas.clear_functions()
            
            # 发射信号添加函数
            self.function_generated.emit(expression, color, x_min, x_max)
            
            # 显示成功消息
            QMessageBox.information(self, "成功", f"函数 f(x) = {expression} 已添加到画布")
            
            # 自动切换到下一个颜色
            self.cycle_color()
            
        except ValueError as e:
            QMessageBox.warning(self, "参数错误", "请检查X范围参数是否为有效数字")
        except Exception as e:
            QMessageBox.critical(self, "添加错误", f"添加函数时出错：{str(e)}")
    
    def clear_preview(self):
        """清除预览"""
        self.preview_canvas.clear_functions()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 保存对话框状态或清理资源
        event.accept()
