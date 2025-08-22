#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QProgressBar, QGroupBox
from .geometry import Point, Line


class AdvancedAnimationManager(QObject):
    """高级动画管理器，管理复杂的动画配置和播放"""
    
    animation_started = pyqtSignal()
    animation_paused = pyqtSignal()
    animation_stopped = pyqtSignal()
    animation_finished = pyqtSignal()
    position_updated = pyqtSignal(dict, dict)  # length_values, area_values
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.animation_config = None
        self.is_playing = False
        self.is_paused = False
        self.current_step = 0
        self.total_steps = 100  # 默认100步
        self.direction = 1  # 1正向，-1反向（用于来回播放）
        
        # 定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animation_step)
        self.timer.setInterval(50)  # 默认20fps
        
        # 路径相关
        self.path_segments = []  # 路径线段列表
        self.segment_lengths = []  # 每段长度
        self.total_path_length = 0  # 总路径长度
        self.cumulative_lengths = []  # 累积长度
        
    def set_animation_config(self, config):
        """设置动画配置"""
        self.animation_config = config
        # 保护动画中使用的对象，防止被系统清理
        self.protect_animation_objects()
        self.prepare_animation()
        
    def protect_animation_objects(self):
        """保护动画中的对象，防止被系统清理"""
        if not self.animation_config:
            return
            
        protected_points = set()
        
        # 标记移动点为受保护状态
        moving_points = self.animation_config.get('moving_points', [])
        for index, point in moving_points:
            if hasattr(point, '__dict__'):
                point._animation_protected = True
                protected_points.add(point)
                print(f"保护移动点 {index}")
                
        # 标记路径点为受保护状态
        path_points = self.animation_config.get('path_points', [])
        for index, point in path_points:
            if hasattr(point, '__dict__'):
                point._animation_protected = True
                protected_points.add(point)
                print(f"保护路径点 {index}")
                
        # 保护连接受保护点的所有线段
        for obj in self.canvas.objects:
            if hasattr(obj, 'p1') and hasattr(obj, 'p2'):  # 这是一条线
                if obj.p1 in protected_points or obj.p2 in protected_points:
                    obj._animation_protected = True
                    print(f"保护连接线: {getattr(obj, 'name', 'Unknown')}")
        
    def prepare_animation(self):
        """准备动画数据"""
        if not self.animation_config:
            return
            
        # 根据运动类型准备数据
        motion_type = self.animation_config.get('motion_type', 'path')
        
        if motion_type == 'path':
            # 计算路径
            self.calculate_path()
        elif motion_type == 'circular':
            # 准备圆周运动数据
            self.prepare_circular_motion()
        
        # 设置动画参数
        duration = self.animation_config.get('duration', 1000)
        fps = 20  # 固定20fps
        self.total_steps = int(duration / 1000 * fps)
        self.timer.setInterval(int(1000 / fps))
        
    def calculate_path(self):
        """计算路径信息"""
        self.path_segments.clear()
        self.segment_lengths.clear()
        self.cumulative_lengths.clear()
        
        path_lines = self.animation_config.get('path_lines', [])
        if not path_lines:
            return
            
        total_length = 0
        for point1, point2 in path_lines:
            # 确保点对象有效且有坐标属性
            if (hasattr(point1, 'x') and hasattr(point1, 'y') and 
                hasattr(point2, 'x') and hasattr(point2, 'y')):
                # 计算线段长度
                dx = point2.x - point1.x
                dy = point2.y - point1.y
                length = math.sqrt(dx*dx + dy*dy)
                
                self.path_segments.append((point1, point2))
                self.segment_lengths.append(length)
                self.cumulative_lengths.append(total_length)
                total_length += length
            
        self.total_path_length = total_length
        
    def prepare_circular_motion(self):
        """准备圆周运动数据"""
        circular_settings = self.animation_config.get('circular_settings')
        if not circular_settings:
            return
            
        # 计算圆心到移动点的距离作为半径
        center_index, center_point = circular_settings['center_point']
        moving_points = self.animation_config.get('moving_points', [])
        
        if moving_points:
            # 使用第一个移动点来计算半径
            _, moving_point = moving_points[0]
            radius = math.sqrt(
                (moving_point.x - center_point.x) ** 2 + 
                (moving_point.y - center_point.y) ** 2
            )
        else:
            radius = 50.0  # 默认半径
            
        # 保存圆周运动参数
        self.circular_motion = {
            'center_point': circular_settings['center_point'],
            'radius': radius,
            'angular_speed': circular_settings['angular_speed'],
            'start_angle': circular_settings['start_angle'],
            'direction': circular_settings['direction']
        }
        print(f"准备圆周运动: 半径={self.circular_motion['radius']:.1f}, 角速度={self.circular_motion['angular_speed']:.2f}")
        
    def get_position_on_path(self, progress):
        """根据进度获取路径上的位置
        
        参数:
        - progress: 0.0到1.0的进度值
        
        返回:
        - (x, y): 路径上的坐标
        """
        if not self.path_segments or self.total_path_length == 0:
            return 0, 0
            
        # 计算目标距离
        target_distance = progress * self.total_path_length
        
        # 找到对应的线段
        for i, (cumulative_length, segment_length) in enumerate(zip(self.cumulative_lengths, self.segment_lengths)):
            if target_distance <= cumulative_length + segment_length:
                # 在这个线段上
                point1, point2 = self.path_segments[i]
                
                if segment_length == 0:
                    return point1.x, point1.y
                    
                # 计算在线段上的位置
                segment_progress = (target_distance - cumulative_length) / segment_length
                x = point1.x + segment_progress * (point2.x - point1.x)
                y = point1.y + segment_progress * (point2.y - point1.y)
                return x, y
                
        # if到达路径末端
        if self.path_segments:
            last_point = self.path_segments[-1][1]
            return last_point.x, last_point.y
            
        return 0, 0
        
    def get_position_on_circle(self, progress):
        """根据进度获取圆周上的位置
        
        参数:
        - progress: 0.0到1.0的进度值
        
        返回:
        - (x, y): 圆周上的坐标
        """
        if not hasattr(self, 'circular_motion'):
            return 0, 0
            
        # 获取圆心坐标
        center_index, center_point = self.circular_motion['center_point']
        center_x = center_point.x
        center_y = center_point.y
        
        # 计算当前角度
        radius = self.circular_motion['radius']
        angular_speed = self.circular_motion['angular_speed']
        start_angle = self.circular_motion['start_angle']
        direction = self.circular_motion['direction']
        
        # 角度随时间变化，progress表示时间进度
        # 这里让一个完整周期对应2π弧度
        total_angle = 2 * math.pi * progress
        current_angle = start_angle + direction * total_angle
        
        # 计算圆周上的位置
        x = center_x + radius * math.cos(current_angle)
        y = center_y + radius * math.sin(current_angle)
        
        return x, y
        
    def calculate_measurements(self):
        """计算当前的测量值"""
        length_values = {}
        area_values = {}
        
        # 计算长度测量
        for measurement in self.animation_config.get('length_measurements', []):
            name = measurement['name']
            _, point1 = measurement['point1']
            _, point2 = measurement['point2']
            
            dx = point2.x - point1.x
            dy = point2.y - point1.y
            length = math.sqrt(dx*dx + dy*dy)
            length_values[name] = length
            
        # 计算面积测量
        for measurement in self.animation_config.get('area_measurements', []):
            name = measurement['name']
            points = [point for _, point in measurement['points']]
            
            if len(points) >= 3:
                area = self.calculate_polygon_area(points)
                area_values[name] = area
                
        return length_values, area_values
        
    def calculate_polygon_area(self, points):
        """计算多边形面积（使用鞋带公式）"""
        if len(points) < 3:
            return 0
            
        area = 0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i].x * points[j].y
            area -= points[j].x * points[i].y
            
        return abs(area) / 2
        
    def start_animation(self):
        """开始动画"""
        if not self.animation_config:
            return
            
        self.is_playing = True
        self.is_paused = False
        self.timer.start()
        self.animation_started.emit()
        
    def pause_animation(self):
        """暂停动画"""
        if self.is_playing:
            self.is_paused = True
            self.timer.stop()
            self.animation_paused.emit()
            
    def resume_animation(self):
        """恢复动画"""
        if self.is_paused:
            self.is_paused = False
            self.timer.start()
            self.animation_started.emit()
            
    def stop_animation(self):
        """停止动画"""
        self.is_playing = False
        self.is_paused = False
        self.timer.stop()
        self.current_step = 0
        self.direction = 1
        self.animation_stopped.emit()
        
        # 重置点位置到起始位置
        self.reset_points_to_start()
        
        # 延迟移除保护标记，给重置操作一些时间
        QTimer.singleShot(500, self.unprotect_animation_objects)
        
    def unprotect_animation_objects(self):
        """移除动画对象的保护标记"""
        if not self.animation_config:
            return
            
        # 移除所有受保护对象的标记
        for obj in self.canvas.objects:
            if hasattr(obj, '_animation_protected'):
                delattr(obj, '_animation_protected')
                obj_name = getattr(obj, 'name', 'Unknown')
                obj_type = type(obj).__name__
                print(f"移除{obj_type} {obj_name} 的保护")
        
    def reset_points_to_start(self):
        """重置移动点到原始位置，路径点保持不动"""
        if not self.animation_config:
            return
            
        try:
            # 只重置移动点，不重置路径点
            moving_points = self.animation_config.get('moving_points', [])
            print(f"重置 {len(moving_points)} 个移动点到原始位置")
            
            for index, point in moving_points:
                # 确保点仍然存在于画布中
                if point not in self.canvas.objects:
                    print(f"警告: 重置时发现点 {index} 已不在画布中")
                    continue
                    
                if hasattr(point, 'x') and hasattr(point, 'y'):
                    # 优先使用原始位置
                    if hasattr(point, '_original_x') and hasattr(point, '_original_y'):
                        old_x, old_y = point.x, point.y
                        point.x = point._original_x
                        point.y = point._original_y
                        print(f"移动点 {index} 从 ({old_x:.2f}, {old_y:.2f}) 重置到原始位置 ({point.x:.2f}, {point.y:.2f})")
                        # 删除原始位置标记
                        delattr(point, '_original_x')
                        delattr(point, '_original_y')
                    else:
                        print(f"移动点 {index} 没有保存的原始位置，保持当前位置")
                    
            self.canvas.update()
            print("移动点位置重置完成")
            
        except Exception as e:
            print(f"重置点位置时发生错误: {e}")
            # 即使重置失败，也要确保画布更新
            self.canvas.update()
        
    def animation_step(self):
        """动画步进"""
        if not self.is_playing or self.is_paused:
            return
            
        try:
            # 验证动画配置和移动点是否仍然有效
            if not self.validate_animation_objects():
                print("动画对象无效，停止动画")
                self.stop_animation()
                return
                
            # 计算当前进度
            progress = self.current_step / max(1, self.total_steps - 1)
            
            # 更新移动点位置
            self.update_moving_points(progress)
            
            # 计算测量值
            length_values, area_values = self.calculate_measurements()
            
            # 发送位置更新信号
            self.position_updated.emit(length_values, area_values)
            
            # 更新画布
            self.canvas.update()
            
            # 检查是否完成
            playback_mode = self.animation_config.get('playback_mode', 'single')
            
            if playback_mode == 'single':
                # 单次播放
                self.current_step += 1
                if self.current_step >= self.total_steps:
                    self.finish_animation()
                    
            elif playback_mode == 'loop':
                # 循环播放
                self.current_step += 1
                if self.current_step >= self.total_steps:
                    self.current_step = 0
                    
            elif playback_mode == 'pingpong':
                # 来回播放
                self.current_step += self.direction
                if self.current_step >= self.total_steps - 1:
                    self.direction = -1
                elif self.current_step <= 0:
                    self.direction = 1
                    
        except Exception as e:
            print(f"动画步进过程中发生错误: {e}")
            self.stop_animation()
            
    def validate_animation_objects(self):
        """验证动画对象是否仍然有效"""
        if not self.animation_config:
            return False
            
        valid = True
        
        # 检查移动点是否仍然存在
        moving_points = self.animation_config.get('moving_points', [])
        valid_moving_points = []
        for index, point in moving_points:
            if point in self.canvas.objects:
                valid_moving_points.append((index, point))
            else:
                print(f"移动点 {index} 不再存在于画布中")
                valid = False
                
        # 检查特定运动类型的对象
        motion_type = self.animation_config.get('motion_type', 'path')
        
        if motion_type == 'path':
            # 检查路径点是否仍然存在
            path_points = self.animation_config.get('path_points', [])
            valid_path_points = []
            for index, point in path_points:
                if point in self.canvas.objects:
                    valid_path_points.append((index, point))
                else:
                    print(f"路径点 {index} 不再存在于画布中")
                    valid = False
                    
            # if有部分对象丢失，更新配置以移除无效对象
            if not valid:
                self.animation_config['moving_points'] = valid_moving_points
                self.animation_config['path_points'] = valid_path_points
                # 重新计算路径
                if valid_moving_points and valid_path_points:
                    self.calculate_path()
                    print("已移除无效对象，继续动画")
                    return True
                else:
                    print("所有关键对象都已丢失，停止动画")
                    return False
                    
        elif motion_type == 'circular':
            # 检查圆心是否仍然存在
            circular_settings = self.animation_config.get('circular_settings')
            if circular_settings:
                center_index, center_point = circular_settings['center_point']
                if center_point not in self.canvas.objects:
                    print(f"圆心点 {center_index} 不再存在于画布中")
                    valid = False
                    
            if not valid:
                self.animation_config['moving_points'] = valid_moving_points
                if valid_moving_points:
                    print("已移除无效对象，但圆心丢失，停止动画")
                    return False
                else:
                    print("所有关键对象都已丢失，停止动画")
                    return False
                
        return True
                
    def update_moving_points(self, progress):
        """更新移动点位置"""
        if not self.animation_config:
            return
            
        moving_points = self.animation_config.get('moving_points', [])
        if not moving_points:
            return
            
        # 根据运动类型获取位置
        motion_type = self.animation_config.get('motion_type', 'path')
        
        if motion_type == 'path':
            x, y = self.get_position_on_path(progress)
        elif motion_type == 'circular':
            x, y = self.get_position_on_circle(progress)
        else:
            x, y = 0, 0
        
        # 更新所有移动点的位置
        for index, point in moving_points:
            # 验证点是否仍然存在于画布中
            if point not in self.canvas.objects:
                print(f"警告: 移动点 {index} 已从画布中移除")
                continue
                
            if hasattr(point, 'x') and hasattr(point, 'y'):
                # 保存原始坐标（用于重置）
                if not hasattr(point, '_original_x'):
                    point._original_x = point.x
                    point._original_y = point.y
                    print(f"保存点 {index} 的原始位置: ({point._original_x}, {point._original_y})")
                # 更新位置
                point.x = x
                point.y = y
            
    def finish_animation(self):
        """完成动画"""
        self.stop_animation()
        self.animation_finished.emit()
        
    def set_speed(self, speed_multiplier):
        """设置播放速度"""
        base_interval = 50  # 基础间隔(ms)
        new_interval = int(base_interval / speed_multiplier)
        new_interval = max(10, min(1000, new_interval))  # 限制范围
        self.timer.setInterval(new_interval)


