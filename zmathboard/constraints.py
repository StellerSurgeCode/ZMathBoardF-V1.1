#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
几何约束系统
支持点、线段之间的依赖关系，如中点、比例点等
"""

from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import math
from .geometry import Point, Line

class Constraint(ABC):
    """约束基类"""
    
    def __init__(self, constrained_object, dependencies: List):
        self.constrained_object = constrained_object  # 被约束的对象
        self.dependencies = dependencies  # 依赖的对象列表
        self.active = True  # 约束是否激活
    
    @abstractmethod
    def update(self):
        """更新被约束对象的位置"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取约束描述"""
        pass

class MidpointConstraint(Constraint):
    """中点约束：点必须是线段的中点"""
    
    def __init__(self, point: Point, line: Line):
        super().__init__(point, [line])
        self.point = point
        self.line = line
    
    def update(self):
        """更新中点位置"""
        if not self.active or not self.line or not self.line.p1 or not self.line.p2:
            return
        
        # 计算中点
        mid_x = (self.line.p1.x + self.line.p2.x) / 2
        mid_y = (self.line.p1.y + self.line.p2.y) / 2
        
        # 更新点位置
        self.point.x = mid_x
        self.point.y = mid_y
    
    def get_description(self) -> str:
        return f"点{self.point.name}是线段{self.line.name}的中点"

class RatioPointConstraint(Constraint):
    """比例点约束：点必须在线段上的指定比例位置"""
    
    def __init__(self, point: Point, line: Line, ratio: float):
        super().__init__(point, [line])
        self.point = point
        self.line = line
        self.ratio = max(0.0, min(1.0, ratio))  # 限制比例在0-1之间
    
    def update(self):
        """更新比例点位置"""
        if not self.active or not self.line or not self.line.p1 or not self.line.p2:
            return
        
        # 计算比例点位置
        x = self.line.p1.x + (self.line.p2.x - self.line.p1.x) * self.ratio
        y = self.line.p1.y + (self.line.p2.y - self.line.p1.y) * self.ratio
        
        # 更新点位置
        self.point.x = x
        self.point.y = y
    
    def get_description(self) -> str:
        return f"点{self.point.name}在线段{self.line.name}上，比例为{self.ratio:.2f}"

class PerpendicularPointConstraint(Constraint):
    """垂足约束：点必须是从另一点到线段的垂足"""
    
    def __init__(self, foot_point: Point, source_point: Point, line: Line):
        super().__init__(foot_point, [source_point, line])
        self.foot_point = foot_point
        self.source_point = source_point
        self.line = line
    
    def update(self):
        """更新垂足位置"""
        if not self.active or not self.line or not self.line.p1 or not self.line.p2 or not self.source_point:
            return
        
        # 计算垂足
        foot_x, foot_y = self._calculate_perpendicular_foot(
            self.source_point.x, self.source_point.y,
            self.line.p1.x, self.line.p1.y,
            self.line.p2.x, self.line.p2.y
        )
        
        # 更新垂足位置
        self.foot_point.x = foot_x
        self.foot_point.y = foot_y
    
    def _calculate_perpendicular_foot(self, px, py, x1, y1, x2, y2):
        """计算点(px,py)到线段(x1,y1)-(x2,y2)的垂足"""
        # 向量AB和AP
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            return x1, y1
        
        # 计算投影参数t
        t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
        
        # 限制t在[0,1]范围内（垂足在线段上）
        t = max(0, min(1, t))
        
        # 计算垂足坐标
        foot_x = x1 + t * dx
        foot_y = y1 + t * dy
        
        return foot_x, foot_y
    
    def get_description(self) -> str:
        return f"点{self.foot_point.name}是从点{self.source_point.name}到线段{self.line.name}的垂足"

class CircleCenterConstraint(Constraint):
    """圆心约束：点必须是经过三个点的圆的圆心"""
    
    def __init__(self, center_point: Point, point1: Point, point2: Point, point3: Point):
        super().__init__(center_point, [point1, point2, point3])
        self.center_point = center_point
        self.point1 = point1
        self.point2 = point2
        self.point3 = point3
    
    def update(self):
        """更新圆心位置"""
        if not self.active or not all([self.point1, self.point2, self.point3]):
            return
        
        # 计算三点确定圆的圆心
        center_x, center_y = self._calculate_circle_center(
            self.point1.x, self.point1.y,
            self.point2.x, self.point2.y,
            self.point3.x, self.point3.y
        )
        
        if center_x is not None and center_y is not None:
            self.center_point.x = center_x
            self.center_point.y = center_y
    
    def _calculate_circle_center(self, x1, y1, x2, y2, x3, y3):
        """计算三点确定的圆的圆心"""
        # 使用行列式方法计算圆心
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        
        if abs(d) < 1e-10:  # 三点共线
            return None, None
        
        ux = ((x1*x1 + y1*y1) * (y2 - y3) + (x2*x2 + y2*y2) * (y3 - y1) + (x3*x3 + y3*y3) * (y1 - y2)) / d
        uy = ((x1*x1 + y1*y1) * (x3 - x2) + (x2*x2 + y2*y2) * (x1 - x3) + (x3*x3 + y3*y3) * (x2 - x1)) / d
        
        return ux, uy
    
    def get_description(self) -> str:
        return f"点{self.center_point.name}是经过点{self.point1.name}、{self.point2.name}、{self.point3.name}的圆的圆心"

