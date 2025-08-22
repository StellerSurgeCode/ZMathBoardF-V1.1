#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import pickle
import os
from datetime import datetime
from typing import Dict, List, Any, Union
import tempfile
import shutil
from PyQt5.QtGui import QColor

class CanvasSerializer:
    """画布序列化器 - 完整保存和加载画布状态"""
    
    def __init__(self, canvas=None):
        self.canvas = canvas
        self.version = "1.0"
        
    def serialize_color(self, color):
        """序列化QColor对象"""
        if isinstance(color, QColor):
            return {
                "type": "QColor",
                "red": color.red(),
                "green": color.green(), 
                "blue": color.blue(),
                "alpha": color.alpha()
            }
        return color
    
    def deserialize_color(self, color_data):
        """反序列化QColor对象"""
        if isinstance(color_data, dict) and color_data.get("type") == "QColor":
            return QColor(color_data["red"], color_data["green"], 
                         color_data["blue"], color_data["alpha"])
        return color_data
    
    def serialize_object(self, obj):
        """序列化单个几何对象"""
        # 获取对象的类名和模块
        obj_type = type(obj).__name__
        obj_module = type(obj).__module__
        
        # 基础数据
        obj_data = {
            "type": obj_type,
            "module": obj_module,
            "name": getattr(obj, 'name', ''),
            "visible": getattr(obj, 'visible', True),
            "selected": getattr(obj, 'selected', False),
            "draggable": getattr(obj, 'draggable', True),
        }
        
        # 需要跳过的属性（避免序列化复杂对象）
        skip_attrs = {
            'animations', 'constraint_manager', 'constraints', 
            'vertices', 'lines', 'parent', 'canvas',
            'style'  # 跳过样式对象，使用默认值
        }
        
        # 序列化安全的属性
        safe_attrs = [
            'x', 'y', 'radius', 'fixed', 'color', 'width', 
            'fixed_length', '_original_length', 'target_angle',
            'fill_color', 'show_fill', 'show_diagonals', 'show_medians',
            'show_heights', 'show_angle_bisectors', 'show_midlines',
            'show_incircle', 'show_circumcircle', 'selected_heights', 'selected_angles',
            'source', 'is_constrained_point', 'exclude_from_intersection'
        ]
        
        for attr_name in safe_attrs:
            if hasattr(obj, attr_name):
                try:
                    attr_value = getattr(obj, attr_name)
                    if isinstance(attr_value, QColor):
                        obj_data[attr_name] = self.serialize_color(attr_value)
                    elif attr_value is None or isinstance(attr_value, (int, float, str, bool, list)):
                        obj_data[attr_name] = attr_value
                    else:
                        # 对于其他类型，尝试转换为基本类型
                        try:
                            if hasattr(attr_value, 'value'):  # 可能是枚举
                                obj_data[attr_name] = attr_value.value
                            else:
                                obj_data[attr_name] = str(attr_value)
                        except:
                            pass
                except Exception as e:
                    print(f"序列化属性 {attr_name} 时出错: {e}")
                    
        # 特殊处理不同对象类型
        if obj_type == "Point":
            obj_data.update({
                "x": float(obj.x),
                "y": float(obj.y),
                "radius": getattr(obj, 'radius', 5),
                "fixed": getattr(obj, 'fixed', False),
            })
            
        elif obj_type == "Line":
            obj_data.update({
                "p1_id": id(obj.p1) if obj.p1 else None,
                "p2_id": id(obj.p2) if obj.p2 else None,
                "width": getattr(obj, 'width', 2),
                "fixed_length": getattr(obj, 'fixed_length', False),
                "_original_length": getattr(obj, '_original_length', None),
            })
            
        elif obj_type == "Angle":
            obj_data.update({
                "p1_id": id(obj.p1) if obj.p1 else None,
                "p2_id": id(obj.p2) if obj.p2 else None,
                "p3_id": id(obj.p3) if obj.p3 else None,
                "fixed": getattr(obj, 'fixed', False),
                "target_angle": getattr(obj, 'target_angle', None),
            })
            
        elif obj_type == "ConstrainedPoint":
            obj_data.update({
                "x": float(obj.x),
                "y": float(obj.y),
                "radius": getattr(obj, 'radius', 5),
                "fixed": getattr(obj, 'fixed', False),
                "is_constrained_point": getattr(obj, 'is_constrained_point', True),
                "exclude_from_intersection": getattr(obj, 'exclude_from_intersection', True),
            })
        
        # 处理多边形对象
        elif hasattr(obj, 'vertices'):
            obj_data.update({
                "vertex_ids": [id(v) for v in obj.vertices] if obj.vertices else [],
                "fill_color": self.serialize_color(getattr(obj, 'fill_color', None)),
                "show_fill": getattr(obj, 'show_fill', False),
                "show_diagonals": getattr(obj, 'show_diagonals', False),
                "show_medians": getattr(obj, 'show_medians', False),
                "show_heights": getattr(obj, 'show_heights', False),
                "show_angle_bisectors": getattr(obj, 'show_angle_bisectors', False),
                "show_midlines": getattr(obj, 'show_midlines', False),
                "show_incircle": getattr(obj, 'show_incircle', False),
                "show_circumcircle": getattr(obj, 'show_circumcircle', False),
                "source": getattr(obj, 'source', 'auto'),
            })
            
        return obj_data
    
    def save_canvas(self, filepath: str) -> bool:
        """保存画布到文件"""
        if not self.canvas:
            print("错误: 没有画布可保存")
            return False
            
        try:
            # 创建对象ID映射
            id_to_index = {}
            objects_data = []
            
            # 第一遍：建立ID映射
            for i, obj in enumerate(self.canvas.objects):
                id_to_index[id(obj)] = i
            
            # 第二遍：序列化所有对象
            for obj in self.canvas.objects:
                obj_data = self.serialize_object(obj)
                obj_data["object_index"] = id_to_index[id(obj)]
                objects_data.append(obj_data)
            
            # 保存约束信息
            constraints_data = []
            if hasattr(self.canvas, 'constraint_manager'):
                for constraint in self.canvas.constraint_manager.constraints:
                    constraint_data = {
                        "type": type(constraint).__name__,
                        "active": getattr(constraint, 'active', True),
                        "constrained_object_id": id(constraint.constrained_object) if hasattr(constraint, 'constrained_object') else None,
                    }
                    
                    # 处理不同约束类型的特殊属性
                    if hasattr(constraint, 'point1'):
                        constraint_data["point1_id"] = id(constraint.point1)
                    if hasattr(constraint, 'point2'):
                        constraint_data["point2_id"] = id(constraint.point2)
                    if hasattr(constraint, 'ratio'):
                        constraint_data["ratio"] = constraint.ratio
                    if hasattr(constraint, 'line'):
                        constraint_data["line_id"] = id(constraint.line)
                        
                    constraints_data.append(constraint_data)
            
            # 保存活跃多边形信息
            active_polygons_data = []
            if hasattr(self.canvas, 'active_polygons'):
                for polygon in self.canvas.active_polygons:
                    if id(polygon) in id_to_index:
                        active_polygons_data.append(id_to_index[id(polygon)])
            
            # 组装完整数据
            canvas_data = {
                "version": self.version,
                "timestamp": datetime.now().isoformat(),
                "canvas_info": {
                    "width": self.canvas.width(),
                    "height": self.canvas.height(),
                    "canvas_offset": {
                        "x": self.canvas.canvas_offset.x() if hasattr(self.canvas, 'canvas_offset') else 0,
                        "y": self.canvas.canvas_offset.y() if hasattr(self.canvas, 'canvas_offset') else 0,
                    }
                },
                "objects": objects_data,
                "constraints": constraints_data,
                "active_polygons": active_polygons_data,
                "id_mapping": id_to_index
            }
            
            # 保存为JSON文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(canvas_data, f, indent=2, ensure_ascii=False)
                
            print(f"画布已保存到: {filepath}")
            print(f"保存了 {len(objects_data)} 个对象和 {len(constraints_data)} 个约束")
            return True
            
        except Exception as e:
            print(f"保存画布时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_canvas(self, filepath: str) -> bool:
        """从文件加载画布"""
        if not self.canvas:
            print("错误: 没有画布可加载")
            return False
            
        if not os.path.exists(filepath):
            print(f"错误: 文件不存在 {filepath}")
            return False
            
        try:
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                canvas_data = json.load(f)
            
            # 检查版本兼容性
            if canvas_data.get("version") != self.version:
                print(f"警告: 文件版本 {canvas_data.get('version')} 与当前版本 {self.version} 不匹配")
            
            # 清空当前画布
            self.canvas.objects.clear()
            if hasattr(self.canvas, 'constraint_manager'):
                self.canvas.constraint_manager.constraints.clear()
            if hasattr(self.canvas, 'active_polygons'):
                self.canvas.active_polygons.clear()
            
            # 重建对象映射
            index_to_object = {}
            
            # 导入必要的类
            from .geometry import Point, Line
            from .oangle import Angle
            from .constraints import ConstrainedPoint, MidpointConstraint, RatioPointConstraint, PerpendicularPointConstraint
            
            # 第一遍：创建所有基础对象
            for obj_data in canvas_data["objects"]:
                obj_type = obj_data["type"]
                obj_index = obj_data["object_index"]
                
                if obj_type == "Point":
                    obj = Point(obj_data["x"], obj_data["y"], obj_data.get("name", ""))
                    obj.radius = obj_data.get("radius", 5)
                    obj.fixed = obj_data.get("fixed", False)
                    
                elif obj_type == "ConstrainedPoint":
                    obj = ConstrainedPoint(obj_data["x"], obj_data["y"], obj_data.get("name", ""))
                    obj.radius = obj_data.get("radius", 5)
                    obj.fixed = obj_data.get("fixed", False)
                    obj.is_constrained_point = obj_data.get("is_constrained_point", True)
                    obj.exclude_from_intersection = obj_data.get("exclude_from_intersection", True)
                    
                elif obj_type == "Line":
                    # 线段需要在第二遍处理，因为需要引用点
                    obj = None
                    
                elif obj_type == "Angle":
                    # 角度需要在第二遍处理，因为需要引用点
                    obj = None
                    
                else:
                    # 尝试动态创建其他类型的对象
                    try:
                        module_name = obj_data.get("module", "zmathboard.geometry")
                        if module_name.startswith("zmathboard."):
                            module = __import__(module_name, fromlist=[obj_type])
                            obj_class = getattr(module, obj_type)
                            obj = obj_class()
                        else:
                            print(f"跳过未知对象类型: {obj_type}")
                            continue
                    except Exception as e:
                        print(f"创建对象 {obj_type} 时出错: {e}")
                        continue
                
                if obj:
                    # 恢复安全的属性
                    safe_restore_attrs = [
                        'name', 'visible', 'selected', 'draggable', 'x', 'y', 'radius', 
                        'fixed', 'color', 'width', 'fixed_length', '_original_length', 
                        'target_angle', 'fill_color', 'show_fill', 'show_diagonals', 
                        'show_medians', 'show_heights', 'show_angle_bisectors', 
                        'show_midlines', 'show_incircle', 'show_circumcircle', 'source',
                        'is_constrained_point', 'exclude_from_intersection'
                    ]
                    
                    for attr_name in safe_restore_attrs:
                        if attr_name in obj_data:
                            try:
                                attr_value = obj_data[attr_name]
                                if attr_name == "color" or attr_name.endswith("_color"):
                                    setattr(obj, attr_name, self.deserialize_color(attr_value))
                                else:
                                    setattr(obj, attr_name, attr_value)
                            except Exception as e:
                                print(f"设置属性 {attr_name} 时出错: {e}")
                    
                    index_to_object[obj_index] = obj
                    self.canvas.objects.append(obj)
            
            # 第二遍：处理引用关系
            for obj_data in canvas_data["objects"]:
                obj_type = obj_data["type"]
                obj_index = obj_data["object_index"]
                
                if obj_type == "Line":
                    p1_id = obj_data.get("p1_id")
                    p2_id = obj_data.get("p2_id")
                    
                    # 通过ID映射找到对应的点
                    p1 = None
                    p2 = None
                    id_mapping = canvas_data["id_mapping"]
                    
                    # 寻找对应的点对象
                    for original_id_str, mapped_index in id_mapping.items():
                        original_id = int(original_id_str)
                        if original_id == p1_id and mapped_index in index_to_object:
                            p1 = index_to_object[mapped_index]
                        if original_id == p2_id and mapped_index in index_to_object:
                            p2 = index_to_object[mapped_index]
                    
                    if p1 and p2:
                        line = Line(p1, p2, obj_data.get("name", ""))
                        line.width = obj_data.get("width", 2)
                        line.fixed_length = obj_data.get("fixed_length", False)
                        line._original_length = obj_data.get("_original_length")
                        
                        # 恢复其他安全属性
                        safe_line_attrs = ['name', 'visible', 'selected', 'draggable', 'color', 'width']
                        for attr_name in safe_line_attrs:
                            if attr_name in obj_data:
                                try:
                                    attr_value = obj_data[attr_name]
                                    if attr_name == "color":
                                        setattr(line, attr_name, self.deserialize_color(attr_value))
                                    else:
                                        setattr(line, attr_name, attr_value)
                                except:
                                    pass
                        
                        # 替换原来的占位符
                        if obj_index < len(self.canvas.objects):
                            self.canvas.objects[obj_index] = line
                            index_to_object[obj_index] = line
                
                elif obj_type == "Angle":
                    p1_id = obj_data.get("p1_id")
                    p2_id = obj_data.get("p2_id")
                    p3_id = obj_data.get("p3_id")
                    
                    # 找到对应的点
                    p1 = p2 = p3 = None
                    id_mapping = canvas_data["id_mapping"]
                    
                    for obj_id_str, idx in id_mapping.items():
                        if int(obj_id_str) == p1_id and idx in index_to_object:
                            p1 = index_to_object[idx]
                        if int(obj_id_str) == p2_id and idx in index_to_object:
                            p2 = index_to_object[idx]
                        if int(obj_id_str) == p3_id and idx in index_to_object:
                            p3 = index_to_object[idx]
                    
                    if p1 and p2 and p3:
                        angle = Angle(p1, p2, p3, obj_data.get("name", ""))
                        angle.fixed = obj_data.get("fixed", False)
                        angle.target_angle = obj_data.get("target_angle")
                        
                        # 恢复其他安全属性
                        safe_angle_attrs = ['name', 'visible', 'selected', 'draggable', 'color']
                        for attr_name in safe_angle_attrs:
                            if attr_name in obj_data:
                                try:
                                    attr_value = obj_data[attr_name]
                                    if attr_name == "color":
                                        setattr(angle, attr_name, self.deserialize_color(attr_value))
                                    else:
                                        setattr(angle, attr_name, attr_value)
                                except:
                                    pass
                        
                        # 替换占位符或添加到列表
                        if obj_index < len(self.canvas.objects):
                            self.canvas.objects[obj_index] = angle
                        else:
                            self.canvas.objects.append(angle)
                        index_to_object[obj_index] = angle
            
            # 清理None对象
            self.canvas.objects = [obj for obj in self.canvas.objects if obj is not None]
            
            # 恢复约束
            if hasattr(self.canvas, 'constraint_manager') and "constraints" in canvas_data:
                for constraint_data in canvas_data["constraints"]:
                    # 这里可以添加约束恢复逻辑
                    # 暂时跳过，因为约束系统比较复杂
                    pass
            
            # 恢复活跃多边形和属性
            if "active_polygons" in canvas_data:
                try:
                    from .draw import PolygonDetector
                    detector = PolygonDetector(self.canvas)
                    detected_polygons = detector.detect_polygons()
                    
                    # 恢复多边形属性
                    saved_polygon_data = []
                    for obj_data in canvas_data["objects"]:
                        if obj_data.get("vertex_ids"):
                            # 这是一个多边形对象，尝试匹配到重新检测的多边形
                            vertex_ids = obj_data["vertex_ids"]
                            
                            # 找到对应的顶点对象
                            vertices = []
                            id_mapping = canvas_data["id_mapping"]
                            for vertex_id in vertex_ids:
                                for original_id_str, mapped_index in id_mapping.items():
                                    if int(original_id_str) == vertex_id and mapped_index in index_to_object:
                                        vertices.append(index_to_object[mapped_index])
                            
                            if len(vertices) == len(vertex_ids):
                                # 在检测到的多边形中找到匹配的
                                for polygon in detected_polygons:
                                    if len(polygon.vertices) == len(vertices):
                                        # 检查顶点是否匹配（使用ID比较避免hash问题）
                                        polygon_vertex_ids = set(id(v) for v in polygon.vertices)
                                        saved_vertex_ids = set(id(v) for v in vertices)
                                        if polygon_vertex_ids == saved_vertex_ids:
                                            # 恢复多边形属性
                                            polygon.fill_color = self.deserialize_color(obj_data.get("fill_color"))
                                            polygon.show_fill = obj_data.get("show_fill", False)
                                            polygon.show_diagonals = obj_data.get("show_diagonals", False)
                                            polygon.show_medians = obj_data.get("show_medians", False)
                                            polygon.show_heights = obj_data.get("show_heights", False)
                                            polygon.show_angle_bisectors = obj_data.get("show_angle_bisectors", False)
                                            polygon.show_midlines = obj_data.get("show_midlines", False)
                                            polygon.show_incircle = obj_data.get("show_incircle", False)
                                            polygon.show_circumcircle = obj_data.get("show_circumcircle", False)
                                            polygon.source = obj_data.get("source", "auto")
                                            
                                            # 恢复其他安全属性
                                            safe_polygon_attrs = [
                                                'name', 'visible', 'selected', 'draggable'
                                            ]
                                            for attr_name in safe_polygon_attrs:
                                                if attr_name in obj_data:
                                                    try:
                                                        setattr(polygon, attr_name, obj_data[attr_name])
                                                    except:
                                                        pass
                                            break
                    
                    self.canvas.active_polygons = detected_polygons
                    
                    # 属性已恢复到多边形对象中
                    
                except Exception as e:
                    print(f"恢复多边形属性时出错: {e}")
                    pass
            
            # 更新画布
            self.canvas.update()
            
            print(f"画布已从 {filepath} 加载")
            print(f"加载了 {len(self.canvas.objects)} 个对象")
            return True
            
        except Exception as e:
            print(f"加载画布时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_auto_save_path(self):
        """获取自动保存文件路径"""
        # 在user临时目录创建自动保存文件
        temp_dir = tempfile.gettempdir()
        auto_save_dir = os.path.join(temp_dir, "zmathboard_autosave")
        
        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)
            
        return os.path.join(auto_save_dir, "canvas_autosave.json")
    
    def auto_save(self):
        """自动保存画布状态"""
        try:
            auto_save_path = self.get_auto_save_path()
            return self.save_canvas(auto_save_path)
        except Exception as e:
            print(f"自动保存失败: {e}")
            return False
    
    def auto_load(self):
        """自动加载最后保存的状态"""
        try:
            auto_save_path = self.get_auto_save_path()
            if os.path.exists(auto_save_path):
                return self.load_canvas(auto_save_path)
            return False
        except Exception as e:
            print(f"自动加载失败: {e}")
            return False
    
    def clear_auto_save(self):
        """清除自动保存文件"""
        try:
            auto_save_path = self.get_auto_save_path()
            if os.path.exists(auto_save_path):
                os.remove(auto_save_path)
                print("自动保存文件已清除")
                return True
        except Exception as e:
            print(f"清除自动保存文件失败: {e}")
        return False
