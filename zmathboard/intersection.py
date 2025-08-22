#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QPen, QBrush, QColor, QPainter, QFont
from PyQt5.QtWidgets import QAction, QMenu

from .geometry import Point, Line, GeometryObject

class Intersection(Point):
    """线段交点类，继承自Point，但有特殊的视觉效果和标记"""
    
    def __init__(self, x=0, y=0, name="", radius=5, parent_lines=None):
        super().__init__(x, y, name, radius)
        self.color = QColor(255, 0, 128)  # 粉红色，区别于普通点的蓝色
        self.is_intersection = True  # 标记为交点
        self.parent_lines = parent_lines or []  # 存储产生此交点的两条线段
        self.fixed = True  # 交点始终固定，不可拖动
        self.draggable = False  # 交点不可拖动
        
    def draw(self, painter):
        """绘制交点，使用特殊样式"""
        if not self.visible:
            return
            
        pen = QPen(self.border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        brush = QBrush(self.color)
        painter.setBrush(brush)
        
        # if被选中，则增加视觉效果
        if self.selected:
            highlight_radius = self.radius + 3
            highlight_pen = QPen(QColor(255, 165, 0))  # 橙色高亮
            highlight_pen.setWidth(2)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(self.x, self.y), highlight_radius, highlight_radius)
            painter.setPen(pen)
            painter.setBrush(brush)
        
        # 绘制交点 - 使用X形标记
        center_point = QPointF(self.x, self.y)
        painter.drawEllipse(center_point, self.radius, self.radius)
        
        # 在圆内绘制X
        pen.setWidth(1)
        painter.setPen(pen)
        size = self.radius * 0.7
        painter.drawLine(
            QPointF(self.x - size, self.y - size),
            QPointF(self.x + size, self.y + size)
        )
        painter.drawLine(
            QPointF(self.x - size, self.y + size),
            QPointF(self.x + size, self.y - size)
        )
        
        # if有名称，绘制名称，使用斜体以区分
        if self.name:
            font = painter.font()
            font.setItalic(True)
            painter.setFont(font)
            painter.drawText(QPointF(self.x + self.radius + 2, self.y - self.radius - 2), self.name)
            font.setItalic(False)
            painter.setFont(font)
            
    def update_position(self):
        """根据父线段更新交点位置"""
        if len(self.parent_lines) != 2:
            return
            
        # 计算两条线段的交点
        x, y = IntersectionManager.calculate_intersection(self.parent_lines[0], self.parent_lines[1])
        if x is not None:
            self.x = x
            self.y = y


