#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QListWidget, QComboBox, QColorDialog,
                           QCheckBox, QGroupBox, QScrollArea, QWidget, QMessageBox)
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath
from PyQt5.QtCore import Qt, QPointF, QRectF

import math
from .geometry import Point, Line, GeometryObject
from .intersection import IntersectionManager, Intersection
import os
import json
import time

# ZAT文件保存功能已移除，改用完整的JSON画布状态保存

class Polygon(GeometryObject):
    """封闭多边形识别和处理类"""
    
    def __init__(self, lines, vertices):
        self.lines = lines          # 构成多边形的线段列表
        self.vertices = vertices    # 多边形的顶点列表
        name = self._generate_name()  # 先生成名称
        super().__init__(name)      # 然后传递给GeometryObject初始化
        self.fill_color = QColor(230, 230, 255, 100)  # 默认填充颜色（浅蓝色半透明）
        self.show_fill = True
        
        # 几何特性
        self.show_diagonals = False
        self.show_medians = False
        self.show_heights = False
        self.show_angle_bisectors = False
        self.show_midlines = False
        self.show_incircle = False  # 内切圆
        self.show_circumcircle = False  # 外接圆
        
        # 几何形状类型
        self.shape_type = self._detect_shape_type()
        self.shape_properties = {}  # 存储形状的特殊属性
        self._analyze_shape_properties()
        
        # 记录与多边形边相交的点
        self.edge_intersections = []
        
        # 标记多边形来源（手动创建或自动检测）
        self.source = 'auto'  # 默认为自动检测
    
    def _generate_name(self):
        """根据顶点生成多边形名称"""
        vertex_names = [v.name for v in self.vertices if v.name]
        if len(vertex_names) == len(self.vertices) and all(vertex_names):
            return "多边形" + "".join(vertex_names)
        else:
            return f"{len(self.vertices)}边形"
    
    def _detect_shape_type(self):
        """检测多边形类型"""
        n = len(self.vertices)
        
        if n == 3:
            return "三角形"
        elif n == 4:
            # 检查是否是特殊四边形
            return self._analyze_quadrilateral()
        elif n == 5:
            return "五边形"
        elif n == 6:
            return "六边形"
        else:
            return f"{n}边形"
    
    def _analyze_quadrilateral(self):
        """分析四边形类型"""
        # 获取四个顶点
        A, B, C, D = self.vertices
        
        # 计算四边的长度
        AB = math.sqrt((B.x - A.x)**2 + (B.y - A.y)**2)
        BC = math.sqrt((C.x - B.x)**2 + (C.y - B.y)**2)
        CD = math.sqrt((D.x - C.x)**2 + (D.y - C.y)**2)
        DA = math.sqrt((A.x - D.x)**2 + (A.y - D.y)**2)
        
        # 计算对角线
        AC = math.sqrt((C.x - A.x)**2 + (C.y - A.y)**2)
        BD = math.sqrt((D.x - B.x)**2 + (D.y - B.y)**2)
        
        # 判断是否为平行四边形
        is_parallelogram = self._is_approximately_equal(AB, CD) and self._is_approximately_equal(BC, DA)
        
        if is_parallelogram:
            # 检查是否是矩形 (对角线相等)
            if self._is_approximately_equal(AC, BD):
                # 检查是否是正方形 (所有边相等)
                if self._is_approximately_equal(AB, BC):
                    return "正方形"
                return "矩形"
            return "平行四边形"
        
        # 检查是否是梯形 (两边平行)
        # 简化判断：计算边的斜率
        AB_slope = float('inf') if abs(B.x - A.x) < 1e-6 else (B.y - A.y) / (B.x - A.x)
        CD_slope = float('inf') if abs(D.x - C.x) < 1e-6 else (D.y - C.y) / (D.x - C.x)
        BC_slope = float('inf') if abs(C.x - B.x) < 1e-6 else (C.y - B.y) / (C.x - B.x)
        DA_slope = float('inf') if abs(A.x - D.x) < 1e-6 else (A.y - D.y) / (A.x - D.x)
        
        if (self._is_approximately_equal(AB_slope, CD_slope) or 
            self._is_approximately_equal(BC_slope, DA_slope)):
            return "梯形"
        
        return "四边形"
    
    def _analyze_triangle(self):
        """分析三角形类型"""
        # 获取三个顶点
        A, B, C = self.vertices
        
        # 计算三边的长度
        AB = math.sqrt((B.x - A.x)**2 + (B.y - A.y)**2)
        BC = math.sqrt((C.x - B.x)**2 + (C.y - B.y)**2)
        CA = math.sqrt((A.x - C.x)**2 + (A.y - C.y)**2)
        
        # 检查是否为等边三角形
        if (self._is_approximately_equal(AB, BC) and 
            self._is_approximately_equal(BC, CA)):
            return "等边三角形"
        
        # 检查是否为等腰三角形
        if (self._is_approximately_equal(AB, BC) or 
            self._is_approximately_equal(BC, CA) or 
            self._is_approximately_equal(CA, AB)):
            return "等腰三角形"
        
        # 使用勾股定理检查是否为直角三角形
        sides = sorted([AB, BC, CA])
        if self._is_approximately_equal(sides[0]**2 + sides[1]**2, sides[2]**2):
            return "直角三角形"
        
        return "三角形"
    
    def _analyze_shape_properties(self):
        """分析几何形状的特殊属性"""
        if len(self.vertices) == 3:
            # 三角形特有属性
            triangle_type = self._analyze_triangle()
            self.shape_type = triangle_type
            
            # 计算三角形的内角
            A, B, C = self.vertices
            
            # 计算向量
            AB = (B.x - A.x, B.y - A.y)
            AC = (C.x - A.x, C.y - A.y)
            BA = (A.x - B.x, A.y - B.y)
            BC = (C.x - B.x, C.y - B.y)
            CA = (A.x - C.x, A.y - C.y)
            CB = (B.x - C.x, B.y - C.y)
            
            # 计算角度（弧度）
            angle_A = self._calculate_angle(AB, AC)
            angle_B = self._calculate_angle(BA, BC)
            angle_C = self._calculate_angle(CA, CB)
            
            # 转换为度数
            angles = {
                "A": math.degrees(angle_A),
                "B": math.degrees(angle_B),
                "C": math.degrees(angle_C)
            }
            
            self.shape_properties["angles"] = angles
            
            # 计算三角形中心
            centroid_x = (A.x + B.x + C.x) / 3
            centroid_y = (A.y + B.y + C.y) / 3
            self.shape_properties["centroid"] = (centroid_x, centroid_y)
        
        elif len(self.vertices) == 4:
            # 四边形可能拥有的特殊属性
            if self.shape_type == "正方形" or self.shape_type == "矩形":
                # 矩形的对角线相等且互相平分
                self.shape_properties["diagonal_properties"] = "相等且互相平分"
            
            if self.shape_type == "平行四边形" or self.shape_type == "菱形":
                # 平行四边形的对角线互相平分
                self.shape_properties["diagonal_properties"] = "互相平分"
    
    def _calculate_angle(self, v1, v2):
        """计算两个向量之间的角度（弧度）"""
        dot_product = v1[0]*v2[0] + v1[1]*v2[1]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        # 防止除以零
        if mag1 * mag2 < 1e-10:
            return 0
            
        cos_angle = dot_product / (mag1 * mag2)
        # 处理浮点数精度问题
        cos_angle = max(-1, min(1, cos_angle))
        return math.acos(cos_angle)
    
    def _is_approximately_equal(self, a, b, tolerance=1e-6):
        """检查两个浮点数是否近似相等"""
        if abs(a) < 1e-10 and abs(b) < 1e-10:
            return True
        return abs(a - b) / max(abs(a), abs(b)) < tolerance
    
    def contains_point(self, point):
        """检查点是否在多边形内部"""
        # 射线法判断点是否在多边形内
        x, y = point.x(), point.y()
        n = len(self.vertices)
        inside = False
        
        p1x, p1y = self.vertices[0].x, self.vertices[0].y
        for i in range(n + 1):
            p2x, p2y = self.vertices[i % n].x, self.vertices[i % n].y
            if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
            p1x, p1y = p2x, p2y
            
        return inside
    
    def draw(self, painter):
        """绘制多边形及其特性"""
        # 绘制填充
        if self.show_fill:
            brush = QBrush(self.fill_color)
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)
            
            # 创建路径
            path = QPainterPath()
            path.moveTo(self.vertices[0].x, self.vertices[0].y)
            for vertex in self.vertices[1:]:
                path.lineTo(vertex.x, vertex.y)
            path.closeSubpath()
            painter.drawPath(path)
        
        # 绘制对角线
        if self.show_diagonals:
            diag_pen = QPen(QColor(100, 100, 200))
            diag_pen.setWidth(2)  # 增加线条粗细
            diag_pen.setStyle(Qt.DashLine)
            painter.setPen(diag_pen)
            
            n = len(self.vertices)
            for i in range(n):
                for j in range(i+2, n):
                    # 跳过相邻顶点
                    if j != (i+1) % n and j != (i-1) % n:
                        painter.drawLine(
                            QPointF(self.vertices[i].x, self.vertices[i].y),
                            QPointF(self.vertices[j].x, self.vertices[j].y)
                        )
        
        # 绘制中位线（三角形特有）
        if self.show_medians and len(self.vertices) == 3:
            median_pen = QPen(QColor(200, 100, 100))
            median_pen.setWidth(2)  # 增加线条粗细
            median_pen.setStyle(Qt.DashLine)  # 使用虚线绘制中位线
            painter.setPen(median_pen)
            
            # 检查是否有选择状态
            has_median_selection = hasattr(self, 'selected_medians')
            
            # 对每个顶点，连接到对边中点
            for i in range(3):
                # if有选择状态，检查当前顶点是否被选中
                if has_median_selection:
                    # 将顶点索引映射到角标识
                    median_keys = ['A', 'B', 'C']
                    median_key = median_keys[i]
                    
                    # 检查该顶点是否被选中
                    if not self.selected_medians.get(median_key, True):
                        continue
                
                # 对边的两个顶点
                j = (i + 1) % 3
                k = (i + 2) % 3
                
                # 计算对边中点
                mid_x = (self.vertices[j].x + self.vertices[k].x) / 2
                mid_y = (self.vertices[j].y + self.vertices[k].y) / 2
                
                # 绘制中位线
                painter.drawLine(
                    QPointF(self.vertices[i].x, self.vertices[i].y),
                    QPointF(mid_x, mid_y)
                )
                
                # 在中点绘制小标记
                marker_size = 4
                painter.setBrush(QBrush(QColor(200, 100, 100)))
                painter.drawEllipse(
                    QPointF(mid_x, mid_y),
                    marker_size,
                    marker_size
                )
        
        # 绘制高线（主要用于三角形）
        if self.show_heights:
            height_pen = QPen(QColor(100, 200, 100))
            height_pen.setWidth(2)  # 增加线条粗细
            height_pen.setStyle(Qt.DashLine)  # 使用虚线绘制高线
            painter.setPen(height_pen)
            
            n = len(self.vertices)
            
            # 检查是否有选择状态
            has_height_selection = hasattr(self, 'selected_heights')
            
            # 确保height_feet是字典
            if not hasattr(self, 'height_feet'):
                self.height_feet = {}
            
            for i in range(n):
                # if有选择状态并且是三角形，检查当前顶点是否被选中
                if has_height_selection and n == 3:
                    # 将顶点索引映射到角标识
                    height_keys = ['A', 'B', 'C']
                    height_key = height_keys[i]
                    
                    # 检查该顶点是否被选中
                    if not self.selected_heights.get(height_key, True):
                        continue
                
                # 取当前顶点
                p = self.vertices[i]
                
                # 对边顶点
                p1 = self.vertices[(i + 1) % n]
                p2 = self.vertices[(i - 1) % n]
                
                # 计算垂足点（投影点）
                foot = self._calculate_perpendicular_foot(p, p1, p2)
                foot_x, foot_y = foot[0], foot[1]
                
                # 检查垂足是否在线段上，if不在，延长线段
                is_foot_on_segment = self._is_point_on_segment(foot, p1, p2)
                if not is_foot_on_segment:
                    # 计算延长线，先确定垂足与哪个顶点更远
                    d1 = self._distance(p1, foot)
                    d2 = self._distance(p2, foot)
                    
                    # 获取从p到垂足的方向向量
                    p_to_foot_x = foot_x - p.x
                    p_to_foot_y = foot_y - p.y
                    p_to_foot_length = math.sqrt(p_to_foot_x**2 + p_to_foot_y**2)
                    
                    if p_to_foot_length > 0:
                        # 单位化
                        p_to_foot_x /= p_to_foot_length
                        p_to_foot_y /= p_to_foot_length
                        
                        # 确定延长方向 - 使用与高线相反的方向
                        # 计算p1和p2与高线方向的点积，决定延长哪个方向
                        p1_dot = (p1.x - foot_x) * p_to_foot_x + (p1.y - foot_y) * p_to_foot_y
                        p2_dot = (p2.x - foot_x) * p_to_foot_x + (p2.y - foot_y) * p_to_foot_y
                        
                        # 准备延长线的点
                        extend_from = None
                        extend_to = None
                        
                        # 延长与高线方向相反的那一侧
                        if p1_dot > p2_dot:  # p1在高线反方向，延长p1方向
                            line_vector_x = p1.x - p2.x
                            line_vector_y = p1.y - p2.y
                            line_length = math.sqrt(line_vector_x**2 + line_vector_y**2)
                            if line_length > 0:
                                line_vector_x /= line_length
                                line_vector_y /= line_length
                                
                                # 起点是p2
                                extend_from = p2
                                # 终点是垂足再多延伸一段距离
                                extend_dist = self._distance(p2, foot) * 0.5  # 额外延伸距离
                                extend_to = (
                                    foot_x + line_vector_x * extend_dist,
                                    foot_y + line_vector_y * extend_dist
                                )
                        else:  # p2在高线反方向，延长p2方向
                            line_vector_x = p2.x - p1.x
                            line_vector_y = p2.y - p1.y
                            line_length = math.sqrt(line_vector_x**2 + line_vector_y**2)
                            if line_length > 0:
                                line_vector_x /= line_length
                                line_vector_y /= line_length
                                
                                # 起点是p1
                                extend_from = p1
                                # 终点是垂足再多延伸一段距离
                                extend_dist = self._distance(p1, foot) * 0.5  # 额外延伸距离
                                extend_to = (
                                    foot_x + line_vector_x * extend_dist,
                                    foot_y + line_vector_y * extend_dist
                                )
                        
                        # if成功确定了延长线
                        if extend_from and extend_to:
                            # 绘制原始线段和延长线，使用更粗的线条
                            # 先保存当前画笔
                            original_pen = painter.pen()
                            
                            # 绘制原始线段
                            base_line_pen = QPen(QColor(100, 100, 100))
                            base_line_pen.setWidth(2)
                            painter.setPen(base_line_pen)
                            painter.drawLine(
                                QPointF(p1.x, p1.y),
                                QPointF(p2.x, p2.y)
                            )
                            
                            # 绘制延长线（虚线）
                            extended_pen = QPen(QColor(100, 100, 100))
                            extended_pen.setWidth(3)
                            extended_pen.setStyle(Qt.DashLine)
                            painter.setPen(extended_pen)
                            
                            # 绘制延长线，从起点到终点
                            painter.drawLine(
                                QPointF(extend_from.x, extend_from.y),
                                QPointF(extend_to[0], extend_to[1])
                            )
                            
                            # 绘制直角符号
                            self._draw_perpendicular_symbol(painter, p, foot, p1, p2)
                            
                            # 恢复高线的画笔
                            painter.setPen(original_pen)
                        else:
                            # 垂足在线段上，直接绘制直角符号
                            self._draw_perpendicular_symbol(painter, p, foot, p1, p2)
                    else:
                        # 垂足与点p重合的特殊情况，直接绘制直角符号
                        self._draw_perpendicular_symbol(painter, p, foot, p1, p2)
                else:
                    # 垂足在线段上，直接绘制直角符号
                    self._draw_perpendicular_symbol(painter, p, foot, p1, p2)
                
                # 绘制高线
                height_line_pen = QPen(QColor(100, 200, 100))
                height_line_pen.setWidth(3)
                painter.setPen(height_line_pen)
                painter.drawLine(
                    QPointF(p.x, p.y),
                    QPointF(foot_x, foot_y)
                )
                
                # 在垂足处画一个小点，表示垂足位置（仅显示，不创建实际点对象）
                foot_pen = QPen(QColor(100, 200, 100))
                foot_pen.setWidth(2)
                painter.setPen(foot_pen)
                painter.setBrush(QBrush(QColor(100, 200, 100)))
                
                # 绘制垂足点
                foot_radius = 5
                painter.drawEllipse(
                    QPointF(foot_x, foot_y),
                    foot_radius,
                    foot_radius
                )
                
                # 记录高线垂足位置，用于后续创建点
                if p.name:
                    self.height_feet[p.name] = {
                    'position': (foot_x, foot_y),
                    'from_vertex': p,
                    'is_created': False  # 标记是否已创建点
                    }
        
        # 绘制角平分线
        if self.show_angle_bisectors:
            bisector_pen = QPen(QColor(200, 100, 200))
            bisector_pen.setWidth(2)  # 增加线条粗细
            bisector_pen.setStyle(Qt.DashDotLine)
            painter.setPen(bisector_pen)
            
            n = len(self.vertices)
            
            # 检查是否有角选择状态
            has_angle_selection = hasattr(self, 'selected_angles')
            
            for i in range(n):
                # if有角选择并且是三角形，根据选择绘制
                if has_angle_selection and n == 3:
                    # 将顶点索引映射到角标识
                    angle_keys = ['A', 'B', 'C']
                    angle_key = angle_keys[i]
                    
                    # 检查该角是否被选中
                    if not self.selected_angles.get(angle_key, True):
                        continue
                
                # 当前顶点
                p = self.vertices[i]
                
                # 相邻顶点
                p_prev = self.vertices[(i - 1) % n]
                p_next = self.vertices[(i + 1) % n]
                
                # 计算角平分线向量
                v1 = QPointF(p_prev.x - p.x, p_prev.y - p.y)
                v2 = QPointF(p_next.x - p.x, p_next.y - p.y)
                
                # 归一化向量
                len1 = math.sqrt(v1.x()**2 + v1.y()**2)
                len2 = math.sqrt(v2.x()**2 + v2.y()**2)
                
                if len1 > 0 and len2 > 0:
                    v1 = QPointF(v1.x()/len1, v1.y()/len1)
                    v2 = QPointF(v2.x()/len2, v2.y()/len2)
                    
                    # 计算角平分线向量
                    bisector = QPointF(v1.x() + v2.x(), v1.y() + v2.y())
                    bisector_len = math.sqrt(bisector.x()**2 + bisector.y()**2)
                    
                    if bisector_len > 0:
                        # 找到角平分线与三角形边的交点
                        intersection = None
                        if n == 3:  # 三角形特殊处理
                            # 对边
                            edge_p1 = self.vertices[(i + 1) % n]
                            edge_p2 = self.vertices[(i + 2) % n]
                            
                            # 计算角平分线方向上足够远的点
                            far_point_x = p.x + bisector.x() / bisector_len * 1000  # 延伸足够远
                            far_point_y = p.y + bisector.y() / bisector_len * 1000
                            
                            # 计算交点
                            intersection = self._line_intersection(
                                (p.x, p.y), (far_point_x, far_point_y),
                                (edge_p1.x, edge_p1.y), (edge_p2.x, edge_p2.y)
                            )
                        
                        # if找到交点，绘制到交点，否则使用原来的方法
                        if intersection:
                            painter.drawLine(
                                QPointF(p.x, p.y),
                                QPointF(intersection[0], intersection[1])
                            )
                            
                            # 在角平分线上绘制角度标记
                            mid_x = (p.x + intersection[0]) / 2
                            mid_y = (p.y + intersection[1]) / 2
                            
                            # 计算角度（0-180度）
                            angle = self._calculate_angle_degrees(v1, v2)
                            
                            # 绘制角度标记
                            painter.save()
                            text_font = painter.font()
                            text_font.setPointSize(9)
                            painter.setFont(text_font)
                            painter.drawText(
                                QPointF(mid_x + 5, mid_y - 5),
                                f"{angle:.1f}°"
                            )
                            painter.restore()
                        else:
                            # 计算一个合理的长度
                            max_len = max(len1, len2) * 1.5  # 增加长度
                            
                            # 计算终点
                            end_x = p.x + bisector.x() / bisector_len * max_len
                            end_y = p.y + bisector.y() / bisector_len * max_len
                            
                            # 绘制角平分线
                            painter.drawLine(
                                QPointF(p.x, p.y),
                                QPointF(end_x, end_y)
                            )
        
        # 绘制中点连线
        if self.show_midlines:
            midline_pen = QPen(QColor(100, 150, 100))
            midline_pen.setWidth(2)  # 增加线条粗细
            midline_pen.setStyle(Qt.DashDotDotLine)
            painter.setPen(midline_pen)
            
            n = len(self.vertices)
            # if是四边形，绘制对边中点的连线
            if n == 4:
                # 计算四个边的中点
                midpoints = []
                for i in range(n):
                    p1 = self.vertices[i]
                    p2 = self.vertices[(i + 1) % n]
                    mid_x = (p1.x + p2.x) / 2
                    mid_y = (p1.y + p2.y) / 2
                    midpoints.append((mid_x, mid_y))
                
                # 连接对边的中点
                painter.drawLine(
                    QPointF(midpoints[0][0], midpoints[0][1]),
                    QPointF(midpoints[2][0], midpoints[2][1])
                )
                painter.drawLine(
                    QPointF(midpoints[1][0], midpoints[1][1]),
                    QPointF(midpoints[3][0], midpoints[3][1])
                )
                
                # 标记中点
                marker_size = 4
                painter.setBrush(QBrush(QColor(100, 150, 100)))
                for mid_x, mid_y in midpoints:
                    painter.drawEllipse(
                        QPointF(mid_x, mid_y),
                        marker_size,
                        marker_size
                    )
            
            # 对于三角形，连接顶点到对边中点的线已经在中位线中画了
            # 对于其他多边形，连接相邻边的中点
            elif n > 4:
                midpoints = []
                for i in range(n):
                    p1 = self.vertices[i]
                    p2 = self.vertices[(i + 1) % n]
                    mid_x = (p1.x + p2.x) / 2
                    mid_y = (p1.y + p2.y) / 2
                    midpoints.append((mid_x, mid_y))
                
                # 绘制连接相邻中点的线
                for i in range(n):
                    painter.drawLine(
                        QPointF(midpoints[i][0], midpoints[i][1]),
                        QPointF(midpoints[(i + 1) % n][0], midpoints[(i + 1) % n][1])
                    )
                    
                # 标记中点
                marker_size = 4
                painter.setBrush(QBrush(QColor(100, 150, 100)))
                for mid_x, mid_y in midpoints:
                    painter.drawEllipse(
                        QPointF(mid_x, mid_y),
                        marker_size,
                        marker_size
                    )
        
        # 绘制内切圆（仅对三角形有效）
        if self.show_incircle and len(self.vertices) == 3:
            # 计算内切圆
            center, radius = self._calculate_incircle()
            if center and radius:
                # 使用淡蓝色虚线绘制内切圆
                incircle_pen = QPen(QColor(0, 128, 255, 180))
                incircle_pen.setWidth(2)
                incircle_pen.setStyle(Qt.DashLine)
                painter.setPen(incircle_pen)
                
                # 绘制内切圆
                painter.drawEllipse(
                    QPointF(center[0], center[1]),
                    radius,
                    radius
                )
                
                # 标记圆心
                painter.setBrush(QBrush(QColor(0, 128, 255)))
                painter.drawEllipse(
                    QPointF(center[0], center[1]),
                    4,
                    4
                )
                
                # 绘制从圆心到三条边的垂直线（内切圆半径）
                radius_pen = QPen(QColor(0, 128, 255, 150))
                radius_pen.setWidth(1)
                radius_pen.setStyle(Qt.DotLine)
                painter.setPen(radius_pen)
                
                # 对三条边分别计算垂足点
                for i in range(3):
                    p1 = self.vertices[i]
                    p2 = self.vertices[(i + 1) % 3]
                    
                    # 计算从圆心到边的垂足
                    foot = self._calculate_perpendicular_foot(
                        QPointF(center[0], center[1]),
                        p1,
                        p2
                    )
                    
                    # 绘制半径线
                    painter.drawLine(
                        QPointF(center[0], center[1]),
                        QPointF(foot[0], foot[1])
                    )
                
                # 显示半径值（取整数）
                text_font = painter.font()
                text_font.setPointSize(9)
                painter.setFont(text_font)
                
                # 在圆心附近显示半径值
                painter.drawText(
                    QPointF(center[0] + 5, center[1] - 5),
                    f"r = {radius:.1f}"
                )
        
        # 绘制外接圆（仅对三角形有效）
        if self.show_circumcircle and len(self.vertices) == 3:
            # 计算外接圆
            center, radius = self._calculate_circumcircle()
            if center and radius:
                # 使用淡紫色虚线绘制外接圆
                circumcircle_pen = QPen(QColor(200, 100, 200, 180))
                circumcircle_pen.setWidth(2)
                circumcircle_pen.setStyle(Qt.DashLine)
                painter.setPen(circumcircle_pen)
                
                # 绘制外接圆
                painter.drawEllipse(
                    QPointF(center[0], center[1]),
                    radius,
                    radius
                )
                
                # 标记圆心
                painter.setBrush(QBrush(QColor(200, 100, 200)))
                painter.drawEllipse(
                    QPointF(center[0], center[1]),
                    4,
                    4
                )
                
                # 绘制从圆心到三个顶点的半径线
                radius_pen = QPen(QColor(200, 100, 200, 150))
                radius_pen.setWidth(1)
                radius_pen.setStyle(Qt.DotLine)
                painter.setPen(radius_pen)
                
                for vertex in self.vertices:
                    painter.drawLine(
                        QPointF(center[0], center[1]),
                        QPointF(vertex.x, vertex.y)
                    )
                
                # 显示半径值（取整数）
                text_font = painter.font()
                text_font.setPointSize(9)
                painter.setFont(text_font)
                
                # 在圆心附近显示半径值
                painter.drawText(
                    QPointF(center[0] + 5, center[1] - 5),
                    f"R = {radius:.1f}"
                )
                    
    def _draw_perpendicular_symbol(self, painter, point, foot, edge_p1, edge_p2):
        """绘制垂直符号（标准直角符号）
        
        参数:
        - painter: QPainter对象
        - point: 顶点
        - foot: 垂足
        - edge_p1, edge_p2: 底边的两个端点
        """
        # 保存原画笔
        old_pen = painter.pen()
        old_brush = painter.brush()
        
        # 获取坐标
        if isinstance(foot, tuple) or isinstance(foot, list):
            foot_x, foot_y = foot[0], foot[1]
        else:
            foot_x, foot_y = foot.x, foot.y
            
        if isinstance(point, tuple) or isinstance(point, list):
            point_x, point_y = point[0], point[1]
        else:
            point_x, point_y = point.x, point.y
        
        # 计算高线方向向量（从垂足指向顶点）
        height_dx = point_x - foot_x
        height_dy = point_y - foot_y
        
        # 归一化高线方向向量
        height_length = math.sqrt(height_dx*height_dx + height_dy*height_dy)
        if height_length < 1e-6:
            return  # if高的长度接近于0，不绘制符号
            
        height_unit_x = height_dx / height_length
        height_unit_y = height_dy / height_length
        
        # 计算小正方形的大小
        square_size = 10  # 符号大小
        
        # 直接计算垂直于高线的方向（顺时针旋转90度）
        perp_dx = -height_unit_y
        perp_dy = height_unit_x
        
        # 计算另一个垂直方向（逆时针旋转90度）
        perp2_dx = height_unit_y
        perp2_dy = -height_unit_x
        
        # 计算底边方向
        if isinstance(edge_p1, QPointF):
            edge_p1_x, edge_p1_y = edge_p1.x(), edge_p1.y()
        else:
            edge_p1_x, edge_p1_y = edge_p1.x, edge_p1.y
            
        if isinstance(edge_p2, QPointF):
            edge_p2_x, edge_p2_y = edge_p2.x(), edge_p2.y()
        else:
            edge_p2_x, edge_p2_y = edge_p2.x, edge_p2.y
            
        # 计算边的方向向量
        edge_dx = edge_p2_x - edge_p1_x
        edge_dy = edge_p2_y - edge_p1_y
        edge_length = math.sqrt(edge_dx*edge_dx + edge_dy*edge_dy)
        
        if edge_length < 1e-6:
            return  # if边长度接近于0，不绘制符号
        
        edge_unit_x = edge_dx / edge_length
        edge_unit_y = edge_dy / edge_length
        
        # 选择正确的垂直方向 - 检查哪一个垂直方向与边的方向更接近
        dot1 = perp_dx * edge_unit_x + perp_dy * edge_unit_y
        dot2 = perp2_dx * edge_unit_x + perp2_dy * edge_unit_y
        
        # 选择点积绝对值更大的方向作为直角符号的一边
        if abs(dot1) > abs(dot2):
            direction_x = perp_dx
            direction_y = perp_dy
        else:
            direction_x = perp2_dx
            direction_y = perp2_dy
            
        # 计算小正方形的四个顶点
        # 垂足点
        p0 = QPointF(foot_x, foot_y)
        # 沿着高线方向的点
        p1 = QPointF(foot_x + direction_x * square_size, foot_y + direction_y * square_size)
        # 沿着与高线垂直方向的点
        p2 = QPointF(foot_x + height_unit_x * square_size, foot_y + height_unit_y * square_size)
        # 对角点
        p3 = QPointF(p1.x() + (p2.x() - p0.x()), p1.y() + (p2.y() - p0.y()))
        
        # 设置直角符号样式 - 使用红色并加粗
        symbol_pen = QPen(QColor(255, 0, 0))  # 红色
        symbol_pen.setWidth(2)
        painter.setPen(symbol_pen)
        
        # 绘制小正方形（标准直角符号）
        path = QPainterPath()
        path.moveTo(p0)
        path.lineTo(p1)
        path.lineTo(p3)
        path.lineTo(p2)
        path.lineTo(p0)
        
        # 填充直角符号
        painter.setBrush(QBrush(QColor(255, 0, 0, 80)))  # 浅红色半透明填充
        painter.drawPath(path)
        
        # 恢复原画笔
        painter.setPen(old_pen)
        painter.setBrush(old_brush)
    
    def _is_point_on_segment(self, point, p1, p2):
        """检查点是否在线段上"""
        # 转换为坐标
        if isinstance(point, QPointF):
            px, py = point.x(), point.y()
        elif isinstance(point, tuple):
            px, py = point
        else:
            px, py = point[0], point[1]
            
        # 处理点对象
        if isinstance(p1, QPointF):
            p1x, p1y = p1.x(), p1.y()
        elif hasattr(p1, 'x') and hasattr(p1, 'y'):
            p1x, p1y = p1.x, p1.y
        else:
            p1x, p1y = p1[0], p1[1]
            
        if isinstance(p2, QPointF):
            p2x, p2y = p2.x(), p2.y()
        elif hasattr(p2, 'x') and hasattr(p2, 'y'):
            p2x, p2y = p2.x, p2.y
        else:
            p2x, p2y = p2[0], p2[1]
        
        # 计算点到线段两端点的距离和
        d1 = math.sqrt((px - p1x)**2 + (py - p1y)**2)
        d2 = math.sqrt((px - p2x)**2 + (py - p2y)**2)
        line_length = math.sqrt((p2x - p1x)**2 + (p2y - p1y)**2)
        
        # if点到两端点的距离之和与线段长度相差很小，则点在线段上
        tolerance = 1e-6
        return abs(d1 + d2 - line_length) < tolerance
    
    def _extend_line_segment(self, p1, p2, extend_length):
        """延长线段"""
        # 计算方向向量
        if isinstance(p1, QPointF):
            p1x, p1y = p1.x(), p1.y()
        elif hasattr(p1, 'x') and hasattr(p1, 'y'):
            p1x, p1y = p1.x, p1.y
        else:
            p1x, p1y = p1[0], p1[1]
            
        if isinstance(p2, QPointF):
            p2x, p2y = p2.x(), p2.y()
        elif hasattr(p2, 'x') and hasattr(p2, 'y'):
            p2x, p2y = p2.x, p2.y
        else:
            p2x, p2y = p2[0], p2[1]
            
        dx = p2x - p1x
        dy = p2y - p1y
        
        length = math.sqrt(dx*dx + dy*dy)
        
        if length < 1e-6:
            return (p1x, p1y), (p2x, p2y)  # 避免除零
        
        # 单位向量
        unit_dx = dx / length
        unit_dy = dy / length
        
        # 延长两端
        extended_p1 = (p1x - unit_dx * extend_length, p1y - unit_dy * extend_length)
        extended_p2 = (p2x + unit_dx * extend_length, p2y + unit_dy * extend_length)
        
        return extended_p1, extended_p2
    
    def _line_intersection(self, p1, p2, p3, p4):
        """计算两条线的交点"""
        # 线段1: p1 - p2
        # 线段2: p3 - p4
        
        # 检查点参数类型
        if hasattr(p1, 'x') and hasattr(p1, 'y'):
            x1, y1 = p1.x, p1.y
        else:
            x1, y1 = p1[0], p1[1]
            
        if hasattr(p2, 'x') and hasattr(p2, 'y'):
            x2, y2 = p2.x, p2.y
        else:
            x2, y2 = p2[0], p2[1]
            
        if hasattr(p3, 'x') and hasattr(p3, 'y'):
            x3, y3 = p3.x, p3.y
        else:
            x3, y3 = p3[0], p3[1]
            
        if hasattr(p4, 'x') and hasattr(p4, 'y'):
            x4, y4 = p4.x, p4.y
        else:
            x4, y4 = p4[0], p4[1]
        
        # 计算行列式
        denominator = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
        
        # 平行或共线
        if abs(denominator) < 1e-6:
            return None
            
        # 计算交点参数
        ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denominator
        ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denominator
        
        # 交点坐标
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        
        # 检查交点是否在第二条线段上
        if 0 <= ub <= 1:
            return (x, y)
        
        return None
    
    def _distance(self, p1, p2):
        """计算两点之间的距离"""
        if isinstance(p1, QPointF):
            p1x, p1y = p1.x(), p1.y()
        elif hasattr(p1, 'x') and hasattr(p1, 'y'):
            p1x, p1y = p1.x, p1.y
        else:
            p1x, p1y = p1[0], p1[1]
            
        if isinstance(p2, QPointF):
            p2x, p2y = p2.x(), p2.y()
        elif hasattr(p2, 'x') and hasattr(p2, 'y'):
            p2x, p2y = p2.x, p2.y
        else:
            p2x, p2y = p2[0], p2[1]
            
        return math.sqrt((p2x - p1x)**2 + (p2y - p1y)**2)
    
    def _calculate_perpendicular_foot(self, p, line_p1, line_p2):
        """计算点p到直线line_p1-line_p2的垂足"""
        # 计算直线方向向量
        # 处理不同类型的参数
        if isinstance(p, QPointF):
            px, py = p.x(), p.y()
        elif hasattr(p, 'x') and hasattr(p, 'y'):
            px, py = p.x, p.y
        else:
            px, py = p[0], p[1]
            
        if isinstance(line_p1, tuple):
            line_p1x, line_p1y = line_p1[0], line_p1[1]
        else:
            line_p1x, line_p1y = line_p1.x, line_p1.y
            
        if isinstance(line_p2, tuple):
            line_p2x, line_p2y = line_p2[0], line_p2[1]
        else:
            line_p2x, line_p2y = line_p2.x, line_p2.y
        
        # 计算直线方向向量
        dx = line_p2x - line_p1x
        dy = line_p2y - line_p1y
        
        # if直线退化为点，返回该点
        if abs(dx) < 1e-10 and abs(dy) < 1e-10:
            return (line_p1x, line_p1y)
        
        # 计算点到直线的投影参数
        t = ((px - line_p1x) * dx + (py - line_p1y) * dy) / (dx*dx + dy*dy)
        
        # 计算垂足坐标
        foot_x = line_p1x + t * dx
        foot_y = line_p1y + t * dy
        
        return (foot_x, foot_y)
    
    def _calculate_angle_degrees(self, v1, v2):
        """计算两个向量之间的角度（度数）"""
        # 计算点积
        dot_product = v1.x() * v2.x() + v1.y() * v2.y()
        
        # 计算模长
        v1_len = math.sqrt(v1.x()**2 + v1.y()**2)
        v2_len = math.sqrt(v2.x()**2 + v2.y()**2)
        
        # 计算夹角余弦值
        if v1_len * v2_len < 1e-10:
            return 0
            
        cos_angle = dot_product / (v1_len * v2_len)
        # 防止浮点数精度问题
        cos_angle = max(-1, min(1, cos_angle))
        
        # 转换为角度
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def _calculate_incircle(self):
        """计算三角形内切圆"""
        if len(self.vertices) != 3:
            return None, None
            
        # 获取三个顶点
        A, B, C = self.vertices
        
        # 计算三边长度
        a = self._distance(B, C)
        b = self._distance(A, C)
        c = self._distance(A, B)
        
        # 计算半周长
        s = (a + b + c) / 2
        
        # 计算内切圆半径
        try:
            r = math.sqrt((s - a) * (s - b) * (s - c) / s)
            
            # 计算内心坐标（使用加权坐标）
            center_x = (a * A.x + b * B.x + c * C.x) / (a + b + c)
            center_y = (a * A.y + b * B.y + c * C.y) / (a + b + c)
            
            return (center_x, center_y), r
        except:
            return None, None
            
    def _calculate_circumcircle(self):
        """计算三角形外接圆"""
        if len(self.vertices) != 3:
            return None, None
            
        # 获取三个顶点
        A, B, C = self.vertices
        
        # 三点共线检查
        area = abs((A.x * (B.y - C.y) + B.x * (C.y - A.y) + C.x * (A.y - B.y)) / 2)
        if area < 1e-10:
            return None, None  # 三点共线
            
        # 计算外接圆半径和圆心
        # 使用行列式计算
        D = 2 * (A.x * (B.y - C.y) + B.x * (C.y - A.y) + C.x * (A.y - B.y))
        
        # 圆心坐标
        Ux = ((A.x*A.x + A.y*A.y) * (B.y - C.y) + 
              (B.x*B.x + B.y*B.y) * (C.y - A.y) + 
              (C.x*C.x + C.y*C.y) * (A.y - B.y)) / D
              
        Uy = ((A.x*A.x + A.y*A.y) * (C.x - B.x) + 
              (B.x*B.x + B.y*B.y) * (A.x - C.x) + 
              (C.x*C.x + C.y*C.y) * (B.x - A.x)) / D
              
        # 半径
        r = math.sqrt((A.x - Ux)**2 + (A.y - Uy)**2)
        
        return (Ux, Uy), r

    def check_edge_intersections(self, canvas):
        """检测与多边形边相交的点，并为它们命名"""
        # 首先清除旧的交点记录
        self.edge_intersections = []
        
        # 获取画布上的所有点
        points = [obj for obj in canvas.objects if isinstance(obj, Point)]
        
        # 检查顶点是否有名称
        vertex_names = {}
        for i, vertex in enumerate(self.vertices):
            if hasattr(vertex, 'name') and vertex.name:
                vertex_names[i] = vertex.name
            else:
                if i < 26:  # A-Z
                    vertex_names[i] = chr(65 + i)  # A, B, C, ...
                else:
                    vertex_names[i] = f"P{i+1}"
        
        # 预先计算垂足位置，以便识别高与边的交点
        height_feet = []
        if len(self.vertices) == 3:
            for i, vertex in enumerate(self.vertices):
                # 对边顶点
                p1 = self.vertices[(i + 1) % 3]
                p2 = self.vertices[(i - 1) % 3]
                
                # 计算垂足
                foot = self._calculate_perpendicular_foot(vertex, p1, p2)
                
                # 检查垂足是否在线段上
                if self._is_point_on_segment(foot, p1, p2):
                    height_feet.append({
                        'position': foot,
                        'vertex_index': i,
                        'vertex_name': vertex_names.get(i, f"V{i+1}")
                    })
        
        # 检查每条边与每个点的关系
        for j, line in enumerate(self.lines):
            # 获取线段端点索引
            line_p1_index = self.vertices.index(line.p1) if line.p1 in self.vertices else -1
            line_p2_index = self.vertices.index(line.p2) if line.p2 in self.vertices else -1
            
            for point in points:
                # 跳过多边形的顶点
                if point in self.vertices:
                    continue
                
                # 检查点是否在线段上
                if self._is_point_on_line(point, line):
                    # 检查是否是高的垂足
                    is_height_foot = False
                    for foot_data in height_feet:
                        foot_pos = foot_data['position']
                        if self._distance(point, foot_pos) < 5:  # 使用较大的阈值判断是否接近
                            # 这是高的垂足点
                            vertex_name = foot_data['vertex_name']
                            # if点没有名称或有默认名称，为其分配垂足名称
                            if not point.name or point.name.startswith("P") or point.name.startswith("I"):
                                point.name = f"{vertex_name}′"
                            is_height_foot = True
                            break
                    
                    # if不是高的垂足，检查是否是中线、角平分线等与边的交点
                    if not is_height_foot:
                        # if点没有名称或有默认名称，分配交点名称
                        if not point.name or point.name.startswith("P"):
                            # 生成交点名称，使用边的端点名称
                            if line_p1_index >= 0 and line_p2_index >= 0:
                                edge_name = f"{vertex_names.get(line_p1_index)}{vertex_names.get(line_p2_index)}"
                                point.name = f"I_{edge_name}"
                            else:
                                # 使用默认交点命名
                                intersection_count = len(self.edge_intersections) + 1
                                point.name = f"I{intersection_count}"
                    
                    # 记录这个交点
                    if point not in self.edge_intersections:
                        self.edge_intersections.append(point)
    
    def _is_point_on_line(self, point, line):
        """检查点是否在线段上"""
        # 计算点到线段两端点的距离之和与线段长度的差值
        d1 = self._distance(point, line.p1)
        d2 = self._distance(point, line.p2)
        line_length = self._distance(line.p1, line.p2)
        
        # if点到两端点的距离之和与线段长度相差很小，则点在线段上
        tolerance = 1e-6
        return abs(d1 + d2 - line_length) < tolerance

    def create_height_intersection_points(self, canvas):
        """自动创建高线与边的交点"""
        from .geometry import Point
        
        # 检查是否有高线垂足记录
        if not hasattr(self, 'height_feet') or not self.height_feet:
            return
        
        points_created = False
        
        # 处理每个垂足
        for foot_data in self.height_feet:
            if foot_data['is_created']:
                continue  # 跳过已创建的点
                
            foot_pos = foot_data['position']
            from_vertex = foot_data['from_vertex']
            foot_x, foot_y = foot_pos
            
            # 检查是否已存在此垂足点
            existing_foot = None
            for obj in canvas.objects:
                if isinstance(obj, Point):
                    dist = math.sqrt((obj.x - foot_x)**2 + (obj.y - foot_y)**2)
                    if dist < 5:  # 使用较大阈值判断
                        existing_foot = obj
                        break
            
            # if不存在，创建新点
            if not existing_foot:
                # 生成垂足名称
                if hasattr(from_vertex, 'name') and from_vertex.name:
                    foot_name = f"{from_vertex.name}′"  # 使用顶点名称加上撇号
                else:
                    # 查找顶点在多边形中的索引
                    if from_vertex in self.vertices:
                        vertex_idx = self.vertices.index(from_vertex)
                        if vertex_idx < 26:  # A-Z
                            vertex_name = chr(65 + vertex_idx)  # A, B, C, ...
                        else:
                            vertex_name = f"V{vertex_idx+1}"
                        foot_name = f"{vertex_name}′"
                    else:
                        foot_name = f"H{len(canvas.objects) + 1}"
                
                # 创建新点
                new_foot = Point(foot_x, foot_y, foot_name)
                canvas.add_object(new_foot)
                foot_data['is_created'] = True
                points_created = True
        
        # 清除已创建的垂足记录
        if points_created:
            self.height_feet = [foot for foot in self.height_feet if not foot['is_created']]
        
        return points_created

    def apply_changes(self):
        """应用所有更改"""
        # 临时保存手动创建的多边形，确保来源标记被保留
        manual_polygons = [p for p in self.polygons if hasattr(p, 'source') and p.source == 'manual']
        
        # 清空画布上的活跃多边形
        self.canvas.active_polygons = []
        
        # 添加所有处于显示状态的多边形
        for polygon in self.polygons:
            # 确保所有多边形都有source属性
            if not hasattr(polygon, 'source'):
                polygon.source = 'auto'  # 默认为自动检测的多边形
                
            # 对于手动创建的多边形，确保source属性正确设置
            if polygon in manual_polygons:
                polygon.source = 'manual'
                
            if polygon.show_fill or polygon.show_diagonals or polygon.show_medians or \
               polygon.show_heights or polygon.show_angle_bisectors or polygon.show_midlines or \
               polygon.show_incircle or polygon.show_circumcircle:
                self.canvas.active_polygons.append(polygon)
                
                # if显示高线，确保创建/更新垂足点
                if polygon.show_heights:
                    # 临时设置当前多边形，以便创建高的垂足点
                    temp_current = self.current_polygon
                    self.current_polygon = polygon
                    created = self.create_height_foot_points()
                    if created:
                        print(f"已更新 {polygon.name} 的高垂足点")
                    self.current_polygon = temp_current
        
        # 检查所有多边形与点的交点，并命名（仅命名已存在的点，不创建新点）
        for polygon in self.canvas.active_polygons:
            polygon.check_edge_intersections(self.canvas)
        
        # 立即保存多边形属性到文件，而不是等待拖动
        # 属性已更新 - 移除ZAT保存
        
        # 更新画布
        self.canvas.update()

    def update_height_foot_points(self, polygon):
        """更新高的垂足点位置"""
        if len(polygon.vertices) != 3:
            return
            
        # 对每个顶点更新垂足
        for i, vertex in enumerate(polygon.vertices):
            # 只处理被选中的高
            vertex_name = chr(65 + i)  # A, B, C
            if not hasattr(polygon, 'selected_heights') or \
               not polygon.selected_heights.get(vertex_name, False):
                continue
                
            # 对边顶点
            p1 = polygon.vertices[(i + 1) % 3]
            p2 = polygon.vertices[(i - 1) % 3]
            
            # 计算垂足
            foot = polygon._calculate_perpendicular_foot(vertex, p1, p2)
            foot_x, foot_y = foot[0], foot[1]
            
            # 检查垂足是否在线段上
            is_on_segment = polygon._is_point_on_segment(foot, p1, p2)
            if not is_on_segment:
                continue
                
            # 垂足名称
            foot_name = f"{vertex.name}′" if vertex.name else f"H{i+1}"
            
            # 查找现有的垂足点
            found = False
            for obj in self.canvas.objects:
                if isinstance(obj, Point) and obj.name == foot_name:
                    # 更新位置
                    obj.x = foot_x
                    obj.y = foot_y
                    found = True
                    break
            
            # if没有找到同名点，再检查是否有距离很近的点
            if not found:
                for obj in self.canvas.objects:
                    if isinstance(obj, Point):
                        dist = math.sqrt((obj.x - foot_x)**2 + (obj.y - foot_y)**2)
                        if dist < 5:  # 使用较大阈值判断
                            # 更新名称和位置
                            obj.name = foot_name
                            obj.x = foot_x
                            obj.y = foot_y
                            found = True
                            break
            
            # if没有找到匹配的点，创建新的垂足点
            if not found:
                new_foot = Point(foot_x, foot_y, foot_name)
                self.canvas.add_object(new_foot)

    def get_bounds_rect(self, margin=0):
        """获取多边形的边界矩形，用于局部重绘"""
        if not self.vertices:
            return QRectF(0, 0, 0, 0)
            
        # 初始化为第一个顶点
        min_x = max_x = self.vertices[0].x
        min_y = max_y = self.vertices[0].y
        
        # 查找最大最小坐标
        for vertex in self.vertices:
            min_x = min(min_x, vertex.x)
            max_x = max(max_x, vertex.x)
            min_y = min(min_y, vertex.y)
            max_y = max(max_y, vertex.y)
        
        # 添加边距
        return QRectF(
            min_x - margin,
            min_y - margin,
            max_x - min_x + 2 * margin,
            max_y - min_y + 2 * margin
        )

    def drag_to(self, new_pos):
        """拖拽多边形到新位置的方法（用于保持GeometryObject接口一致）
        对于多边形，拖动由Canvas类中的特定代码处理，所以这里只是保持接口一致
        """
        # 由于多边形的拖拽需要移动所有顶点，通常由Canvas类中的代码处理
        # 此方法仅用于保持接口一致
        return False


