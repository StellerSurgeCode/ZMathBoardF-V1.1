#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QColorDialog, QDoubleSpinBox, QCheckBox,
    QComboBox, QListWidget, QListWidgetItem, QGroupBox,
    QMessageBox, QDialog, QDialogButtonBox, QTextEdit,
    QSpinBox, QFrame, QScrollArea
)
from PyQt5.QtGui import QColor, QPainter, QPen, QFont, QBrush
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
import re

class FunctionExpression:
    """函数表达式类"""
    
    def __init__(self, expression: str, color: QColor = None, x_min: float = -10, x_max: float = 10):
        self.expression = expression
        self.color = color or QColor(0, 100, 200)
        self.x_min = x_min
        self.x_max = x_max
        self.visible = True
        self.name = f"f(x) = {expression}"
        self.line_width = 2
        self.points = []  # 缓存计算的点
        self.valid = True
        self.error_message = ""
        
    def evaluate(self, x: float) -> float:
        """计算函数在x处的值"""
        try:
            # 替换常见的数学函数和常数
            safe_expression = self.expression.replace('^', '**')
            
            # 支持的数学函数
            safe_dict = {
                'x': x,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'asin': math.asin,
                'acos': math.acos,
                'atan': math.atan,
                'sinh': math.sinh,
                'cosh': math.cosh,
                'tanh': math.tanh,
                'exp': math.exp,
                'log': math.log,
                'log10': math.log10,
                'sqrt': math.sqrt,
                'abs': abs,
                'pi': math.pi,
                'e': math.e,
                'pow': pow,
                'floor': math.floor,
                'ceil': math.ceil,
                'round': round,
            }
            
            # 评估表达式
            result = eval(safe_expression, {"__builtins__": {}}, safe_dict)
            return float(result) if result is not None else float('nan')
            
        except Exception as e:
            return float('nan')
    
    def calculate_points(self, resolution: int = 1000) -> List[QPointF]:
        """计算函数图像的点"""
        points = []
        dx = (self.x_max - self.x_min) / resolution
        
        for i in range(resolution + 1):
            x = self.x_min + i * dx
            y = self.evaluate(x)
            
            if not math.isnan(y) and not math.isinf(y):
                points.append(QPointF(x, y))
            else:
                # if遇到不连续点，添加分隔符
                if points and points[-1] is not None:
                    points.append(None)
        
        self.points = points
        return points
    
    def is_valid_expression(self) -> bool:
        """检查表达式是否有效"""
        try:
            # 测试计算一个点
            test_value = self.evaluate(0)
            self.valid = not (math.isnan(test_value) and self.expression.strip() != "")
            return self.valid
        except:
            self.valid = False
            return False