class IntersectionManager:
    """管理线段交点的类"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.intersections = []  # 存储所有交点
        self.show_intersections = True  # 是否显示交点
        self.next_intersection_id = 0  # 交点命名计数器
        
    def toggle_intersections(self, show=None):
        """切换是否显示交点"""
        if show is None:
            self.show_intersections = not self.show_intersections
        else:
            self.show_intersections = show
        
        # 更新所有交点的可见性
        for intersection in self.intersections:
            intersection.visible = self.show_intersections
            
        # if开启显示，则更新所有交点
        if self.show_intersections:
            self.update_all_intersections()
        else:
            # if关闭显示，清除所有交点
            self.clear_all_intersections()
            
        # 请求画布重绘
        self.canvas.update()
        
        return self.show_intersections
        
    def update_all_intersections(self):
        """更新所有交点"""
        # if不显示交点，直接返回
        if not self.show_intersections:
            self.clear_all_intersections()
            return
            
        # 获取所有线段
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        
        # 记录现有交点信息，以便保留名称
        existing_intersections = {}
        for intersection in self.intersections:
            if len(intersection.parent_lines) == 2:
                # 使用父线段对作为键（排序以确保唯一性）
                line_ids = sorted([id(line) for line in intersection.parent_lines])
                key = (line_ids[0], line_ids[1])
                existing_intersections[key] = intersection
        
        # 临时存储将要保留的交点
        intersections_to_keep = []
        
        # 检查所有线段对的交点
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                line1, line2 = lines[i], lines[j]
                
                # 构建当前线段对的键
                line_ids = sorted([id(line1), id(line2)])
                key = (line_ids[0], line_ids[1])
                
                # 计算交点位置
                x, y = self.calculate_intersection(line1, line2)
                
                # if没有交点，继续下一对
                if x is None or y is None:
                    # if之前有交点但现在没有了，确保删除
                    if key in existing_intersections:
                        intersection_to_remove = existing_intersections[key]
                        if intersection_to_remove in self.intersections:
                            self.canvas.remove_object(intersection_to_remove)
                            self.intersections.remove(intersection_to_remove)
                    continue
                    
                # 检查是否是线段的端点
                if self.is_endpoint(x, y, line1) or self.is_endpoint(x, y, line2):
                    # if是端点，也要删除可能存在的旧交点
                    if key in existing_intersections:
                        intersection_to_remove = existing_intersections[key]
                        if intersection_to_remove in self.intersections:
                            self.canvas.remove_object(intersection_to_remove)
                            self.intersections.remove(intersection_to_remove)
                    continue
                
                # 检查是否是约束点（如中点）
                if self.is_constrained_point_position(x, y):
                    # if是约束点位置，不创建交点
                    if key in existing_intersections:
                        intersection_to_remove = existing_intersections[key]
                        if intersection_to_remove in self.intersections:
                            self.canvas.remove_object(intersection_to_remove)
                            self.intersections.remove(intersection_to_remove)
                    continue
                
                # 检查是否已存在此交点
                if key in existing_intersections:
                    # 已存在的交点，只更新位置
                    intersection = existing_intersections[key]
                    intersection.x = x
                    intersection.y = y
                    intersection.parent_lines = [line1, line2]  # 更新父线段引用
                    intersections_to_keep.append(intersection)
                else:
                    # 创建新的交点
                    # 使用简短的命名方式：A, B, C...
                    if self.next_intersection_id < 26:
                        name = chr(65 + self.next_intersection_id)  # 65是'A'的ASCII码
                    else:
                        # 当超过26个交点时，使用A1, B1, C1等命名方式
                        letter_index = (self.next_intersection_id) % 26
                        number = (self.next_intersection_id) // 26
                        name = chr(65 + letter_index) + str(number)
                        
                    self.next_intersection_id += 1
                    
                    # 创建新交点
                    intersection = Intersection(x, y, name, radius=5, parent_lines=[line1, line2])
                    
                    # 将交点添加到画布
                    self.canvas.add_object(intersection, skip_intersection_update=True)
                    intersections_to_keep.append(intersection)
        
        # 移除不再存在的交点
        for intersection in list(self.intersections):
            if intersection not in intersections_to_keep:
                self.canvas.remove_object(intersection)
                self.intersections.remove(intersection)
        
        # 更新交点列表
        self.intersections = intersections_to_keep
        
        # 请求画布重绘
        self.canvas.update()
        
    def check_and_create_intersection(self, line1, line2):
        """检查两条线段是否相交，if相交则创建交点"""
        x, y = self.calculate_intersection(line1, line2)
        
        # if没有交点，返回
        if x is None or y is None:
            return None
            
        # 检查是否是线段的端点
        if self.is_endpoint(x, y, line1) or self.is_endpoint(x, y, line2):
            return None
            
        # 创建新的交点，使用简短的命名方式：A, B, C...
        # 使用ASCII码生成字母名称(A-Z, if超过26个交点，则使用A1, A2, A3...)
        if self.next_intersection_id < 26:
            name = chr(65 + self.next_intersection_id)  # 65是'A'的ASCII码
        else:
            # 当超过26个交点时，使用A1, B1, C1等命名方式
            letter_index = (self.next_intersection_id) % 26
            number = (self.next_intersection_id) // 26
            name = chr(65 + letter_index) + str(number)
            
        self.next_intersection_id += 1
        
        intersection = Intersection(x, y, name, radius=5, parent_lines=[line1, line2])
        
        # 将交点添加到画布和管理器
        self.canvas.add_object(intersection, skip_intersection_update=True)
        self.intersections.append(intersection)
        
        return intersection
        
    def clear_all_intersections(self):
        """清除所有交点"""
        # 从画布中移除所有交点
        for intersection in self.intersections:
            self.canvas.remove_object(intersection)
            
        # 清空交点列表
        self.intersections = []
        
    @staticmethod
    def calculate_intersection(line1, line2):
        """计算两条线段的交点坐标"""
        # 提取线段的端点坐标
        x1, y1 = line1.p1.x, line1.p1.y
        x2, y2 = line1.p2.x, line1.p2.y
        x3, y3 = line2.p1.x, line2.p1.y
        x4, y4 = line2.p2.x, line2.p2.y
        
        # 计算分母
        denominator = ((y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1))
        
        # if分母为0，线段平行或共线，无交点
        if abs(denominator) < 1e-10:
            return None, None
            
        # 计算交点参数
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denominator
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denominator
        
        # 检查交点是否在两条线段上
        if 0 <= ua <= 1 and 0 <= ub <= 1:
            # 计算交点坐标
            x = x1 + ua * (x2 - x1)
            y = y1 + ua * (y2 - y1)
            return x, y
            
        return None, None
        
    @staticmethod
    def is_endpoint(x, y, line, threshold=1e-10):
        """检查点(x,y)是否是线段的端点"""
        # 检查是否与端点1接近
        if abs(x - line.p1.x) < threshold and abs(y - line.p1.y) < threshold:
            return True
            
        # 检查是否与端点2接近
        if abs(x - line.p2.x) < threshold and abs(y - line.p2.y) < threshold:
            return True
            
        return False
    
    def is_constrained_point_position(self, x, y, threshold=5.0):
        """检查指定位置是否是约束点的位置"""
        # 导入约束点类
        try:
            from .constraints import ConstrainedPoint
            
            # 检查所有对象中的约束点
            for obj in self.canvas.objects:
                if isinstance(obj, ConstrainedPoint):
                    # 检查是否与约束点位置接近
                    if abs(x - obj.x) < threshold and abs(y - obj.y) < threshold:
                        return True
            
            return False
        except ImportError:
            return False
        
    def update_after_object_change(self):
        """在对象变化后更新所有交点"""
        # 先移除所有无效的交点引用
        for intersection in list(self.intersections):
            # 检查父线段是否仍然存在
            if len(intersection.parent_lines) != 2:
                self.canvas.remove_object(intersection)
                self.intersections.remove(intersection)
                continue
                
            # 检查父线段是否仍在画布中
            if not all(line in self.canvas.objects for line in intersection.parent_lines):
                self.canvas.remove_object(intersection)
                self.intersections.remove(intersection)
                continue
                
            # 检查交点是否仍然有效
            x, y = self.calculate_intersection(intersection.parent_lines[0], intersection.parent_lines[1])
            if x is None or y is None:
                self.canvas.remove_object(intersection)
                self.intersections.remove(intersection)
                
        # 然后更新所有交点位置并查找新的交点
        self.update_all_intersections() 