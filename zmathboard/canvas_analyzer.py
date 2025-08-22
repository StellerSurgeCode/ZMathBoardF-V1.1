#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
画布状态分析器
用于分析当前画布上的几何对象，生成结构化描述
"""

from typing import List, Dict, Any, Optional, Tuple
import json
from .geometry import Point, Line
from .constraints import ConstrainedPoint, MidpointConstraint, RatioPointConstraint, PerpendicularPointConstraint

class CanvasAnalyzer:
    """画布状态分析器"""
    
    def __init__(self, canvas):
        self.canvas = canvas
    
    def analyze_canvas(self) -> Dict[str, Any]:
        """分析画布状态，返回结构化描述"""
        analysis = {
            "summary": self._generate_summary(),
            "objects": self._analyze_objects(),
            "constraints": self._analyze_constraints(),
            "geometric_relations": self._analyze_geometric_relations(),
            "suggestions": self._generate_suggestions()
        }
        return analysis
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成画布概要信息"""
        points = [obj for obj in self.canvas.objects if isinstance(obj, Point)]
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        
        return {
            "total_objects": len(self.canvas.objects),
            "points_count": len(points),
            "lines_count": len(lines),
            "constraints_count": len(self.canvas.constraint_manager.constraints),
            "canvas_size": {
                "width": self.canvas.width(),
                "height": self.canvas.height()
            }
        }
    
    def _analyze_objects(self) -> List[Dict[str, Any]]:
        """分析所有几何对象"""
        objects_info = []
        
        for obj in self.canvas.objects:
            if isinstance(obj, Point):
                obj_info = {
                    "type": "point",
                    "name": obj.name,
                    "position": {"x": round(obj.x, 2), "y": round(obj.y, 2)},
                    "color": obj.color.name(),
                    "fixed": getattr(obj, 'fixed', False),
                    "constrained": isinstance(obj, ConstrainedPoint) and len(obj.constraints) > 0
                }
                objects_info.append(obj_info)
                
            elif isinstance(obj, Line):
                obj_info = {
                    "type": "line",
                    "name": obj.name,
                    "start_point": obj.p1.name,
                    "end_point": obj.p2.name,
                    "length": round(obj.length(), 2),
                    "color": obj.color.name(),
                    "width": obj.width,
                    "fixed_length": getattr(obj, 'fixed_length', False)
                }
                objects_info.append(obj_info)
        
        return objects_info
    
    def _analyze_constraints(self) -> List[Dict[str, Any]]:
        """分析约束关系"""
        constraints_info = []
        
        for constraint in self.canvas.constraint_manager.constraints:
            if isinstance(constraint, MidpointConstraint):
                constraint_info = {
                    "type": "midpoint",
                    "description": constraint.get_description(),
                    "constrained_point": constraint.point.name,
                    "reference_line": constraint.line.name
                }
            elif isinstance(constraint, RatioPointConstraint):
                constraint_info = {
                    "type": "ratio_point",
                    "description": constraint.get_description(),
                    "constrained_point": constraint.point.name,
                    "reference_line": constraint.line.name,
                    "ratio": constraint.ratio
                }
            elif isinstance(constraint, PerpendicularPointConstraint):
                constraint_info = {
                    "type": "perpendicular_foot",
                    "description": constraint.get_description(),
                    "foot_point": constraint.foot_point.name,
                    "source_point": constraint.source_point.name,
                    "reference_line": constraint.line.name
                }
            else:
                constraint_info = {
                    "type": "unknown",
                    "description": constraint.get_description()
                }
            
            constraints_info.append(constraint_info)
        
        return constraints_info
    
    def _analyze_geometric_relations(self) -> List[Dict[str, Any]]:
        """分析几何关系"""
        relations = []
        
        # 分析三角形
        triangles = self._find_triangles()
        for triangle in triangles:
            relations.append({
                "type": "triangle",
                "vertices": triangle,
                "description": f"三角形由点{', '.join(triangle)}组成"
            })
        
        # 分析平行线
        parallel_lines = self._find_parallel_lines()
        for pair in parallel_lines:
            relations.append({
                "type": "parallel_lines",
                "lines": pair,
                "description": f"线段{pair[0]}与{pair[1]}平行"
            })
        
        # 分析垂直线
        perpendicular_lines = self._find_perpendicular_lines()
        for pair in perpendicular_lines:
            relations.append({
                "type": "perpendicular_lines",
                "lines": pair,
                "description": f"线段{pair[0]}与{pair[1]}垂直"
            })
        
        return relations
    
    def _find_triangles(self) -> List[List[str]]:
        """查找三角形"""
        points = [obj for obj in self.canvas.objects if isinstance(obj, Point)]
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        
        triangles = []
        
        # 检查每三个点是否形成三角形
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                for k in range(j + 1, len(points)):
                    p1, p2, p3 = points[i], points[j], points[k]
                    
                    # 检查是否有三条边连接这三个点
                    edges = []
                    for line in lines:
                        if (line.p1 == p1 and line.p2 == p2) or (line.p1 == p2 and line.p2 == p1):
                            edges.append((p1.name, p2.name))
                        elif (line.p1 == p1 and line.p2 == p3) or (line.p1 == p3 and line.p2 == p1):
                            edges.append((p1.name, p3.name))
                        elif (line.p1 == p2 and line.p2 == p3) or (line.p1 == p3 and line.p2 == p2):
                            edges.append((p2.name, p3.name))
                    
                    if len(edges) >= 3:  # 形成三角形
                        triangle = sorted([p1.name, p2.name, p3.name])
                        if triangle not in triangles:
                            triangles.append(triangle)
        
        return triangles
    
    def _find_parallel_lines(self) -> List[Tuple[str, str]]:
        """查找平行线"""
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        parallel_pairs = []
        
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                line1, line2 = lines[i], lines[j]
                
                # 计算斜率
                slope1 = self._calculate_slope(line1)
                slope2 = self._calculate_slope(line2)
                
                # 检查是否平行（斜率相等，容差0.01）
                if slope1 is not None and slope2 is not None:
                    if abs(slope1 - slope2) < 0.01:
                        parallel_pairs.append((line1.name, line2.name))
                elif slope1 is None and slope2 is None:  # 都是垂直线
                    parallel_pairs.append((line1.name, line2.name))
        
        return parallel_pairs
    
    def _find_perpendicular_lines(self) -> List[Tuple[str, str]]:
        """查找垂直线"""
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        perpendicular_pairs = []
        
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                line1, line2 = lines[i], lines[j]
                
                # 计算斜率
                slope1 = self._calculate_slope(line1)
                slope2 = self._calculate_slope(line2)
                
                # 检查是否垂直
                if slope1 is not None and slope2 is not None:
                    if abs(slope1 * slope2 + 1) < 0.01:  # 斜率乘积为-1
                        perpendicular_pairs.append((line1.name, line2.name))
                elif (slope1 is None and slope2 == 0) or (slope2 is None and slope1 == 0):
                    # 一条垂直线，一条水平线
                    perpendicular_pairs.append((line1.name, line2.name))
        
        return perpendicular_pairs
    
    def _calculate_slope(self, line: Line) -> Optional[float]:
        """计算线段斜率"""
        dx = line.p2.x - line.p1.x
        dy = line.p2.y - line.p1.y
        
        if abs(dx) < 1e-6:  # 垂直线
            return None
        
        return dy / dx
    
    def _generate_suggestions(self) -> List[str]:
        """生成操作建议"""
        suggestions = []
        
        points = [obj for obj in self.canvas.objects if isinstance(obj, Point)]
        lines = [obj for obj in self.canvas.objects if isinstance(obj, Line)]
        
        # 基于当前状态提供建议
        if len(points) >= 2 and len(lines) == 0:
            suggestions.append("您可以连接这些点创建线段")
        
        if len(points) >= 3:
            triangles = self._find_triangles()
            if len(triangles) == 0:
                suggestions.append("您可以创建三角形")
            else:
                suggestions.append("您可以为三角形添加中点、高线或中线")
        
        if len(lines) >= 1:
            suggestions.append("您可以为线段添加中点或比例点")
            if len(lines) >= 2:
                suggestions.append("您可以查找线段的交点")
        
        if len(self.canvas.constraint_manager.constraints) == 0 and len(lines) > 0:
            suggestions.append("您可以添加约束关系，如中点、比例点等")
        
        return suggestions
    
    def export_to_json(self) -> str:
        """导出分析结果为JSON格式"""
        analysis = self.analyze_canvas()
        return json.dumps(analysis, ensure_ascii=False, indent=2)
    
    def generate_context_description(self) -> str:
        """生成用于AI的上下文描述"""
        analysis = self.analyze_canvas()
        
        description = "当前画布状态：\n\n"
        
        # 概要信息
        summary = analysis["summary"]
        description += f"画布大小：{summary['canvas_size']['width']}x{summary['canvas_size']['height']}\n"
        description += f"总对象数：{summary['total_objects']}\n"
        description += f"点的数量：{summary['points_count']}\n"
        description += f"线段数量：{summary['lines_count']}\n"
        description += f"约束数量：{summary['constraints_count']}\n\n"
        
        # 对象详情
        if analysis["objects"]:
            description += "现有对象：\n"
            for obj in analysis["objects"]:
                if obj["type"] == "point":
                    description += f"- 点{obj['name']}: 坐标({obj['position']['x']}, {obj['position']['y']})"
                    if obj["fixed"]:
                        description += " [固定]"
                    if obj["constrained"]:
                        description += " [有约束]"
                    description += "\n"
                elif obj["type"] == "line":
                    description += f"- 线段{obj['name']}: 连接{obj['start_point']}到{obj['end_point']}, 长度{obj['length']}"
                    if obj["fixed_length"]:
                        description += " [固定长度]"
                    description += "\n"
        
        # 约束关系
        if analysis["constraints"]:
            description += "\n约束关系：\n"
            for constraint in analysis["constraints"]:
                description += f"- {constraint['description']}\n"
        
        # 几何关系
        if analysis["geometric_relations"]:
            description += "\n几何关系：\n"
            for relation in analysis["geometric_relations"]:
                description += f"- {relation['description']}\n"
        
        # 建议
        if analysis["suggestions"]:
            description += "\n操作建议：\n"
            for suggestion in analysis["suggestions"]:
                description += f"- {suggestion}\n"
        
        return description
