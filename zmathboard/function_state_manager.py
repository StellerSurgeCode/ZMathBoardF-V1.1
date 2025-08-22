#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from PyQt5.QtGui import QColor

from .function_plotter import FunctionExpression, FunctionCanvas

class FunctionStateManager:
    """函数图像状态管理器"""
    
    def __init__(self, function_canvas: FunctionCanvas = None):
        self.function_canvas = function_canvas
        self.version = "1.0"
    
    def extract_function_state(self) -> Dict[str, Any]:
        """提取函数图像状态"""
        if not self.function_canvas:
            return {}
        
        # 序列化函数表达式
        functions_data = []
        for func in self.function_canvas.functions:
            func_data = {
                'expression': func.expression,
                'color': {
                    'r': func.color.red(),
                    'g': func.color.green(),
                    'b': func.color.blue(),
                    'a': func.color.alpha()
                },
                'x_min': func.x_min,
                'x_max': func.x_max,
                'visible': func.visible,
                'name': func.name,
                'line_width': func.line_width
            }
            functions_data.append(func_data)
        
        function_state = {
            'version': self.version,
            'timestamp': datetime.now().isoformat(),
            'type': 'function',  # 标识这是函数图像状态
            
            # 函数列表
            'functions': functions_data,
            'selected_function_index': None,
            
            # 画布视图状态
            'view_range': {
                'x_min': self.function_canvas.x_min,
                'x_max': self.function_canvas.x_max,
                'y_min': self.function_canvas.y_min,
                'y_max': self.function_canvas.y_max
            },
            'zoom_factor': getattr(self.function_canvas, 'zoom_factor', 1.0),
            'offset_x': getattr(self.function_canvas, 'offset_x', 0.0),
            'offset_y': getattr(self.function_canvas, 'offset_y', 0.0),
            
            # 显示设置
            'show_grid': self.function_canvas.show_grid,
            'show_axes': self.function_canvas.show_axes,
            'grid_color': {
                'r': self.function_canvas.grid_color.red(),
                'g': self.function_canvas.grid_color.green(),
                'b': self.function_canvas.grid_color.blue(),
                'a': self.function_canvas.grid_color.alpha()
            },
            'axes_color': {
                'r': self.function_canvas.axes_color.red(),
                'g': self.function_canvas.axes_color.green(),
                'b': self.function_canvas.axes_color.blue(),
                'a': self.function_canvas.axes_color.alpha()
            }
        }
        
        # 记录选中的函数
        if self.function_canvas.selected_function:
            for i, func in enumerate(self.function_canvas.functions):
                if func == self.function_canvas.selected_function:
                    function_state['selected_function_index'] = i
                    break
        
        return function_state
    
    def restore_function_state(self, function_state: Dict[str, Any]) -> bool:
        """恢复函数图像状态"""
        if not self.function_canvas or not function_state:
            return False
        
        try:
            # 检查状态类型
            if function_state.get('type') != 'function':
                print(f"错误: 尝试加载非函数图像状态，类型: {function_state.get('type', 'unknown')}")
                return False
            
            # 清除当前函数
            self.function_canvas.clear_functions()
            
            # 恢复函数列表
            functions_data = function_state.get('functions', [])
            for func_data in functions_data:
                try:
                    # 恢复颜色
                    color_data = func_data.get('color', {'r': 0, 'g': 100, 'b': 200, 'a': 255})
                    color = QColor(
                        color_data.get('r', 0),
                        color_data.get('g', 100),
                        color_data.get('b', 200),
                        color_data.get('a', 255)
                    )
                    
                    # 创建函数表达式
                    func = FunctionExpression(
                        func_data.get('expression', 'x'),
                        color,
                        func_data.get('x_min', -10),
                        func_data.get('x_max', 10)
                    )
                    
                    # 恢复其他属性
                    func.visible = func_data.get('visible', True)
                    func.name = func_data.get('name', f"f(x) = {func.expression}")
                    func.line_width = func_data.get('line_width', 2)
                    
                    # 添加到画布
                    if func.is_valid_expression():
                        self.function_canvas.functions.append(func)
                        func.calculate_points()
                    
                except Exception as e:
                    print(f"恢复函数时出错: {e}")
                    continue
            
            # 恢复视图范围
            view_range = function_state.get('view_range', {})
            if view_range:
                self.function_canvas.set_view_range(
                    view_range.get('x_min', -10),
                    view_range.get('x_max', 10),
                    view_range.get('y_min', -10),
                    view_range.get('y_max', 10)
                )
            
            # 恢复其他属性
            self.function_canvas.zoom_factor = function_state.get('zoom_factor', 1.0)
            self.function_canvas.offset_x = function_state.get('offset_x', 0.0)
            self.function_canvas.offset_y = function_state.get('offset_y', 0.0)
            
            # 恢复显示设置
            self.function_canvas.show_grid = function_state.get('show_grid', True)
            self.function_canvas.show_axes = function_state.get('show_axes', True)
            
            # 恢复颜色
            grid_color_data = function_state.get('grid_color', {'r': 200, 'g': 200, 'b': 200, 'a': 255})
            self.function_canvas.grid_color = QColor(
                grid_color_data.get('r', 200),
                grid_color_data.get('g', 200),
                grid_color_data.get('b', 200),
                grid_color_data.get('a', 255)
            )
            
            axes_color_data = function_state.get('axes_color', {'r': 0, 'g': 0, 'b': 0, 'a': 255})
            self.function_canvas.axes_color = QColor(
                axes_color_data.get('r', 0),
                axes_color_data.get('g', 0),
                axes_color_data.get('b', 0),
                axes_color_data.get('a', 255)
            )
            
            # 恢复选中状态
            selected_index = function_state.get('selected_function_index')
            if selected_index is not None and 0 <= selected_index < len(self.function_canvas.functions):
                self.function_canvas.selected_function = self.function_canvas.functions[selected_index]
            else:
                self.function_canvas.selected_function = None
            
            # 更新画布
            self.function_canvas.update()
            
            print(f"函数图像状态恢复成功，版本: {function_state.get('version', 'unknown')}")
            print(f"恢复了 {len(self.function_canvas.functions)} 个函数")
            return True
            
        except Exception as e:
            print(f"恢复函数图像状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_function_state(self, filepath: str) -> bool:
        """保存函数图像状态到文件"""
        try:
            function_state = self.extract_function_state()
            
            with open(filepath, 'wb') as f:
                pickle.dump(function_state, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            print(f"函数图像状态已保存到: {filepath}")
            print(f"保存了 {len(function_state.get('functions', []))} 个函数")
            return True
            
        except Exception as e:
            print(f"保存函数图像状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_function_state(self, filepath: str) -> bool:
        """从文件加载函数图像状态"""
        try:
            if not os.path.exists(filepath):
                print(f"状态文件不存在: {filepath}")
                return False
            
            with open(filepath, 'rb') as f:
                function_state = pickle.load(f)
            
            return self.restore_function_state(function_state)
            
        except Exception as e:
            print(f"加载函数图像状态时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_function_auto_save_path(self):
        """获取函数图像自动保存文件路径"""
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        auto_save_dir = os.path.join(current_dir, "data")
        
        if not os.path.exists(auto_save_dir):
            os.makedirs(auto_save_dir)
            
        return os.path.join(auto_save_dir, "function_state_autosave.pkl")
    
    def auto_save_function_state(self) -> bool:
        """自动保存函数图像状态"""
        try:
            auto_save_path = self.get_function_auto_save_path()
            return self.save_function_state(auto_save_path)
        except Exception as e:
            print(f"自动保存函数图像状态失败: {e}")
            return False
    
    def auto_load_function_state(self) -> bool:
        """自动加载最后保存的函数图像状态"""
        try:
            auto_save_path = self.get_function_auto_save_path()
            if os.path.exists(auto_save_path):
                return self.load_function_state(auto_save_path)
            return False
        except Exception as e:
            print(f"自动加载函数图像状态失败: {e}")
            return False

def detect_state_type(filepath: str) -> Optional[str]:
    """检测状态文件的类型"""
    try:
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        # 检查状态类型标识
        state_type = state.get('type')
        if state_type in ['function', 'geometry']:
            return state_type
        
        # 根据内容推断类型
        if 'functions' in state:
            return 'function'
        elif 'objects' in state:
            return 'geometry'
        
        return 'unknown'
        
    except Exception as e:
        print(f"检测状态文件类型时出错: {e}")
        return None
