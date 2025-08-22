#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QFontMetrics, QFont

class NamePositionManager:
    """名称位置管理器 - 负责管理几何对象名称的位置，避免重叠"""
    
    def __init__(self, canvas):
        """初始化名称位置管理器
        
        Args:
            canvas: 画布对象引用
        """
        self.canvas = canvas
        self.max_adjustment_tries = 8  # 最大尝试调整次数
        self.adjustment_step = 7  # 每次调整步长（减小为7，使名称更靠近元素）
        self.spiral_factor = 1.1  # 螺旋搜索因子（减小，使搜索更集中）
        
        # 定义八个方向的偏移量，从最优先的方向开始排序
        self.directions = [
            (1, 0),    # 右
            (1, -1),   # 右上
            (0, -1),   # 上
            (-1, -1),  # 左上
            (-1, 0),   # 左
            (-1, 1),   # 左下
            (0, 1),    # 下
            (1, 1)     # 右下
        ]
        
        # 名称位置的偏移量，用于储存计算后的最佳位置
        self.name_offsets = {}  # 格式: {对象id: (x_offset, y_offset)}
        
        # 默认位置缓存，用于回溯功能
        self.default_positions = {}  # 格式: {对象id: (x, y)}
        
        # 添加稳定性控制参数，避免线段名称抽搐
        self.position_history = {}  # 格式: {对象id: [(x, y), ...]} 存储历史位置
        self.stability_threshold = 3.0  # 避免小于此距离的位置变化
        self.max_history = 5  # 存储历史位置的最大数量
        
        self.name_positions = {}  # 存储对象ID到名称位置的映射
        self.drag_sensitive = True  # 是否对拖动状态敏感，确保拖动时实时更新
    
    def get_default_position(self, obj):
        """获取对象名称的默认位置
        
        Args:
            obj: 对象
            
        Returns:
            tuple: (x, y)默认位置坐标
        """
        from .geometry import Point, Line
        if isinstance(obj, Point):
            # 点对象名称通常显示在右上角
            base_x = obj.x + obj.radius + 2
            base_y = obj.y - obj.radius - 2
        elif isinstance(obj, Line):
            # 线段名称通常显示在中点右侧，距离更近
            base_x = (obj.p1.x + obj.p2.x) / 2 + 3  # 减小水平偏移从5到3
            base_y = (obj.p1.y + obj.p2.y) / 2 - 3  # 减小垂直偏移从5到3
        else:
            # 默认位置
            base_x = 0
            base_y = 0
            
        return (base_x, base_y)
    
    def get_text_bounds(self, obj):
        """获取对象名称文本的边界矩形
        
        Args:
            obj: 对象
            
        Returns:
            QRectF: 文本的边界矩形
        """
        if not hasattr(obj, 'name') or not obj.name:
            return None
            
        # 默认字体获取文字度量
        font = QFont()
        metrics = QFontMetrics(font)
        text_width = metrics.width(obj.name)
        text_height = metrics.height()
        
        # 计算默认文本位置
        obj_id = id(obj)
        
        # 缓存默认位置（if不存在）
        if obj_id not in self.default_positions:
            self.default_positions[obj_id] = self.get_default_position(obj)
            
        base_x, base_y = self.default_positions[obj_id]
            
        # 应用存储的偏移量（if有）
        if obj_id in self.name_offsets:
            offset_x, offset_y = self.name_offsets[obj_id]
            base_x += offset_x
            base_y += offset_y
            
        return QRectF(base_x, base_y - text_height, text_width, text_height)
    
    def check_name_overlap_with_self(self, obj):
        """检查对象名称是否与其自身元素重叠
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: if重叠返回True，否则返回False
        """
        name_bounds = self.get_text_bounds(obj)
        if not name_bounds:
            return False
            
        # 获取元素自身的边界
        obj_bounds = self._get_object_bounds(obj)
        if not obj_bounds:
            return False
            
        # 检查与自身的重叠
        return name_bounds.intersects(obj_bounds)
    
    def check_name_overlap_with_others(self, obj):
        """检查对象名称是否与其他元素或名称重叠
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: if重叠返回True，否则返回False
        """
        name_bounds = self.get_text_bounds(obj)
        if not name_bounds:
            return False
            
        # 检查与其他元素及其名称的重叠
        for other in self.canvas.objects:
            if other == obj:
                continue
                
            # 检查与元素本身的重叠
            other_bounds = self._get_object_bounds(other)
            if other_bounds and name_bounds.intersects(other_bounds):
                return True
                
            # 检查与其他元素名称的重叠
            other_name_bounds = self.get_text_bounds(other)
            if other_name_bounds and name_bounds.intersects(other_name_bounds):
                return True
                
            # 特别检查：线段与点名称的重叠（更严格的检测）
            from .geometry import Point, Line
            if isinstance(obj, Point) and isinstance(other, Line):
                # 检查点名称是否与线段重叠
                if self._line_intersects_rect(other, name_bounds):
                    return True
            elif isinstance(obj, Line) and isinstance(other, Point):
                # 检查线段名称是否与点重叠
                if name_bounds.contains(other.x, other.y):
                    return True
                
        return False
    
    def _line_intersects_rect(self, line, rect):
        """检查线段是否与矩形相交
        
        Args:
            line: 线段对象
            rect: QRectF矩形
            
        Returns:
            bool: if相交返回True
        """
        # 获取线段端点
        p1 = QPointF(line.p1.x, line.p1.y)
        p2 = QPointF(line.p2.x, line.p2.y)
        
        # 获取矩形四个边的端点
        rect_left = rect.left()
        rect_right = rect.right()
        rect_top = rect.top()
        rect_bottom = rect.bottom()
        
        # 矩形的四个角点
        tl = QPointF(rect_left, rect_top)
        tr = QPointF(rect_right, rect_top)
        bl = QPointF(rect_left, rect_bottom)
        br = QPointF(rect_right, rect_bottom)
        
        # 矩形的四条边
        rect_edges = [
            (tl, tr),  # 上边
            (tr, br),  # 右边
            (br, bl),  # 下边
            (bl, tl)   # 左边
        ]
        
        # 检查线段是否完全在矩形内
        if (rect.contains(p1) and rect.contains(p2)):
            return True
            
        # 检查线段是否与矩形的任意一条边相交
        from PyQt5.QtCore import QLineF
        line_segment = QLineF(p1, p2)
        
        for edge_start, edge_end in rect_edges:
            edge = QLineF(edge_start, edge_end)
            intersection_point = QPointF()
            
            if line_segment.intersect(edge, intersection_point) == QLineF.BoundedIntersection:
                return True
                
        return False
    
    def reset_to_default_position(self, obj):
        """将对象名称位置重置为默认位置
        
        Args:
            obj: 要重置的对象
            
        Returns:
            bool: if重置成功返回True
        """
        obj_id = id(obj)
        
        if obj_id in self.name_offsets:
            del self.name_offsets[obj_id]
            return True
        return False
    
    def adjust_name_position(self, obj):
        """调整对象名称位置以避免重叠
        
        Args:
            obj: 要调整名称位置的对象
            
        Returns:
            bool: if成功调整位置返回True，否则返回False
        """
        if not hasattr(obj, 'name') or not obj.name:
            return False
            
        obj_id = id(obj)
        
        # 首先检查名称是否与自身元素或其他元素重叠
        self_overlap = self.check_name_overlap_with_self(obj)
        others_overlap = self.check_name_overlap_with_others(obj)
        
        # if没有任何重叠，回溯到默认位置
        if not self_overlap and not others_overlap:
            return self.reset_to_default_position(obj)
        
        # 保存当前偏移量，用于后续比较
        current_offset_x = 0
        current_offset_y = 0
        if obj_id in self.name_offsets:
            current_offset_x, current_offset_y = self.name_offsets[obj_id]
        
        # 获取默认位置
        if obj_id not in self.default_positions:
            self.default_positions[obj_id] = self.get_default_position(obj)
        
        base_x, base_y = self.default_positions[obj_id]
        
        # 分析周围元素分布情况，找出空白区域
        empty_sectors = self._find_empty_sectors(obj)
        
        # 根据空白区域排序方向优先级
        prioritized_directions = self._prioritize_directions_by_sectors(empty_sectors)
        
        # 用于保存找到的所有可行位置
        valid_positions = []
        
        # 线段特殊处理：尝试垂直方向的最小偏移
        from .geometry import Line
        if isinstance(obj, Line):
            # 使用更小的步长，减少避让距离
            smallest_step = self.adjustment_step * 0.4  # 非常小的初始步长
            
            # 获取线段方向
            dx = obj.p2.x - obj.p1.x
            dy = obj.p2.y - obj.p1.y
            line_length = math.sqrt(dx*dx + dy*dy)
            
            if line_length > 0.001:  # 避免除以零
                # 计算垂直于线段的方向（两个方向）
                nx1, ny1 = -dy / line_length, dx / line_length  # 一个垂直方向
                nx2, ny2 = dy / line_length, -dx / line_length  # 另一个垂直方向
                
                # 检查哪个垂直方向对应的区域更空
                score1 = self._calculate_sector_emptiness(obj, nx1, ny1)
                score2 = self._calculate_sector_emptiness(obj, nx2, ny2)
                
                # 选择更空的方向
                best_nx, best_ny = (nx1, ny1) if score1 >= score2 else (nx2, ny2)
                
                # 使用非常小的步长在最佳方向尝试避让
                for multiplier in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]:
                    new_offset_x = best_nx * smallest_step * multiplier
                    new_offset_y = best_ny * smallest_step * multiplier
                    
                    self.name_offsets[obj_id] = (new_offset_x, new_offset_y)
                    
                    # 一旦找到不重叠的位置，立即返回
                    if not self.check_name_overlap_with_self(obj) and not self.check_name_overlap_with_others(obj):
                        return True
        
        # 尝试所有优先方向，使用更小的步长
        smaller_step = self.adjustment_step * 0.6  # 使用更小的基本步长
        
        for direction_x, direction_y in prioritized_directions:
            # 使用递增的小步长尝试
            for multiplier in [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5]:
                new_offset_x = direction_x * smaller_step * multiplier
                new_offset_y = direction_y * smaller_step * multiplier
                
                self.name_offsets[obj_id] = (new_offset_x, new_offset_y)
                
                # if此位置没有重叠，保存到可行位置列表
                if not self.check_name_overlap_with_self(obj) and not self.check_name_overlap_with_others(obj):
                    # 计算与原点的距离作为排序依据
                    distance = math.sqrt(new_offset_x**2 + new_offset_y**2)
                    valid_positions.append((new_offset_x, new_offset_y, distance))
                    break  # 找到一个合适的位置就停止增加步长
        
        # if找到有效位置，选择距离最近的一个
        if valid_positions:
            # 按距离排序
            valid_positions.sort(key=lambda pos: pos[2])
            # 选择最近的位置
            best_offset_x, best_offset_y, _ = valid_positions[0]
            self.name_offsets[obj_id] = (best_offset_x, best_offset_y)
            return True
        
        # if常规方向尝试失败，使用更密集的搜索
        angle_step = math.pi / 12  # 更小的角度步长
        initial_radius = smaller_step  # 使用较小的初始半径
        
        for radius_multiplier in range(1, 4):  # 尝试不同的半径
            radius = initial_radius * radius_multiplier
            
            for angle_multiplier in range(24):  # 覆盖整个圆，更多方向
                angle = angle_multiplier * angle_step
                
                # 计算新偏移量
                new_offset_x = radius * math.cos(angle)
                new_offset_y = radius * math.sin(angle)
                
                # 临时设置新偏移量
                self.name_offsets[obj_id] = (new_offset_x, new_offset_y)
                
                # 检查新位置是否解决了重叠问题
                if not self.check_name_overlap_with_self(obj) and not self.check_name_overlap_with_others(obj):
                    # 找到第一个可行位置就返回
                    return True
        
        # if所有尝试都失败，但有当前偏移量，保留当前偏移量
        if current_offset_x != 0 or current_offset_y != 0:
            self.name_offsets[obj_id] = (current_offset_x, current_offset_y)
            return False
        
        # if一切都失败，使用一个安全的默认偏移
        # 这将使名称至少不会完全重叠在元素上
        if isinstance(obj, Line):
            # 线段使用更小的偏移距离
            self.name_offsets[obj_id] = (self.adjustment_step * 1.0, -self.adjustment_step * 0.7)
        else:
            # 点默认向右偏移，使用更小的步长
            self.name_offsets[obj_id] = (self.adjustment_step * 1.0, 0)
            
        return True
    
    def update_default_positions(self):
        """更新所有对象的默认位置缓存"""
        for obj in self.canvas.objects:
            if hasattr(obj, 'name') and obj.name:
                obj_id = id(obj)
                self.default_positions[obj_id] = self.get_default_position(obj)
    
    def update_all_name_positions(self):
        """更新画布上所有对象的名称位置，避免重叠
        
        Returns:
            int: 成功调整的名称数量
        """
        # 首先更新所有对象的默认位置
        self.update_default_positions()
        
        adjusted_count = 0
        
        # 获取所有有名称的对象
        objects_with_names = [obj for obj in self.canvas.objects 
                             if hasattr(obj, 'name') and obj.name]
        
        # 第一轮：检查所有需要回溯到默认位置的对象
        for obj in objects_with_names:
            obj_id = id(obj)
            if obj_id in self.name_offsets:
                # 临时移除偏移，检查默认位置是否有重叠
                temp_offset = self.name_offsets.pop(obj_id, None)
                
                if not self.check_name_overlap_with_self(obj) and not self.check_name_overlap_with_others(obj):
                    # if默认位置没有重叠，保持回溯状态
                    adjusted_count += 1
                else:
                    # 否则恢复偏移
                    if temp_offset:
                        self.name_offsets[obj_id] = temp_offset
        
        # 第二轮：处理需要调整位置的对象
        for obj in objects_with_names:
            # 检查是否与元素自身或其他元素重叠
            if self.check_name_overlap_with_self(obj) or self.check_name_overlap_with_others(obj):
                # 尝试调整位置
                if self.adjust_name_position(obj):
                    adjusted_count += 1
        
        # 更新画布显示
        self.canvas.update()
        return adjusted_count
    
    def get_name_position(self, obj):
        """获取对象的名称位置"""
        obj_id = id(obj)
        
        # if之前没有计算过位置或对象改变，重新计算
        if obj_id not in self.name_positions or self.canvas.dragging:
            self.update_object_changed(obj)
            
        return self.name_positions.get(obj_id)
    
    def update_object_changed(self, obj):
        """当对象改变时更新其名称位置"""
        if hasattr(obj, 'name') and obj.name:
            # 为对象计算一个新的合适位置
            new_pos = self.calculate_name_position(obj)
            # 更新名称位置
            self.name_positions[id(obj)] = new_pos
            
            # if处于拖动状态，强制更新重绘
            if self.drag_sensitive and self.canvas.dragging:
                self.canvas.update()
                
    def calculate_name_position(self, obj):
        """计算对象名称的位置"""
        from .geometry import Point, Line
        
        if isinstance(obj, Point):
            # 点名称默认在右上
            return QPointF(obj.x + obj.radius + 2, obj.y - obj.radius - 2)
            
        elif isinstance(obj, Line):
            # 线段名称平行于线段并紧贴显示
            # 计算线段中点
            mid_x = (obj.p1.x + obj.p2.x) / 2
            mid_y = (obj.p1.y + obj.p2.y) / 2
            
            # 计算线段方向和长度
            dx = obj.p2.x - obj.p1.x
            dy = obj.p2.y - obj.p1.y
            length = math.sqrt(dx*dx + dy*dy)
            
            if length > 0.0001:  # 避免除以零
                # 计算垂直于线段的偏移方向（用于上下偏移）
                nx = -dy / length  # 法向量X分量
                ny = dx / length   # 法向量Y分量
                
                # 较小的偏移量，使名称更贴近线段
                offset = 8  # 减少偏移距离
                
                # 智能选择偏移方向：优先向上，if与其他元素冲突则向下
                best_offset_y = offset
                name_x = mid_x + nx * best_offset_y
                name_y = mid_y + ny * best_offset_y
                
                # 检查是否与其他元素冲突
                if self._has_naming_conflict(QPointF(name_x, name_y), obj):
                    # 尝试向下偏移
                    best_offset_y = -offset
                    name_x = mid_x + nx * best_offset_y
                    name_y = mid_y + ny * best_offset_y
                    
                    # if仍有冲突，尝试更远的距离
                    if self._has_naming_conflict(QPointF(name_x, name_y), obj):
                        best_offset_y = offset * 1.8  # 向上更远一点
                        name_x = mid_x + nx * best_offset_y
                        name_y = mid_y + ny * best_offset_y
                
                return QPointF(name_x, name_y)
            else:
                # if线段长度太小，默认放在中点右上方
                return QPointF(mid_x + 5, mid_y - 5)
        
        # 其他类型对象默认不显示名称
        return None
    
    def _has_naming_conflict(self, position, current_obj):
        """检查指定位置是否与其他元素的名称或对象本身冲突
        
        Args:
            position: QPointF - 要检查的位置
            current_obj: 当前对象（用于排除自身）
            
        Returns:
            bool: True表示有冲突，False表示无冲突
        """
        # 定义名称区域的大小（估算）
        name_width = 30  # 估算名称宽度
        name_height = 16  # 估算名称高度
        
        test_rect = QRectF(
            position.x() - name_width/2,
            position.y() - name_height/2,
            name_width,
            name_height
        )
        
        # 检查与画布上其他对象的冲突
        for obj in self.canvas.objects:
            if obj == current_obj:
                continue  # 跳过当前对象
                
            # 检查与对象本身的冲突
            obj_bounds = self._get_object_bounds(obj)
            if obj_bounds and test_rect.intersects(obj_bounds):
                return True
                
            # 检查与其他对象名称的冲突 - 避免递归调用
            if hasattr(obj, 'name') and obj.name:
                # 直接从缓存中获取名称位置，避免触发递归计算
                obj_id = id(obj)
                other_name_pos = self.name_positions.get(obj_id)
                if other_name_pos:
                    other_rect = QRectF(
                        other_name_pos.x() - name_width/2,
                        other_name_pos.y() - name_height/2,
                        name_width,
                        name_height
                    )
                    if test_rect.intersects(other_rect):
                        return True
        
        return False
    
    def _get_object_bounds(self, obj):
        """获取对象本身的边界矩形
        
        Args:
            obj: 对象
            
        Returns:
            QRectF: 对象的边界矩形
        """
        # 检查对象是否有获取边界的方法
        if hasattr(obj, 'get_bounds_rect'):
            # 获取基本边界，但不包括名称的空间
            from .geometry import Point, Line
            if isinstance(obj, Point):
                radius = getattr(obj, 'radius', 5)  # 默认半径为5
                # 只考虑点本身的空间，不考虑选中状态和名称
                return QRectF(obj.x - radius, obj.y - radius, radius * 2, radius * 2)
            elif isinstance(obj, Line):
                # 只考虑线段本身的空间
                min_x = min(obj.p1.x, obj.p2.x)
                min_y = min(obj.p1.y, obj.p2.y)
                max_x = max(obj.p1.x, obj.p2.x)
                max_y = max(obj.p1.y, obj.p2.y)
                
                # 考虑线段宽度
                line_width = getattr(obj, 'width', 2)
                return QRectF(
                    min_x - line_width/2,
                    min_y - line_width/2,
                    max_x - min_x + line_width,
                    max_y - min_y + line_width
                )
            else:
                return obj.get_bounds_rect()
            
        # 对于点对象的特殊处理
        from .geometry import Point
        if isinstance(obj, Point):
            radius = getattr(obj, 'radius', 5)  # 默认半径为5
            return QRectF(obj.x - radius, obj.y - radius, radius * 2, radius * 2)
            
        return None
    
    def _find_empty_sectors(self, obj):
        """分析对象周围的元素分布，找出空白区域
        
        Args:
            obj: 要分析的对象
            
        Returns:
            list: 包含空白区域的方向索引（0-7）
        """
        # 以对象为中心，将周围空间分为8个扇区
        sectors = [True] * 8  # 初始假设所有扇区都是空的
        
        # 获取对象中心点
        obj_center = self._get_object_center(obj)
        if not obj_center:
            return list(range(8))  # 无法获取中心点，返回所有方向
            
        center_x, center_y = obj_center
        
        # 获取扇区检查半径（根据对象大小确定）
        obj_bounds = self._get_object_bounds(obj)
        if not obj_bounds:
            check_radius = 50  # 默认检查半径
        else:
            # 根据对象边界估算合适的检查半径
            width = obj_bounds.width()
            height = obj_bounds.height()
            check_radius = max(width, height) * 1.5
        
        # 检查每个其他对象与当前对象的相对位置
        for other in self.canvas.objects:
            if other == obj:
                continue
                
            # 获取其他对象的中心点
            other_center = self._get_object_center(other)
            if not other_center:
                continue
                
            other_x, other_y = other_center
            
            # 计算相对位置向量
            dx = other_x - center_x
            dy = other_y - center_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            # 只考虑一定距离内的对象
            if distance > check_radius:
                continue
                
            # 确定扇区索引
            angle = math.atan2(dy, dx)
            sector_index = int(((angle + math.pi) / (2 * math.pi) * 8) % 8)
            
            # 标记该扇区为非空
            sectors[sector_index] = False
        
        # 返回空白扇区的索引
        return [i for i in range(8) if sectors[i]]
        
    def _get_object_center(self, obj):
        """获取对象的中心点坐标
        
        Args:
            obj: 对象
            
        Returns:
            tuple: (x, y) 中心点坐标，if无法确定则返回None
        """
        from .geometry import Point, Line
        
        if isinstance(obj, Point):
            return (obj.x, obj.y)
        elif isinstance(obj, Line):
            # 线段的中点
            return ((obj.p1.x + obj.p2.x) / 2, (obj.p1.y + obj.p2.y) / 2)
        else:
            obj_bounds = self._get_object_bounds(obj)
            if obj_bounds:
                return (obj_bounds.center().x(), obj_bounds.center().y())
            return None
            
    def _prioritize_directions_by_sectors(self, empty_sectors):
        """根据空白扇区重新排序方向优先级
        
        Args:
            empty_sectors: 空白扇区索引列表
            
        Returns:
            list: 排序后的方向列表
        """
        # 没有空白扇区，使用默认顺序
        if not empty_sectors:
            return list(self.directions)
            
        # 重新排序方向，使空白扇区对应的方向排在前面
        all_directions = list(self.directions)
        prioritized = []
        
        # 首先添加空白扇区对应的方向
        for i in empty_sectors:
            prioritized.append(self.directions[i])
            
        # 然后添加其他方向
        for direction in all_directions:
            if direction not in prioritized:
                prioritized.append(direction)
                
        return prioritized
        
    def _calculate_sector_emptiness(self, obj, nx, ny):
        """计算指定方向区域的空白程度
        
        Args:
            obj: 对象
            nx, ny: 方向向量
            
        Returns:
            float: 空白程度分数，越高表示越空
        """
        # 获取对象中心点
        obj_center = self._get_object_center(obj)
        if not obj_center:
            return 0
            
        center_x, center_y = obj_center
        
        # 检查半径
        check_radius = 100
        
        # 计算区域中心点
        sector_center_x = center_x + nx * check_radius * 0.5
        sector_center_y = center_y + ny * check_radius * 0.5
        
        # 统计区域内其他对象的数量
        object_count = 0
        for other in self.canvas.objects:
            if other == obj:
                continue
                
            # 获取其他对象的中心点
            other_center = self._get_object_center(other)
            if not other_center:
                continue
                
            other_x, other_y = other_center
            
            # 计算到区域中心的距离
            dx = other_x - sector_center_x
            dy = other_y - sector_center_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < check_radius * 0.5:
                object_count += 1
        
        # 返回空白程度分数（对象越少分数越高）
        return 10 - min(object_count, 10)  # 最高10分

# 用于测试的辅助函数
def test_name_manager(canvas):
    """测试名称位置管理器
    
    Args:
        canvas: 画布对象
        
    Returns:
        str: 测试结果报告
    """
    manager = NamePositionManager(canvas)
    adjusted = manager.update_all_name_positions()
    return f"检测完成，共调整了{adjusted}个名称位置"
