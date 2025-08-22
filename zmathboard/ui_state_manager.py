#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os
import tempfile
import shutil
from typing import Dict, Any, Optional
from datetime import datetime

class UIStateManager:
    """UI状态管理器 - 直接保存和加载UI的完整状态（二进制）"""
    
    def __init__(self, canvas=None):
        self.canvas = canvas
        self.version = "2.0"
        
    def extract_ui_state(self) -> Dict[str, Any]:
        """提取UI的完整状态"""
        if not self.canvas:
            return {}
        
        # 保存所有关键的UI状态
        ui_state = {
            'version': self.version,
            'timestamp': datetime.now().isoformat(),
            'type': 'geometry',  # 标识这是几何图形状态
            
            # 画布基本状态
            'canvas_offset': {
                'x': self.canvas.canvas_offset.x() if hasattr(self.canvas, 'canvas_offset') else 0,
                'y': self.canvas.canvas_offset.y() if hasattr(self.canvas, 'canvas_offset') else 0,
            },
            'zoom_factor': getattr(self.canvas, 'zoom_factor', 1.0),
            'canvas_size': {
                'width': self.canvas.width(),
                'height': self.canvas.height()
            },
            
            # 几何对象（直接序列化对象本身）
            'objects': self.canvas.objects.copy(),
            'selected_object': self.canvas.selected_object,
            'selected_objects': getattr(self.canvas, 'selected_objects', []).copy(),
            
            # 多边形状态
            'active_polygons': getattr(self.canvas, 'active_polygons', []).copy(),
            
            # 交点管理器状态
            'intersection_manager_state': None,
            
            # 绘图工具状态
            'current_tool': getattr(self.canvas, 'current_tool', 'select'),
            'drawing_mode': getattr(self.canvas, 'drawing_mode', False),
            'constraint_mode': getattr(self.canvas, 'constraint_mode', False),
            
            # 其他UI状态
            'snap_enabled': getattr(self.canvas, 'snap_enabled', True),
            'snap_threshold': getattr(self.canvas, 'snap_threshold', 15),
            'grid_visible': getattr(self.canvas, 'grid_visible', False),
            'show_coordinates': getattr(self.canvas, 'show_coordinates', False),
        }
        
        # 保存交点管理器状态
        if hasattr(self.canvas, 'intersection_manager'):
            im = self.canvas.intersection_manager
            ui_state['intersection_manager_state'] = {
                'show_intersections': getattr(im, 'show_intersections', False),
                'intersections': getattr(im, 'intersections', []).copy(),
                'auto_update': getattr(im, 'auto_update', True),
            }
        
        return ui_state
    
    def restore_ui_state(self, ui_state: Dict[str, Any]) -> bool:
        """恢复UI的完整状态"""
        if not self.canvas or not ui_state:
            return False
        
        try:
            # 清空当前状态
            self.canvas.objects.clear()
            self.canvas.selected_object = None
            if hasattr(self.canvas, 'selected_objects'):
                self.canvas.selected_objects.clear()
            if hasattr(self.canvas, 'active_polygons'):
                self.canvas.active_polygons.clear()
            
            # 恢复画布基本状态
            canvas_offset = ui_state.get('canvas_offset', {})
            if hasattr(self.canvas, 'canvas_offset'):
                from PyQt5.QtCore import QPointF
                self.canvas.canvas_offset = QPointF(
                    canvas_offset.get('x', 0),
                    canvas_offset.get('y', 0)
                )
            
            if 'zoom_factor' in ui_state:
                self.canvas.zoom_factor = ui_state['zoom_factor']
            
            # 恢复几何对象
            if 'objects' in ui_state:
                self.canvas.objects = ui_state['objects']
                
            if 'selected_object' in ui_state:
                self.canvas.selected_object = ui_state['selected_object']
                
            if 'selected_objects' in ui_state and hasattr(self.canvas, 'selected_objects'):
                self.canvas.selected_objects = ui_state['selected_objects']
            
            # 恢复多边形状态
            if 'active_polygons' in ui_state and hasattr(self.canvas, 'active_polygons'):
                self.canvas.active_polygons = ui_state['active_polygons']
            
            # 恢复工具状态
            if 'current_tool' in ui_state:
                self.canvas.current_tool = ui_state['current_tool']
                
            if 'drawing_mode' in ui_state:
                self.canvas.drawing_mode = ui_state['drawing_mode']
                
            if 'constraint_mode' in ui_state:
                self.canvas.constraint_mode = ui_state['constraint_mode']
            
            # 恢复其他UI状态
            for attr in ['snap_enabled', 'snap_threshold', 'grid_visible', 'show_coordinates']:
                if attr in ui_state:
                    setattr(self.canvas, attr, ui_state[attr])
            
            # 恢复交点管理器状态
            if 'intersection_manager_state' in ui_state and ui_state['intersection_manager_state']:
                im_state = ui_state['intersection_manager_state']
                if hasattr(self.canvas, 'intersection_manager'):
                    im = self.canvas.intersection_manager
                    for attr, value in im_state.items():
                        if hasattr(im, attr):
                            setattr(im, attr, value)
            
            # 触发重绘
            self.canvas.update()
            
            print(f"UI状态恢复成功，版本: {ui_state.get('version', 'unknown')}")
            print(f"恢复了 {len(ui_state.get('objects', []))} 个对象")
            return True
            
        except Exception as e:
            print(f"恢复UI状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_ui_state(self, filepath: str) -> bool:
        """保存UI状态到二进制文件"""
        try:
            ui_state = self.extract_ui_state()
            
            # 使用pickle保存为二进制文件
            with open(filepath, 'wb') as f:
                pickle.dump(ui_state, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"UI状态已保存到: {filepath}")
            print(f"保存了 {len(ui_state.get('objects', []))} 个对象")
            return True
            
        except Exception as e:
            print(f"保存UI状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_ui_state(self, filepath: str) -> bool:
        """从二进制文件加载UI状态"""
        try:
            if not os.path.exists(filepath):
                print(f"状态文件不存在: {filepath}")
                return False
            
            # 使用pickle加载二进制文件
            with open(filepath, 'rb') as f:
                ui_state = pickle.load(f)
            
            return self.restore_ui_state(ui_state)
            
        except Exception as e:
            print(f"加载UI状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_auto_save_path(self):
        """获取自动保存文件路径"""
        # 获取项目根目录的data文件夹
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        auto_save_dir = os.path.join(current_dir, "data")
        
        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)
            
        return os.path.join(auto_save_dir, "ui_state_autosave.pkl")
    
    def auto_save_ui_state(self) -> bool:
        """自动保存UI状态"""
        try:
            auto_save_path = self.get_auto_save_path()
            return self.save_ui_state(auto_save_path)
        except Exception as e:
            print(f"自动保存UI状态失败: {e}")
            return False
    
    def auto_load_ui_state(self) -> bool:
        """自动加载最后保存的UI状态"""
        try:
            auto_save_path = self.get_auto_save_path()
            if os.path.exists(auto_save_path):
                return self.load_ui_state(auto_save_path)
            return False
        except Exception as e:
            print(f"自动加载UI状态失败: {e}")
            return False
    
    def clear_auto_save(self) -> bool:
        """清除自动保存文件"""
        try:
            auto_save_path = self.get_auto_save_path()
            if os.path.exists(auto_save_path):
                os.remove(auto_save_path)
                print("自动保存的UI状态文件已清除")
                return True
        except Exception as e:
            print(f"清除自动保存UI状态文件失败: {e}")
        return False