class FunctionCanvas(QWidget):
    """函数图像画布"""
    
    function_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        
        # 函数列表
        self.functions = []  # List[FunctionExpression]
        self.selected_function = None
        
        # 动点列表
        self.dynamic_points = []  # List[DynamicPoint]
        
        # 画布设置
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        
        # 坐标系设置
        self.x_min = -10.0
        self.x_max = 10.0
        self.y_min = -10.0
        self.y_max = 10.0
        
        # 网格和坐标轴设置
        self.show_grid = True
        self.show_axes = True
        self.grid_color = QColor(200, 200, 200)
        self.axes_color = QColor(0, 0, 0)
        
        # 鼠标交互
        self.dragging = False
        self.last_pos = None
        
        # 背景色
        self.setStyleSheet("background-color: white;")
        
        # 长宽比控制
        self.maintain_aspect_ratio = True  # 默认保持长宽比
        
        # 初始调整长宽比（延迟执行，确保画布尺寸已设置）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.adjust_aspect_ratio)
        
    def add_function(self, expression: str, color: QColor = None, x_min: float = -10, x_max: float = 10) -> FunctionExpression:
        """添加函数"""
        func = FunctionExpression(expression, color, x_min, x_max)
        if func.is_valid_expression():
            self.functions.append(func)
            func.calculate_points()
            self.update()
            return func
        else:
            raise ValueError(f"无效的函数表达式: {expression}")
    
    def remove_function(self, func: FunctionExpression):
        """移除函数"""
        if func in self.functions:
            self.functions.remove(func)
            if self.selected_function == func:
                self.selected_function = None
            self.update()
    
    def add_dynamic_point(self, point):
        """添加动点"""
        self.dynamic_points.append(point)
        point.position_changed.connect(self.update)
        self.update()
    
    def remove_dynamic_point(self, point):
        """移除动点"""
        if point in self.dynamic_points:
            self.dynamic_points.remove(point)
            point.position_changed.disconnect(self.update)
            self.update()
    
    def clear_functions(self):
        """清除所有函数"""
        self.functions.clear()
        self.selected_function = None
        self.update()
    
    def set_view_range(self, x_min: float, x_max: float, y_min: float, y_max: float, maintain_aspect_ratio: bool = True):
        """设置视图范围
        
        Args:
            x_min, x_max, y_min, y_max: 视图范围
            maintain_aspect_ratio: 是否保持长宽比
        """
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        
        if maintain_aspect_ratio:
            self.adjust_aspect_ratio()
        
        self.update()
    
    def adjust_aspect_ratio(self):
        """调整视图范围以保持正确的长宽比，使圆形显示为圆形"""
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width <= 0 or widget_height <= 0:
            return  # 无效的画布尺寸
        
        # 计算当前视图范围
        view_x_range = self.x_max - self.x_min
        view_y_range = self.y_max - self.y_min
        
        # 计算理想的长宽比（基于屏幕像素比例）
        screen_aspect_ratio = widget_width / widget_height
        view_aspect_ratio = view_x_range / view_y_range
        
        # 调整视图范围以匹配屏幕长宽比
        if view_aspect_ratio > screen_aspect_ratio:
            # 当前Y轴范围太小，需要扩大Y轴范围
            new_y_range = view_x_range / screen_aspect_ratio
            y_center = (self.y_min + self.y_max) / 2
            self.y_min = y_center - new_y_range / 2
            self.y_max = y_center + new_y_range / 2
        else:
            # 当前X轴范围太小，需要扩大X轴范围
            new_x_range = view_y_range * screen_aspect_ratio
            x_center = (self.x_min + self.x_max) / 2
            self.x_min = x_center - new_x_range / 2
            self.x_max = x_center + new_x_range / 2
    
    def screen_to_world(self, screen_point: QPointF) -> QPointF:
        """屏幕坐标转世界坐标"""
        width = self.width()
        height = self.height()
        
        # 计算世界坐标
        world_x = self.x_min + (screen_point.x() / width) * (self.x_max - self.x_min)
        world_y = self.y_max - (screen_point.y() / height) * (self.y_max - self.y_min)
        
        return QPointF(world_x, world_y)
    
    def world_to_screen(self, world_point: QPointF) -> QPointF:
        """世界坐标转屏幕坐标"""
        width = self.width()
        height = self.height()
        
        # 计算屏幕坐标
        screen_x = (world_point.x() - self.x_min) / (self.x_max - self.x_min) * width
        screen_y = (self.y_max - world_point.y()) / (self.y_max - self.y_min) * height
        
        return QPointF(screen_x, screen_y)
    
    def paintEvent(self, event):
        """绘制函数图像"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # 绘制网格
        if self.show_grid:
            self.draw_grid(painter)
        
        # 绘制坐标轴
        if self.show_axes:
            self.draw_axes(painter)
        
        # 绘制函数
        for func in self.functions:
            if func.visible:
                self.draw_function(painter, func)
        
        # 绘制选中函数的高亮
        if self.selected_function:
            self.draw_function_highlight(painter, self.selected_function)
        
        # 绘制动点
        for point in self.dynamic_points:
            if point.visible:
                self.draw_dynamic_point(painter, point)
    
    def draw_grid(self, painter: QPainter):
        """绘制网格"""
        painter.setPen(QPen(self.grid_color, 1, Qt.DotLine))
        
        width = self.width()
        height = self.height()
        
        # 计算网格间距
        x_range = self.x_max - self.x_min
        y_range = self.y_max - self.y_min
        
        # 自适应网格密度
        x_step = self.calculate_grid_step(x_range)
        y_step = self.calculate_grid_step(y_range)
        
        # 绘制垂直网格线
        x = math.ceil(self.x_min / x_step) * x_step
        while x <= self.x_max:
            screen_x = (x - self.x_min) / x_range * width
            painter.drawLine(int(screen_x), 0, int(screen_x), height)
            x += x_step
        
        # 绘制水平网格线
        y = math.ceil(self.y_min / y_step) * y_step
        while y <= self.y_max:
            screen_y = (self.y_max - y) / y_range * height
            painter.drawLine(0, int(screen_y), width, int(screen_y))
            y += y_step
    
    def calculate_grid_step(self, range_val: float) -> float:
        """计算合适的网格步长"""
        if range_val <= 0:
            return 1.0
        
        # 目标网格数量
        target_grids = 10
        
        # 计算基础步长
        base_step = range_val / target_grids
        
        # 调整到合适的数值 (1, 2, 5, 10, 20, 50, 100, ...)
        magnitude = 10 ** math.floor(math.log10(base_step))
        normalized = base_step / magnitude
        
        if normalized <= 1:
            step = 1 * magnitude
        elif normalized <= 2:
            step = 2 * magnitude
        elif normalized <= 5:
            step = 5 * magnitude
        else:
            step = 10 * magnitude
        
        return step
    
    def draw_axes(self, painter: QPainter):
        """绘制坐标轴"""
        painter.setPen(QPen(self.axes_color, 2))
        
        width = self.width()
        height = self.height()
        
        # X轴
        if self.y_min <= 0 <= self.y_max:
            y_screen = (self.y_max - 0) / (self.y_max - self.y_min) * height
            painter.drawLine(0, int(y_screen), width, int(y_screen))
        
        # Y轴
        if self.x_min <= 0 <= self.x_max:
            x_screen = (0 - self.x_min) / (self.x_max - self.x_min) * width
            painter.drawLine(int(x_screen), 0, int(x_screen), height)
        
        # 绘制刻度标签
        self.draw_tick_labels(painter)
    
    def draw_tick_labels(self, painter: QPainter):
        """绘制刻度标签"""
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Arial", 8))
        
        width = self.width()
        height = self.height()
        
        # X轴刻度
        x_step = self.calculate_grid_step(self.x_max - self.x_min)
        x = math.ceil(self.x_min / x_step) * x_step
        
        y_axis_screen = (self.y_max - 0) / (self.y_max - self.y_min) * height
        y_axis_screen = max(15, min(height - 15, y_axis_screen))  # 限制在画布范围内
        
        while x <= self.x_max:
            if abs(x) > 1e-10:  # 跳过原点
                screen_x = (x - self.x_min) / (self.x_max - self.x_min) * width
                painter.drawText(int(screen_x - 15), int(y_axis_screen + 15), f"{x:.1f}")
            x += x_step
        
        # Y轴刻度
        y_step = self.calculate_grid_step(self.y_max - self.y_min)
        y = math.ceil(self.y_min / y_step) * y_step
        
        x_axis_screen = (0 - self.x_min) / (self.x_max - self.x_min) * width
        x_axis_screen = max(25, min(width - 25, x_axis_screen))  # 限制在画布范围内
        
        while y <= self.y_max:
            if abs(y) > 1e-10:  # 跳过原点
                screen_y = (self.y_max - y) / (self.y_max - self.y_min) * height
                painter.drawText(int(x_axis_screen - 25), int(screen_y + 5), f"{y:.1f}")
            y += y_step
    
    def draw_function(self, painter: QPainter, func: FunctionExpression):
        """绘制函数图像"""
        if not func.points:
            func.calculate_points()
        
        if not func.points:
            return
        
        painter.setPen(QPen(func.color, func.line_width))
        
        # 绘制函数曲线
        last_point = None
        for point in func.points:
            if point is None:
                last_point = None
                continue
            
            screen_point = self.world_to_screen(point)
            
            # 检查点是否在屏幕范围内或附近
            if (-100 <= screen_point.x() <= self.width() + 100 and 
                -100 <= screen_point.y() <= self.height() + 100):
                
                if last_point is not None:
                    painter.drawLine(last_point, screen_point)
                
                last_point = screen_point
            else:
                last_point = None
    
    def draw_function_highlight(self, painter: QPainter, func: FunctionExpression):
        """绘制选中函数的高亮效果"""
        if not func.points:
            return
        
        # 绘制高亮边框
        highlight_color = QColor(func.color)
        highlight_color.setAlpha(100)
        painter.setPen(QPen(highlight_color, func.line_width + 2))
        
        last_point = None
        for point in func.points:
            if point is None:
                last_point = None
                continue
            
            screen_point = self.world_to_screen(point)
            
            if (-100 <= screen_point.x() <= self.width() + 100 and 
                -100 <= screen_point.y() <= self.height() + 100):
                
                if last_point is not None:
                    painter.drawLine(last_point, screen_point)
                
                last_point = screen_point
            else:
                last_point = None
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()
            
            # 检查是否点击了函数
            world_pos = self.screen_to_world(QPointF(event.pos()))
            clicked_func = self.get_function_at_point(world_pos)
            
            if clicked_func:
                self.selected_function = clicked_func
                self.function_selected.emit(clicked_func)
                self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and self.last_pos:
            delta = event.pos() - self.last_pos
            
            # 平移视图
            dx = delta.x() / self.width() * (self.x_max - self.x_min)
            dy = delta.y() / self.height() * (self.y_max - self.y_min)
            
            self.x_min -= dx
            self.x_max -= dx
            self.y_min += dy
            self.y_max += dy
            
            self.last_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.last_pos = None
    
    def wheelEvent(self, event):
        """鼠标滚轮事件"""
        # 缩放
        zoom_in = event.angleDelta().y() > 0
        zoom_factor = 0.9 if zoom_in else 1.1
        
        # 获取鼠标位置的世界坐标
        mouse_world = self.screen_to_world(QPointF(event.pos()))
        
        # 计算新的视图范围
        x_center = mouse_world.x()
        y_center = mouse_world.y()
        
        new_x_range = (self.x_max - self.x_min) * zoom_factor
        new_y_range = (self.y_max - self.y_min) * zoom_factor
        
        self.x_min = x_center - new_x_range / 2
        self.x_max = x_center + new_x_range / 2
        self.y_min = y_center - new_y_range / 2
        self.y_max = y_center + new_y_range / 2
        
        # 重新计算函数点
        for func in self.functions:
            func.calculate_points()
        
        self.update()
    
    def resizeEvent(self, event):
        """画布尺寸改变事件"""
        super().resizeEvent(event)
        
        # 当画布尺寸改变时，自动调整长宽比
        if self.maintain_aspect_ratio:
            self.adjust_aspect_ratio()
    
    def get_function_at_point(self, world_point: QPointF, tolerance: float = 0.5) -> Optional[FunctionExpression]:
        """获取指定点附近的函数"""
        for func in reversed(self.functions):  # 从上往下检查
            if not func.visible or not func.points:
                continue
            
            # 检查点是否在函数附近
            for point in func.points:
                if point is None:
                    continue
                
                distance = math.sqrt((point.x() - world_point.x())**2 + (point.y() - world_point.y())**2)
                if distance <= tolerance:
                    return func
        
        return None
    
    def zoom_to_fit(self):
        """缩放到合适大小"""
        if not self.functions:
            return
        
        # 计算所有函数的边界
        all_points = []
        for func in self.functions:
            if func.visible and func.points:
                all_points.extend([p for p in func.points if p is not None])
        
        if not all_points:
            return
        
        # 计算边界
        x_coords = [p.x() for p in all_points]
        y_coords = [p.y() for p in all_points]
        
        min_x, max_x = min(x_coords), max(x_coords)
        min_y, max_y = min(y_coords), max(y_coords)
        
        # 添加边距
        margin_x = (max_x - min_x) * 0.1
        margin_y = (max_y - min_y) * 0.1
        
        self.set_view_range(
            min_x - margin_x, max_x + margin_x,
            min_y - margin_y, max_y + margin_y
        )
    
    def draw_dynamic_point(self, painter: QPainter, point):
        """绘制动点"""
        if math.isnan(point.x) or math.isnan(point.y):
            return
        
        # 转换为屏幕坐标
        screen_pos = self.world_to_screen(QPointF(point.x, point.y))
        
        # 绘制轨迹
        if point.show_trail and point.trail_points:
            painter.setPen(QPen(point.color, 1, Qt.DotLine))
            trail_path = []
            for trail_x, trail_y in point.trail_points:
                if not (math.isnan(trail_x) or math.isnan(trail_y)):
                    trail_screen = self.world_to_screen(QPointF(trail_x, trail_y))
                    trail_path.append(trail_screen)
            
            # 绘制轨迹线
            for i in range(1, len(trail_path)):
                painter.drawLine(trail_path[i-1], trail_path[i])
        
        # 绘制动点
        painter.setPen(QPen(point.color, 2))
        painter.setBrush(QBrush(point.color))
        
        # 绘制点
        point_rect = QRectF(
            screen_pos.x() - point.size/2,
            screen_pos.y() - point.size/2,
            point.size,
            point.size
        )
        painter.drawEllipse(point_rect)
        
        # 绘制点名称
        if point.name:
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            text_rect = QRectF(screen_pos.x() + point.size, screen_pos.y() - point.size, 100, 20)
            painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, point.name)
    
    def set_maintain_aspect_ratio(self, maintain: bool):
        """设置是否保持长宽比"""
        self.maintain_aspect_ratio = maintain
        if maintain:
            self.adjust_aspect_ratio()
            self.update()
