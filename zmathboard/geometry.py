#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import numpy as np
from PyQt5.QtCore import QPointF, QLineF, QRectF, Qt, QVariantAnimation, QEasingCurve
from PyQt5.QtGui import QPen, QBrush, QColor

class GeometryObject:
    """几何对象基类"""
    
    def __init__(self, name=""):
        self.name = name
        self.visible = True
        self.selected = False
        self.animations = []
        self.draggable = True  # 是否可拖拽
        
    def draw(self, painter):
        """绘制图形方法，需要子类实现"""
        pass
        
    def contains(self, point):
        """检查点是否在对象上，需要子类实现"""
        return False
        
    def animate(self, animation):
        """添加动画"""
        self.animations.append(animation)
        
    def clear_animations(self):
        """清除所有动画"""
        self.animations = []
        
    def drag_to(self, new_pos):
        """拖拽到新位置，需要子类实现"""
        pass
        
    def get_bounds_rect(self, margin=0):
        """获取对象的边界矩形，用于局部重绘，需要子类实现"""
        return QRectF(0, 0, 0, 0)


class Point(GeometryObject):
    """点对象"""
    
    def __init__(self, x=0, y=0, name="", radius=5):
        super().__init__(name)
        self.x = float(x)  # 确保是浮点数
        self.y = float(y)  # 确保是浮点数
        self.radius = radius
        self.color = QColor(0, 0, 255)
        self.border_color = QColor(0, 0, 0)
        self.path_object = None  # 运动路径对象
        self.fixed = False  # 是否固定位置
        self.visible = True  # 是否可见，用于重叠检测
        
    def set_position(self, x, y):
        """设置点的坐标"""
        if not self.fixed:
            self.x = float(x)  # 确保是浮点数
            self.y = float(y)  # 确保是浮点数
        
    def get_qpointf(self):
        """获取QPointF对象"""
        return QPointF(self.x, self.y)
        
    def draw(self, painter):
        """绘制点"""
        if not self.visible:
            return
            
        pen = QPen(self.border_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        brush = QBrush(self.color)
        painter.setBrush(brush)
        
        # if被选中或固定，则增加视觉效果
        if self.selected:
            highlight_radius = self.radius + 3
            highlight_pen = QPen(QColor(255, 165, 0))  # 橙色高亮
            highlight_pen.setWidth(2)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(self.x, self.y), highlight_radius, highlight_radius)
            painter.setPen(pen)
            painter.setBrush(brush)
            
        if self.fixed:
            # 绘制固定标记 - 双圈
            fixed_pen = QPen(QColor(255, 0, 0))  # 红色固定标记
            fixed_pen.setWidth(1)
            painter.setPen(fixed_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(self.x, self.y), self.radius + 5, self.radius + 5)
            painter.setPen(pen)
            painter.setBrush(brush)
            
        # 绘制点
        center_point = QPointF(self.x, self.y)
        painter.drawEllipse(center_point, self.radius, self.radius)
        
        # if有名称，绘制名称
        if self.name:
            # 尝试获取画布
            canvas = self._find_canvas()
            if canvas and hasattr(canvas, 'name_position_manager'):
                # 使用名称位置管理器获取名称位置
                name_pos = canvas.name_position_manager.get_name_position(self)
                if name_pos:
                    painter.drawText(name_pos, self.name)
            else:
                # 没有找到画布或名称位置管理器，使用默认位置
                painter.drawText(QPointF(self.x + self.radius + 2, self.y - self.radius - 2), self.name)
                
    def _find_canvas(self):
        """查找包含此对象的画布"""
        # 这个方法尝试找到包含此对象的画布
        # 在线条或其他对象中也需要实现此方法
        from PyQt5.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            # 查找所有顶级窗口
            from .canvas import Canvas  # 避免循环导入
            for canvas in widget.findChildren(Canvas):
                # 检查此对象是否在画布的对象列表中
                if hasattr(canvas, 'objects') and self in canvas.objects:
                    return canvas
        return None
        
    def contains(self, point):
        """检查点是否包含在此对象中"""
        dx = point.x() - self.x
        dy = point.y() - self.y
        return math.sqrt(dx*dx + dy*dy) <= self.radius
        
    def drag_to(self, new_pos):
        """拖拽到新位置"""
        if self.draggable and not self.fixed:
            self.x = float(new_pos.x())  # 确保是浮点数
            self.y = float(new_pos.y())  # 确保是浮点数
            return True
        return False
        
    def distance_to(self, point):
        """计算到另一个点的距离"""
        if isinstance(point, Point):
            dx = self.x - point.x
            dy = self.y - point.y
            return math.sqrt(dx*dx + dy*dy)
        elif isinstance(point, QPointF):
            dx = self.x - point.x()
            dy = self.y - point.y()
            return math.sqrt(dx*dx + dy*dy)
        return float('inf')
        
    def toggle_fixed(self):
        """切换固定状态"""
        self.fixed = not self.fixed
        
    def get_bounds_rect(self, margin=0):
        """获取点的边界矩形，用于局部重绘"""
        # 考虑点的半径、选中状态和固定状态可能产生的额外视觉效果
        extra_radius = max(5, self.radius)
        if self.selected:
            extra_radius += 3
        if self.fixed:
            extra_radius += 5
        
        total_radius = self.radius + extra_radius + margin
        
        # 包含名称区域
        name_width = 0
        name_height = 0
        if self.name:
            # 估计文本尺寸
            name_width = len(self.name) * 8  # 估计每个字符宽度为8像素
            name_height = 16                 # 估计文本高度为16像素
        
        return QRectF(
            self.x - total_radius,
            self.y - total_radius,
            total_radius * 2 + name_width,
            total_radius * 2 + name_height
        )