class PolygonDetector:
    """多边形检测类"""
    
    def __init__(self, canvas):
        self.canvas = canvas
    
    def detect_polygons(self):
        """检测画布上的所有封闭多边形"""
        # 导入所需的类
        from .geometry import Line
        from .intersection import Intersection
        
        # 获取所有线段
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        
        # 获取所有顶点（点和交点）
        points = []
        for obj in self.canvas.objects:
            # 同时包含Point和Intersection类型
            if isinstance(obj, Point):
                # 确保交点也被视为多边形的顶点
                if isinstance(obj, Intersection) or (hasattr(obj, 'is_intersection') and obj.is_intersection):
                    # 这是一个交点，确保它存在于points列表中
                    if obj not in points:
                        points.append(obj)
                else:
                    # 这是一个普通点
                    points.append(obj)
        
        # 构建顶点-线段连接关系字典
        vertex_lines = {}
        for point in points:
            vertex_lines[point] = []
        
        # 添加每条线的端点到连接关系中
        for line in lines:
            if line.p1 in vertex_lines:
                vertex_lines[line.p1].append(line)
            if line.p2 in vertex_lines:
                vertex_lines[line.p2].append(line)
                
        # 查找交点，为每个交点添加相连线段
        for point in points:
            # 检查是否是Intersection类型或有is_intersection属性
            is_intersection = isinstance(point, Intersection) or (hasattr(point, 'is_intersection') and point.is_intersection)
            
            if not is_intersection:
                continue
                
            # 对于每条线，检查这个交点是否在线上
            for line in lines:
                # if已经是端点，跳过
                if point == line.p1 or point == line.p2:
                    continue
                    
                # 计算点到线段两端点的距离之和与线段长度的差值
                d1 = math.sqrt((point.x - line.p1.x)**2 + (point.y - line.p1.y)**2)
                d2 = math.sqrt((point.x - line.p2.x)**2 + (point.y - line.p2.y)**2)
                line_length = math.sqrt((line.p2.x - line.p1.x)**2 + (line.p2.y - line.p1.y)**2)
                
                # if点在线段上（允许一定误差）
                if abs(d1 + d2 - line_length) < 1e-6:
                    # 将线段添加到交点的连接关系中
                    if point in vertex_lines:
                        if line not in vertex_lines[point]:
                            vertex_lines[point].append(line)
        
        # 检查并拆分穿过交点的线段，以便更好地检测多边形
        self.split_lines_at_intersections(lines, points, vertex_lines)
        
        # 查找封闭多边形
        polygons = []
        visited_lines = set()
        
        for start_point in points:
            if len(vertex_lines[start_point]) < 2:
                continue  # 至少需要2条线段相连才可能形成多边形
                
            for first_line in vertex_lines[start_point]:
                if first_line in visited_lines:
                    continue
                    
                # 跳过非Line类型的对象（如Intersection）
                if not isinstance(first_line, Line):
                    continue
                    
                # 尝试找到封闭路径
                polygon_lines = []
                polygon_vertices = []
                current_point = start_point
                current_line = first_line
                found_polygon = False
                
                while True:
                    # 添加当前线段
                    polygon_lines.append(current_line)
                    
                    # 只有当顶点还不在列表中时才添加，避免重复
                    if current_point not in polygon_vertices:
                        polygon_vertices.append(current_point)
                    
                    # 获取当前线段的另一个端点
                    next_point = current_line.p2 if current_point == current_line.p1 else current_line.p1
                    
                    # if回到起点，找到一个多边形
                    if next_point == start_point and len(polygon_lines) >= 3:
                        found_polygon = True
                        break
                    
                    # 确保顶点按顺序添加
                    if next_point not in polygon_vertices:
                        polygon_vertices.append(next_point)
                    
                    # 查找从next_point出发的未访问线段
                    next_line = None
                    for line in vertex_lines[next_point]:
                        # 跳过非Line类型的对象
                        if not isinstance(line, Line):
                            continue
                        if line != current_line and line not in polygon_lines:
                            next_line = line
                            break
                    
                    # if没有找到下一条线段，路径不能闭合
                    if next_line is None:
                        break
                    
                    # 继续路径搜索
                    current_point = next_point
                    current_line = next_line
                    
                    # 避免无限循环
                    if len(polygon_lines) > 100:  # 设置合理上限
                        break
                
                # if找到有效多边形，添加到结果
                if found_polygon:
                    # 标记所有使用的线段为已访问
                    for line in polygon_lines:
                        visited_lines.add(line)
                    
                    # 确保顶点是按顺序排列的
                    if len(polygon_vertices) >= 3:
                        # if起点不是第一个添加的顶点，调整顶点顺序
                        if polygon_vertices[0] != start_point:
                            # 找到起点在顶点列表中的位置
                            start_idx = polygon_vertices.index(start_point)
                            # 重新排序顶点，使起点成为第一个顶点
                            polygon_vertices = polygon_vertices[start_idx:] + polygon_vertices[:start_idx]
                        
                        polygons.append(Polygon(polygon_lines, polygon_vertices))
        
        return polygons
        
    def split_lines_at_intersections(self, lines, points, vertex_lines):
        """拆分穿过交点的线段
        
        参数:
        - lines: 画布上的所有线段
        - points: 画布上的所有点和交点
        - vertex_lines: 顶点与线段的连接关系字典
        """
        from .intersection import Intersection
        from .geometry import Line
        
        # 查找所有需要拆分的线段和交点
        virtual_splits = []
        for point in points:
            # 检查是否是交点
            is_intersection = isinstance(point, Intersection) or (hasattr(point, 'is_intersection') and point.is_intersection)
            if not is_intersection:
                continue
                
            # 找出所有经过这个交点但不以它为端点的线段
            for line in lines:
                if point == line.p1 or point == line.p2:
                    continue
                    
                # 检查点是否在线段上
                d1 = math.sqrt((point.x - line.p1.x)**2 + (point.y - line.p1.y)**2)
                d2 = math.sqrt((point.x - line.p2.x)**2 + (point.y - line.p2.y)**2)
                line_length = math.sqrt((line.p2.x - line.p1.x)**2 + (line.p2.y - line.p1.y)**2)
                
                if abs(d1 + d2 - line_length) < 1e-6:
                    # 记录需要拆分的线段和交点
                    virtual_splits.append((line, point))
        
        # 对于虚拟拆分的线段，在顶点-线段连接关系中进行更新
        for line, point in virtual_splits:
            # 确保交点与这条线相连
            if point in vertex_lines and line not in vertex_lines[point]:
                vertex_lines[point].append(line)
                
            # 确保线段的两个端点都与交点相连
            if line.p1 in vertex_lines:
                endpoints = vertex_lines[line.p1]
                for i, other_line in enumerate(endpoints):
                    # 跳过非Line类型的对象
                    if not isinstance(other_line, Line):
                        continue
                    if other_line == line:
                        # 找到了线段，确保端点知道它连接了交点
                        if point not in vertex_lines[line.p1]:
                            vertex_lines[line.p1].append(point)
                            
            if line.p2 in vertex_lines:
                endpoints = vertex_lines[line.p2]
                for i, other_line in enumerate(endpoints):
                    # 跳过非Line类型的对象
                    if not isinstance(other_line, Line):
                        continue
                    if other_line == line:
                        # 找到了线段，确保端点知道它连接了交点
                        if point not in vertex_lines[line.p2]:
                            vertex_lines[line.p2].append(point)


