#!/usr/bin/env python
# -*- coding: utf-8 -*-

from typing import List, Dict, Any, Optional
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor
from .geometry import Point, Line
from .ai_assistant import DrawingCommand
from .constraints import ConstrainedPoint, MidpointConstraint, RatioPointConstraint, PerpendicularPointConstraint

class DrawingAPI:
    """绘图API，用于执行AI生成的绘图命令"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.created_objects = {}  # 存储创建的对象，键为名称
        
    def execute_commands(self, commands: List[DrawingCommand]) -> bool:
        """执行一系列绘图命令"""
        try:
            self.created_objects.clear()  # 清空之前创建的对象记录
            
            for command in commands:
                success = self.execute_single_command(command)
                if not success:
                    return False
                    
            # 更新画布
            self.canvas.update()
            return True
            
        except Exception as e:
            print(f"执行绘图命令时出错: {str(e)}")
            return False
    
    def _generate_unique_name(self, base_name: str, obj_type: str = "") -> str:
        """生成唯一的名称，避免重复"""
        # 检查现有对象名称
        existing_names = set()
        for obj in self.canvas.objects:
            if hasattr(obj, 'name') and obj.name:
                existing_names.add(obj.name)
        
        # 检查已创建的对象名称
        existing_names.update(self.created_objects.keys())
        
        # if基础名称不重复，直接返回
        if base_name not in existing_names:
            return base_name
        
        # 生成带序号的唯一名称
        counter = 1
        while f"{base_name}{counter}" in existing_names:
            counter += 1
        
        return f"{base_name}{counter}"
    
    def execute_single_command(self, command: DrawingCommand) -> bool:
        """执行单个绘图命令"""
        try:
            if command.command_type == "point":
                return self.create_point(command.params)
            elif command.command_type == "line":
                return self.create_line(command.params)
            elif command.command_type == "triangle":
                return self.create_triangle(command.params)
            elif command.command_type == "midpoint":
                return self.create_midpoint(command.params)
            elif command.command_type == "ratio_point":
                return self.create_ratio_point(command.params)
            elif command.command_type == "perpendicular_foot":
                return self.create_perpendicular_foot(command.params)
            elif command.command_type == "equilateral_triangle":
                return self.create_equilateral_triangle(command.params)
            elif command.command_type == "isosceles_triangle":
                return self.create_isosceles_triangle(command.params)
            elif command.command_type == "right_triangle":
                return self.create_right_triangle(command.params)
            elif command.command_type == "rectangle":
                return self.create_rectangle_from_params(command.params)
            elif command.command_type == "regular_polygon":
                return self.create_regular_polygon(command.params)
            elif command.command_type == "fixed_length_line":
                return self.create_fixed_length_line(command.params)
            elif command.command_type == "fixed_angle":
                return self.create_fixed_angle(command.params)
            elif command.command_type == "fixed_point":
                return self.create_fixed_point(command.params)
            else:
                print(f"不支持的命令类型: {command.command_type}")
                return False
                
        except Exception as e:
            print(f"执行命令 {command.command_type} 时出错: {str(e)}")
            return False
    
    def create_point(self, params: Dict[str, Any]) -> bool:
        """创建点"""
        try:
            base_name = params.get("name", f"P{len(self.created_objects) + 1}")
            # 生成唯一名称
            name = self._generate_unique_name(base_name, "point")
            x = float(params.get("x", 0))
            y = float(params.get("y", 0))
            color_str = params.get("color", "#000000")
            
            # 转换颜色
            color = self.parse_color(color_str)
            
            # 创建点对象
            point = Point(x, y, name)
            point.color = color
            
            # 添加到画布
            self.canvas.add_object(point)
            
            # 记录创建的对象
            self.created_objects[name] = point
            
            print(f"创建点: {name} 在 ({x}, {y})")
            return True
            
        except Exception as e:
            print(f"创建点时出错: {str(e)}")
            return False
    
    def create_line(self, params: Dict[str, Any]) -> bool:
        """创建线段"""
        try:
            base_name = params.get("name", f"L{len([obj for obj in self.created_objects.values() if hasattr(obj, 'p1')]) + 1}")
            # 生成唯一名称
            name = self._generate_unique_name(base_name, "line")
            start_point_name = params.get("start_point")
            end_point_name = params.get("end_point")
            color_str = params.get("color", "#000000")
            width = params.get("width", 2)
            
            # 查找起点和终点
            start_point = self.find_point_by_name(start_point_name)
            end_point = self.find_point_by_name(end_point_name)
            
            if not start_point or not end_point:
                print(f"无法找到线段的端点: {start_point_name}, {end_point_name}")
                return False
            
            # 转换颜色
            color = self.parse_color(color_str)
            
            # 创建线段对象
            line = Line(start_point, end_point, name)
            line.color = color
            line.width = width
            
            # 添加到画布
            self.canvas.add_object(line)
            
            # 记录创建的对象
            self.created_objects[name] = line
            
            print(f"创建线段: {name} 连接 {start_point_name} 和 {end_point_name}")
            return True
            
        except Exception as e:
            print(f"创建线段时出错: {str(e)}")
            return False
    
    def create_triangle(self, params: Dict[str, Any]) -> bool:
        """创建三角形（通过创建三条边）"""
        try:
            name = params.get("name", f"T{len(self.created_objects) + 1}")
            points = params.get("points", [])
            color_str = params.get("color", "#000000")
            fill_color_str = params.get("fill_color", "#FFCCCC")
            
            if len(points) != 3:
                print("三角形需要exactly 3个点")
                return False
            
            # 查找三个顶点
            triangle_points = []
            for point_name in points:
                point = self.find_point_by_name(point_name)
                if not point:
                    print(f"无法找到三角形的顶点: {point_name}")
                    return False
                triangle_points.append(point)
            
            # 转换颜色
            color = self.parse_color(color_str)
            
            # 创建三条边
            edges = []
            for i in range(3):
                start_point = triangle_points[i]
                end_point = triangle_points[(i + 1) % 3]
                
                # 检查是否已经有这条边
                existing_line = self.find_line_between_points(start_point, end_point)
                if existing_line:
                    edges.append(existing_line)
                else:
                    # 创建新的边
                    edge_name = f"{name}_边{i+1}"
                    line = Line(start_point, end_point, edge_name)
                    line.color = color
                    line.width = 2
                    
                    self.canvas.add_object(line)
                    self.created_objects[edge_name] = line
                    edges.append(line)
            
            print(f"创建三角形: {name} 由点 {', '.join(points)} 组成")
            return True
            
        except Exception as e:
            print(f"创建三角形时出错: {str(e)}")
            return False
    
    def find_point_by_name(self, name: str) -> Optional[Point]:
        """根据名称查找点"""
        # 首先在刚创建的对象中查找
        if name in self.created_objects and isinstance(self.created_objects[name], Point):
            return self.created_objects[name]
        
        # 然后在画布所有对象中查找
        for obj in self.canvas.objects:
            if isinstance(obj, Point) and obj.name == name:
                return obj
        
        return None
    
    def find_line_between_points(self, point1: Point, point2: Point) -> Optional[Line]:
        """查找连接两个点的线段"""
        for obj in self.canvas.objects:
            if isinstance(obj, Line):
                if (obj.p1 == point1 and obj.p2 == point2) or (obj.p1 == point2 and obj.p2 == point1):
                    return obj
        return None
    
    def parse_color(self, color_str: str) -> QColor:
        """解析颜色字符串"""
        try:
            if color_str.startswith("#"):
                return QColor(color_str)
            elif color_str.lower() in ["red", "红色"]:
                return QColor("#FF0000")
            elif color_str.lower() in ["green", "绿色"]:
                return QColor("#00FF00")
            elif color_str.lower() in ["blue", "蓝色"]:
                return QColor("#0000FF")
            elif color_str.lower() in ["black", "黑色"]:
                return QColor("#000000")
            elif color_str.lower() in ["white", "白色"]:
                return QColor("#FFFFFF")
            else:
                return QColor("#000000")  # 默认黑色
        except:
            return QColor("#000000")  # 默认黑色
    
    def create_regular_triangle(self, center_x: float, center_y: float, size: float = 100, name_prefix: str = "T") -> bool:
        """创建等边三角形"""
        try:
            import math
            
            # 计算三个顶点的位置
            angles = [0, 2*math.pi/3, 4*math.pi/3]  # 0°, 120°, 240°
            points = []
            
            for i, angle in enumerate(angles):
                x = center_x + size * math.cos(angle)
                y = center_y + size * math.sin(angle)
                
                point_name = f"{name_prefix}{chr(65+i)}"  # A, B, C
                point = Point(x, y, point_name)
                point.color = QColor("#FF0000")
                
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建三条边
            edges = [(0,1), (1,2), (2,0)]
            for i, (start_idx, end_idx) in enumerate(edges):
                edge_name = f"{name_prefix}_边{i+1}"
                line = Line(points[start_idx], points[end_idx], edge_name)
                line.color = QColor("#000000")
                line.width = 2
                
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建等边三角形: 中心 ({center_x}, {center_y}), 大小 {size}")
            return True
            
        except Exception as e:
            print(f"创建等边三角形时出错: {str(e)}")
            return False
    
    def create_rectangle(self, x: float, y: float, width: float, height: float, name_prefix: str = "R") -> bool:
        """创建矩形"""
        try:
            # 计算四个顶点
            points_data = [
                (x, y, f"{name_prefix}A"),
                (x + width, y, f"{name_prefix}B"),
                (x + width, y + height, f"{name_prefix}C"),
                (x, y + height, f"{name_prefix}D")
            ]
            
            points = []
            for px, py, point_name in points_data:
                point = Point(px, py, point_name)
                point.color = QColor("#FF0000")
                
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建四条边
            edges = [(0,1), (1,2), (2,3), (3,0)]
            for i, (start_idx, end_idx) in enumerate(edges):
                edge_name = f"{name_prefix}_边{i+1}"
                line = Line(points[start_idx], points[end_idx], edge_name)
                line.color = QColor("#000000")
                line.width = 2
                
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建矩形: 位置 ({x}, {y}), 大小 {width}x{height}")
            return True
            
        except Exception as e:
            print(f"创建矩形时出错: {str(e)}")
            return False
    
    def clear_objects(self):
        """清空所有对象"""
        self.canvas.objects.clear()
        self.canvas.active_polygons.clear()
        self.created_objects.clear()
        self.canvas.update()
        print("已清空所有对象")
    
    def create_midpoint(self, params: Dict[str, Any]) -> bool:
        """创建中点约束"""
        try:
            point_name = params.get("point_name", f"M{len(self.created_objects) + 1}")
            line_name = params.get("line_name")
            color_str = params.get("color", "#FF0000")
            
            # 查找线段
            line = self.find_line_by_name(line_name)
            if not line:
                print(f"无法找到线段: {line_name}")
                return False
            
            # 计算中点位置
            mid_x = (line.p1.x + line.p2.x) / 2
            mid_y = (line.p1.y + line.p2.y) / 2
            
            # 创建约束点
            color = self.parse_color(color_str)
            point = ConstrainedPoint(mid_x, mid_y, point_name)
            point.color = color
            point.set_constraint_manager(self.canvas.constraint_manager)
            
            # 添加到画布
            self.canvas.add_object(point)
            
            # 创建中点约束
            constraint = MidpointConstraint(point, line)
            point.add_constraint(constraint)
            
            # 记录创建的对象
            self.created_objects[point_name] = point
            
            print(f"创建中点: {point_name} 为线段 {line_name} 的中点")
            return True
            
        except Exception as e:
            print(f"创建中点时出错: {str(e)}")
            return False
    
    def create_ratio_point(self, params: Dict[str, Any]) -> bool:
        """创建比例点约束"""
        try:
            point_name = params.get("point_name", f"R{len(self.created_objects) + 1}")
            line_name = params.get("line_name")
            ratio = float(params.get("ratio", 0.5))
            color_str = params.get("color", "#FF0000")
            
            # 查找线段
            line = self.find_line_by_name(line_name)
            if not line:
                print(f"无法找到线段: {line_name}")
                return False
            
            # 计算比例点位置
            x = line.p1.x + (line.p2.x - line.p1.x) * ratio
            y = line.p1.y + (line.p2.y - line.p1.y) * ratio
            
            # 创建约束点
            color = self.parse_color(color_str)
            point = ConstrainedPoint(x, y, point_name)
            point.color = color
            point.set_constraint_manager(self.canvas.constraint_manager)
            
            # 添加到画布
            self.canvas.add_object(point)
            
            # 创建比例约束
            constraint = RatioPointConstraint(point, line, ratio)
            point.add_constraint(constraint)
            
            # 记录创建的对象
            self.created_objects[point_name] = point
            
            print(f"创建比例点: {point_name} 在线段 {line_name} 上，比例为 {ratio}")
            return True
            
        except Exception as e:
            print(f"创建比例点时出错: {str(e)}")
            return False
    
    def create_perpendicular_foot(self, params: Dict[str, Any]) -> bool:
        """创建垂足约束"""
        try:
            foot_name = params.get("foot_name", f"F{len(self.created_objects) + 1}")
            source_point_name = params.get("source_point_name")
            line_name = params.get("line_name")
            color_str = params.get("color", "#FF0000")
            
            # 查找源点和线段
            source_point = self.find_point_by_name(source_point_name)
            line = self.find_line_by_name(line_name)
            
            if not source_point:
                print(f"无法找到源点: {source_point_name}")
                return False
            if not line:
                print(f"无法找到线段: {line_name}")
                return False
            
            # 计算垂足位置
            foot_x, foot_y = self._calculate_perpendicular_foot(
                source_point.x, source_point.y,
                line.p1.x, line.p1.y,
                line.p2.x, line.p2.y
            )
            
            # 创建约束点
            color = self.parse_color(color_str)
            foot_point = ConstrainedPoint(foot_x, foot_y, foot_name)
            foot_point.color = color
            foot_point.set_constraint_manager(self.canvas.constraint_manager)
            
            # 添加到画布
            self.canvas.add_object(foot_point)
            
            # 创建垂足约束
            constraint = PerpendicularPointConstraint(foot_point, source_point, line)
            foot_point.add_constraint(constraint)
            
            # 记录创建的对象
            self.created_objects[foot_name] = foot_point
            
            print(f"创建垂足: {foot_name} 是从点 {source_point_name} 到线段 {line_name} 的垂足")
            return True
            
        except Exception as e:
            print(f"创建垂足时出错: {str(e)}")
            return False
    
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
    
    def find_line_by_name(self, name: str) -> Optional[Line]:
        """根据名称查找线段"""
        # 首先在刚创建的对象中查找
        if name in self.created_objects and isinstance(self.created_objects[name], Line):
            return self.created_objects[name]
        
        # 然后在画布所有对象中查找
        for obj in self.canvas.objects:
            if isinstance(obj, Line) and obj.name == name:
                return obj
        
        return None
    
    def create_equilateral_triangle(self, params: Dict[str, Any]) -> bool:
        """创建等边三角形"""
        try:
            name_prefix = params.get("name", "T")
            center_x = float(params.get("center_x", 300))
            center_y = float(params.get("center_y", 200))
            side_length = float(params.get("side_length", 100))
            
            import math
            # 计算等边三角形的三个顶点
            height = side_length * math.sqrt(3) / 2
            radius = side_length / math.sqrt(3)
            
            points_data = [
                (center_x, center_y - radius, f"{name_prefix}A"),
                (center_x - side_length/2, center_y + radius/2, f"{name_prefix}B"),
                (center_x + side_length/2, center_y + radius/2, f"{name_prefix}C")
            ]
            
            points = []
            for px, py, point_name in points_data:
                point = Point(px, py, point_name)
                point.color = QColor("#FF0000")
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建三条边
            edges = [(0,1), (1,2), (2,0)]
            for i, (start_idx, end_idx) in enumerate(edges):
                edge_name = f"{name_prefix}{chr(65+start_idx)}{chr(65+end_idx)}"
                line = Line(points[start_idx], points[end_idx], edge_name)
                line.color = QColor("#000000")
                line.width = 2
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建等边三角形: {name_prefix}, 边长 {side_length}")
            return True
            
        except Exception as e:
            print(f"创建等边三角形时出错: {str(e)}")
            return False
    
    def create_isosceles_triangle(self, params: Dict[str, Any]) -> bool:
        """创建等腰三角形"""
        try:
            name_prefix = params.get("name", "T")
            apex_x = float(params.get("apex_x", 300))
            apex_y = float(params.get("apex_y", 100))
            base_width = float(params.get("base_width", 200))
            height = float(params.get("height", 150))
            
            # 顶点和底边两端点
            points_data = [
                (apex_x, apex_y, f"{name_prefix}A"),  # 顶点
                (apex_x - base_width/2, apex_y + height, f"{name_prefix}B"),  # 底边左端
                (apex_x + base_width/2, apex_y + height, f"{name_prefix}C")   # 底边右端
            ]
            
            points = []
            for px, py, point_name in points_data:
                point = Point(px, py, point_name)
                point.color = QColor("#FF0000")
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建三条边
            edges = [(0,1), (1,2), (2,0)]
            for i, (start_idx, end_idx) in enumerate(edges):
                edge_name = f"{name_prefix}{chr(65+start_idx)}{chr(65+end_idx)}"
                line = Line(points[start_idx], points[end_idx], edge_name)
                line.color = QColor("#000000")
                line.width = 2
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建等腰三角形: {name_prefix}")
            return True
            
        except Exception as e:
            print(f"创建等腰三角形时出错: {str(e)}")
            return False
    
    def create_right_triangle(self, params: Dict[str, Any]) -> bool:
        """创建直角三角形"""
        try:
            name_prefix = params.get("name", "T")
            right_angle_x = float(params.get("right_angle_x", 200))
            right_angle_y = float(params.get("right_angle_y", 200))
            leg1_length = float(params.get("leg1_length", 100))
            leg2_length = float(params.get("leg2_length", 150))
            
            # 直角顶点和两条直角边的端点
            points_data = [
                (right_angle_x, right_angle_y, f"{name_prefix}A"),  # 直角顶点
                (right_angle_x + leg1_length, right_angle_y, f"{name_prefix}B"),  # 第一条边
                (right_angle_x, right_angle_y + leg2_length, f"{name_prefix}C")   # 第二条边
            ]
            
            points = []
            for px, py, point_name in points_data:
                point = Point(px, py, point_name)
                point.color = QColor("#FF0000")
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建三条边
            edges = [(0,1), (1,2), (2,0)]
            for i, (start_idx, end_idx) in enumerate(edges):
                edge_name = f"{name_prefix}{chr(65+start_idx)}{chr(65+end_idx)}"
                line = Line(points[start_idx], points[end_idx], edge_name)
                line.color = QColor("#000000")
                line.width = 2
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建直角三角形: {name_prefix}")
            return True
            
        except Exception as e:
            print(f"创建直角三角形时出错: {str(e)}")
            return False
    
    def create_rectangle_from_params(self, params: Dict[str, Any]) -> bool:
        """从参数创建矩形"""
        try:
            name_prefix = params.get("name", "R")
            x = float(params.get("x", 200))
            y = float(params.get("y", 150))
            width = float(params.get("width", 200))
            height = float(params.get("height", 100))
            
            return self.create_rectangle(x, y, width, height, name_prefix)
            
        except Exception as e:
            print(f"创建矩形时出错: {str(e)}")
            return False
    
    def create_regular_polygon(self, params: Dict[str, Any]) -> bool:
        """创建正多边形"""
        try:
            name_prefix = params.get("name", "P")
            center_x = float(params.get("center_x", 300))
            center_y = float(params.get("center_y", 200))
            radius = float(params.get("radius", 80))
            sides = int(params.get("sides", 6))
            
            import math
            points = []
            
            # 计算各顶点位置
            for i in range(sides):
                angle = 2 * math.pi * i / sides - math.pi/2  # 从顶部开始
                px = center_x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                
                point_name = f"{name_prefix}{chr(65+i)}"
                point = Point(px, py, point_name)
                point.color = QColor("#FF0000")
                
                self.canvas.add_object(point)
                self.created_objects[point_name] = point
                points.append(point)
            
            # 创建边
            for i in range(sides):
                start_point = points[i]
                end_point = points[(i + 1) % sides]
                edge_name = f"{name_prefix}_边{i+1}"
                
                line = Line(start_point, end_point, edge_name)
                line.color = QColor("#000000")
                line.width = 2
                
                self.canvas.add_object(line)
                self.created_objects[edge_name] = line
            
            print(f"创建正{sides}边形: {name_prefix}")
            return True
            
        except Exception as e:
            print(f"创建正多边形时出错: {str(e)}")
            return False
    
    def create_fixed_length_line(self, params: Dict[str, Any]) -> bool:
        """创建固定长度的线段"""
        try:
            name = params.get("name", f"L{len([obj for obj in self.created_objects.values() if isinstance(obj, Line)]) + 1}")
            start_point_name = params.get("start_point")
            end_point_name = params.get("end_point")
            fixed_length = float(params.get("length", 100))
            color_str = params.get("color", "#000000")
            width = params.get("width", 2)
            
            # 查找起点和终点
            start_point = self.find_point_by_name(start_point_name)
            end_point = self.find_point_by_name(end_point_name)
            
            if not start_point or not end_point:
                print(f"无法找到线段的端点: {start_point_name}, {end_point_name}")
                return False
            
            # 转换颜色
            color = self.parse_color(color_str)
            
            # 创建线段对象
            line = Line(start_point, end_point, name)
            line.color = color
            line.width = width
            
            # 设置固定长度
            line.fixed_length = True
            line._original_length = fixed_length
            line._force_maintain_length = True
            
            # 调整线段到指定长度
            current_length = line.length()
            if current_length > 0:
                ratio = fixed_length / current_length
                # 保持起点不变，调整终点位置
                dx = end_point.x - start_point.x
                dy = end_point.y - start_point.y
                end_point.x = start_point.x + dx * ratio
                end_point.y = start_point.y + dy * ratio
            
            # 添加到画布
            self.canvas.add_object(line)
            
            # 记录创建的对象
            self.created_objects[name] = line
            
            print(f"创建固定长度线段: {name} 连接 {start_point_name} 和 {end_point_name}, 长度 {fixed_length}")
            return True
            
        except Exception as e:
            print(f"创建固定长度线段时出错: {str(e)}")
            return False
    
    def create_fixed_angle(self, params: Dict[str, Any]) -> bool:
        """创建固定角度"""
        try:
            base_name = params.get("name", f"A{len(self.created_objects) + 1}")
            # 生成唯一名称
            angle_name = self._generate_unique_name(base_name, "angle")
            vertex_name = params.get("vertex")
            point1_name = params.get("point1") 
            point2_name = params.get("point2")
            target_angle = float(params.get("angle", 60))  # 默认60度
            
            # 查找三个点
            vertex_point = self.find_point_by_name(vertex_name)
            point1 = self.find_point_by_name(point1_name)
            point2 = self.find_point_by_name(point2_name)
            
            if not all([vertex_point, point1, point2]):
                print(f"无法找到角度的顶点: {vertex_name}, {point1_name}, {point2_name}")
                return False
            
            # 导入角度类
            try:
                from .oangle import Angle
                
                # 创建角度对象
                angle = Angle(vertex_point, point1, point2, angle_name)
                angle.target_angle = target_angle
                angle.fixed = True
                
                # 立即调整到目标角度（在添加到画布前）
                self._enforce_angle_immediately(angle)
                
                # 添加到画布
                self.canvas.add_object(angle)
                
                # 记录创建的对象
                self.created_objects[angle_name] = angle
                
                print(f"创建固定角度: {angle_name} 在顶点 {vertex_name}, 角度 {target_angle}°")
                return True
                
            except ImportError:
                print("无法导入角度模块")
                return False
            
        except Exception as e:
            print(f"创建固定角度时出错: {str(e)}")
            return False
    
    def _enforce_angle_immediately(self, angle):
        """立即强制角度到目标值，一次性调整"""
        if not angle.target_angle or not all([angle.p1, angle.p2, angle.p3]):
            return
        
        import math
        
        # 计算当前角度
        current_angle = angle.calculate_angle()
        
        # if已经接近目标角度，不需要调整
        if abs(current_angle - angle.target_angle) < 0.5:
            return
        
        # 保持顶点和第一个点不动，调整第三个点
        vertex = angle.p2
        point1 = angle.p1
        point3 = angle.p3
        
        # 计算顶点到第三个点的距离
        distance = math.sqrt((point3.x - vertex.x)**2 + (point3.y - vertex.y)**2)
        
        # 计算第一个点相对于顶点的角度
        ref_angle = math.atan2(point1.y - vertex.y, point1.x - vertex.x)
        
        # 目标角度（弧度）
        target_rad = math.radians(angle.target_angle)
        
        # 计算当前第三个点的角度
        current_p3_angle = math.atan2(point3.y - vertex.y, point3.x - vertex.x)
        
        # 确定应该是顺时针还是逆时针
        angle_diff = current_p3_angle - ref_angle
        while angle_diff < 0:
            angle_diff += 2 * math.pi
        while angle_diff > 2 * math.pi:
            angle_diff -= 2 * math.pi
        
        # 根据当前方向决定新角度
        if angle_diff <= math.pi:
            # 逆时针方向
            new_angle = ref_angle + target_rad
        else:
            # 顺时针方向  
            new_angle = ref_angle - target_rad
        
        # 计算新位置
        new_x = vertex.x + distance * math.cos(new_angle)
        new_y = vertex.y + distance * math.sin(new_angle)
        
        # 一次性设置到准确位置
        point3.x = new_x
        point3.y = new_y
        
        # 保持角度固定状态
        angle.fixed = True
        # 记录初始目标角度
        angle._initial_target = angle.target_angle
        
        print(f"角度{angle.name}已调整到{angle.target_angle}°")
    
    def create_fixed_point(self, params: Dict[str, Any]) -> bool:
        """创建固定位置的点（不可拖动）"""
        try:
            point_name = params.get("point")
            if not point_name:
                print("固定点命令缺少点名称")
                return False
            
            # 查找要固定的点
            point = self.find_point_by_name(point_name)
            if not point:
                print(f"无法找到要固定的点: {point_name}")
                return False
            
            # 设置点为不可拖动
            point.draggable = False
            print(f"固定点位置: {point_name} 在 ({point.x:.1f}, {point.y:.1f})")
            return True
            
        except Exception as e:
            print(f"固定点位置时出错: {str(e)}")
            return False
    
    def get_canvas_info(self) -> Dict[str, Any]:
        """获取画布信息"""
        return {
            "width": self.canvas.width(),
            "height": self.canvas.height(),
            "object_count": len(self.canvas.objects),
            "point_count": len([obj for obj in self.canvas.objects if isinstance(obj, Point)]),
            "line_count": len([obj for obj in self.canvas.objects if isinstance(obj, Line)]),
            "constraint_count": len(self.canvas.constraint_manager.constraints)
        }
