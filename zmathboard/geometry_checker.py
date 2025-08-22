#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from typing import List, Dict, Set, Tuple
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from .geometry import Point, Line, GeometryObject
from .intersection import Intersection

class GeometryChecker(QObject):
    """几何异常检查系统 - 实时监测和修复画布上的异常几何信息"""
    
    # 信号：检测到异常时发出
    anomaly_detected = pyqtSignal(str, object)  # 异常类型，异常对象
    anomaly_fixed = pyqtSignal(str, object)     # 修复类型，修复对象
    
    def __init__(self, canvas=None):
        super().__init__()
        self.canvas = canvas
        self.enabled = True
        self.auto_fix = True  # 是否自动修复异常
        
        # 检查定时器
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.perform_check)
        self.check_timer.start(2000)  # 每2秒检查一次
        
        # 异常记录
        self.detected_anomalies = set()
        
    def enable_checking(self, enabled: bool):
        """启用或禁用检查"""
        self.enabled = enabled
        if enabled:
            self.check_timer.start(2000)
        else:
            self.check_timer.stop()
    
    def set_auto_fix(self, auto_fix: bool):
        """设置是否自动修复异常"""
        self.auto_fix = auto_fix
    
    def perform_check(self):
        """执行完整的几何异常检查"""
        if not self.enabled or not self.canvas:
            return
        
        try:
            # 检查交点异常
            self.check_intersection_anomalies()
            
            # 先检查无效线段并修复（在删除重复对象之前）
            self.check_invalid_lines()
            
            # 再检查重复对象（此时线段已修复）
            self.check_duplicate_objects()
            
            # 检查孤立点
            self.check_orphaned_points()
            
            # 检查独立交点（不在任何线段上的交点）
            self.check_orphaned_intersections()
            
        except Exception as e:
            print(f"几何检查过程中出错: {e}")
    
    def check_intersection_anomalies(self):
        """检查交点异常"""
        if not hasattr(self.canvas, 'intersection_manager'):
            return
        
        im = self.canvas.intersection_manager
        invalid_intersections = []
        
        for intersection in im.intersections:
            if not self.is_valid_intersection(intersection):
                invalid_intersections.append(intersection)
                anomaly_key = f"invalid_intersection_{id(intersection)}"
                
                if anomaly_key not in self.detected_anomalies:
                    self.detected_anomalies.add(anomaly_key)
                    self.anomaly_detected.emit("无效交点", intersection)
                    print(f"检测到无效交点: {intersection.name}")
        
        # 自动修复：移除无效交点
        if self.auto_fix and invalid_intersections:
            for intersection in invalid_intersections:
                try:
                    im.intersections.remove(intersection)
                    self.anomaly_fixed.emit("移除无效交点", intersection)
                    print(f"已移除无效交点: {intersection.name}")
                except ValueError:
                    pass  # 交点已被移除
    
    def is_valid_intersection(self, intersection: Intersection) -> bool:
        """检查交点是否有效"""
        if not intersection.parent_lines or len(intersection.parent_lines) != 2:
            return False
        
        line1, line2 = intersection.parent_lines[0], intersection.parent_lines[1]
        
        # 检查线段是否还存在于画布上
        if (line1 not in self.canvas.objects or 
            line2 not in self.canvas.objects):
            return False
        
        # 检查线段是否真的相交
        return self.lines_actually_intersect(line1, line2, intersection)
    
    def lines_actually_intersect(self, line1: Line, line2: Line, intersection: Intersection) -> bool:
        """检查两条线段是否真的在交点位置相交"""
        try:
            # 计算理论交点
            theoretical_intersection = self.calculate_line_intersection(line1, line2)
            if not theoretical_intersection:
                return False
            
            # 检查实际交点与理论交点是否接近
            distance = math.sqrt(
                (intersection.x - theoretical_intersection[0]) ** 2 + 
                (intersection.y - theoretical_intersection[1]) ** 2
            )
            
            return distance < 5.0  # 允许5像素的误差
            
        except Exception:
            return False
    
    def calculate_line_intersection(self, line1: Line, line2: Line) -> Tuple[float, float] or None:
        """计算两条线段的交点"""
        try:
            x1, y1 = line1.p1.x, line1.p1.y
            x2, y2 = line1.p2.x, line1.p2.y
            x3, y3 = line2.p1.x, line2.p1.y
            x4, y4 = line2.p2.x, line2.p2.y
            
            # 计算交点
            denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
            if abs(denom) < 1e-10:  # 平行线
                return None
            
            t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
            u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
            
            # 检查交点是否在两条线段上
            if 0 <= t <= 1 and 0 <= u <= 1:
                x = x1 + t * (x2 - x1)
                y = y1 + t * (y2 - y1)
                return (x, y)
            
            return None
            
        except Exception:
            return None
    
    def check_duplicate_objects(self):
        """检查重复对象"""
        seen_objects = {}
        duplicates = []
        
        for obj in self.canvas.objects:
            obj_key = self.get_object_key(obj)
            if obj_key in seen_objects:
                duplicates.append(obj)
                anomaly_key = f"duplicate_{id(obj)}"
                
                if anomaly_key not in self.detected_anomalies:
                    self.detected_anomalies.add(anomaly_key)
                    self.anomaly_detected.emit("重复对象", obj)
                    print(f"检测到重复对象: {getattr(obj, 'name', 'Unknown')}")
            else:
                seen_objects[obj_key] = obj
        
        # 自动修复：移除重复对象
        if self.auto_fix and duplicates:
            for duplicate in duplicates:
                # 检查对象是否受到动画保护
                if hasattr(duplicate, '_animation_protected'):
                    print(f"跳过删除受保护的对象: {getattr(duplicate, 'name', 'Unknown')}")
                    continue
                
                # 检查是否是线段的端点，if是，跳过删除
                is_line_endpoint = False
                if hasattr(duplicate, 'x') and hasattr(duplicate, 'y'):  # 是点对象
                    for obj in self.canvas.objects:
                        if hasattr(obj, 'p1') and hasattr(obj, 'p2'):  # 是线段
                            if obj.p1 == duplicate or obj.p2 == duplicate:
                                is_line_endpoint = True
                                print(f"跳过删除线段端点: {getattr(duplicate, 'name', 'Unknown')}")
                                break
                
                if not is_line_endpoint:
                    try:
                        self.canvas.objects.remove(duplicate)
                        self.anomaly_fixed.emit("移除重复对象", duplicate)
                        print(f"已移除重复对象: {getattr(duplicate, 'name', 'Unknown')}")
                    except ValueError:
                        pass
    
    def get_object_key(self, obj: GeometryObject) -> str:
        """获取对象的唯一标识符"""
        if isinstance(obj, Point):
            return f"Point_{round(obj.x, 1)}_{round(obj.y, 1)}"
        elif isinstance(obj, Line):
            return f"Line_{round(obj.p1.x, 1)}_{round(obj.p1.y, 1)}_{round(obj.p2.x, 1)}_{round(obj.p2.y, 1)}"
        else:
            return f"{type(obj).__name__}_{id(obj)}"
    
    def check_invalid_lines(self):
        """检查无效线段"""
        invalid_lines = []
        
        for obj in self.canvas.objects:
            if isinstance(obj, Line):
                if self.is_invalid_line(obj):
                    invalid_lines.append(obj)
                    anomaly_key = f"invalid_line_{id(obj)}"
                    
                    if anomaly_key not in self.detected_anomalies:
                        self.detected_anomalies.add(anomaly_key)
                        self.anomaly_detected.emit("无效线段", obj)
                        print(f"检测到无效线段: {getattr(obj, 'name', 'Unknown')}")
        
        # 自动修复：尝试修复无效线段
        if self.auto_fix and invalid_lines:
            for line in invalid_lines:
                # 检查线段是否受到动画保护
                if hasattr(line, '_animation_protected'):
                    print(f"跳过修复受保护的线段: {getattr(line, 'name', 'Unknown')}")
                    continue
                    
                try:
                    # 尝试修复长度为0的线段
                    if self.fix_invalid_line(line):
                        self.anomaly_fixed.emit("修复无效线段", line)
                        print(f"已修复无效线段: {getattr(line, 'name', 'Unknown')}")
                    else:
                        # 修复失败才删除
                        self.canvas.objects.remove(line)
                        self.anomaly_fixed.emit("移除无效线段", line)
                        print(f"无法修复，已移除无效线段: {getattr(line, 'name', 'Unknown')}")
                except ValueError:
                    pass
    
    def is_invalid_line(self, line: Line) -> bool:
        """检查线段是否无效"""
        try:
            # 检查线段长度是否为零
            length = math.sqrt(
                (line.p2.x - line.p1.x) ** 2 + 
                (line.p2.y - line.p1.y) ** 2
            )
            if length < 1.0:  # 长度小于1像素认为无效
                return True
            
            # 检查端点是否还在画布上（但跳过受保护的线段的端点检查）
            if not hasattr(line, '_animation_protected'):
                if (line.p1 not in self.canvas.objects or 
                    line.p2 not in self.canvas.objects):
                    return True
            
            return False
            
        except Exception:
            return True
            
    def fix_invalid_line(self, line: Line) -> bool:
        """尝试修复无效线段"""
        try:
            # 检查是否是长度为0的问题（两点重合）
            current_length = math.sqrt(
                (line.p2.x - line.p1.x) ** 2 + 
                (line.p2.y - line.p1.y) ** 2
            )
            
            if current_length < 1.0:  # 长度小于1像素
                # 检查线段是否有保存的原始长度
                if hasattr(line, '_original_length') and line._original_length > 1.0:
                    # 使用保存的原始长度来修复
                    target_length = line._original_length
                    print(f"尝试将线段 {getattr(line, 'name', 'Unknown')} 恢复到原始长度: {target_length:.2f}")
                    
                    # 计算p2应该在的位置（保持p1不变）
                    # if两点完全重合，使用一个默认方向
                    if abs(line.p2.x - line.p1.x) < 0.0001 and abs(line.p2.y - line.p1.y) < 0.0001:
                        # 使用水平方向作为默认方向
                        line.p2.x = line.p1.x + target_length
                        line.p2.y = line.p1.y
                    else:
                        # 保持原有方向，只调整长度
                        dx = line.p2.x - line.p1.x
                        dy = line.p2.y - line.p1.y
                        current_length = math.sqrt(dx*dx + dy*dy)
                        if current_length > 0:
                            # 标准化方向向量并乘以目标长度
                            factor = target_length / current_length
                            line.p2.x = line.p1.x + dx * factor
                            line.p2.y = line.p1.y + dy * factor
                    
                    # 验证修复结果
                    new_length = math.sqrt(
                        (line.p2.x - line.p1.x) ** 2 + 
                        (line.p2.y - line.p1.y) ** 2
                    )
                    
                    if abs(new_length - target_length) < 0.1:
                        print(f"成功修复线段 {getattr(line, 'name', 'Unknown')}，新长度: {new_length:.2f}")
                        
                        # 确保端点在画布中
                        if line.p1 not in self.canvas.objects:
                            self.canvas.objects.append(line.p1)
                            print(f"将端点 {getattr(line.p1, 'name', 'P1')} 重新添加到画布")
                        if line.p2 not in self.canvas.objects:
                            self.canvas.objects.append(line.p2)
                            print(f"将端点 {getattr(line.p2, 'name', 'P2')} 重新添加到画布")
                        
                        return True
                    else:
                        print(f"修复失败，实际长度: {new_length:.2f}，目标长度: {target_length:.2f}")
                        return False
                else:
                    # 没有原始长度信息，使用默认长度50
                    default_length = 50.0
                    print(f"线段 {getattr(line, 'name', 'Unknown')} 无原始长度信息，使用默认长度: {default_length}")
                    
                    line.p2.x = line.p1.x + default_length
                    line.p2.y = line.p1.y
                    
                    return True
            
            return False  # 不是长度问题，无法修复
            
        except Exception as e:
            print(f"修复线段时发生错误: {e}")
            return False
    
    def check_orphaned_points(self):
        """检查孤立点（没有连接到任何线段的点）"""
        connected_points = set()
        
        # 收集所有连接到线段的点
        for obj in self.canvas.objects:
            if isinstance(obj, Line):
                connected_points.add(obj.p1)
                connected_points.add(obj.p2)
        
        orphaned_points = []
        for obj in self.canvas.objects:
            if isinstance(obj, Point) and obj not in connected_points:
                # 跳过固定点、特殊点和受保护的点
                if (not getattr(obj, 'fixed', False) and 
                    not getattr(obj, 'is_special', False) and 
                    not getattr(obj, '_animation_protected', False)):
                    orphaned_points.append(obj)
                    anomaly_key = f"orphaned_point_{id(obj)}"
                    
                    if anomaly_key not in self.detected_anomalies:
                        self.detected_anomalies.add(anomaly_key)
                        self.anomaly_detected.emit("孤立点", obj)
                        print(f"检测到孤立点: {getattr(obj, 'name', 'Unknown')}")
                elif getattr(obj, '_animation_protected', False):
                    print(f"跳过检测受保护的点: {getattr(obj, 'name', 'Unknown')}")
        
        # 注意：不自动删除孤立点，因为user可能有意创建它们
        # 只发出警告
    
    def manual_fix_all(self):
        """手动修复所有检测到的异常"""
        print("开始手动修复所有异常...")
        old_auto_fix = self.auto_fix
        self.auto_fix = True
        self.perform_check()
        self.auto_fix = old_auto_fix
        print("异常修复完成")
    
    def clear_anomaly_records(self):
        """清除异常记录"""
        self.detected_anomalies.clear()
    
    def check_orphaned_intersections(self):
        """检查独立交点（不在任何线段上的交点）"""
        if not hasattr(self.canvas, 'intersection_manager'):
            return
            
        orphaned_intersections = []
        im = self.canvas.intersection_manager
        
        for intersection in im.intersections:
            if self.is_orphaned_intersection(intersection):
                orphaned_intersections.append(intersection)
                anomaly_key = f"orphaned_intersection_{id(intersection)}"
                
                if anomaly_key not in self.detected_anomalies:
                    self.detected_anomalies.add(anomaly_key)
                    self.anomaly_detected.emit("独立交点", intersection)
                    print(f"检测到独立交点: {intersection.name} - 不在任何线段上或依赖的线段已不存在")
        
        # 自动修复：移除独立交点
        if self.auto_fix and orphaned_intersections:
            for intersection in orphaned_intersections:
                try:
                    # 从交点管理器中移除
                    if intersection in im.intersections:
                        im.intersections.remove(intersection)
                    # 从画布中移除
                    if intersection in self.canvas.objects:
                        self.canvas.objects.remove(intersection)
                    self.anomaly_fixed.emit("移除独立交点", intersection)
                    print(f"已移除独立交点: {intersection.name}")
                except (ValueError, AttributeError) as e:
                    print(f"移除独立交点时出错: {e}")
    
    def is_orphaned_intersection(self, intersection) -> bool:
        """检查交点是否是独立存在的（孤立交点）"""
        try:
            # 检查是否有父线段信息
            if not hasattr(intersection, 'parent_lines') or not intersection.parent_lines:
                print(f"交点 {intersection.name} 没有父线段信息")
                return True
            
            # 检查父线段数量是否正确
            if len(intersection.parent_lines) != 2:
                print(f"交点 {intersection.name} 的父线段数量不正确: {len(intersection.parent_lines)}")
                return True
            
            line1, line2 = intersection.parent_lines[0], intersection.parent_lines[1]
            
            # 检查父线段是否仍然存在于画布上
            if line1 not in self.canvas.objects:
                print(f"交点 {intersection.name} 的父线段1不在画布上")
                return True
            if line2 not in self.canvas.objects:
                print(f"交点 {intersection.name} 的父线段2不在画布上")
                return True
            
            # 检查交点是否真的在两条线段上
            if not self.is_point_on_line_segment(intersection, line1):
                print(f"交点 {intersection.name} 不在父线段1上")
                return True
            if not self.is_point_on_line_segment(intersection, line2):
                print(f"交点 {intersection.name} 不在父线段2上")
                return True
            
            # 检查两条线段是否真的在交点位置相交
            theoretical_intersection = self.calculate_line_intersection(line1, line2)
            if not theoretical_intersection:
                print(f"交点 {intersection.name} 的父线段实际上不相交")
                return True
            
            # 检查理论交点与实际交点位置是否接近
            distance = math.sqrt(
                (intersection.x - theoretical_intersection[0]) ** 2 + 
                (intersection.y - theoretical_intersection[1]) ** 2
            )
            
            if distance > 10.0:  # 允许10像素的误差
                print(f"交点 {intersection.name} 位置偏差过大: {distance:.2f}像素")
                return True
            
            return False
            
        except Exception as e:
            print(f"检查交点 {getattr(intersection, 'name', 'Unknown')} 时出错: {e}")
            return True
    
    def is_point_on_line_segment(self, point, line, tolerance=5.0) -> bool:
        """检查点是否在线段上"""
        try:
            # 获取线段的两个端点
            x1, y1 = line.p1.x, line.p1.y
            x2, y2 = line.p2.x, line.p2.y
            px, py = point.x, point.y
            
            # 计算点到线段的距离
            # 使用点到直线的距离公式
            A = y2 - y1
            B = x1 - x2
            C = x2 * y1 - x1 * y2
            
            # 避免除零
            line_length = math.sqrt(A*A + B*B)
            if line_length < 1e-10:
                return False
            
            # 点到直线的距离
            distance = abs(A * px + B * py + C) / line_length
            
            if distance > tolerance:
                return False
            
            # 检查点是否在线段范围内（而不是延长线上）
            # 使用投影方法
            dot_product = (px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)
            squared_length = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1)
            
            if squared_length < 1e-10:
                # 线段长度为0，检查点是否与端点重合
                return math.sqrt((px - x1)**2 + (py - y1)**2) <= tolerance
            
            # 投影参数，0表示在起点，1表示在终点
            param = dot_product / squared_length
            
            # 点在线段上的条件：0 <= param <= 1
            return 0 <= param <= 1
            
        except Exception as e:
            print(f"检查点是否在线段上时出错: {e}")
            return False

    def get_statistics(self) -> Dict[str, int]:
        """获取检查统计信息"""
        stats = {
            "总对象数": len(self.canvas.objects) if self.canvas else 0,
            "检测到的异常": len(self.detected_anomalies),
            "交点数": len(self.canvas.intersection_manager.intersections) if hasattr(self.canvas, 'intersection_manager') else 0
        }
        return stats
