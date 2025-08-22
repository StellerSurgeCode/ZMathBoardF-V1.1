#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QComboBox, QTextEdit, QGroupBox, QFormLayout,
    QDoubleSpinBox, QListWidget, QListWidgetItem, QTabWidget,
    QWidget, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor

from .function_plotter import FunctionExpression

class FunctionAnalyzer:
    """函数分析器 - 用于计算函数的各种属性"""
    
    @staticmethod
    def find_intersections(func1: FunctionExpression, func2: FunctionExpression, 
                          x_start: float = -10, x_end: float = 10, precision: float = 0.001) -> List[Tuple[float, float]]:
        """寻找两个函数的交点"""
        intersections = []
        
        # 使用数值方法寻找交点
        x_values = np.linspace(x_start, x_end, int((x_end - x_start) / precision))
        
        prev_diff = None
        for i, x in enumerate(x_values):
            try:
                y1 = func1.evaluate(x)
                y2 = func2.evaluate(x)
                
                if math.isnan(y1) or math.isnan(y2) or math.isinf(y1) or math.isinf(y2):
                    continue
                
                diff = y1 - y2
                
                # 检查符号变化（穿越零点）
                if prev_diff is not None and prev_diff * diff < 0:
                    # 使用二分法精确定位交点
                    x_precise = FunctionAnalyzer._binary_search_intersection(
                        func1, func2, x_values[i-1], x, precision / 10
                    )
                    if x_precise is not None:
                        y_precise = func1.evaluate(x_precise)
                        if not (math.isnan(y_precise) or math.isinf(y_precise)):
                            intersections.append((x_precise, y_precise))
                
                prev_diff = diff
                
            except:
                continue
        
        # 去除重复的交点
        unique_intersections = []
        for intersection in intersections:
            is_unique = True
            for existing in unique_intersections:
                if abs(intersection[0] - existing[0]) < precision * 10:
                    is_unique = False
                    break
            if is_unique:
                unique_intersections.append(intersection)
        
        return unique_intersections
    
    @staticmethod
    def _binary_search_intersection(func1: FunctionExpression, func2: FunctionExpression,
                                   x_left: float, x_right: float, tolerance: float) -> Optional[float]:
        """二分法精确定位交点"""
        for _ in range(50):  # 最多迭代50次
            x_mid = (x_left + x_right) / 2
            
            try:
                diff_left = func1.evaluate(x_left) - func2.evaluate(x_left)
                diff_mid = func1.evaluate(x_mid) - func2.evaluate(x_mid)
                
                if abs(diff_mid) < tolerance:
                    return x_mid
                
                if diff_left * diff_mid < 0:
                    x_right = x_mid
                else:
                    x_left = x_mid
                    
                if abs(x_right - x_left) < tolerance:
                    return x_mid
                    
            except:
                return None
        
        return None
    
    @staticmethod
    def find_extrema(func: FunctionExpression, x_start: float = -10, x_end: float = 10, 
                    step: float = 0.01) -> Dict[str, List[Tuple[float, float]]]:
        """寻找函数的极值点"""
        extrema = {"maxima": [], "minima": []}
        
        x_values = np.linspace(x_start, x_end, int((x_end - x_start) / step))
        y_values = []
        
        # 计算函数值
        for x in x_values:
            try:
                y = func.evaluate(x)
                if not (math.isnan(y) or math.isinf(y)):
                    y_values.append(y)
                else:
                    y_values.append(None)
            except:
                y_values.append(None)
        
        # 寻找局部极值
        for i in range(1, len(y_values) - 1):
            if y_values[i] is None:
                continue
                
            prev_y = y_values[i-1]
            next_y = y_values[i+1]
            
            if prev_y is None or next_y is None:
                continue
            
            current_y = y_values[i]
            
            # 局部最大值
            if current_y > prev_y and current_y > next_y:
                extrema["maxima"].append((x_values[i], current_y))
            
            # 局部最小值
            elif current_y < prev_y and current_y < next_y:
                extrema["minima"].append((x_values[i], current_y))
        
        return extrema
    
    @staticmethod
    def get_function_range(func: FunctionExpression, x_start: float = -10, x_end: float = 10) -> Dict[str, float]:
        """获取函数在给定区间的值域"""
        x_values = np.linspace(x_start, x_end, 1000)
        y_values = []
        
        for x in x_values:
            try:
                y = func.evaluate(x)
                if not (math.isnan(y) or math.isinf(y)):
                    y_values.append(y)
            except:
                continue
        
        if not y_values:
            return {"min": float('nan'), "max": float('nan')}
        
        return {"min": min(y_values), "max": max(y_values)}