class Line(GeometryObject):
    """线对象"""
    
    def __init__(self, p1=None, p2=None, name=""):
        super().__init__(name)
        self.p1 = p1 or Point()
        self.p2 = p2 or Point()
        self.width = 2
        self.style = Qt.SolidLine
        self.draggable = True
        self.fixed_length = False
        self._original_length = self.length()  # 初始长度
        self.color = QColor(0, 0, 0)  # 默认黑色
        
        # 强制长度控制
        self._force_maintain_length = False
        
        # 自适应比例显示
        self.adaptive_scale = False  # 是否启用自适应比例 - 默认禁用
        self._display_scale = 1.0   # 当前显示比例
        
    def set_points(self, p1, p2):
        """设置线的两个端点"""
        self.p1 = p1
        self.p2 = p2
        if self.fixed_length:
            self._original_length = self.length()
        
    def get_qlinef(self):
        """获取QLineF对象"""
        return QLineF(self.p1.get_qpointf(), self.p2.get_qpointf())
        
    def length(self):
        """获取线段长度"""
        dx = self.p2.x - self.p1.x
        dy = self.p2.y - self.p1.y
        return math.sqrt(dx*dx + dy*dy)
    
    def calculate_optimal_scale(self, canvas_size=(800, 600), target_visible_length=(50, 200)):
        """计算线段的最优显示比例
        
        Args:
            canvas_size: 画布尺寸 (width, height)
            target_visible_length: 目标可见长度范围 (min, max) 像素
            
        Returns:
            float: 最优缩放比例
        """
        # 确保属性存在，以保证向后兼容
        adaptive_scale = getattr(self, 'adaptive_scale', True)
        if not adaptive_scale:
            return 1.0
            
        actual_length = self.length()
        if actual_length <= 0.001:  # 避免除零
            return 1.0
        
        # 计算当前线段在画布上的实际像素长度（基于画布坐标）
        # 这里假设画布坐标系与像素坐标系1:1对应，if有缩放则需要调整
        current_pixel_length = actual_length
        
        min_target, max_target = target_visible_length
        
        # 计算理想的缩放比例
        if current_pixel_length < min_target:
            # 线段太短，需要放大
            scale = min_target / current_pixel_length
        elif current_pixel_length > max_target:
            # 线段太长，需要缩小
            scale = max_target / current_pixel_length
        else:
            # 长度合适，不需要缩放
            scale = 1.0
        
        # 限制缩放范围，避免过度缩放
        scale = max(0.1, min(10.0, scale))
        
        return scale
    
    def update_display_scale(self, canvas_size=(800, 600)):
        """更新显示比例"""
        # 确保属性存在，以保证向后兼容
        if not hasattr(self, 'adaptive_scale'):
            self.adaptive_scale = True
        if not hasattr(self, '_display_scale'):
            self._display_scale = 1.0
            
        if self.adaptive_scale:
            self._display_scale = self.calculate_optimal_scale(canvas_size)
        else:
            self._display_scale = 1.0
        
    def midpoint(self):
        """获取线段中点"""
        return Point((self.p1.x + self.p2.x) / 2, (self.p1.y + self.p2.y) / 2)
        
    def draw(self, painter):
        """绘制线段"""
        if not self.visible:
            return
            
        pen = QPen(self.color)
        pen.setWidth(self.width)
        pen.setStyle(self.style)
        painter.setPen(pen)
        
        # if被选中，则增加视觉效果
        if self.selected:
            highlight_pen = QPen(QColor(255, 165, 0))  # 橙色高亮
            highlight_pen.setWidth(self.width + 2)
            highlight_pen.setStyle(self.style)
            painter.setPen(highlight_pen)
            painter.drawLine(self.p1.get_qpointf(), self.p2.get_qpointf())
            painter.setPen(pen)
            
        # if固定长度，则添加视觉标记
        if self.fixed_length:
            # 使用红色线包裹整个线段
            fixed_pen = QPen(QColor(255, 0, 0))  # 红色标记
            fixed_pen.setWidth(self.width + 2)  # 比线段本身略粗
            fixed_pen.setStyle(Qt.SolidLine)
            painter.setPen(fixed_pen)
            painter.drawLine(self.p1.get_qpointf(), self.p2.get_qpointf())
            painter.setPen(pen)
            
        # 使用基本样式绘制线段（应用自适应比例）
        # 检查属性是否存在，以确保向后兼容
        adaptive_scale = getattr(self, 'adaptive_scale', True)
        display_scale = getattr(self, '_display_scale', 1.0)
        
        if adaptive_scale and display_scale != 1.0:
            # 计算缩放后的端点位置
            mid = self.midpoint()
            mid_point = QPointF(mid.x, mid.y)
            
            # 计算从中点到端点的向量
            vec1 = QPointF(self.p1.x - mid.x, self.p1.y - mid.y)
            vec2 = QPointF(self.p2.x - mid.x, self.p2.y - mid.y)
            
            # 应用缩放
            scaled_p1 = QPointF(mid.x + vec1.x() * display_scale, 
                               mid.y + vec1.y() * display_scale)
            scaled_p2 = QPointF(mid.x + vec2.x() * display_scale, 
                               mid.y + vec2.y() * display_scale)
            
            painter.drawLine(scaled_p1, scaled_p2)
        else:
            painter.drawLine(self.p1.get_qpointf(), self.p2.get_qpointf())
        
        # if有名称且非空，则绘制名称，使其平行于线段
        if self.name:
            # 计算线段中点
            mid_x = (self.p1.x + self.p2.x) / 2
            mid_y = (self.p1.y + self.p2.y) / 2
            
            # 计算线段的法向量（垂直于线段方向的单位向量）
            dx = self.p2.x - self.p1.x
            dy = self.p2.y - self.p1.y
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0.0001:  # 避免除以零
                # 计算法向量 - 逆时针旋转90度
                nx = -dy / length
                ny = dx / length
                
                # 将名称放置在线段中点上方（沿法向量方向偏移）
                offset = 10  # 固定偏移距离
                text_x = mid_x + nx * offset
                text_y = mid_y + ny * offset
                
                # 计算线段角度以使文本平行于线段
                angle_rad = math.atan2(dy, dx)
                angle_deg = math.degrees(angle_rad)
                
                # 保持文本可读性
                if angle_deg > 90 or angle_deg < -90:
                    angle_deg += 180
                
                # 保存当前变换状态
                painter.save()
                
                # 移动到文本位置并旋转
                painter.translate(QPointF(text_x, text_y))
                painter.rotate(angle_deg)
                
                # 绘制文本
                painter.drawText(QPointF(0, 0), self.name)
                
                # 恢复变换状态
                painter.restore()
            else:
                # if线段长度接近零，直接在中点附近显示名称
                painter.drawText(QPointF(mid_x + 5, mid_y - 5), self.name)
                
    def _find_canvas(self):
        """查找包含此对象的画布"""
        # 这个方法尝试找到包含此对象的画布
        from PyQt5.QtWidgets import QApplication
        for widget in QApplication.topLevelWidgets():
            # 查找所有顶级窗口
            from .canvas import Canvas  # 避免循环导入
            for canvas in widget.findChildren(Canvas):
                # 检查此对象是否在画布的对象列表中
                if hasattr(canvas, 'objects') and self in canvas.objects:
                    return canvas
        return None
        
    def contains(self, point):
        """检查点是否在线上"""
        line = self.get_qlinef()
        tolerance = 5.0  # 容许误差
        
        # 计算点到线的距离
        normal = line.normalVector()
        normal_unit = normal.unitVector()
        
        # 创建一个通过给定点的线，该线与原线平行
        test_line = QLineF(point, QPointF(point.x() + normal_unit.dx(), point.y() + normal_unit.dy()))
        
        # 求交点
        intersection_point = QPointF()
        intersection_type = line.intersect(test_line, intersection_point)
        
        if intersection_type == QLineF.NoIntersection:
            return False
            
        # 计算距离
        dx = point.x() - intersection_point.x()
        dy = point.y() - intersection_point.y()
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 检查交点是否在线段上
        line_rect = QRectF(
            min(self.p1.x, self.p2.x),
            min(self.p1.y, self.p2.y),
            abs(self.p2.x - self.p1.x),
            abs(self.p2.y - self.p1.y)
        )
        
        return distance <= tolerance and line_rect.contains(intersection_point)
        
    def drag_to(self, new_pos, drag_point=None):
        """拖拽到新位置
        
        参数:
        - new_pos: 新位置
        - drag_point: 被拖拽的端点，if为None则拖拽整个线段
        """
        if not self.draggable:
            return False
            
        # if是固定长度线段，确保_original_length有有效值
        if self.fixed_length and (not hasattr(self, '_original_length') or self._original_length <= 0):
            current_length = self.length()
            self._original_length = current_length
            print(f"线段{self.name}: 初始化_original_length={self._original_length}")
            
        if drag_point is not None:
            # 拖拽端点
            if drag_point == self.p1:
                # 先保存旧的位置，以便需要时恢复
                temp_x, temp_y = self.p1.x, self.p1.y
                
                # if是固定长度的线段，需要特殊处理
                if self.fixed_length:
                    # 记录p2位置
                    p2_x, p2_y = self.p2.x, self.p2.y
                    
                    # 临时让点移动到新位置
                    if not self.p1.fixed:
                        self.p1.x = float(new_pos.x())
                        self.p1.y = float(new_pos.y())
                        
                    # 立即强制应用固定长度约束
                    self._enforce_fixed_length(drag_point=self.p1)
                    
                    # 检查是否有其他与此端点相连的固定长度线段
                    # 这部分逻辑由Canvas负责处理，避免代码重复
                    
                    return True
                else:
                    # 非固定长度线段，正常处理
                    return self.p1.drag_to(new_pos)
                
            elif drag_point == self.p2:
                # 先保存旧的位置，以便需要时恢复
                temp_x, temp_y = self.p2.x, self.p2.y
                
                # if是固定长度的线段，需要特殊处理
                if self.fixed_length:
                    # 记录p1位置
                    p1_x, p1_y = self.p1.x, self.p1.y
                    
                    # 临时让点移动到新位置
                    if not self.p2.fixed:
                        self.p2.x = float(new_pos.x())
                        self.p2.y = float(new_pos.y())
                        
                    # 立即强制应用固定长度约束
                    self._enforce_fixed_length(drag_point=self.p2)
                    
                    # 检查是否有其他与此端点相连的固定长度线段
                    # 这部分逻辑由Canvas负责处理，避免代码重复
                    
                    return True
                else:
                    # 非固定长度线段，正常处理
                    return self.p2.drag_to(new_pos)
        else:
            # 拖拽整条线段
            dx = new_pos.x() - self.midpoint().x
            dy = new_pos.y() - self.midpoint().y
            
            # 只有当两个端点都可以移动时才整体移动
            if (not self.p1.fixed) and (not self.p2.fixed):
                # 临时保存端点位置，以便检查是否与固定长度线段相连
                old_p1_x, old_p1_y = self.p1.x, self.p1.y
                old_p2_x, old_p2_y = self.p2.x, self.p2.y
                
                # 应用移动
                self.p1.x += dx
                self.p1.y += dy
                self.p2.x += dx
                self.p2.y += dy
                
                # 对于固定长度线段，验证长度没有变化
                if self.fixed_length:
                    current_length = self.length()
                    if abs(current_length - self._original_length) > 0.0001:
                        # 使用改进的方法强制保持长度，不传递端点保持中点不变
                        self._enforce_fixed_length()
                
                return True
                
        return False
        
    def toggle_fixed_length(self):
        """切换固定长度状态"""
        # 记录之前的状态，用于判断是开启还是关闭固定长度
        old_state = self.fixed_length
        
        # 切换状态
        self.fixed_length = not self.fixed_length
        
        # 无论是开启还是关闭固定长度，都强制更新原始长度
        current_length = self.length()
        self._original_length = current_length
        
        # 输出调试信息
        print(f"线段{self.name}: 固定长度{'开启' if self.fixed_length else '关闭'}, 当前长度={current_length}, 原始长度={self._original_length}")

        # 启用强制维持长度功能
        self._force_maintain_length = self.fixed_length
        if self._force_maintain_length:
            self._enforce_fixed_length()
        
    def _enforce_fixed_length(self, drag_point=None):
        """强制维持固定长度
        
        参数:
        - drag_point: 被拖拽的端点，if为None则保持中点位置不变
        """
        if not self.fixed_length or not hasattr(self, '_original_length'):
            return
            
        current_length = self.length()
        
        # if长度已经足够接近，不需要调整
        if abs(current_length - self._original_length) < 0.0001:
            return
            
        # 根据拖拽点不同采取不同策略
        if drag_point is not None:
            # if指定了被拖拽的点，则保持另一点固定
            if drag_point == self.p1:
                # p1被拖拽，保持p2固定
                fixed_point = self.p2
                moving_point = self.p1
            else:
                # p2被拖拽，保持p1固定
                fixed_point = self.p1
                moving_point = self.p2
                
            # 计算方向向量
            dx = moving_point.x - fixed_point.x
            dy = moving_point.y - fixed_point.y
            
            # 计算当前长度
            current_length = math.sqrt(dx*dx + dy*dy)
            
            # if长度足够接近，不需要调整
            if abs(current_length - self._original_length) < 0.0001:
                return
                
            # 计算调整系数
            if current_length > 0.0001:  # 避免除以零
                scale = self._original_length / current_length
                
                # 只调整拖拽点的位置，保持另一点固定
                moving_point.x = fixed_point.x + dx * scale
                moving_point.y = fixed_point.y + dy * scale
        else:
            # if没有指定拖拽点，保持中点位置不变（整体拖拽）
            mid_x = (self.p1.x + self.p2.x) / 2
            mid_y = (self.p1.y + self.p2.y) / 2
            
            # 计算两个端点到中点的向量
            dx1 = self.p1.x - mid_x
            dy1 = self.p1.y - mid_y
            dx2 = self.p2.x - mid_x
            dy2 = self.p2.y - mid_y
            
            # 计算当前半长度（中点到端点的距离）
            half_length = math.sqrt(dx1*dx1 + dy1*dy1)
            
            # if长度足够接近，不需要调整
            if abs(half_length*2 - self._original_length) < 0.0001:
                return
                
            # 计算调整系数
            if half_length > 0.0001:  # 避免除以零
                scale = (self._original_length/2) / half_length
                
                # 从中点向两端扩展，保持中点位置不变
                self.p1.x = mid_x + dx1 * scale
                self.p1.y = mid_y + dy1 * scale
                self.p2.x = mid_x + dx2 * scale
                self.p2.y = mid_y + dy2 * scale
        
        # 验证调整后的长度
        new_length = self.length()
        if abs(new_length - self._original_length) > 0.0001:
            print(f"警告: 线段{self.name}长度调整后仍不符合, 当前={new_length}, 应为={self._original_length}")

    def set_length(self, new_length):
        """设置线段的长度，保持p1位置不变"""
        if new_length <= 0:
            return  # 长度必须为正数
        
        # 先强制记录新的目标长度
        self._original_length = new_length
        self.fixed_length = True
        self._force_maintain_length = True
        
        current_length = self.length()
        if abs(current_length) < 0.001:  # 避免除以零
            # if当前长度接近零，设置一个默认方向
            self.p2.x = self.p1.x + new_length
            self.p2.y = self.p1.y
            return
            
        # 计算方向向量
        dx = self.p2.x - self.p1.x
        dy = self.p2.y - self.p1.y
        
        # 计算单位向量
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0.0001:  # 避免除以零
            unit_dx = dx / length
            unit_dy = dy / length
            
            # 设置新的p2位置，保持p1不变，使用单位向量乘以目标长度
            self.p2.x = self.p1.x + unit_dx * new_length
            self.p2.y = self.p1.y + unit_dy * new_length
        
        # 验证并强制保证长度准确
        self._enforce_fixed_length()
        
        # 最终验证
        final_length = self.length()
        if abs(final_length - new_length) > 0.0001:
            print(f"严重警告: set_length后线段{self.name}长度仍不符! 当前={final_length}, 应为={new_length}")

    def endpoint_near(self, point, threshold=10):
        """检查给定点是否靠近线段的端点
        
        返回:
        - None: 不靠近任何端点
        - self.p1: 靠近起点
        - self.p2: 靠近终点
        """
        if isinstance(point, QPointF):
            p1_dist = math.sqrt((point.x() - self.p1.x)**2 + (point.y() - self.p1.y)**2)
            p2_dist = math.sqrt((point.x() - self.p2.x)**2 + (point.y() - self.p2.y)**2)
            
            if p1_dist <= threshold:
                return self.p1
            if p2_dist <= threshold:
                return self.p2
                
        return None
        
    def get_bounds_rect(self, margin=0):
        """获取线的边界矩形，用于局部重绘"""
        # 获取线段的包围盒
        min_x = min(self.p1.x, self.p2.x)
        min_y = min(self.p1.y, self.p2.y)
        max_x = max(self.p1.x, self.p2.x)
        max_y = max(self.p1.y, self.p2.y)
        
        # 考虑线宽、选中状态和固定状态可能产生的额外视觉效果
        extra_width = max(5, self.width)
        if self.selected:
            extra_width += 2
            
        total_margin = extra_width + margin
        
        # 包含名称区域和中点标记
        name_width = 0
        name_height = 0
        if self.name:
            # 估计文本尺寸
            name_width = len(self.name) * 8  # 估计每个字符宽度为8像素
            name_height = 16                 # 估计文本高度为16像素
        
        # 返回包含所有元素的矩形
        return QRectF(
            min_x - total_margin,
            min_y - total_margin,
            max_x - min_x + total_margin * 2 + name_width,
            max_y - min_y + total_margin * 2 + name_height
        )