class ConstraintManager:
    """约束管理器"""
    
    def __init__(self):
        self.constraints: List[Constraint] = []
        self.update_in_progress = False  # 防止循环更新
    
    def add_constraint(self, constraint: Constraint):
        """添加约束"""
        if constraint not in self.constraints:
            self.constraints.append(constraint)
            # 立即更新一次
            self.update_constraint(constraint)
    
    def remove_constraint(self, constraint: Constraint):
        """移除约束"""
        if constraint in self.constraints:
            self.constraints.remove(constraint)
    
    def remove_constraints_for_object(self, obj):
        """移除与指定对象相关的所有约束"""
        to_remove = []
        for constraint in self.constraints:
            if (constraint.constrained_object == obj or 
                obj in constraint.dependencies):
                to_remove.append(constraint)
        
        for constraint in to_remove:
            self.remove_constraint(constraint)
    
    def update_constraint(self, constraint: Constraint):
        """更新单个约束"""
        if not self.update_in_progress and constraint.active:
            try:
                constraint.update()
            except Exception as e:
                print(f"更新约束时出错: {e}")
                constraint.active = False
    
    def update_all_constraints(self):
        """更新所有约束"""
        if self.update_in_progress:
            return
        
        self.update_in_progress = True
        try:
            # 减少迭代次数以提高性能
            max_iterations = 2
            for iteration in range(max_iterations):
                any_updated = False
                for constraint in self.constraints[:]:  # 复制列表防止修改过程中改变
                    if constraint.active:
                        try:
                            old_pos = None
                            if hasattr(constraint.constrained_object, 'x') and hasattr(constraint.constrained_object, 'y'):
                                old_pos = (constraint.constrained_object.x, constraint.constrained_object.y)
                            
                            constraint.update()
                            
                            # 检查是否有实际变化
                            if old_pos and hasattr(constraint.constrained_object, 'x') and hasattr(constraint.constrained_object, 'y'):
                                new_pos = (constraint.constrained_object.x, constraint.constrained_object.y)
                                if abs(old_pos[0] - new_pos[0]) > 0.1 or abs(old_pos[1] - new_pos[1]) > 0.1:
                                    any_updated = True
                        except Exception as e:
                            print(f"约束更新错误: {e}")
                            constraint.active = False
                
                # if没有显著变化，提前退出
                if not any_updated:
                    break
        finally:
            self.update_in_progress = False
    
    def get_constraints_for_object(self, obj) -> List[Constraint]:
        """获取对象的所有约束"""
        result = []
        for constraint in self.constraints:
            if constraint.constrained_object == obj:
                result.append(constraint)
        return result
    
    def get_dependent_constraints(self, obj) -> List[Constraint]:
        """获取依赖于指定对象的约束"""
        result = []
        for constraint in self.constraints:
            if obj in constraint.dependencies:
                result.append(constraint)
        return result
    
    def clear_all_constraints(self):
        """清空所有约束"""
        self.constraints.clear()
    
    def get_constraint_descriptions(self) -> List[str]:
        """获取所有约束的描述"""
        return [constraint.get_description() for constraint in self.constraints if constraint.active]

# 为Point类添加约束支持的扩展
class ConstrainedPoint(Point):
    """支持约束的点类"""
    
    def __init__(self, x=0, y=0, name="", radius=5):
        super().__init__(x, y, name, radius)
        self.constraints = []  # 该点的约束列表
        self.constraint_manager = None  # 约束管理器引用
        self.is_constrained_point = True  # 标识这是一个约束点
        self.exclude_from_intersection = True  # 排除在交点检测之外
    
    def set_constraint_manager(self, manager: ConstraintManager):
        """设置约束管理器"""
        self.constraint_manager = manager
    
    def add_constraint(self, constraint: Constraint):
        """添加约束"""
        if constraint not in self.constraints:
            self.constraints.append(constraint)
            if self.constraint_manager:
                self.constraint_manager.add_constraint(constraint)
    
    def remove_all_constraints(self):
        """移除所有约束"""
        if self.constraint_manager:
            for constraint in self.constraints[:]:
                self.constraint_manager.remove_constraint(constraint)
        self.constraints.clear()
    
    def set_position(self, x, y):
        """设置位置（会触发约束更新）"""
        if not self.fixed and not self.has_position_constraint():
            self.x = float(x)
            self.y = float(y)
            # 触发依赖于此点的约束更新
            if self.constraint_manager:
                dependent_constraints = self.constraint_manager.get_dependent_constraints(self)
                for constraint in dependent_constraints:
                    self.constraint_manager.update_constraint(constraint)
    
    def has_position_constraint(self) -> bool:
        """检查是否有位置约束"""
        return len(self.constraints) > 0
    
    def drag_to(self, new_pos):
        """拖拽到新位置"""
        if not self.has_position_constraint():
            super().drag_to(new_pos)
        # if有约束，则不允许自由拖拽