class FunctionQueryDialog(QDialog):
    """函数查询对话框"""
    
    def __init__(self, functions: List[FunctionExpression], parent=None):
        super().__init__(parent)
        self.functions = functions
        self.setup_ui()
    
    def setup_ui(self):
        """设置user界面"""
        self.setWindowTitle("函数查询工具")
        self.setMinimumSize(500, 400)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("函数查询工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 点查询选项卡
        self.create_point_query_tab(tab_widget)
        
        # 函数信息选项卡
        self.create_function_info_tab(tab_widget)
        
        # 交点分析选项卡
        self.create_intersection_tab(tab_widget)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
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
            QTextEdit, QTableWidget {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                background-color: white;
            }
        """)
    
    def create_point_query_tab(self, tab_widget):
        """创建点查询选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 函数选择
        func_group = QGroupBox("选择函数")
        func_layout = QFormLayout(func_group)
        
        self.function_combo = QComboBox()
        for i, func in enumerate(self.functions):
            self.function_combo.addItem(f"{func.name}", i)
        func_layout.addRow("函数:", self.function_combo)
        
        layout.addWidget(func_group)
        
        # X值输入
        input_group = QGroupBox("查询参数")
        input_layout = QFormLayout(input_group)
        
        self.x_input = QDoubleSpinBox()
        self.x_input.setRange(-1000, 1000)
        self.x_input.setDecimals(4)
        self.x_input.setValue(0)
        input_layout.addRow("x值:", self.x_input)
        
        query_button = QPushButton("查询y值")
        query_button.clicked.connect(self.query_point)
        input_layout.addRow("", query_button)
        
        layout.addWidget(input_group)
        
        # 结果显示
        result_group = QGroupBox("查询结果")
        result_layout = QVBoxLayout(result_group)
        
        self.result_text = QTextEdit()
        self.result_text.setMaximumHeight(150)
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        
        layout.addWidget(result_group)
        layout.addStretch()
        
        tab_widget.addTab(widget, "点查询")
    
    def create_function_info_tab(self, tab_widget):
        """创建函数信息选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 函数选择
        func_group = QGroupBox("选择函数")
        func_layout = QFormLayout(func_group)
        
        self.info_function_combo = QComboBox()
        for i, func in enumerate(self.functions):
            self.info_function_combo.addItem(f"{func.name}", i)
        func_layout.addRow("函数:", self.info_function_combo)
        
        analyze_button = QPushButton("分析函数")
        analyze_button.clicked.connect(self.analyze_function)
        func_layout.addRow("", analyze_button)
        
        layout.addWidget(func_group)
        
        # 信息显示
        info_group = QGroupBox("函数信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(info_group)
        
        tab_widget.addTab(widget, "函数信息")
    
    def create_intersection_tab(self, tab_widget):
        """创建交点分析选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 函数选择
        func_group = QGroupBox("选择两个函数")
        func_layout = QFormLayout(func_group)
        
        self.func1_combo = QComboBox()
        self.func2_combo = QComboBox()
        
        for i, func in enumerate(self.functions):
            self.func1_combo.addItem(f"{func.name}", i)
            self.func2_combo.addItem(f"{func.name}", i)
        
        func_layout.addRow("函数1:", self.func1_combo)
        func_layout.addRow("函数2:", self.func2_combo)
        
        intersection_button = QPushButton("查找交点")
        intersection_button.clicked.connect(self.find_intersections)
        func_layout.addRow("", intersection_button)
        
        layout.addWidget(func_group)
        
        # 交点显示
        intersection_group = QGroupBox("交点信息")
        intersection_layout = QVBoxLayout(intersection_group)
        
        self.intersection_table = QTableWidget()
        self.intersection_table.setColumnCount(2)
        self.intersection_table.setHorizontalHeaderLabels(["X坐标", "Y坐标"])
        self.intersection_table.horizontalHeader().setStretchLastSection(True)
        intersection_layout.addWidget(self.intersection_table)
        
        layout.addWidget(intersection_group)
        
        tab_widget.addTab(widget, "交点分析")
    
    def query_point(self):
        """查询点的y值"""
        if not self.functions:
            self.result_text.setText("没有可用的函数")
            return
        
        func_index = self.function_combo.currentData()
        if func_index is None:
            return
            
        func = self.functions[func_index]
        x_value = self.x_input.value()
        
        try:
            y_value = func.evaluate(x_value)
            
            if math.isnan(y_value):
                result = f"函数 {func.name} 在 x = {x_value} 处未定义"
            elif math.isinf(y_value):
                result = f"函数 {func.name} 在 x = {x_value} 处趋于无穷大"
            else:
                result = f"函数 {func.name} 在 x = {x_value} 处的值为 y = {y_value:.6f}"
            
            self.result_text.setText(result)
            
        except Exception as e:
            self.result_text.setText(f"计算错误: {str(e)}")
    
    def analyze_function(self):
        """分析函数信息"""
        if not self.functions:
            self.info_text.setText("没有可用的函数")
            return
        
        func_index = self.info_function_combo.currentData()
        if func_index is None:
            return
            
        func = self.functions[func_index]
        
        try:
            # 基本信息
            info = f"函数: {func.name}\n"
            info += f"表达式: f(x) = {func.expression}\n"
            info += f"定义域: [{func.x_min:.2f}, {func.x_max:.2f}]\n"
            info += f"颜色: {func.color.name()}\n"
            info += f"线宽: {func.line_width}px\n\n"
            
            # 值域分析
            range_info = FunctionAnalyzer.get_function_range(func, func.x_min, func.x_max)
            if not math.isnan(range_info["min"]):
                info += f"值域: [{range_info['min']:.4f}, {range_info['max']:.4f}]\n\n"
            else:
                info += "值域: 无法计算\n\n"
            
            # 极值分析
            extrema = FunctionAnalyzer.find_extrema(func, func.x_min, func.x_max)
            
            if extrema["maxima"]:
                info += "局部最大值:\n"
                for x, y in extrema["maxima"]:
                    info += f"  ({x:.4f}, {y:.4f})\n"
                info += "\n"
            
            if extrema["minima"]:
                info += "局部最小值:\n"
                for x, y in extrema["minima"]:
                    info += f"  ({x:.4f}, {y:.4f})\n"
                info += "\n"
            
            if not extrema["maxima"] and not extrema["minima"]:
                info += "在当前定义域内未发现局部极值\n\n"
            
            # 与其他函数的交点
            intersections_count = 0
            for other_func in self.functions:
                if other_func != func:
                    intersections = FunctionAnalyzer.find_intersections(func, other_func, func.x_min, func.x_max)
                    if intersections:
                        intersections_count += len(intersections)
            
            info += f"与其他函数的交点数量: {intersections_count}"
            
            self.info_text.setText(info)
            
        except Exception as e:
            self.info_text.setText(f"分析错误: {str(e)}")
    
    def find_intersections(self):
        """查找两个函数的交点"""
        if len(self.functions) < 2:
            QMessageBox.warning(self, "错误", "需要至少两个函数才能查找交点")
            return
        
        func1_index = self.func1_combo.currentData()
        func2_index = self.func2_combo.currentData()
        
        if func1_index is None or func2_index is None:
            return
        
        if func1_index == func2_index:
            QMessageBox.warning(self, "错误", "请选择两个不同的函数")
            return
        
        func1 = self.functions[func1_index]
        func2 = self.functions[func2_index]
        
        try:
            # 计算交点
            x_min = max(func1.x_min, func2.x_min)
            x_max = min(func1.x_max, func2.x_max)
            
            intersections = FunctionAnalyzer.find_intersections(func1, func2, x_min, x_max)
            
            # 显示结果
            self.intersection_table.setRowCount(len(intersections))
            
            for i, (x, y) in enumerate(intersections):
                self.intersection_table.setItem(i, 0, QTableWidgetItem(f"{x:.6f}"))
                self.intersection_table.setItem(i, 1, QTableWidgetItem(f"{y:.6f}"))
            
            if not intersections:
                QMessageBox.information(self, "结果", "在指定范围内未找到交点")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算交点时出错: {str(e)}")