class DrawDialog(QDialog):
    """封闭图形绘制对话框"""
    
    def __init__(self, parent=None, canvas=None):
        super().__init__(parent)
        self.canvas = canvas
        self.polygons = []
        self.current_polygon = None
        
        # 导入所需的类
        from .geometry import Point, Line
        
        # 手动创建多边形需要的变量
        self.manual_points = []  # 存储手动选择的点
        self.canvas_points = []  # 存储画布上的所有点
        self.is_manual_mode = False  # 是否处于手动创建模式
        
        self.setWindowTitle("绘制封闭图形")
        self.resize(700, 600)  # 进一步增加窗口宽度
        
        self.setup_ui()
        self.detect_polygons()
        
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout(self)
        
        
        # 使用水平布局将主要功能区并排放置
        main_layout = QHBoxLayout()
        
        # 左侧：多边形列表和手动创建面板
        left_panel = QVBoxLayout()
        
        # 多边形列表
        list_group = QGroupBox("检测到的图形")
        list_layout = QVBoxLayout(list_group)
        
        self.polygon_list = QListWidget()
        self.polygon_list.currentRowChanged.connect(self.select_polygon)
        list_layout.addWidget(self.polygon_list)
        
        left_panel.addWidget(list_group)
        
        # 手动创建多边形面板
        manual_create_group = QGroupBox("手动创建多边形")
        manual_layout = QVBoxLayout(manual_create_group)
        
        manual_desc = QLabel("从画布上的点中选择点创建自定义封闭图形")
        manual_layout.addWidget(manual_desc)
        
        # 添加状态标签
        self.status_label = QLabel("当前状态：未开始选择")
        self.status_label.setStyleSheet("color: blue;")
        manual_layout.addWidget(self.status_label)
        
        # 画布上的点列表
        canvas_points_group = QGroupBox("画布上的点")
        canvas_points_layout = QVBoxLayout(canvas_points_group)
        
        self.canvas_points_list = QListWidget()
        self.canvas_points_list.setSelectionMode(QListWidget.SingleSelection)
        self.canvas_points_list.itemDoubleClicked.connect(self.add_point_from_list)
        canvas_points_layout.addWidget(self.canvas_points_list)
        
        # 添加点按钮
        add_point_btn = QPushButton("添加选中的点")
        add_point_btn.clicked.connect(self.add_selected_point)
        canvas_points_layout.addWidget(add_point_btn)
        
        # 刷新点列表按钮
        refresh_points_btn = QPushButton("刷新点列表")
        refresh_points_btn.clicked.connect(self.refresh_canvas_points)
        canvas_points_layout.addWidget(refresh_points_btn)
        
        manual_layout.addWidget(canvas_points_group)
        
        btn_layout = QHBoxLayout()
        self.start_select_btn = QPushButton("开始选择点")
        self.start_select_btn.clicked.connect(self.start_manual_selection)
        btn_layout.addWidget(self.start_select_btn)
        
        self.create_polygon_btn = QPushButton("创建多边形")
        self.create_polygon_btn.clicked.connect(self.create_manual_polygon)
        self.create_polygon_btn.setEnabled(False)
        btn_layout.addWidget(self.create_polygon_btn)
        
        self.cancel_select_btn = QPushButton("取消选择")
        self.cancel_select_btn.clicked.connect(self.cancel_manual_selection)
        self.cancel_select_btn.setEnabled(False)
        btn_layout.addWidget(self.cancel_select_btn)
        
        manual_layout.addLayout(btn_layout)
        
        # 显示已选择的点
        point_select_layout = QHBoxLayout()
        point_select_layout.addWidget(QLabel("已选择的点:"))
        
        points_widget = QWidget()
        points_inner_layout = QVBoxLayout(points_widget)
        points_inner_layout.setContentsMargins(0, 0, 0, 0)
        
        self.selected_points_list = QListWidget()
        self.selected_points_list.setSelectionMode(QListWidget.ExtendedSelection)  # 允许多选
        points_inner_layout.addWidget(self.selected_points_list)
        
        # 添加移除按钮
        self.remove_points_btn = QPushButton("移除选中的点")
        self.remove_points_btn.clicked.connect(self.remove_selected_points)
        self.remove_points_btn.setEnabled(False)
        points_inner_layout.addWidget(self.remove_points_btn)
        
        point_select_layout.addWidget(points_widget)
        manual_layout.addLayout(point_select_layout)
        
        # 连接点列表选择变化信号
        self.selected_points_list.itemSelectionChanged.connect(self.on_points_selection_changed)
        
        left_panel.addWidget(manual_create_group)
        
        # 右侧：图形属性面板
        right_panel = QVBoxLayout()
        
        # 图形类型显示
        self.shape_type_group = QGroupBox("图形类型")
        shape_type_layout = QVBoxLayout(self.shape_type_group)
        self.shape_type_label = QLabel("未选择图形")
        shape_type_layout.addWidget(self.shape_type_label)
        right_panel.addWidget(self.shape_type_group)
        
        # 绘制属性面板
        properties_group = QGroupBox("绘制属性")
        properties_layout = QVBoxLayout(properties_group)
        
        # 颜色选择
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("填充颜色:"))
        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(60, 20)
        self.color_btn.clicked.connect(self.change_color)
        color_layout.addWidget(self.color_btn)
        properties_layout.addLayout(color_layout)
        
        # 显示填充选项
        self.fill_checkbox = QCheckBox("显示填充")
        self.fill_checkbox.setChecked(True)
        self.fill_checkbox.toggled.connect(self.toggle_fill)
        properties_layout.addWidget(self.fill_checkbox)
        
        # 创建特性选项卡区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # 添加几何特性复选框
        self.diag_checkbox = QCheckBox("显示对角线")
        self.diag_checkbox.toggled.connect(self.toggle_diagonals)
        scroll_layout.addWidget(self.diag_checkbox)
        
        # 三角形特有属性区域
        self.triangle_props_widget = QWidget()
        triangle_layout = QVBoxLayout(self.triangle_props_widget)
        
        # 中位线选择区域
        median_group = QGroupBox("中位线")
        median_layout = QVBoxLayout(median_group)
        
        self.medians_checkbox = QCheckBox("显示中位线")
        self.medians_checkbox.toggled.connect(self.toggle_medians)
        median_layout.addWidget(self.medians_checkbox)
        
        # 顶点选择区域
        self.median_selection_widget = QWidget()
        median_selection_layout = QHBoxLayout(self.median_selection_widget)
        self.median_A_checkbox = QCheckBox("顶点A")
        self.median_B_checkbox = QCheckBox("顶点B")
        self.median_C_checkbox = QCheckBox("顶点C")
        
        self.median_A_checkbox.toggled.connect(self.update_median_selection)
        self.median_B_checkbox.toggled.connect(self.update_median_selection)
        self.median_C_checkbox.toggled.connect(self.update_median_selection)
        
        median_selection_layout.addWidget(self.median_A_checkbox)
        median_selection_layout.addWidget(self.median_B_checkbox)
        median_selection_layout.addWidget(self.median_C_checkbox)
        
        median_layout.addWidget(self.median_selection_widget)
        triangle_layout.addWidget(median_group)
        
        # 高线选择
        height_group = QGroupBox("高")
        height_layout = QVBoxLayout(height_group)
        
        self.heights_checkbox = QCheckBox("显示高")
        self.heights_checkbox.toggled.connect(self.toggle_heights)
        height_layout.addWidget(self.heights_checkbox)
        
        # 顶点选择区域
        self.height_selection_widget = QWidget()
        height_selection_layout = QHBoxLayout(self.height_selection_widget)
        self.height_A_checkbox = QCheckBox("顶点A")
        self.height_B_checkbox = QCheckBox("顶点B")
        self.height_C_checkbox = QCheckBox("顶点C")
        
        self.height_A_checkbox.toggled.connect(self.update_height_selection)
        self.height_B_checkbox.toggled.connect(self.update_height_selection)
        self.height_C_checkbox.toggled.connect(self.update_height_selection)
        
        height_selection_layout.addWidget(self.height_A_checkbox)
        height_selection_layout.addWidget(self.height_B_checkbox)
        height_selection_layout.addWidget(self.height_C_checkbox)
        
        height_layout.addWidget(self.height_selection_widget)
        
        # 添加创建垂足点按钮
        create_height_foot_btn = QPushButton("创建高的垂足点")
        create_height_foot_btn.clicked.connect(self.create_height_foot_points)
        height_layout.addWidget(create_height_foot_btn)
        
        triangle_layout.addWidget(height_group)
        
        # 角平分线选择区域
        bisector_group = QGroupBox("角平分线")
        bisector_layout = QVBoxLayout(bisector_group)
        
        self.bisectors_checkbox = QCheckBox("显示角平分线")
        self.bisectors_checkbox.toggled.connect(self.toggle_angle_bisectors)
        bisector_layout.addWidget(self.bisectors_checkbox)
        
        # 角选择区域
        self.angle_selection_widget = QWidget()
        angle_layout = QHBoxLayout(self.angle_selection_widget)
        self.angle_A_checkbox = QCheckBox("角A")
        self.angle_B_checkbox = QCheckBox("角B")
        self.angle_C_checkbox = QCheckBox("角C")
        
        self.angle_A_checkbox.toggled.connect(self.update_angle_selection)
        self.angle_B_checkbox.toggled.connect(self.update_angle_selection)
        self.angle_C_checkbox.toggled.connect(self.update_angle_selection)
        
        angle_layout.addWidget(self.angle_A_checkbox)
        angle_layout.addWidget(self.angle_B_checkbox)
        angle_layout.addWidget(self.angle_C_checkbox)
        
        bisector_layout.addWidget(self.angle_selection_widget)
        
        # 添加创建角平分线交点按钮
        create_angle_bisector_points_btn = QPushButton("创建角平分线交点")
        create_angle_bisector_points_btn.clicked.connect(self.create_angle_bisector_points)
        bisector_layout.addWidget(create_angle_bisector_points_btn)
        
        triangle_layout.addWidget(bisector_group)
        
        # 添加三角形特有属性到滚动区域
        self.triangle_props_widget.setVisible(False)
        scroll_layout.addWidget(self.triangle_props_widget)
        
        # 四边形特有属性区域
        self.quadrilateral_props_widget = QWidget()
        quad_layout = QVBoxLayout(self.quadrilateral_props_widget)
        
        self.midlines_checkbox = QCheckBox("显示中点连线")
        self.midlines_checkbox.toggled.connect(self.toggle_midlines)
        quad_layout.addWidget(self.midlines_checkbox)
        
        # 添加四边形特有属性到滚动区域
        self.quadrilateral_props_widget.setVisible(False)
        scroll_layout.addWidget(self.quadrilateral_props_widget)
        
        scroll_area.setWidget(scroll_widget)
        properties_layout.addWidget(scroll_area)
        
        right_panel.addWidget(properties_group)
        
        # 将左右面板添加到主布局
        main_layout.addLayout(left_panel, 1)  # 左侧占比更小
        main_layout.addLayout(right_panel, 3)  # 右侧占比更大
        
        layout.addLayout(main_layout)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self.apply_changes)
        button_layout.addWidget(apply_btn)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def detect_polygons(self):
        """检测画布上的多边形"""
        detector = PolygonDetector(self.canvas)
        try:
            self.polygons = detector.detect_polygons()
        except Exception as e:
            # 捕获可能的错误
            import traceback
            print(f"检测多边形时出错: {e}")
            print(traceback.format_exc())
            self.polygons = []  # 错误时使用空列表
        
        # 清空多边形列表并重新添加
        self.polygon_list.clear()
        for i, polygon in enumerate(self.polygons):
            # 使用多边形名称或生成默认名称
            if hasattr(polygon, 'name') and polygon.name:
                item_text = polygon.name
            else:
                item_text = f"多边形 {i+1}"
            self.polygon_list.addItem(item_text)
            
        # if检测到多边形，默认选择第一个
        if self.polygons:
            self.polygon_list.setCurrentRow(0)
            self.current_polygon = self.polygons[0]
            self.update_ui()
        else:
            self.current_polygon = None
            self.shape_type_label.setText("未检测到多边形")
    
    def select_polygon(self, index):
        """选择多边形"""
        if index < 0 or index >= len(self.polygons):
            self.current_polygon = None
            return
        
        self.current_polygon = self.polygons[index]
        self.update_ui()
        
        # 选择多边形时，if显示高线，确保更新垂足点位置
        if self.current_polygon and self.current_polygon.show_heights:
            if self.create_height_foot_points():
                print(f"已更新 {self.current_polygon.name} 的高垂足点")
    
    def update_ui(self):
        """更新界面控件状态"""
        has_polygon = self.current_polygon is not None
        
        # 启用/禁用控件
        self.color_btn.setEnabled(has_polygon)
        self.fill_checkbox.setEnabled(has_polygon)
        self.diag_checkbox.setEnabled(has_polygon)
        
        # 隐藏所有特定图形类型控件
        self.triangle_props_widget.setVisible(False)
        self.quadrilateral_props_widget.setVisible(False)
        
        if has_polygon:
            # 更新图形类型显示
            self.shape_type_label.setText(f"类型: {self.current_polygon.shape_type}")
            
            # 更新颜色按钮背景
            self.set_color_button_background(self.current_polygon.fill_color)
            
            # 更新通用复选框状态
            self.fill_checkbox.setChecked(self.current_polygon.show_fill)
            self.diag_checkbox.setChecked(self.current_polygon.show_diagonals)
            
            # 根据图形类型显示特定控件
            if len(self.current_polygon.vertices) == 3:
                # 三角形特有属性
                self.triangle_props_widget.setVisible(True)
                self.medians_checkbox.setChecked(self.current_polygon.show_medians)
                self.heights_checkbox.setChecked(self.current_polygon.show_heights)
                self.bisectors_checkbox.setChecked(self.current_polygon.show_angle_bisectors)
                
                # 设置中位线选择复选框
                if not hasattr(self.current_polygon, 'selected_medians'):
                    self.current_polygon.selected_medians = {'A': True, 'B': True, 'C': True}
                self.median_A_checkbox.setChecked(self.current_polygon.selected_medians.get('A', True))
                self.median_B_checkbox.setChecked(self.current_polygon.selected_medians.get('B', True))
                self.median_C_checkbox.setChecked(self.current_polygon.selected_medians.get('C', True))
                
                # 设置高选择复选框
                if not hasattr(self.current_polygon, 'selected_heights'):
                    self.current_polygon.selected_heights = {'A': True, 'B': True, 'C': True}
                self.height_A_checkbox.setChecked(self.current_polygon.selected_heights.get('A', True))
                self.height_B_checkbox.setChecked(self.current_polygon.selected_heights.get('B', True))
                self.height_C_checkbox.setChecked(self.current_polygon.selected_heights.get('C', True))
                
                # 设置角平分线选择复选框
                if not hasattr(self.current_polygon, 'selected_angles'):
                    self.current_polygon.selected_angles = {'A': True, 'B': True, 'C': True}
                self.angle_A_checkbox.setChecked(self.current_polygon.selected_angles.get('A', True))
                self.angle_B_checkbox.setChecked(self.current_polygon.selected_angles.get('B', True))
                self.angle_C_checkbox.setChecked(self.current_polygon.selected_angles.get('C', True))
                
            elif len(self.current_polygon.vertices) == 4:
                # 四边形特有属性
                self.quadrilateral_props_widget.setVisible(True)
                self.midlines_checkbox.setChecked(self.current_polygon.show_midlines)
                
            else:
                # 其他多边形
                self.diag_checkbox.setEnabled(len(self.current_polygon.vertices) > 3)
    
    def update_angle_selection(self):
        """更新角平分线的选择状态"""
        if not self.current_polygon or len(self.current_polygon.vertices) != 3:
            return
            
        # 存储角选择状态
        if not hasattr(self.current_polygon, 'selected_angles'):
            self.current_polygon.selected_angles = {'A': True, 'B': True, 'C': True}
            
        self.current_polygon.selected_angles['A'] = self.angle_A_checkbox.isChecked()
        self.current_polygon.selected_angles['B'] = self.angle_B_checkbox.isChecked()
        self.current_polygon.selected_angles['C'] = self.angle_C_checkbox.isChecked()
        
        # if至少有一个角被选中，启用角平分线
        has_selected = any(self.current_polygon.selected_angles.values())
        self.bisectors_checkbox.setEnabled(has_selected)
        
        if has_selected:
            self.current_polygon.show_angle_bisectors = self.bisectors_checkbox.isChecked()
        else:
            self.current_polygon.show_angle_bisectors = False
            self.bisectors_checkbox.setChecked(False)
            
        self.canvas.update()
    
    def set_color_button_background(self, color):
        """设置颜色按钮背景色"""
        self.color_btn.setStyleSheet(
            f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()});"
        )
    
    def change_color(self):
        """更改填充颜色"""
        if not self.current_polygon:
            return
            
        color = QColorDialog.getColor(
            self.current_polygon.fill_color, 
            self, 
            "选择填充颜色",
            QColorDialog.ShowAlphaChannel
        )
        
        if color.isValid():
            self.current_polygon.fill_color = color
            self.set_color_button_background(color)
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_fill(self, checked):
        """切换填充显示"""
        if self.current_polygon:
            self.current_polygon.show_fill = checked
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_diagonals(self, checked):
        """切换对角线显示"""
        if self.current_polygon:
            self.current_polygon.show_diagonals = checked
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_medians(self, checked):
        """切换中位线显示"""
        if self.current_polygon:
            self.current_polygon.show_medians = checked
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_heights(self, checked):
        """切换显示高"""
        if self.current_polygon:
            self.current_polygon.show_heights = checked
            
            # if开启了高显示，确保创建垂足点
            if checked:
                if self.create_height_foot_points():
                    print("已创建/更新高的垂足点")
                else:
                    print("没有需要创建/更新的高的垂足点")
            
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_angle_bisectors(self, checked):
        """切换角平分线显示"""
        if self.current_polygon:
            self.current_polygon.show_angle_bisectors = checked
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def toggle_midlines(self, checked):
        """切换中点连线显示"""
        if self.current_polygon:
            self.current_polygon.show_midlines = checked
            # 立即保存属性
            # 属性已更新 - 移除ZAT保存
            self.canvas.update()
    
    def apply_changes(self):
        """应用所有更改"""
        # 临时保存手动创建的多边形，确保来源标记被保留
        manual_polygons = [p for p in self.polygons if hasattr(p, 'source') and p.source == 'manual']
        
        # 清空画布上的活跃多边形
        self.canvas.active_polygons = []
        
        # 添加所有处于显示状态的多边形
        for polygon in self.polygons:
            # 确保所有多边形都有source属性
            if not hasattr(polygon, 'source'):
                polygon.source = 'auto'  # 默认为自动检测的多边形
                
            # 对于手动创建的多边形，确保source属性正确设置
            if polygon in manual_polygons:
                polygon.source = 'manual'
                
            if polygon.show_fill or polygon.show_diagonals or polygon.show_medians or \
               polygon.show_heights or polygon.show_angle_bisectors or polygon.show_midlines or \
               polygon.show_incircle or polygon.show_circumcircle:
                self.canvas.active_polygons.append(polygon)
                
                # if显示高线，确保创建/更新垂足点
                if polygon.show_heights:
                    # 临时设置当前多边形，以便创建高的垂足点
                    temp_current = self.current_polygon
                    self.current_polygon = polygon
                    created = self.create_height_foot_points()
                    if created:
                        print(f"已更新 {polygon.name} 的高垂足点")
                    self.current_polygon = temp_current
        
        # 检查所有多边形与点的交点，并命名（仅命名已存在的点，不创建新点）
        for polygon in self.canvas.active_polygons:
            polygon.check_edge_intersections(self.canvas)
        
        # 立即保存多边形属性到文件，而不是等待拖动
        # 属性已更新 - 移除ZAT保存
        
        # 更新画布
        self.canvas.update()
    
    def update_median_selection(self):
        """更新中位线的选择状态"""
        if not self.current_polygon or len(self.current_polygon.vertices) != 3:
            return
            
        # 存储中位线选择状态
        if not hasattr(self.current_polygon, 'selected_medians'):
            self.current_polygon.selected_medians = {'A': True, 'B': True, 'C': True}
            
        self.current_polygon.selected_medians['A'] = self.median_A_checkbox.isChecked()
        self.current_polygon.selected_medians['B'] = self.median_B_checkbox.isChecked()
        self.current_polygon.selected_medians['C'] = self.median_C_checkbox.isChecked()
        
        # if至少有一个顶点被选中，启用中位线
        has_selected = any(self.current_polygon.selected_medians.values())
        self.medians_checkbox.setEnabled(has_selected)
        
        if has_selected:
            self.current_polygon.show_medians = self.medians_checkbox.isChecked()
        else:
            self.current_polygon.show_medians = False
            self.medians_checkbox.setChecked(False)
            
        self.canvas.update()
    
    def update_height_selection(self):
        """更新高的选择状态"""
        if not self.current_polygon or len(self.current_polygon.vertices) != 3:
            return
            
        # 存储高的选择状态
        if not hasattr(self.current_polygon, 'selected_heights'):
            self.current_polygon.selected_heights = {'A': True, 'B': True, 'C': True}
            
        self.current_polygon.selected_heights['A'] = self.height_A_checkbox.isChecked()
        self.current_polygon.selected_heights['B'] = self.height_B_checkbox.isChecked()
        self.current_polygon.selected_heights['C'] = self.height_C_checkbox.isChecked()
        
        # if至少有一个顶点被选中，启用高
        has_selected = any(self.current_polygon.selected_heights.values())
        self.heights_checkbox.setEnabled(has_selected)
        
        if has_selected:
            self.current_polygon.show_heights = self.heights_checkbox.isChecked()
            # if高处于显示状态，更新垂足点
            if self.current_polygon.show_heights:
                self.create_height_foot_points()
        else:
            self.current_polygon.show_heights = False
            self.heights_checkbox.setChecked(False)
            
        self.canvas.update()

    def create_height_foot_points(self):
        """创建高的垂足点"""
        if not self.current_polygon or len(self.current_polygon.vertices) != 3:
            return False
            
        # 引用在__init__方法中导入的Point类    
        from .geometry import Point
        points_created_or_updated = False
        
        # 对每个顶点计算垂足
        for i, vertex in enumerate(self.current_polygon.vertices):
            # 只处理被选中的高
            vertex_name = chr(65 + i)  # A, B, C
            if not hasattr(self.current_polygon, 'selected_heights') or \
               not self.current_polygon.selected_heights.get(vertex_name, False):
                continue
                
            # 对边顶点
            p1 = self.current_polygon.vertices[(i + 1) % 3]
            p2 = self.current_polygon.vertices[(i - 1) % 3]
            
            # 计算垂足
            foot = self.current_polygon._calculate_perpendicular_foot(vertex, p1, p2)
            foot_x, foot_y = foot[0], foot[1]
            
            # 检查垂足是否在线段上
            is_on_segment = self.current_polygon._is_point_on_segment(foot, p1, p2)
            if not is_on_segment:
                # if垂足不在线段上，可以选择延长线段或者跳过
                # 这里尝试找到垂足在延长线上的位置
                from_p1_to_p2 = (p2.x - p1.x, p2.y - p1.y)
                from_p2_to_p1 = (p1.x - p2.x, p1.y - p2.y)
                
                # 计算点到线段的距离
                dist_p1_to_foot = math.sqrt((p1.x - foot_x)**2 + (p1.y - foot_y)**2)
                dist_p2_to_foot = math.sqrt((p2.x - foot_x)**2 + (p2.y - foot_y)**2)
                
                # 检查垂足是在哪条射线上
                if dist_p1_to_foot < dist_p2_to_foot:
                    # 垂足在p1射线上，向p1方向延伸
                    pass
                else:
                    # 垂足在p2射线上，向p2方向延伸
                    pass
                
                # 由于垂足不在线段上，这里仍然创建点，但给出提示
                print(f"警告: 顶点{vertex.name}的高的垂足不在对边上，将在延长线上创建")
            
            # 生成垂足名称
            foot_name = f"{vertex.name}′" if vertex.name else f"H{i+1}"
            
            # 首先尝试查找名称匹配的点
            existing_foot = None
            for obj in self.canvas.objects:
                if isinstance(obj, Point) and obj.name == foot_name:
                    # 找到同名点，更新位置
                    obj.x = foot_x
                    obj.y = foot_y
                    # 更新标签位置
                    if hasattr(self.canvas, 'name_position_manager'):
                        self.canvas.name_position_manager.update_object_changed(obj)
                    existing_foot = obj
                    points_created_or_updated = True
                    print(f"更新高的垂足点: {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                    break
            
            # if没有找到同名点，查找相近位置的点
            if not existing_foot:
                for obj in self.canvas.objects:
                    if isinstance(obj, Point):
                        dist = math.sqrt((obj.x - foot_x)**2 + (obj.y - foot_y)**2)
                        if dist < 5:  # 使用较大阈值判断
                            # 更新位置和名称
                            old_name = obj.name
                            obj.name = foot_name
                            obj.x = foot_x
                            obj.y = foot_y
                            # 更新标签位置
                            if hasattr(self.canvas, 'name_position_manager'):
                                self.canvas.name_position_manager.update_object_changed(obj)
                            existing_foot = obj
                            points_created_or_updated = True
                            print(f"将点 {old_name} 更新为高的垂足点 {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                            break
            
            # if仍未找到，创建新的垂足点
            if not existing_foot:
                new_foot = Point(foot_x, foot_y, foot_name)
                # 将此点标记为高的垂足点
                new_foot.is_height_foot = True
                new_foot.from_vertex = vertex
                self.canvas.add_object(new_foot)
                points_created_or_updated = True
                print(f"创建新的高的垂足点: {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                
                # 存储关联信息
                if not hasattr(self.current_polygon, 'height_feet'):
                    self.current_polygon.height_feet = {}
                self.current_polygon.height_feet[vertex.name] = new_foot
            elif not hasattr(existing_foot, 'is_height_foot'):
                # 将现有点标记为高的垂足点
                existing_foot.is_height_foot = True
                existing_foot.from_vertex = vertex
                
                # 存储关联信息
                if not hasattr(self.current_polygon, 'height_feet'):
                    self.current_polygon.height_feet = {}
                self.current_polygon.height_feet[vertex.name] = existing_foot
        
        # if创建或更新了点，检查交点并更新显示
        if points_created_or_updated:
            # 检查与多边形边的交点
            self.current_polygon.check_edge_intersections(self.canvas)
            # 更新画布
            self.canvas.update()
            
        return points_created_or_updated
    
    def create_angle_bisector_points(self):
        """创建角平分线交点"""
        if not self.current_polygon or len(self.current_polygon.vertices) != 3:
            return
            
        # 直接使用已导入的Point类
        points_created = False
        
        # 检查每个角
        for i, vertex in enumerate(self.current_polygon.vertices):
            # 相邻顶点
            p_prev = self.current_polygon.vertices[(i - 1) % 3]
            p_next = self.current_polygon.vertices[(i + 1) % 3]
            
            # 计算角平分线向量
            v1 = QPointF(p_prev.x - vertex.x, p_prev.y - vertex.y)
            v2 = QPointF(p_next.x - vertex.x, p_next.y - vertex.y)
            
            # 归一化向量
            len1 = math.sqrt(v1.x()**2 + v1.y()**2)
            len2 = math.sqrt(v2.x()**2 + v2.y()**2)
            
            if len1 > 0 and len2 > 0:
                v1 = QPointF(v1.x()/len1, v1.y()/len1)
                v2 = QPointF(v2.x()/len2, v2.y()/len2)
                
                # 计算角平分线向量
                bisector = QPointF(v1.x() + v2.x(), v1.y() + v2.y())
                bisector_len = math.sqrt(bisector.x()**2 + bisector.y()**2)
                
                if bisector_len > 0:
                    # 对边（相对角顶点的对边）
                    edge_p1 = self.current_polygon.vertices[(i + 1) % 3]
                    edge_p2 = self.current_polygon.vertices[(i + 2) % 3]
                    
                    # 计算角平分线方向上足够远的点
                    far_point_x = vertex.x + bisector.x() / bisector_len * 1000  # 延伸足够远
                    far_point_y = vertex.y + bisector.y() / bisector_len * 1000
                    
                    # 计算交点
                    intersection = self.current_polygon._line_intersection(
                        (vertex.x, vertex.y), (far_point_x, far_point_y),
                        (edge_p1.x, edge_p1.y), (edge_p2.x, edge_p2.y)
                    )
                    
                    # if找到交点，创建新点
                    if intersection:
                        # 检查是否已存在此交点
                        existing_point = None
                        for obj in self.canvas.objects:
                            if isinstance(obj, Point):
                                dist = math.sqrt((obj.x - intersection[0])**2 + (obj.y - intersection[1])**2)
                                if dist < 5:  # 使用较大阈值判断
                                    existing_point = obj
                                    break
                        
                        # if不存在，创建新点
                        if not existing_point:
                            # 使用角顶点的名称生成交点名称
                            if vertex.name:
                                point_name = f"{vertex.name}_D"  # D表示角平分线(Divider)
                            else:
                                point_name = f"D{i+1}"
                                
                            new_point = Point(intersection[0], intersection[1], point_name)
                            self.canvas.add_object(new_point)
                            points_created = True
                            
        # if创建了新点，检查交点并更新显示
        if points_created:
            # 检查与多边形边的交点
            self.current_polygon.check_edge_intersections(self.canvas)
            # 更新画布
            self.canvas.update()
        
        self.canvas.update()

    def start_manual_selection(self):
        """开始手动选择点模式"""
        self.is_manual_mode = True
        self.manual_points = []  # 清空已选点列表
        self.selected_points_list.clear()
        self.start_select_btn.setEnabled(False)
        self.create_polygon_btn.setEnabled(False)
        self.cancel_select_btn.setEnabled(True)
        self.remove_points_btn.setEnabled(False)  # 初始时没有选中的点，禁用移除按钮
        
        # 刷新画布上的点
        self.refresh_canvas_points()
        
        # 更新状态标签
        self.status_label.setText("当前状态：正在选择点")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        
        # 显示提示信息
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("选择提示")
        msg.setText("请从列表中选择点，至少需要3个点构成多边形")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def refresh_canvas_points(self):
        """刷新画布上的点列表"""
        self.canvas_points = []
        self.canvas_points_list.clear()
        
        if not self.canvas:
            return
            
        # 收集画布上的所有点（包括普通点和交点）
        for obj in self.canvas.objects:
            if isinstance(obj, Point):
                self.canvas_points.append(obj)
                
                # 在列表中显示点信息
                item_text = f"{obj.name} ({obj.x:.1f}, {obj.y:.1f})"
                self.canvas_points_list.addItem(item_text)
    
    def add_selected_point(self):
        """添加当前选中的点到已选择列表"""
        if not self.is_manual_mode:
            return
            
        selected_items = self.canvas_points_list.selectedItems()
        if not selected_items:
            return
            
        item_idx = self.canvas_points_list.row(selected_items[0])
        if item_idx < 0 or item_idx >= len(self.canvas_points):
            return
            
        point = self.canvas_points[item_idx]
        self.add_point_to_selection(point)
    
    def add_point_from_list(self, item):
        """从列表中双击添加点"""
        if not self.is_manual_mode:
            return
            
        item_idx = self.canvas_points_list.row(item)
        if item_idx < 0 or item_idx >= len(self.canvas_points):
            return
            
        point = self.canvas_points[item_idx]
        self.add_point_to_selection(point)
    
    def add_point_to_selection(self, point):
        """将点添加到选择列表中"""
        # 检查点是否已经在选择列表中
        if point in self.manual_points:
            # 提示user点已被选择
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("提示")
            msg.setText(f"点 {point.name} 已被选择")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return
            
        # 添加到已选择点列表
        self.manual_points.append(point)
        
        # 更新列表显示
        item_text = f"{point.name} ({point.x:.1f}, {point.y:.1f})"
        self.selected_points_list.addItem(item_text)
        
        # 更新状态标签
        points_count = len(self.manual_points)
        self.status_label.setText(f"当前状态：已选择 {points_count} 个点" + 
                                 (" (可以创建多边形)" if points_count >= 3 else ""))
        
        # if点数达到3个或以上，启用创建多边形按钮
        if points_count >= 3:
            self.create_polygon_btn.setEnabled(True)
    
    def cancel_manual_selection(self):
        """取消手动选择点模式"""
        self.is_manual_mode = False
        self.manual_points = []
        self.selected_points_list.clear()
        self.start_select_btn.setEnabled(True)
        self.create_polygon_btn.setEnabled(False)
        self.cancel_select_btn.setEnabled(False)
        
        # 更新状态标签
        self.status_label.setText("当前状态：未开始选择")
        self.status_label.setStyleSheet("color: blue;")

    def on_points_selection_changed(self):
        """处理点列表选择变化事件"""
        # 只有在手动模式下且有选中项时才启用移除按钮
        has_selection = len(self.selected_points_list.selectedItems()) > 0
        self.remove_points_btn.setEnabled(has_selection and self.is_manual_mode)
    
    def remove_selected_points(self):
        """移除选中的点"""
        if not self.is_manual_mode:
            return
            
        # 获取所有选中项的索引（从大到小排序，便于从列表中删除）
        selected_indices = sorted([self.selected_points_list.row(item) 
                                  for item in self.selected_points_list.selectedItems()], 
                                 reverse=True)
        
        if not selected_indices:
            return
            
        # 从列表和数据中移除点
        for index in selected_indices:
            self.selected_points_list.takeItem(index)
            if index < len(self.manual_points):
                del self.manual_points[index]
        
        # 更新状态标签
        points_count = len(self.manual_points)
        self.status_label.setText(f"当前状态：已选择 {points_count} 个点" + 
                                 (" (可以创建多边形)" if points_count >= 3 else ""))
        
        # 更新创建按钮状态
        self.create_polygon_btn.setEnabled(points_count >= 3)

    def create_manual_polygon(self):
        """根据手动选择的点创建多边形"""
        if len(self.manual_points) < 3:
            # 提示user点数不足
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("创建多边形至少需要3个点")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return
            
        # 创建连接线
        from .geometry import Line
        lines = []
        
        # 检查是否有重复点
        unique_points = []
        for point in self.manual_points:
            if point not in unique_points:
                unique_points.append(point)
                
        if len(unique_points) < 3:
            # 提示user有重复点
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("存在重复点，请确保至少有3个不同的点")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return
            
        # 创建闭合的线段环
        for i in range(len(self.manual_points)):
            p1 = self.manual_points[i]
            p2 = self.manual_points[(i + 1) % len(self.manual_points)]
            
            # 防止自环
            if p1 == p2:
                continue
                
            # 检查是否已存在连接这两点的线段
            existing_line = None
            for obj in self.canvas.objects:
                if isinstance(obj, Line):
                    if (obj.p1 == p1 and obj.p2 == p2) or (obj.p1 == p2 and obj.p2 == p1):
                        existing_line = obj
                        break
            
            if existing_line:
                lines.append(existing_line)
            else:
                # 创建新线段
                new_line = Line(p1, p2)
                self.canvas.add_object(new_line)
                lines.append(new_line)
        
        # 确保有足够的线段形成多边形
        if len(lines) < 3:
            # 提示user线段不足
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("警告")
            msg.setText("无法创建有效的多边形，请重新选择点")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return
            
        # 检查是否已存在相同的多边形
        for existing_polygon in self.polygons:
            # 检查顶点集是否相同（忽略顺序）
            if set(existing_polygon.vertices) == set(self.manual_points):
                # 提示user多边形已存在
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("提示")
                msg.setText(f"已存在相同顶点的多边形: {existing_polygon.name}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
                
                # 选中已存在的多边形
                for i, polygon in enumerate(self.polygons):
                    if polygon == existing_polygon:
                        self.polygon_list.setCurrentRow(i)
                        self.select_polygon(i)
                        break
                        
                # 重置手动选择模式
                self.is_manual_mode = False
                self.manual_points = []
                self.selected_points_list.clear()
                self.start_select_btn.setEnabled(True)
                self.create_polygon_btn.setEnabled(False)
                self.cancel_select_btn.setEnabled(False)
                
                # 更新状态标签
                self.status_label.setText("当前状态：使用已存在的多边形")
                self.status_label.setStyleSheet("color: blue;")
                
                return
        
        # 创建多边形对象
        new_polygon = Polygon(lines, self.manual_points)
        
        # 标记为手动创建的多边形，这样在拖动时能保留属性
        new_polygon.source = 'manual'
        
        # 初始化多边形的选择状态属性（对于三角形）
        if len(self.manual_points) == 3:
            new_polygon.selected_heights = {'A': True, 'B': True, 'C': True}
            new_polygon.selected_medians = {'A': True, 'B': True, 'C': True}
            new_polygon.selected_angles = {'A': True, 'B': True, 'C': True}
            # 默认开启高度线显示
            new_polygon.show_heights = True
        
        # 添加到多边形列表
        self.polygons.append(new_polygon)
        self.polygon_list.addItem(new_polygon.name)
        self.polygon_list.setCurrentRow(len(self.polygons) - 1)
        
        # 选择新创建的多边形并更新UI
        self.current_polygon = new_polygon
        self.update_ui()
        
        # 对于三角形，确保创建高的垂足点
        if len(self.manual_points) == 3:
            if self.create_height_foot_points():
                print(f"已为 {new_polygon.name} 创建高的垂足点")
        
        # 应用更改以更新画布上的活跃多边形
        self.apply_changes()
        
        # 立即保存多边形属性到文件，确保属性被保存
        # 属性已更新 - 移除ZAT保存
        
        # 重置手动选择模式
        self.is_manual_mode = False
        self.manual_points = []
        self.selected_points_list.clear()
        self.start_select_btn.setEnabled(True)
        self.create_polygon_btn.setEnabled(False)
        self.cancel_select_btn.setEnabled(False)
        
        # 更新状态标签
        self.status_label.setText("当前状态：多边形已创建")
        self.status_label.setStyleSheet("color: blue;")
        
        # 显示成功提示
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("成功")
        msg.setText(f"已成功创建多边形: {new_polygon.name}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def closeEvent(self, event):
        """关闭对话框前的处理"""
        # if处于手动模式，确保清理状态
        if self.is_manual_mode:
            self.is_manual_mode = False
            self.manual_points = []
            
        # 应用更改，确保更新所有垂足点
        self.apply_changes()
        
        # 更新所有多边形的高垂足点
        update_all_height_foot_points(self.canvas)
        
        # 接受关闭事件
        event.accept()


def show_draw_dialog(canvas):
    """显示绘制对话框"""
    try:
        # 刷新画布上所有多边形的高垂足点
        update_all_height_foot_points(canvas)
        
        dialog = DrawDialog(canvas=canvas)
        dialog.exec_()
    except Exception as e:
        import traceback
        print(f"打开绘制对话框时出错: {e}")
        print(traceback.format_exc())
        # 可以考虑显示错误提示对话框
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("错误")
        msg.setText("打开绘制对话框时出错")
        msg.setDetailedText(str(e))
        msg.exec_()


def update_all_height_foot_points(canvas):
    """更新画布上所有多边形的高垂足点"""
    # 找到所有活跃多边形
    active_polygons = canvas.active_polygons
    
    # 引用Point类
    from .geometry import Point
    points_updated = False
    
    # 保存所有多边形的属性，防止属性丢失
    polygon_attributes = {}
    for polygon in active_polygons:
        # 使用ID作为键
        polygon_id = id(polygon)
        polygon_attributes[polygon_id] = {
            'fill_color': polygon.fill_color,
            'show_fill': polygon.show_fill,
            'show_diagonals': polygon.show_diagonals,
            'show_medians': polygon.show_medians,
            'show_heights': polygon.show_heights,
            'show_angle_bisectors': polygon.show_angle_bisectors,
            'show_midlines': polygon.show_midlines,
            'show_incircle': polygon.show_incircle,
            'show_circumcircle': polygon.show_circumcircle
        }
        # 保存特殊属性
        if hasattr(polygon, 'selected_heights'):
            polygon_attributes[polygon_id]['selected_heights'] = polygon.selected_heights.copy()
        if hasattr(polygon, 'selected_angles'):
            polygon_attributes[polygon_id]['selected_angles'] = polygon.selected_angles.copy()
        if hasattr(polygon, 'height_feet'):
            polygon_attributes[polygon_id]['height_feet'] = polygon.height_feet
    
    # 首先删除所有标记为垂足点但原始顶点已不存在的点
    to_remove = []
    for obj in canvas.objects:
        if isinstance(obj, Point) and hasattr(obj, 'is_height_foot') and obj.is_height_foot:
            # 检查关联的顶点是否仍然存在
            if hasattr(obj, 'from_vertex'):
                vertex_exists = False
                # 检查顶点是否在任何活跃多边形中
                for polygon in active_polygons:
                    if obj.from_vertex in polygon.vertices:
                        # 还需要检查该顶点的高是否被选中
                        if polygon.show_heights and len(polygon.vertices) == 3:
                            i = polygon.vertices.index(obj.from_vertex)
                            vertex_name = chr(65 + i)  # A, B, C
                            if hasattr(polygon, 'selected_heights') and polygon.selected_heights.get(vertex_name, False):
                                vertex_exists = True
                                break
                if not vertex_exists:
                    to_remove.append(obj)
                    
    # 删除废弃的垂足点
    for obj in to_remove:
        if obj in canvas.objects:
            canvas.objects.remove(obj)
            print(f"移除过期的垂足点: {obj.name}")
            points_updated = True
    
    # 更新或创建垂足点
    for polygon in active_polygons:
        if polygon.show_heights and len(polygon.vertices) == 3:
            # 对每个顶点计算垂足
            for i, vertex in enumerate(polygon.vertices):
                # 检查是否有选择状态信息
                vertex_name = chr(65 + i)  # A, B, C
                # 注意这里的默认值改为False，只处理被明确选中的顶点高
                if hasattr(polygon, 'selected_heights') and not polygon.selected_heights.get(vertex_name, False):
                    continue
                
                # 对边顶点
                p1 = polygon.vertices[(i + 1) % 3]
                p2 = polygon.vertices[(i - 1) % 3]
                
                # 计算垂足
                foot = polygon._calculate_perpendicular_foot(vertex, p1, p2)
                foot_x, foot_y = foot[0], foot[1]
                
                # 生成垂足名称
                foot_name = f"{vertex.name}′" if vertex.name else f"H{i+1}"
                
                # 首先查找关联到此顶点的已有垂足点
                existing_foot = None
                for obj in canvas.objects:
                    if isinstance(obj, Point) and hasattr(obj, 'is_height_foot') and obj.is_height_foot:
                        if hasattr(obj, 'from_vertex') and obj.from_vertex == vertex:
                            existing_foot = obj
                            # 更新位置和名称
                            obj.x = foot_x
                            obj.y = foot_y
                            obj.name = foot_name  # 确保名称一致
                            # 更新标签位置
                            if hasattr(canvas, 'name_position_manager'):
                                canvas.name_position_manager.update_object_changed(obj)
                            points_updated = True
                            print(f"更新关联垂足点: {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                            break
                
                # if没找到关联垂足，再按名称查找
                if not existing_foot:
                    for obj in canvas.objects:
                        if isinstance(obj, Point) and obj.name == foot_name:
                            # 找到同名点，更新位置和关联
                            obj.x = foot_x
                            obj.y = foot_y
                            obj.is_height_foot = True  # 标记为垂足点
                            obj.from_vertex = vertex  # 建立关联
                            # 更新标签位置
                            if hasattr(canvas, 'name_position_manager'):
                                canvas.name_position_manager.update_object_changed(obj)
                            existing_foot = obj
                            points_updated = True
                            print(f"更新同名垂足点: {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                            break
                
                # if仍未找到，查找位置接近的点
                if not existing_foot:
                    for obj in canvas.objects:
                        if isinstance(obj, Point):
                            dist = math.sqrt((obj.x - foot_x)**2 + (obj.y - foot_y)**2)
                            if dist < 5:  # 使用较大阈值判断
                                # 更新位置和名称
                                old_name = obj.name
                                obj.name = foot_name
                                obj.x = foot_x
                                obj.y = foot_y
                                obj.is_height_foot = True  # 标记为垂足点
                                obj.from_vertex = vertex  # 建立关联
                                # 更新标签位置
                                if hasattr(canvas, 'name_position_manager'):
                                    canvas.name_position_manager.update_object_changed(obj)
                                existing_foot = obj
                                points_updated = True
                                print(f"将点 {old_name} 更新为高的垂足点 {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                                break
                
                # if仍未找到，创建新点
                if not existing_foot:
                    new_foot = Point(foot_x, foot_y, foot_name)
                    # 标记为垂足点并建立关联
                    new_foot.is_height_foot = True
                    new_foot.from_vertex = vertex
                    canvas.add_object(new_foot)
                    # 更新标签位置（add_object会自动调用update_all_name_positions）
                    points_updated = True
                    print(f"创建新的高的垂足点: {foot_name} 位置: ({foot_x:.1f}, {foot_y:.1f})")
                    
                    # 存储关联信息
                    if not hasattr(polygon, 'height_feet'):
                        polygon.height_feet = {}
                    polygon.height_feet[vertex.name] = new_foot
                elif not hasattr(polygon, 'height_feet') or vertex.name not in polygon.height_feet:
                    # 更新多边形的垂足点引用
                    if not hasattr(polygon, 'height_feet'):
                        polygon.height_feet = {}
                    polygon.height_feet[vertex.name] = existing_foot
    
    # 恢复所有多边形的属性
    for polygon in active_polygons:
        polygon_id = id(polygon)
        if polygon_id in polygon_attributes:
            attrs = polygon_attributes[polygon_id]
            polygon.fill_color = attrs.get('fill_color', polygon.fill_color)
            polygon.show_fill = attrs.get('show_fill', polygon.show_fill)
            polygon.show_diagonals = attrs.get('show_diagonals', polygon.show_diagonals)
            polygon.show_medians = attrs.get('show_medians', polygon.show_medians)
            polygon.show_heights = attrs.get('show_heights', polygon.show_heights)
            polygon.show_angle_bisectors = attrs.get('show_angle_bisectors', polygon.show_angle_bisectors)
            polygon.show_midlines = attrs.get('show_midlines', polygon.show_midlines)
            polygon.show_incircle = attrs.get('show_incircle', polygon.show_incircle)
            polygon.show_circumcircle = attrs.get('show_circumcircle', polygon.show_circumcircle)
            # 恢复特殊属性
            if 'selected_heights' in attrs:
                polygon.selected_heights = attrs['selected_heights'].copy()
            if 'selected_angles' in attrs:
                polygon.selected_angles = attrs['selected_angles'].copy()
            if 'height_feet' in attrs:
                polygon.height_feet = attrs['height_feet']
    
    # if有更新，刷新画布
    if points_updated:
        canvas.update()
        return True
    
    return False

# 全局变量，用于存储当前会话的属性文件名
# 全局变量current_session_file已移除