class AnimationControlWidget(QWidget):
    """动画控制界面组件"""
    
    def __init__(self, animation_manager, chart_display=None, parent=None):
        super().__init__(parent)
        self.animation_manager = animation_manager
        self.chart_display = chart_display
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """设置user界面"""
        layout = QVBoxLayout(self)
        
        # 控制按钮组
        control_group = QGroupBox("动画控制")
        control_layout = QHBoxLayout(control_group)
        
        self.play_pause_btn = QPushButton("播放")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        control_layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_animation)
        control_layout.addWidget(self.stop_btn)
        
        layout.addWidget(control_group)
        
        # 进度显示
        progress_group = QGroupBox("播放进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("进度: 0/100")
        progress_layout.addWidget(self.progress_label)
        
        layout.addWidget(progress_group)
        
        # 状态显示
        status_group = QGroupBox("动画状态")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("状态: 停止")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
    def connect_signals(self):
        """连接信号"""
        self.animation_manager.animation_started.connect(self.on_animation_started)
        self.animation_manager.animation_paused.connect(self.on_animation_paused)
        self.animation_manager.animation_stopped.connect(self.on_animation_stopped)
        self.animation_manager.animation_finished.connect(self.on_animation_finished)
        self.animation_manager.position_updated.connect(self.on_position_updated)
        
        # 连接定时器更新进度
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.start(100)  # 每100ms更新一次
        
    def toggle_play_pause(self):
        """切换播放/暂停"""
        if self.animation_manager.is_playing and not self.animation_manager.is_paused:
            self.animation_manager.pause_animation()
        else:
            if self.animation_manager.is_paused:
                self.animation_manager.resume_animation()
            else:
                self.animation_manager.start_animation()
                
    def stop_animation(self):
        """停止动画"""
        self.animation_manager.stop_animation()
        
    def update_progress(self):
        """更新进度显示"""
        if self.animation_manager.animation_config:
            progress = int(self.animation_manager.current_step / max(1, self.animation_manager.total_steps - 1) * 100)
            self.progress_bar.setValue(progress)
            self.progress_label.setText(f"进度: {self.animation_manager.current_step}/{self.animation_manager.total_steps}")
            
    def on_animation_started(self):
        """动画开始时的处理"""
        self.play_pause_btn.setText("暂停")
        self.status_label.setText("状态: 播放中")
        
    def on_animation_paused(self):
        """动画暂停时的处理"""
        self.play_pause_btn.setText("播放")
        self.status_label.setText("状态: 已暂停")
        
    def on_animation_stopped(self):
        """动画停止时的处理"""
        self.play_pause_btn.setText("播放")
        self.status_label.setText("状态: 停止")
        self.progress_bar.setValue(0)
        self.progress_label.setText("进度: 0/100")
        
    def on_animation_finished(self):
        """动画完成时的处理"""
        self.play_pause_btn.setText("播放")
        self.status_label.setText("状态: 完成")
        
    def on_position_updated(self, length_values, area_values):
        """位置更新时的处理"""
        if self.chart_display:
            self.chart_display.add_data_point(length_values, area_values)