class PointAnimation:
    """点的动画类"""
    
    def __init__(self, point, duration=1000, loop_count=1):
        self.point = point
        self.duration = duration
        self.loop_count = loop_count
        self.animation = QVariantAnimation()
        self.animation.setDuration(duration)
        self.animation.setLoopCount(loop_count)
        
    def start(self):
        """开始动画"""
        self.animation.start()
        
    def stop(self):
        """停止动画"""
        self.animation.stop()


class PathAnimation(PointAnimation):
    """沿路径的点动画"""
    
    def __init__(self, point, path_object, duration=1000, loop_count=1):
        """
        创建沿路径的动画
        
        参数:
        - point: 要进行动画的点
        - path_object: 路径对象(线)
        - duration: 动画持续时间(毫秒)
        - loop_count: 循环次数
        """
        super().__init__(point, duration, loop_count)
        self.path_object = path_object
        
        # 设置动画
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Linear)
        
        # 连接值变化的信号
        self.animation.valueChanged.connect(self._update_position)
        
    def _update_position(self, progress):
        """更新点的位置"""
        if isinstance(self.path_object, Line):
            # 沿线段移动
            x = self.path_object.p1.x + progress * (self.path_object.p2.x - self.path_object.p1.x)
            y = self.path_object.p1.y + progress * (self.path_object.p2.y - self.path_object.p1.y)
            self.point.set_position(x, y)


class ConnectAnimation(PointAnimation):
    """连接点的动画"""
    
    def __init__(self, from_point, to_point, duration=1000):
        """
        创建两点之间连接动画
        
        参数:
        - from_point: 起始点
        - to_point: 目标点
        - duration: 动画持续时间(毫秒)
        """
        super().__init__(from_point, duration, 1)
        self.from_point = from_point
        self.to_point = to_point
        
        # 设置动画
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # 连接值变化的信号
        self.animation.valueChanged.connect(self._update_position)
        
    def _update_position(self, progress):
        """更新点的位置"""
        if hasattr(self.to_point, 'x') and hasattr(self.to_point, 'y'):
            x = self.from_point.x + progress * (self.to_point.x - self.from_point.x)
            y = self.from_point.y + progress * (self.to_point.y - self.from_point.y)
            self.from_point.set_position(x, y) 