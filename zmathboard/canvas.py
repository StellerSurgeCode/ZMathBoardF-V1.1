#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import QWidget, QMenu, QAction, QInputDialog
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QCursor, QPixmap, QFont
from PyQt5.QtCore import Qt, QPointF, QPoint, QRectF, QTimer, pyqtSignal, QDateTime, QLineF
import math
import os
import time

from .geometry import Point, Line, GeometryObject
from .intersection import IntersectionManager
from .canvas_serializer import CanvasSerializer
from .ui_state_manager import UIStateManager
from .geometry_checker import GeometryChecker

class Canvas(QWidget):
    """绘图画布组件"""
    
    object_selected = pyqtSignal(GeometryObject)  # 选中对象信号
    canvas_clicked = pyqtSignal(QPointF)  # 画布点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置基本属性
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        
        # 几何对象
        self.objects = []
        self.selected_object = None
        
        # 约束系统
        from .constraints import ConstraintManager
        self.constraint_manager = ConstraintManager()
        self.dragged_object = None  # 当前拖拽的对象
        self.dragged_line = None  # 当前拖拽的线段（用于固定长度处理）
        self.dragging = False
        self.drag_start_pos = None
        self.drag_indicator_enabled = True
        self.cursor_distance = 10  # 指示器与鼠标的距离
        self.active_polygons = []  # 活跃的多边形对象
        self.drag_outline_color = QColor(255, 0, 0)  # 拖动时的轮廓颜色
        self.show_cursor_indicator = True  # 是否显示右下角的鼠标指示器
        
        # 添加框选相关变量
        self.selection_box = False  # 是否正在框选
        self.selection_start_pos = None  # 框选起始位置
        self.selection_current_pos = None  # 框选当前位置
        self.selection_rect = None  # 框选的矩形区域
        self.selected_objects = []  # 框选选中的对象列表
        
        # 角度约束相关
        self._angle_enforcing = False  # 防止递归调用
        self.group_dragging = False  # 是否正在拖动选中的一组对象
        self.show_selection_rect_while_dragging = True  # 拖动时是否显示选择框
        
        # 动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.setInterval(16)  # 约60fps
        self.animation_timer.timeout.connect(self.update)
        
        # 工具状态
        self.current_tool = "select"
        self.drawing_line = False
        self.temp_line_start = None
        self.connecting = False
        self.connect_start = None
        
        # 显示设置
        self.show_grid = True
        self.grid_size = 20
        self.grid_color = QColor(230, 230, 230)  # 添加grid_color属性
        self.show_point_names = True
        self.show_line_names = True
        self.show_angles = True          # 是否显示角度
        self.show_angle_values = True    # 是否显示角度值
        
        # 吸附设置
        self.snap_enabled = True
        self.snap_threshold = 15  # 吸附阈值
        self.snap_highlight_pos = None  # 吸附高亮点
        
        # 加载鼠标图片
        self.cursor_image = None
        cursor_path = os.path.join(os.path.dirname(__file__), 'img', '选中.png')
        if os.path.exists(cursor_path):
            # 加载图片并缩小尺寸
            original_pixmap = QPixmap(cursor_path)
            # 将图片缩小到原来的10%大小（进一步缩小）
            self.cursor_image = original_pixmap.scaled(
                int(original_pixmap.width() * 0.05),
                int(original_pixmap.height() * 0.05),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        else:
            print(f"无法加载光标图像: {cursor_path} 不存在")
        
        # 性能优化参数
        self.last_update_time = QDateTime.currentMSecsSinceEpoch()  # 初始化为当前时间
        self.update_interval = 16  # 最小更新间隔(毫秒)
        
        # 设置焦点策略
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 启用右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # UI状态管理功能
        self.ui_state_manager = UIStateManager(self)
        self.state_changed = False  # 状态变化标记
        
        # 程序启动时尝试恢复上次UI状态
        self.ui_state_manager.auto_load_ui_state()
        
        # 注释掉频繁的自动保存功能，只在程序退出时保存
        # self.auto_save_timer = QTimer()
        # self.auto_save_timer.timeout.connect(self.perform_auto_save)
        # self.auto_save_timer.start(10000)  # 每10秒自动保存一次
        
        # 创建交点管理器
        self.intersection_manager = IntersectionManager(self)
        
        # 创建几何异常检查器
        self.geometry_checker = GeometryChecker(self)
        self.geometry_checker.anomaly_detected.connect(self.on_anomaly_detected)
        self.geometry_checker.anomaly_fixed.connect(self.on_anomaly_fixed)
        
        # 创建名称位置管理器
        from .evade import NamePositionManager
        self.name_position_manager = NamePositionManager(self)
        
        # 固定长度监控定时器
        self.fixed_length_timer = QTimer(self)
        self.fixed_length_timer.timeout.connect(self.check_fixed_lengths)
        self.fixed_length_timer.start(100)  # 每100ms检查一次
        
        # 自适应比例设置
        self.adaptive_line_scaling = False  # 是否启用线段自适应比例 - 默认禁用
        self.auto_update_scales = False     # 是否自动更新比例 - 默认禁用
        
        # 画布拖动相关属性
        self.canvas_dragging = False  # 是否正在拖动画布
        self.canvas_offset = QPoint(0, 0)  # 画布偏移量
        self.canvas_drag_start_pos = None  # 画布拖动起始位置
        self.is_canvas_drag_mode = False  # 是否处于画布拖动模式
        self.drag_mode = False  # 通过工具栏按钮控制的拖动模式
        self.drag_message_timer = QTimer(self)  # 用于控制提示消息的显示时间
        self.drag_message_timer.setSingleShot(True)  # 只触发一次
        self.drag_message_timer.setInterval(2000)  # 2秒后隐藏提示
        self.drag_message = ""  # 拖动提示消息
        
    def paintEvent(self, event):
        """绘制事件"""
        # 获取需要重绘的区域，减少不必要的绘制
        update_rect = event.rect()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 仅绘制需要更新的区域
        painter.setClipRect(update_rect)
        
        # 填充背景
        painter.fillRect(update_rect, QColor(255, 255, 255))
        
        # 保存当前画笔状态
        painter.save()
        
        # 应用画布偏移量
        painter.translate(self.canvas_offset)
        
        # 绘制网格
        if self.show_grid:
            self.draw_grid(painter)
            
        # 绘制选择框（if正在选择或拖动群组或已选中但未拖动）
        if (self.selection_box and self.selection_start_pos and self.selection_current_pos) or \
           (self.selection_rect is not None and (self.group_dragging or self.selected_objects)):
            # 设置选择框的样式
            pen = QPen(QColor(0, 120, 215))  # 蓝色
            pen.setStyle(Qt.DashLine)
            pen.setWidth(1)
            painter.setPen(pen)
            
            # 设置半透明填充色
            painter.setBrush(QBrush(QColor(0, 120, 215, 40)))  # 蓝色，40%透明度
            
            if self.selection_box:
                # 计算选择框矩形（正在框选中）
                x = min(self.selection_start_pos.x(), self.selection_current_pos.x())
                y = min(self.selection_start_pos.y(), self.selection_current_pos.y())
                width = abs(self.selection_current_pos.x() - self.selection_start_pos.x())
                height = abs(self.selection_current_pos.y() - self.selection_start_pos.y())
                
                # 绘制选择框
                selection_rect = QRectF(x, y, width, height)
                self.selection_rect = selection_rect
                painter.drawRect(selection_rect)
            elif self.selection_rect:
                # 在群组拖动状态或已选中状态下显示选择框
                painter.drawRect(self.selection_rect)
        
        # 绘制活跃的多边形
        for polygon in self.active_polygons:
            polygon.draw(painter)
        
        # 在拖动过程中，确保更新所有线段的名称位置
        if self.dragging:
            # if拖动的是线段或点，更新所有相关线段的名称位置
            affected_lines = []
            
            if isinstance(self.dragged_object, Line):
                # 自己必然受影响
                affected_lines.append(self.dragged_object)
                
                # 查找所有共享端点的线段
                for obj in self.objects:
                    if isinstance(obj, Line) and obj != self.dragged_object:
                        if (obj.p1 == self.dragged_object.p1 or obj.p1 == self.dragged_object.p2 or
                            obj.p2 == self.dragged_object.p1 or obj.p2 == self.dragged_object.p2):
                            affected_lines.append(obj)
            
            elif isinstance(self.dragged_object, Point):
                # 查找所有连接到该点的线段
                for obj in self.objects:
                    if isinstance(obj, Line) and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                        affected_lines.append(obj)
            
            # 绘制前，确保所有受影响线段的名称位置都被更新
            for line in affected_lines:
                self.name_position_manager.update_object_changed(line)
        
        # 绘制所有几何对象
        for obj in self.objects:
            # 根据类型和显示名称设置决定是否传递名称
            if isinstance(obj, Point):
                if not self.show_point_names and hasattr(obj, 'name'):
                    # 保存原始名称
                    original_name = obj.name
                    # 临时设置名称为空
                    obj.name = ""
                    obj.draw(painter)
                    # 恢复原始名称
                    obj.name = original_name
                else:
                    obj.draw(painter)
            elif isinstance(obj, Line):
                if not self.show_line_names and hasattr(obj, 'name'):
                    # 保存原始名称
                    original_name = obj.name
                    # 临时设置名称为空
                    obj.name = ""
                    obj.draw(painter)
                    # 恢复原始名称
                    obj.name = original_name
                else:
                    obj.draw(painter)
            # 处理角度对象
            elif self._is_angle_object(obj):
                # if角度显示被禁用，跳过绘制
                if not self.show_angles:
                    continue
                obj.draw(painter)
            else:
                obj.draw(painter)
        
        # 恢复画笔状态
        painter.restore()
        
        # if在画布拖动模式下，显示状态提示
        if self.is_canvas_drag_mode or self.drag_mode:
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(10, 20, "画布拖动模式：按住鼠标左键拖动画布")
            
        # 显示拖动限制提示消息
        if self.drag_message:
            painter.setPen(QPen(QColor(255, 0, 0)))  # 红色提示
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(QRectF(0, 30, self.width(), 30), Qt.AlignCenter, self.drag_message)
        
        # 绘制临时线段 (暂时保留注释以帮助定位)
        if self.drawing_line and self.temp_line_start:
            pen = QPen(QColor(0, 0, 0))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            
            # 获取实际鼠标位置
            cursor_global_pos = self.cursor().pos()
            cursor_local_pos = self.mapFromGlobal(cursor_global_pos)
            
            # 确保注意：这里的self.temp_line_start是画布坐标系中的位置
            start_point = QPointF(self.temp_line_start.x, self.temp_line_start.y)
            
            # 转换鼠标位置到画布坐标系
            end_point = QPointF(cursor_local_pos.x() - self.canvas_offset.x(), 
                                cursor_local_pos.y() - self.canvas_offset.y())
            
            # if有吸附点，使用吸附点位置（吸附点已经是画布坐标系）
            if self.snap_highlight_pos is not None and isinstance(self.snap_highlight_pos, Point):
                end_point = QPointF(self.snap_highlight_pos.x, self.snap_highlight_pos.y)
                    
            # 使用重新保存的画布状态，确保变换矩阵正确
            painter.save()
            painter.translate(self.canvas_offset)
            # 绘制临时线段
            painter.drawLine(start_point, end_point)
            painter.restore()
            
        # if正在连接点，绘制连接线 (暂时保留注释以帮助定位)
        if self.connecting and self.connect_start:
            pen = QPen(QColor(0, 128, 255))
            pen.setWidth(2)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            
            # 获取实际鼠标位置
            cursor_global_pos = self.cursor().pos()
            cursor_local_pos = self.mapFromGlobal(cursor_global_pos)
            
            # 确保注意：这里的self.connect_start是画布坐标系中的位置
            start_point = QPointF(self.connect_start.x, self.connect_start.y)
            
            # 转换鼠标位置到画布坐标系
            end_point = QPointF(cursor_local_pos.x() - self.canvas_offset.x(), 
                                cursor_local_pos.y() - self.canvas_offset.y())
            
            # if有吸附点，使用吸附点位置（吸附点已经是画布坐标系）
            if self.snap_highlight_pos is not None and isinstance(self.snap_highlight_pos, Point):
                end_point = QPointF(self.snap_highlight_pos.x, self.snap_highlight_pos.y)
                    
            # 使用重新保存的画布状态，确保变换矩阵正确
            painter.save()
            painter.translate(self.canvas_offset)
            # 绘制临时线段
            painter.drawLine(start_point, end_point)
            painter.restore()
            
        # 绘制吸附提示 - 已经应用了canvas_offset，所以坐标是正确的
        if self.snap_highlight_pos is not None:
            if isinstance(self.snap_highlight_pos, Point):
                pen = QPen(QColor(0, 255, 0))  # 绿色
                pen.setWidth(2)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(
                    QPointF(self.snap_highlight_pos.x, self.snap_highlight_pos.y),
                    self.snap_highlight_pos.radius + 8,
                    self.snap_highlight_pos.radius + 8
                )
        
        # 绘制拖动状态指示器 - 已经应用了canvas_offset，所以坐标是正确的
        if self.dragging and self.dragged_object and self.drag_indicator_enabled:
            # 绘制红色轮廓
            pen = QPen(self.drag_outline_color)
            pen.setWidth(2)
            pen.setStyle(Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            
            # 获取拖动对象的位置，用于放置鼠标指示器
            indicator_pos = QPointF()
            
            if isinstance(self.dragged_object, Point):
                # 绘制点的红色轮廓
                painter.drawEllipse(
                    QPointF(self.dragged_object.x, self.dragged_object.y),
                    self.dragged_object.radius + 5,
                    self.dragged_object.radius + 5
                )
                # 设置指示器位置在点的右下方
                indicator_pos = QPointF(
                    self.dragged_object.x + self.dragged_object.radius + self.cursor_distance,
                    self.dragged_object.y + self.dragged_object.radius + self.cursor_distance
                )
            elif isinstance(self.dragged_object, Line):
                # 绘制线段的红色轮廓
                if self.dragged_point:
                    # 仅绘制端点的红色轮廓
                    painter.drawEllipse(
                        QPointF(self.dragged_point.x, self.dragged_point.y),
                        5 + 5,
                        5 + 5
                    )
                    indicator_pos = QPointF(
                        self.dragged_point.x + 5 + self.cursor_distance,
                        self.dragged_point.y + 5 + self.cursor_distance
                    )
                else:
                    # 绘制整个线段的红色轮廓
                    painter.drawLine(
                        QPointF(self.dragged_object.p1.x, self.dragged_object.p1.y),
                        QPointF(self.dragged_object.p2.x, self.dragged_object.p2.y)
                    )
                    # 线段中点作为指示器位置参考
                    mid_x = (self.dragged_object.p1.x + self.dragged_object.p2.x) / 2
                    mid_y = (self.dragged_object.p1.y + self.dragged_object.p2.y) / 2
                    indicator_pos = QPointF(
                        mid_x + self.cursor_distance,
                        mid_y + self.cursor_distance
                    )
            
            # 绘制光标指示器
            if self.show_cursor_indicator and self.cursor_image:
                painter.drawPixmap(
                    int(indicator_pos.x()),
                    int(indicator_pos.y()),
                    self.cursor_image
                )
        
    def draw_grid(self, painter):
        """绘制网格"""
        # 使用纯数学方法重新实现网格绘制，确保在任何方向都能正确显示
        
        # 设置网格线的画笔
        pen = QPen(self.grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # 获取视图大小
        view_width = self.width()
        view_height = self.height()
        
        # 获取当前画布偏移
        offset_x = self.canvas_offset.x() 
        offset_y = self.canvas_offset.y()
        
        # 计算超大范围以确保全覆盖
        extra_buffer = max(view_width, view_height) * 50
        
        # 计算网格起始位置 (计算在当前视图中应该从哪里开始绘制第一条网格线)
        # 这里取模操作确保了网格线从整数倍的grid_size位置开始
        start_x_mod = offset_x % self.grid_size
        start_y_mod = offset_y % self.grid_size
        
        # 找到在视图区域内的第一条水平和垂直的网格线
        first_visible_x = -start_x_mod - extra_buffer
        first_visible_y = -start_y_mod - extra_buffer
        
        # 计算需要绘制的网格线数量
        h_lines_count = int((view_height + 2 * extra_buffer) / self.grid_size) + 2
        v_lines_count = int((view_width + 2 * extra_buffer) / self.grid_size) + 2
        
        # 绘制所有水平网格线
        for i in range(h_lines_count):
            y = first_visible_y + i * self.grid_size
            # 使用QLineF代替drawLine，可以避免一些渲染问题
            line = QLineF(-extra_buffer, y, view_width + extra_buffer, y)
            painter.drawLine(line)
        
        # 绘制所有垂直网格线  
        for i in range(v_lines_count):
            x = first_visible_x + i * self.grid_size
            # 使用QLineF代替drawLine，可以避免一些渲染问题
            line = QLineF(x, -extra_buffer, x, view_height + extra_buffer)
            painter.drawLine(line)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        pos = event.pos()
        
        # 转换为考虑画布偏移的坐标
        canvas_pos = QPoint(int(pos.x() - self.canvas_offset.x()), int(pos.y() - self.canvas_offset.y()))
        
        if event.button() == Qt.LeftButton:
            # 在画布拖动模式下，左键按下开始拖动画布
            if self.is_canvas_drag_mode or self.drag_mode:
                self.canvas_dragging = True
                self.canvas_drag_start_pos = pos
                self.setCursor(Qt.ClosedHandCursor)  # 设置拖动时的光标
                return
                
            if self.current_tool == "select":
                # 检查点击位置是否在选择框内
                if self.selection_rect and self.selection_rect.contains(QPointF(canvas_pos.x(), canvas_pos.y())) and self.selected_objects:
                    # 点击在选择框内，进入群组拖动模式
                    # 群组拖动应该无视属性障碍，唯一需要保护的是不丢失属性
                    
                    # 直接允许群组拖动，无需检查限制条件
                    self.group_dragging = True
                    self.dragging = True
                    self.drag_start_pos = canvas_pos
                    return
                
                # 检查是否点击在对象上
                obj = self.select_object_at(canvas_pos)
                
                if obj:
                    # 检查是否是手动创建的多边形或与手动多边形共点的图形
                    is_restricted = False
                    
                    # 检查是否是手动创建的多边形
                    if hasattr(obj, 'vertices') and isinstance(obj.vertices, list) and hasattr(obj, 'source') and obj.source == 'manual':
                        is_restricted = True
                    
                    # 点击在对象上的处理逻辑（保持原有功能）
                    if self.selected_object:
                        self.selected_object.selected = False
                    self.selected_object = obj
                    obj.selected = True
                    self.object_selected.emit(obj)
                    
                    # if对象在已选择列表中，且不是受限制的对象，进入群组拖动模式
                    if obj in self.selected_objects and not is_restricted:
                        self.group_dragging = True
                        self.dragging = True
                        self.drag_start_pos = canvas_pos
                        
                        # 更新选择框位置（根据所有选中对象的边界）
                        self.update_selection_rect_from_objects()
                    else:
                        # 清除之前的选择
                        for selected_obj in self.selected_objects:
                            if hasattr(selected_obj, 'selected'):
                                selected_obj.selected = False
                        self.selected_objects = []
                        
                        # 清除选择框，因为点击了一个非选中组内的对象
                        self.selection_rect = None
                        
                        # if不是受限制的对象，开始常规拖拽
                        if not is_restricted:
                            self.dragging = True
                            self.dragged_object = obj
                            self.drag_start_pos = canvas_pos
                            
                            # 线段端点处理逻辑保持不变
                            if isinstance(obj, Line):
                                # 检查是否点击了线段的端点
                                endpoint = self.find_line_endpoint_at(canvas_pos)
                                if endpoint:
                                    self.dragged_point = endpoint[1]
                                    self.dragged_line = endpoint[0]
                            # 固定长度线段的端点处理逻辑保持不变
                            elif isinstance(obj, Point):
                                # 重置dragged_line，避免上次操作的影响
                                self.dragged_line = None
                                # 查找点所在的固定长度线段
                                for line_obj in self.objects:
                                    if isinstance(line_obj, Line) and line_obj.fixed_length and (line_obj.p1 == obj or line_obj.p2 == obj):
                                        self.dragged_line = line_obj
                                        self.dragged_point = obj
                                        break
                        else:
                            # 显示提示消息
                            self.drag_message = "无法拖动：此图形是手动创建的多边形或与之关联"
                            self.drag_message_timer.start()
                            self.drag_message_timer.timeout.connect(self.clear_drag_message)
                            self.update()
                else:
                    # 点击在空白处，开始框选或处理多边形
                    polygon = self.find_polygon_at(canvas_pos)
                    if polygon:
                        # 检查是否是手动创建的多边形
                        is_manual_polygon = (hasattr(polygon, 'source') and polygon.source == 'manual')
                        
                        # if不是手动创建的多边形，允许拖动
                        if not is_manual_polygon:
                            # 处理多边形拖动（保持原有功能）
                            self.dragging = True
                            self.dragged_object = polygon
                            self.drag_start_pos = canvas_pos
                            
                            # 清除选择框，因为点击了多边形
                            self.selection_rect = None
                            
                            # 清除选中的对象列表
                            for selected_obj in self.selected_objects:
                                if hasattr(selected_obj, 'selected'):
                                    selected_obj.selected = False
                            self.selected_objects = []
                        else:
                            # if是手动创建的多边形，只选中但不允许拖动
                            if self.selected_object:
                                self.selected_object.selected = False
                            self.selected_object = polygon
                            polygon.selected = True
                            
                            # 设置标志表示当前选中的是手动多边形，应保留其属性
                            polygon._preserve_attributes = True
                            
                            self.object_selected.emit(polygon)
                            
                            # 显示提示消息
                            self.drag_message = "无法整体拖动手动创建的多边形，但可以拖动其顶点和边线"
                            self.drag_message_timer.start()
                            self.drag_message_timer.timeout.connect(self.clear_drag_message)
                            self.update()
                    else:
                        # 开始框选
                        self.selection_box = True
                        self.selection_start_pos = canvas_pos
                        self.selection_current_pos = canvas_pos
                        
                        # 清除之前的选择
                        if self.selected_object:
                            self.selected_object.selected = False
                            self.selected_object = None
                            self.object_selected.emit(None)
                        
                        for selected_obj in self.selected_objects:
                            if hasattr(selected_obj, 'selected'):
                                selected_obj.selected = False
                        self.selected_objects = []
                        
                        # 清除选择框，因为要开始新的框选
                        self.selection_rect = None
                        
                        # 触发画布点击信号（保留原有功能）
                        self.canvas_clicked.emit(QPointF(canvas_pos))
            
            elif self.current_tool == "point":
                # 创建新点
                point_pos = self.get_snap_position(canvas_pos) if self.snap_enabled else canvas_pos
                new_point = self.create_point_at(point_pos)
                
                # 选中新创建的点
                if self.selected_object:
                    self.selected_object.selected = False
                self.selected_object = new_point
                new_point.selected = True
                self.object_selected.emit(new_point)
                
            elif self.current_tool == "line":
                # 开始绘制线段
                start_point = self.find_point_at(canvas_pos)
                
                if not start_point:
                    # if点击位置没有点，则创建新点
                    point_pos = self.get_snap_position(canvas_pos) if self.snap_enabled else canvas_pos
                    start_point = self.create_point_at(point_pos)
                
                self.drawing_line = True
                self.temp_line_start = start_point
                
            elif self.current_tool == "connect":
                # 连接两点
                start_point = self.find_point_at(canvas_pos)
                
                # 检查是否点击了线段端点 - if是，优先使用端点而不是创建新点
                if not start_point:
                    endpoint = self.find_line_endpoint_at(canvas_pos)
                    if endpoint:
                        # 使用线段端点作为起始点
                        start_point = endpoint[1]
                
                if start_point:
                    self.connecting = True
                    self.connect_start = start_point
            
            # 每当处理完鼠标事件后，if涉及线段操作，更新交点
            if self.intersection_manager.show_intersections and self.current_tool in ["line", "connect"]:
                self.intersection_manager.update_all_intersections()
                
        elif event.button() == Qt.RightButton:
            # 右键菜单或取消当前操作
            if self.drawing_line:
                self.drawing_line = False
                self.temp_line_start = None
                self.update()
            elif self.connecting:
                self.connecting = False
                self.connect_start = None
                self.update()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        pos = event.pos()

        # 控制更新频率
        current_time = QDateTime.currentMSecsSinceEpoch()
        if current_time - self.last_update_time < self.update_interval:
            return
        self.last_update_time = current_time

        # 处理画布拖动
        if self.canvas_dragging:
            dx = pos.x() - self.canvas_drag_start_pos.x()
            dy = pos.y() - self.canvas_drag_start_pos.y()
            self.canvas_offset = QPoint(int(self.canvas_offset.x() + dx), int(self.canvas_offset.y() + dy))
            self.canvas_drag_start_pos = pos
            self.update()
            return

        # 转换为考虑画布偏移的坐标 (核心修改点：后续逻辑使用 canvas_pos)
        canvas_pos = QPoint(int(pos.x() - self.canvas_offset.x()), int(pos.y() - self.canvas_offset.y()))

        # 更新吸附高亮 - 使用画布坐标
        self.update_snap_highlight(canvas_pos)

        # 处理框选 - 使用画布坐标
        if self.selection_box:
            self.selection_current_pos = canvas_pos
            self.update()
            return

        # 处理群组拖动
        if self.group_dragging and self.dragging and self.selected_objects:
            self.clear_drag_message()

            # --- 核心修改: 使用 canvas_pos 计算位移 ---
            # Ensure drag_start_pos is QPointF for consistency if needed, though QPoint should work
            if isinstance(self.drag_start_pos, QPoint):
                 start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
            elif isinstance(self.drag_start_pos, QPointF):
                 start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
            else: # Fallback or error handling if drag_start_pos is unexpected type
                 start_x, start_y = canvas_pos.x(), canvas_pos.y() # Use current pos as fallback start

            dx = canvas_pos.x() - start_x
            dy = canvas_pos.y() - start_y
            # -------------------------------------------

            points_to_update = []
            for obj in self.selected_objects:
                if isinstance(obj, Point) and not obj.fixed:
                    # --- 应用画布坐标系的位移 ---
                    obj.x += dx
                    obj.y += dy
                    # --------------------------
                    points_to_update.append(obj)

            additional_points = []
            for polygon in self.active_polygons:
                shared_vertices = [v for v in polygon.vertices if v in points_to_update]
                if shared_vertices and len(shared_vertices) < len(polygon.vertices):
                    for vertex in polygon.vertices:
                        if vertex not in points_to_update and not vertex.fixed:
                            # --- 应用画布坐标系的位移 ---
                            vertex.x += dx
                            vertex.y += dy
                            # --------------------------
                            additional_points.append(vertex)

            points_to_update.extend(additional_points)

            for point in points_to_update:
                self.name_position_manager.update_object_changed(point)

            affected_lines = set()
            for point in points_to_update:
                for line in self.objects:
                    if isinstance(line, Line) and (line.p1 == point or line.p2 == point):
                        affected_lines.add(line)

            for line in affected_lines:
                self.name_position_manager.update_object_changed(line)

            if self.selection_rect:
                # --- 使用画布坐标系的位移平移选择框 ---
                self.selection_rect.translate(dx, dy)
                # ------------------------------------

            if self.intersection_manager.show_intersections:
                self.intersection_manager.update_all_intersections()

            affected_polygons = []
            polygon_attributes = {}
            for polygon in self.active_polygons:
                polygon_affected = False
                for vertex in polygon.vertices:
                    if vertex in points_to_update:
                        polygon_affected = True
                        break
                if polygon_affected:
                    affected_polygons.append(polygon)

            try:
                from .draw import update_all_height_foot_points, PolygonDetector
                update_all_height_foot_points(self)
                if affected_polygons:
                    old_polygons = self.active_polygons.copy() # Changed from affected_polygons.copy()
                    detector = PolygonDetector(self)
                    detected_polygons = detector.detect_polygons()
                    if detected_polygons:
                        # Pass the correct old_polygons list for attribute restoration
                        restored_polygons = self.restore_polygon_attributes(old_polygons, detected_polygons)
                        self.active_polygons = restored_polygons # Update the active list
            except Exception as e:
                print(f"更新垂足点或多边形检测出错: {str(e)}")

            # --- 核心修改: 更新 drag_start_pos 为画布坐标 ---
            self.drag_start_pos = canvas_pos # Use QPoint canvas_pos directly
            # ----------------------------------------------
            self.update()
            return

        if self.dragging and self.dragged_object:
            affected_lines = []

            if hasattr(self.dragged_object, 'vertices') and isinstance(self.dragged_object.vertices, list):
                dragged_polygon = self.dragged_object
                has_attributes = False
                # ... (检查属性的代码不变)
                if hasattr(dragged_polygon, 'show_fill') and dragged_polygon.show_fill: has_attributes = True
                elif hasattr(dragged_polygon, 'fill_color') and dragged_polygon.fill_color != QColor(230, 230, 255, 100): has_attributes = True
                elif hasattr(dragged_polygon, 'show_diagonals') and dragged_polygon.show_diagonals: has_attributes = True
                elif hasattr(dragged_polygon, 'show_medians') and dragged_polygon.show_medians: has_attributes = True
                elif hasattr(dragged_polygon, 'show_heights') and dragged_polygon.show_heights: has_attributes = True
                elif hasattr(dragged_polygon, 'show_angle_bisectors') and dragged_polygon.show_angle_bisectors: has_attributes = True
                elif hasattr(dragged_polygon, 'show_midlines') and dragged_polygon.show_midlines: has_attributes = True
                elif hasattr(dragged_polygon, 'show_incircle') and dragged_polygon.show_incircle: has_attributes = True
                elif hasattr(dragged_polygon, 'show_circumcircle') and dragged_polygon.show_circumcircle: has_attributes = True

                if has_attributes:
                    self.drag_message = "无法整体拖动手动创建的多边形，但可以拖动其顶点和边线，或使用群组拖动"
                    self.drag_message_timer.start()
                    self.drag_message_timer.timeout.connect(self.clear_drag_message)
                    self.update()
                    return

                dragged_polygon_vertex_ids = tuple(sorted([id(v) for v in dragged_polygon.vertices]))
                dragged_polygon_attrs = {
                    'fill_color': dragged_polygon.fill_color,
                    'show_fill': dragged_polygon.show_fill,
                    'show_diagonals': dragged_polygon.show_diagonals,
                    'show_medians': dragged_polygon.show_medians,
                    'show_heights': dragged_polygon.show_heights,
                    'show_angle_bisectors': dragged_polygon.show_angle_bisectors,
                    'show_midlines': dragged_polygon.show_midlines,
                    'show_incircle': dragged_polygon.show_incircle,
                    'show_circumcircle': dragged_polygon.show_circumcircle,
                    'source': getattr(dragged_polygon, 'source', 'auto')
                }
                is_manual_polygon = dragged_polygon_attrs['source'] == 'manual'
                if hasattr(dragged_polygon, 'selected_heights'): dragged_polygon_attrs['selected_heights'] = dragged_polygon.selected_heights.copy()
                if hasattr(dragged_polygon, 'selected_angles'): dragged_polygon_attrs['selected_angles'] = dragged_polygon.selected_angles.copy()
                if hasattr(dragged_polygon, 'height_feet'): dragged_polygon_attrs['height_feet'] = getattr(dragged_polygon, 'height_feet', {}).copy()


                if not hasattr(self, '_drag_saved') or not self._drag_saved:
                    self._drag_saved = True

                # --- 核心修改: 使用 canvas_pos 计算位移 ---
                # Ensure drag_start_pos is QPointF for consistency if needed
                if isinstance(self.drag_start_pos, QPoint):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                elif isinstance(self.drag_start_pos, QPointF):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                else: # Fallback
                    start_x, start_y = canvas_pos.x(), canvas_pos.y()

                dx = canvas_pos.x() - start_x
                dy = canvas_pos.y() - start_y
                # -------------------------------------------

                moved_vertices = []
                for vertex in self.dragged_object.vertices:
                    if not vertex.fixed:
                        # --- 应用画布坐标系的位移 ---
                        vertex.x += dx
                        vertex.y += dy
                        # --------------------------
                        moved_vertices.append(vertex)
                        self.name_position_manager.update_object_changed(vertex)

                linked_polygons = []
                # ... (查找链接多边形的代码保持不变) ...
                for polygon in self.active_polygons:
                    if polygon == self.dragged_object: continue
                    has_shared_vertex = False
                    for vertex in polygon.vertices:
                        if vertex in moved_vertices:
                            has_shared_vertex = True
                            break
                    if has_shared_vertex: linked_polygons.append(polygon)


                for polygon in linked_polygons:
                    for vertex in polygon.vertices:
                        if vertex not in moved_vertices and not vertex.fixed:
                            # --- 应用画布坐标系的位移 ---
                            vertex.x += dx
                            vertex.y += dy
                            # --------------------------
                            moved_vertices.append(vertex)
                            self.name_position_manager.update_object_changed(vertex)
                    for line in polygon.lines:
                        self.name_position_manager.update_object_changed(line)
                        if line not in affected_lines: affected_lines.append(line)

                for line in self.dragged_object.lines:
                    self.name_position_manager.update_object_changed(line)
                    affected_lines.append(line)

                # --- 核心修改: 更新 drag_start_pos 为画布坐标 ---
                self.drag_start_pos = canvas_pos # Use QPoint canvas_pos directly
                # ----------------------------------------------

                try:
                    from .draw import update_all_height_foot_points, PolygonDetector
                    # 保存当前活跃多边形，用于后续恢复属性
                    old_active_polygons = self.active_polygons.copy()
                    update_all_height_foot_points(self)
                    detector = PolygonDetector(self)
                    detected_polygons = detector.detect_polygons()
                    if detected_polygons:
                        # 使用恢复属性函数确保颜色和填充属性被正确保留
                        restored_polygons = self.restore_polygon_attributes(old_active_polygons, detected_polygons)
                        # ... (强制恢复拖动多边形属性的代码保持不变) ...
                        found_dragged_polygon = None
                        for polygon in restored_polygons:
                            current_vertex_ids = tuple(sorted([id(v) for v in polygon.vertices]))
                            if current_vertex_ids == dragged_polygon_vertex_ids:
                                found_dragged_polygon = polygon
                                break
                        if found_dragged_polygon:
                            found_dragged_polygon.fill_color = dragged_polygon_attrs['fill_color']
                            found_dragged_polygon.show_fill = dragged_polygon_attrs['show_fill']
                            found_dragged_polygon.show_diagonals = dragged_polygon_attrs['show_diagonals']
                            found_dragged_polygon.show_medians = dragged_polygon_attrs['show_medians']
                            found_dragged_polygon.show_heights = dragged_polygon_attrs['show_heights']
                            found_dragged_polygon.show_angle_bisectors = dragged_polygon_attrs['show_angle_bisectors']
                            found_dragged_polygon.show_midlines = dragged_polygon_attrs['show_midlines']
                            found_dragged_polygon.show_incircle = dragged_polygon_attrs['show_incircle']
                            found_dragged_polygon.show_circumcircle = dragged_polygon_attrs['show_circumcircle']
                            found_dragged_polygon.source = dragged_polygon_attrs['source'] # 强制恢复source
                            if 'selected_heights' in dragged_polygon_attrs: found_dragged_polygon.selected_heights = dragged_polygon_attrs['selected_heights'].copy()
                            if 'selected_angles' in dragged_polygon_attrs: found_dragged_polygon.selected_angles = dragged_polygon_attrs['selected_angles'].copy()
                            if 'height_feet' in dragged_polygon_attrs: found_dragged_polygon.height_feet = dragged_polygon_attrs['height_feet'].copy()
                            # 更新拖动对象引用为恢复后的对象
                            self.dragged_object = found_dragged_polygon

                        self.active_polygons = restored_polygons
                        # ... (确保拖动对象在活跃列表中的代码保持不变) ...
                        if self.dragged_object not in self.active_polygons:
                            # Check if a polygon with the same vertices already exists
                            current_dragged_vertex_ids = tuple(sorted([id(v) for v in self.dragged_object.vertices]))
                            already_exists = False
                            for poly in self.active_polygons:
                                 poly_id_tuple = tuple(sorted([id(v) for v in poly.vertices]))
                                 if poly_id_tuple == current_dragged_vertex_ids:
                                     already_exists = True
                                     # If the existing one is auto and the dragged one is manual, replace
                                     if getattr(poly, 'source', 'auto') == 'auto' and is_manual_polygon:
                                         self.active_polygons.remove(poly)
                                         self.active_polygons.append(self.dragged_object)
                                         print(f"Replaced auto polygon with dragged manual polygon: {self.dragged_object.name}")
                                     break
                            if not already_exists:
                                self.active_polygons.append(self.dragged_object)


                except Exception as e:
                    print(f"拖动多边形时出错: {str(e)}")
                    # ... (错误恢复代码保持不变) ...
                    if hasattr(self.dragged_object, 'fill_color'): self.dragged_object.fill_color = dragged_polygon_attrs['fill_color']
                    if hasattr(self.dragged_object, 'show_fill'): self.dragged_object.show_fill = dragged_polygon_attrs['show_fill']

                self.update()
                return

            elif isinstance(self.dragged_object, Point) and self.dragged_line is not None and self.dragged_line.fixed_length:
                # --- 核心修改: 更新点位置使用画布坐标 ---
                # Use snapped position (already canvas coordinates) or current mouse canvas coordinates
                target_pos_qpointf = self.get_snap_position(canvas_pos) # get_snap_position returns QPointF or original QPoint
                if isinstance(target_pos_qpointf, QPoint): # Convert QPoint back to QPointF if necessary
                    target_pos = QPointF(target_pos_qpointf)
                else:
                    target_pos = target_pos_qpointf # Already QPointF or None (use canvas_pos)

                if target_pos is None: # Fallback if get_snap_position returns None unexpectedly
                     target_pos = QPointF(canvas_pos)


                if not self.dragged_object.fixed:
                    # --- 更新为目标画布坐标 ---
                    self.dragged_object.x = float(target_pos.x())
                    self.dragged_object.y = float(target_pos.y())
                    # -------------------------

                # 立即应用固定长度约束
                self.dragged_line._enforce_fixed_length(drag_point=self.dragged_object)
                affected_lines.append(self.dragged_line)

                # --- 核心修改: 更新 drag_start_pos 为画布坐标 ---
                # Update with the actual point position after enforcing constraints (already canvas coordinates)
                # Use canvas_pos as the *intended* next start, aligning with mouse
                self.drag_start_pos = canvas_pos
                # ----------------------------------------------

                self.name_position_manager.update_object_changed(self.dragged_line)
                self.name_position_manager.update_object_changed(self.dragged_line.p1)
                self.name_position_manager.update_object_changed(self.dragged_line.p2)

                connected_lines = []
                # ... (查找连接线段的代码保持不变) ...
                for obj in self.objects:
                    if isinstance(obj, Line) and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object) and obj != self.dragged_line:
                        connected_lines.append(obj)
                        affected_lines.append(obj)
                        self.name_position_manager.update_object_changed(obj)


                if self.intersection_manager.show_intersections:
                    for intersection in self.intersection_manager.intersections:
                        if self.dragged_line in intersection.parent_lines:
                            intersection.update_position()

                from .draw import update_all_height_foot_points
                update_all_height_foot_points(self)
                self.update()
                return

            elif isinstance(self.dragged_object, Point) and not self.dragged_object.fixed:

                # --- 核心修改: 使用 canvas_pos 计算位移 ---
                # Ensure drag_start_pos is QPointF for consistency if needed
                if isinstance(self.drag_start_pos, QPoint):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                elif isinstance(self.drag_start_pos, QPointF):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                else: # Fallback
                    start_x, start_y = canvas_pos.x(), canvas_pos.y()

                dx = canvas_pos.x() - start_x
                dy = canvas_pos.y() - start_y
                # -------------------------------------------

                # --- 核心修改: 使用 canvas_pos 获取吸附位置 ---
                snap_pos_qpointf = self.get_snap_position(canvas_pos) # Returns QPointF or original QPoint
                if isinstance(snap_pos_qpointf, QPoint):
                     snap_pos = QPointF(snap_pos_qpointf) # Convert to QPointF
                else:
                     snap_pos = snap_pos_qpointf # Already QPointF or None

                # -------------------------------------------

                # Check if snap_pos is different from canvas_pos *and* not None
                is_snapping = snap_pos is not None and (abs(snap_pos.x() - canvas_pos.x()) > 0.1 or abs(snap_pos.y() - canvas_pos.y()) > 0.1)


                if is_snapping:
                    # Apply movement based on delta (dx, dy) first
                    self.dragged_object.x += dx
                    self.dragged_object.y += dy

                    # --- 固定长度处理保持不变 ---
                    affected_fixed_lines = []
                    for obj in self.objects:
                        if isinstance(obj, Line) and obj.fixed_length and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                            affected_fixed_lines.append(obj)
                            affected_lines.append(obj) # Keep track for name updates
                    for line in affected_fixed_lines:
                        line._enforce_fixed_length(drag_point=self.dragged_object)

                    # --- 吸附效果处理 (using canvas coordinates) ---
                    # Calculate vector towards snap position *from current position*
                    dx_snap = snap_pos.x() - self.dragged_object.x
                    dy_snap = snap_pos.y() - self.dragged_object.y
                    dist_to_snap = math.sqrt(dx_snap*dx_snap + dy_snap*dy_snap)

                    if dist_to_snap < self.snap_threshold * 2 and dist_to_snap > 0.1: # Add threshold to avoid snapping to self
                        # Apply snapping adjustment
                        snap_factor = min(0.5, 6.0 / (dist_to_snap + 1))
                        self.dragged_object.x += dx_snap * snap_factor
                        self.dragged_object.y += dy_snap * snap_factor

                        # Re-enforce fixed length after snapping adjustment if necessary
                        for line in affected_fixed_lines:
                             line._enforce_fixed_length(drag_point=self.dragged_object)

                else: # Not snapping or snap target is the same as cursor
                    # --- 应用画布坐标系的位移 ---
                    self.dragged_object.x += dx
                    self.dragged_object.y += dy
                    # --------------------------
                    # --- 固定长度处理 (apply here too if not snapping) ---
                    affected_fixed_lines = []
                    for obj in self.objects:
                        if isinstance(obj, Line) and obj.fixed_length and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                            affected_fixed_lines.append(obj)
                            affected_lines.append(obj) # Keep track for name updates
                    for line in affected_fixed_lines:
                        line._enforce_fixed_length(drag_point=self.dragged_object)

                # 实时更新约束系统
                self.constraint_manager.update_all_constraints()
                
                # 实时强制角度约束
                self._enforce_angle_constraints_during_drag()

                # --- 核心修改: 更新 drag_start_pos 为画布坐标 ---
                self.drag_start_pos = canvas_pos # Use QPoint canvas_pos directly
                # ----------------------------------------------

                self.name_position_manager.update_object_changed(self.dragged_object)

                affected_lines = [] # Re-calculate affected lines based on final position
                for obj in self.objects:
                    if isinstance(obj, Line) and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                        self.name_position_manager.update_object_changed(obj)
                        affected_lines.append(obj)
                        if obj.p1 == self.dragged_object:
                            self.name_position_manager.update_object_changed(obj.p2)
                        else:
                            self.name_position_manager.update_object_changed(obj.p1)

                if self.intersection_manager.show_intersections and affected_lines:
                    for intersection in self.intersection_manager.intersections:
                        # Check if any parent line is in affected_lines
                        if any(parent_line in affected_lines for parent_line in intersection.parent_lines):
                             intersection.update_position()


                from .draw import update_all_height_foot_points
                update_all_height_foot_points(self)

            elif isinstance(self.dragged_object, Line): # Dragging a Line
                # --- 核心修改: 使用 canvas_pos 计算位移 ---
                # Ensure drag_start_pos is QPointF for consistency if needed
                if isinstance(self.drag_start_pos, QPoint):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                elif isinstance(self.drag_start_pos, QPointF):
                    start_x, start_y = self.drag_start_pos.x(), self.drag_start_pos.y()
                else: # Fallback
                    start_x, start_y = canvas_pos.x(), canvas_pos.y()
                dx = canvas_pos.x() - start_x
                dy = canvas_pos.y() - start_y
                # -------------------------------------------

                p1_can_move = not self.dragged_object.p1.fixed
                p2_can_move = not self.dragged_object.p2.fixed

                if p1_can_move and p2_can_move:
                    old_p1_x, old_p1_y = self.dragged_object.p1.x, self.dragged_object.p1.y
                    old_p2_x, old_p2_y = self.dragged_object.p2.x, self.dragged_object.p2.y

                    # --- 应用画布坐标系的位移 ---
                    self.dragged_object.p1.x += dx
                    self.dragged_object.p1.y += dy
                    self.dragged_object.p2.x += dx
                    self.dragged_object.p2.y += dy
                    # --------------------------

                    # --- 固定长度处理逻辑保持不变 ---
                    affected_fixed_lines = []
                    connected_lines = []
                    for obj in self.objects:
                        if isinstance(obj, Line) and obj != self.dragged_object:
                            # Check if endpoints match either p1 or p2 of the dragged line
                            is_connected = False
                            if obj.p1 == self.dragged_object.p1 or obj.p1 == self.dragged_object.p2: is_connected = True
                            if obj.p2 == self.dragged_object.p1 or obj.p2 == self.dragged_object.p2: is_connected = True

                            if is_connected:
                                connected_lines.append(obj)
                                if obj.fixed_length:
                                    affected_fixed_lines.append(obj)

                    # If connected to fixed length lines, adjust movement along the line's direction
                    if affected_fixed_lines:
                        # Restore original position before calculating projection
                        self.dragged_object.p1.x, self.dragged_object.p1.y = old_p1_x, old_p1_y
                        self.dragged_object.p2.x, self.dragged_object.p2.y = old_p2_x, old_p2_y

                        drag_vector_x = dx # Use canvas coordinate delta
                        drag_vector_y = dy # Use canvas coordinate delta
                        line_vector_x = self.dragged_object.p2.x - self.dragged_object.p1.x
                        line_vector_y = self.dragged_object.p2.y - self.dragged_object.p1.y

                        line_length_sq = line_vector_x**2 + line_vector_y**2
                        if line_length_sq > 1e-6: # Avoid division by zero/small numbers
                            line_length = math.sqrt(line_length_sq)
                            unit_x = line_vector_x / line_length
                            unit_y = line_vector_y / line_length

                            # Project the drag vector onto the line vector
                            projection = drag_vector_x * unit_x + drag_vector_y * unit_y

                            # Apply the projected movement
                            self.dragged_object.p1.x += projection * unit_x
                            self.dragged_object.p1.y += projection * unit_y
                            self.dragged_object.p2.x += projection * unit_x
                            self.dragged_object.p2.y += projection * unit_y
                        # Else: line is essentially a point, cannot move along direction

                        # Update names for connected lines as they might have moved implicitly
                        for line in connected_lines:
                            self.name_position_manager.update_object_changed(line)

                    # Enforce fixed length *after* potential adjustment
                    if self.dragged_object.fixed_length:
                        self.dragged_object._enforce_fixed_length()

                    # Update names for the dragged line and its endpoints
                    self.name_position_manager.update_object_changed(self.dragged_object)
                    self.name_position_manager.update_object_changed(self.dragged_object.p1)
                    self.name_position_manager.update_object_changed(self.dragged_object.p2)

                    if self.intersection_manager.show_intersections:
                        # Update intersections involving the dragged line or connected lines
                        lines_to_check_intersections = {self.dragged_object} | set(connected_lines)
                        for intersection in self.intersection_manager.intersections:
                           if any(line in lines_to_check_intersections for line in intersection.parent_lines):
                                intersection.update_position()


                    from .draw import update_all_height_foot_points
                    update_all_height_foot_points(self)

                    # --- 核心修改: 更新 drag_start_pos 为画布坐标 ---
                    self.drag_start_pos = canvas_pos # Use QPoint canvas_pos directly
                    # ----------------------------------------------
            else:
                 # Handle dragging other object types if needed
                 pass


            # --- 更新区域逻辑: Use canvas_pos for old_bounds ---
            # Get current bounds in canvas coordinates
            update_rect = self.dragged_object.get_bounds_rect(margin=20)

            # Define old bounds based on the *previous* canvas position
            if isinstance(self.drag_start_pos, QPoint): # Check type before accessing x,y
                 old_x, old_y = self.drag_start_pos.x(), self.drag_start_pos.y()
            elif isinstance(self.drag_start_pos, QPointF):
                 old_x, old_y = self.drag_start_pos.x(), self.drag_start_pos.y()
            else: # Fallback, use current pos - might cause slight drawing artifact on first move
                 old_x, old_y = canvas_pos.x(), canvas_pos.y()

            old_bounds = QRectF(old_x - 30, old_y - 30, 60, 60)

            # Combine old and new bounds in canvas coordinates
            combined_canvas_rect = update_rect.united(old_bounds)

            # Translate the combined *canvas* rectangle to *screen* coordinates for update
            screen_update_rect = combined_canvas_rect.translated(self.canvas_offset)
            self.update(screen_update_rect.toRect())


        elif self.drawing_line or self.connecting:
            # --- 临时线段绘制逻辑已正确使用 canvas_pos, 无需修改 ---
            if self.drawing_line or self.connecting:
                start_pos = None
                if self.drawing_line and self.temp_line_start:
                    start_pos = QPointF(self.temp_line_start.x, self.temp_line_start.y)
                elif self.connecting and self.connect_start:
                    start_pos = QPointF(self.connect_start.x, self.connect_start.y)

                if start_pos:
                    # canvas_pos 已在函数开头计算好 (当前鼠标的画布坐标)
                    snap_highlight_point = None
                    if self.snap_highlight_pos and isinstance(self.snap_highlight_pos, Point):
                         snap_highlight_point = self.snap_highlight_pos

                    if snap_highlight_point:
                        end_pos = QPointF(snap_highlight_point.x, snap_highlight_point.y)
                    else:
                        end_pos = QPointF(canvas_pos.x(), canvas_pos.y()) # Use current canvas_pos

                    # Build update rectangle in canvas coordinates
                    canvas_update_rect = QRectF(
                        min(start_pos.x(), end_pos.x()) - 20,
                        min(start_pos.y(), end_pos.y()) - 20,
                        abs(end_pos.x() - start_pos.x()) + 40,
                        abs(end_pos.y() - start_pos.y()) + 40
                    )

                    # Translate canvas rect to screen rect for update
                    screen_update_rect = canvas_update_rect.translated(self.canvas_offset)

                    self.update(screen_update_rect.toRect())
                else:
                    self.update() # Full update if no start pos
            else:
                 # Should not happen based on outer condition, but update just in case
                 self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        from .geometry import Line, Point  # 添加导入，避免未定义错误
        
        # if进行了拖动操作，标记状态改变
        if self.dragging or self.group_dragging or self.canvas_dragging:
            self.mark_state_changed()
        
        # 清除拖动提示消息
        if self.drag_message:
            self.clear_drag_message()
        
        # 清除多边形属性保护标志
        for polygon in self.active_polygons:
            if hasattr(polygon, '_preserve_attributes'):
                polygon._preserve_attributes = False
        
        # 处理画布拖动结束
        if self.canvas_dragging and event.button() == Qt.LeftButton:
            self.canvas_dragging = False
            self.setCursor(Qt.ArrowCursor)  # 恢复默认光标
            self.update()
            return
            
        # 清除拖动保存标记，使下次拖动时能够再次保存属性
        self._drag_saved = False
        
        pos = event.pos()
        # 转换为考虑画布偏移的坐标
        canvas_pos = QPoint(int(pos.x() - self.canvas_offset.x()), int(pos.y() - self.canvas_offset.y()))
        
        points_moved = False
        
        # 处理框选完成事件
        if self.selection_box and event.button() == Qt.LeftButton:
            # 结束框选
            self.selection_box = False
            
            # 查找选择框内的所有对象
            self.find_objects_in_selection_rect()
            
            # 保留选择框，以便user可以通过点击选择框内部进行群组拖动
            # 选择框在群组拖动结束后或点击其他区域后才会消失
            
            # 重置临时变量
            self.selection_current_pos = None
            
            self.update()
            return
        
        # 处理群组拖动结束
        if self.group_dragging and event.button() == Qt.LeftButton:
            self.group_dragging = False
            self.dragging = False
            
            # 清理拖动状态
            
            # 记录移动的点和影响的多边形
            moved_points = []
            affected_polygons = []
            polygon_attributes = {}
            
            # 标记哪些多边形是手动创建的，用于确保它们的属性被完全保留
            manual_polygons = []
            
            # 更新所有选中点的名称位置
            for obj in self.selected_objects:
                if isinstance(obj, Point):
                    self.name_position_manager.update_object_changed(obj)
                    moved_points.append(obj)
            
            # 更新所有与选中点相连的线段
            affected_lines = set()
            for obj in self.selected_objects:
                if isinstance(obj, Point):
                    for line in self.objects:
                        if isinstance(line, Line) and (line.p1 == obj or line.p2 == obj):
                            affected_lines.add(line)
            
            # 更新线段的名称位置
            for line in affected_lines:
                self.name_position_manager.update_object_changed(line)
            
            # 检查固定长度线段
            for line in affected_lines:
                if hasattr(line, 'fixed_length') and line.fixed_length:
                    line._enforce_fixed_length()
            
            # 强制保存所有活跃多边形的属性，特别是手动创建的多边形
            for polygon in self.active_polygons:
                is_manual = getattr(polygon, 'source', 'auto') == 'manual'
                if is_manual:
                    manual_polygons.append(polygon)
                    
                polygon_id = tuple(sorted([id(vertex) for vertex in polygon.vertices]))
                polygon_attributes[polygon_id] = {
                    'fill_color': polygon.fill_color,
                    'show_fill': polygon.show_fill,
                    'show_diagonals': polygon.show_diagonals,
                    'show_medians': polygon.show_medians,
                    'show_heights': polygon.show_heights,
                    'show_angle_bisectors': polygon.show_angle_bisectors,
                    'show_midlines': polygon.show_midlines,
                    'show_incircle': polygon.show_incircle,
                    'show_circumcircle': polygon.show_circumcircle,
                    'source': getattr(polygon, 'source', 'auto'),  # 保存来源信息（手动/自动）
                    'name': getattr(polygon, 'name', '')  # 添加名称，帮助匹配
                }
                # if是三角形，保存选择的高和角平分线
                if hasattr(polygon, 'selected_heights'):
                    polygon_attributes[polygon_id]['selected_heights'] = polygon.selected_heights.copy()
                if hasattr(polygon, 'selected_angles'):
                    polygon_attributes[polygon_id]['selected_angles'] = polygon.selected_angles.copy()
                # 保存高度垂足点信息
                if hasattr(polygon, 'height_feet'):
                    polygon_attributes[polygon_id]['height_feet'] = polygon.height_feet
                    
                # 检查多边形的顶点是否在移动的点中
                polygon_affected = False
                for vertex in polygon.vertices:
                    if vertex in moved_points:
                        polygon_affected = True
                        break
                
                if polygon_affected:
                    affected_polygons.append(polygon)
            
            # 更新画布状态
            
            # 更新垂足点
            from .draw import update_all_height_foot_points
            update_all_height_foot_points(self)
                
            # 更新交点
            if self.intersection_manager.show_intersections:
                self.intersection_manager.update_all_intersections()
            
            # 保存当前活跃多边形，用于后续匹配
            old_active_polygons = self.active_polygons.copy()
            
            # 重新检测多边形
            from .draw import PolygonDetector
            detector = PolygonDetector(self)
            detected_polygons = detector.detect_polygons()
            
            if detected_polygons:
                # 确保使用增强版的恢复属性函数，优先保留手动多边形
                restored_polygons = self.restore_polygon_attributes(old_active_polygons, detected_polygons)
                
                # 更新活跃多边形列表
                self.active_polygons = restored_polygons
                
                # 属性已更新
            
            # 更新界面
            self.update()
            return
        
        # if鼠标是右键点击，不处理拖拽和绘制操作
        if event.button() == Qt.RightButton:
            return
        
        # 处理拖拽结束
        if self.dragging and self.dragged_object:
            # if是拖动多边形，保存其属性以备恢复
            dragged_polygon_attrs = {}
            original_fill_color = None # 保留原始颜色，以便出错时恢复
            original_show_fill = None  # 保留原始填充状态
            dragged_polygon_vertex_ids = None # 用于标识被拖动的多边形
            was_polygon_dragged = False # 标记是否拖动了多边形
            
            if hasattr(self.dragged_object, 'vertices') and isinstance(self.dragged_object.vertices, list):
                was_polygon_dragged = True
                dragged_polygon = self.dragged_object
                dragged_polygon_vertex_ids = tuple(sorted([id(v) for v in dragged_polygon.vertices]))
                
                # 保存多边形属性
                dragged_polygon_attrs = {
                    'fill_color': dragged_polygon.fill_color,
                    'show_fill': dragged_polygon.show_fill,
                    'show_diagonals': dragged_polygon.show_diagonals,
                    'show_medians': dragged_polygon.show_medians,
                    'show_heights': dragged_polygon.show_heights,
                    'show_angle_bisectors': dragged_polygon.show_angle_bisectors,
                    'show_midlines': dragged_polygon.show_midlines,
                    'show_incircle': dragged_polygon.show_incircle,
                    'show_circumcircle': dragged_polygon.show_circumcircle,
                    'source': getattr(dragged_polygon, 'source', 'auto'),  # 保存来源信息
                    'name': getattr(dragged_polygon, 'name', '')  # 添加名称，帮助匹配
                }
                
                # 检查多边形来源类型，手动创建的多边形需要特殊处理
                is_manual_polygon = dragged_polygon_attrs['source'] == 'manual'
                
                # 保存特殊属性
                if hasattr(dragged_polygon, 'selected_heights'):
                    dragged_polygon_attrs['selected_heights'] = dragged_polygon.selected_heights.copy()
                if hasattr(dragged_polygon, 'selected_angles'):
                    dragged_polygon_attrs['selected_angles'] = dragged_polygon.selected_angles.copy()
                if hasattr(dragged_polygon, 'height_feet'):
                    dragged_polygon_attrs['height_feet'] = getattr(dragged_polygon, 'height_feet', {}).copy()
                
                # 记住原始填充颜色和状态，用于后续强制应用或错误恢复
                original_fill_color = dragged_polygon_attrs['fill_color']
                original_show_fill = dragged_polygon_attrs['show_fill']
                
                # 在拖动多边形的情况下，标记点已移动，后续将更新垂足点
                points_moved = True
            
            # if拖动的是点或线段，进行固定长度处理
            if isinstance(self.dragged_object, Point):
                fixed_lines_affected = []
                for obj in self.objects:
                    if isinstance(obj, Line) and obj.fixed_length and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                        fixed_lines_affected.append(obj)
                
                for line in fixed_lines_affected:
                    # 立即强制调整长度，传递被拖拽的点
                    line._enforce_fixed_length(drag_point=self.dragged_object)
                    
                    # 输出最终长度信息
                    final_length = line.length()
                    print(f"拖拽结束: 线段{line.name}最终长度={final_length}, 原始长度={line._original_length}")
                
                points_moved = True
            
            # if拖动的是固定长度线段的端点，确保结束拖拽后线段长度正确
            if isinstance(self.dragged_object, Point) and self.dragged_line is not None and self.dragged_line.fixed_length:
                # 记录拖拽前的长度
                original_length = self.dragged_line._original_length
                
                # 最终强制应用原始长度，传递被拖拽的点
                self.dragged_line._enforce_fixed_length(drag_point=self.dragged_object)
                
                # 最终验证长度，确保_original_length正确应用
                current_length = self.dragged_line.length()
                if abs(current_length - original_length) > 0.0001:
                    print(f"拖拽结束: 线段{self.dragged_line.name}长度不符，当前={current_length}，应为={original_length}")
                    
                    # 再次强制应用原始长度
                    self.dragged_line._enforce_fixed_length()
                    
                    # 再次检查修正后的长度
                    final_length = self.dragged_line.length()
                    print(f"拖拽结束后最终长度: {final_length}, 目标长度: {original_length}")
                    
            # if拖动的是线段，检查是否有与该线段共享端点的固定长度线段
            if isinstance(self.dragged_object, Line):
                # 查找所有与当前线段共享端点的固定长度线段
                shared_fixed_lines = []
                connected_lines = []
                for obj in self.objects:
                    if obj != self.dragged_object and isinstance(obj, Line):
                        # 检查是否共享端点
                        if (obj.p1 == self.dragged_object.p1 or obj.p1 == self.dragged_object.p2 or
                            obj.p2 == self.dragged_object.p1 or obj.p2 == self.dragged_object.p2):
                            connected_lines.append(obj)
                            # if是固定长度线段，添加到特定列表
                            if obj.fixed_length:
                                shared_fixed_lines.append(obj)
                
                # 对所有相关的固定长度线段应用约束
                for line in shared_fixed_lines:
                    # 查找共享的端点
                    shared_point = None
                    if line.p1 == self.dragged_object.p1 or line.p1 == self.dragged_object.p2:
                        shared_point = line.p1
                    else:
                        shared_point = line.p2
                    
                    # 应用固定长度约束，保持共享点的位置
                    line._enforce_fixed_length(drag_point=shared_point)
                    
                    # 验证固定长度是否正确应用
                    current_length = line.length()
                    if abs(current_length - line._original_length) > 0.0001:
                        print(f"拖拽相关线段结束: 线段{line.name}长度不符，当前={current_length}，应为={line._original_length}")
                        line._enforce_fixed_length()
                
                # 更新所有相连线段的名称位置
                for line in connected_lines:
                    self.name_position_manager.update_object_changed(line)
            
            # 拖拽结束后更新名称位置
            if isinstance(self.dragged_object, GeometryObject):
                self.name_position_manager.update_object_changed(self.dragged_object)
                
                # if是点，更新所有与该点相连的线段及其端点的名称位置
                if isinstance(self.dragged_object, Point):
                    connected_lines = []
                    for obj in self.objects:
                        if isinstance(obj, Line) and (obj.p1 == self.dragged_object or obj.p2 == self.dragged_object):
                            connected_lines.append(obj)
                            self.name_position_manager.update_object_changed(obj)
                            # 更新线段另一个端点的名称位置
                            if obj.p1 == self.dragged_object:
                                self.name_position_manager.update_object_changed(obj.p2)
                            else:
                                self.name_position_manager.update_object_changed(obj.p1)
                    
                    # 更新所有与这些线段相连的其他线段
                    for line1 in connected_lines:
                        for line2 in self.objects:
                            if isinstance(line2, Line) and line2 != line1 and (
                                line2.p1 == line1.p1 or line2.p1 == line1.p2 or
                                line2.p2 == line1.p1 or line2.p2 == line1.p2
                            ):
                                self.name_position_manager.update_object_changed(line2)
                
                # if是线段，更新其两个端点的名称位置和所有相连线段
                elif isinstance(self.dragged_object, Line):
                    self.name_position_manager.update_object_changed(self.dragged_object.p1)
                    self.name_position_manager.update_object_changed(self.dragged_object.p2)
                    
                    # 更新所有与端点相连的其他线段
                    for obj in self.objects:
                        if isinstance(obj, Line) and obj != self.dragged_object and (
                            obj.p1 == self.dragged_object.p1 or obj.p1 == self.dragged_object.p2 or
                            obj.p2 == self.dragged_object.p1 or obj.p2 == self.dragged_object.p2
                        ):
                            self.name_position_manager.update_object_changed(obj)
            
            # if拖动的是固定长度线段的端点，确保两个端点的名称位置更新
            if self.dragged_line is not None:
                self.name_position_manager.update_object_changed(self.dragged_line)
                self.name_position_manager.update_object_changed(self.dragged_line.p1)
                self.name_position_manager.update_object_changed(self.dragged_line.p2)
                
                # 更新所有与固定长度线段的端点相连的其他线段
                for obj in self.objects:
                    if isinstance(obj, Line) and obj != self.dragged_line and (
                        obj.p1 == self.dragged_line.p1 or obj.p1 == self.dragged_line.p2 or
                        obj.p2 == self.dragged_line.p1 or obj.p2 == self.dragged_line.p2
                    ):
                        self.name_position_manager.update_object_changed(obj)
            
            # if拖动了多边形，进行重新检测并恢复属性
            if was_polygon_dragged:
                try:
                    # 保存当前活跃多边形
                    old_active_polygons = self.active_polygons.copy()
                    
                    # 更新高度垂足点
                    from .draw import update_all_height_foot_points, PolygonDetector
                    update_all_height_foot_points(self)
                    
                    # 重新检测多边形
                    detector = PolygonDetector(self)
                    detected_polygons = detector.detect_polygons()
                    
                    # 恢复属性
                    restored_polygons = self.restore_polygon_attributes(old_active_polygons, detected_polygons)
                    
                    # 强制恢复被拖动多边形的属性
                    found_dragged_polygon = None
                    for polygon in restored_polygons:
                        current_vertex_ids = tuple(sorted([id(v) for v in polygon.vertices]))
                        if current_vertex_ids == dragged_polygon_vertex_ids:
                            found_dragged_polygon = polygon
                            # 应用保存的完整属性
                            found_dragged_polygon.fill_color = dragged_polygon_attrs['fill_color']
                            found_dragged_polygon.show_fill = dragged_polygon_attrs['show_fill']
                            found_dragged_polygon.show_diagonals = dragged_polygon_attrs['show_diagonals']
                            found_dragged_polygon.show_medians = dragged_polygon_attrs['show_medians']
                            found_dragged_polygon.show_heights = dragged_polygon_attrs['show_heights']
                            found_dragged_polygon.show_angle_bisectors = dragged_polygon_attrs['show_angle_bisectors']
                            found_dragged_polygon.show_midlines = dragged_polygon_attrs['show_midlines']
                            found_dragged_polygon.show_incircle = dragged_polygon_attrs['show_incircle']
                            found_dragged_polygon.show_circumcircle = dragged_polygon_attrs['show_circumcircle']
                            
                            # 特别确保手动创建的多边形的source属性被正确保留
                            if is_manual_polygon:
                                found_dragged_polygon.source = 'manual'
                            else:
                                found_dragged_polygon.source = dragged_polygon_attrs['source']
                            
                            # 恢复特殊属性
                            if 'selected_heights' in dragged_polygon_attrs:
                                found_dragged_polygon.selected_heights = dragged_polygon_attrs['selected_heights'].copy()
                            if 'selected_angles' in dragged_polygon_attrs:
                                found_dragged_polygon.selected_angles = dragged_polygon_attrs['selected_angles'].copy()
                            if 'height_feet' in dragged_polygon_attrs:
                                found_dragged_polygon.height_feet = dragged_polygon_attrs['height_feet'].copy()
                            break
                
                    # 更新活跃多边形列表
                    self.active_polygons = restored_polygons
                    
                    # if拖动的多边形未在列表中（可能因为restore逻辑），确保它在列表中
                    if found_dragged_polygon and found_dragged_polygon not in self.active_polygons:
                         # 检查是否有顶点匹配的多边形已经在列表中
                        already_exists = False
                        for poly in self.active_polygons:
                             if tuple(sorted([id(v) for v in poly.vertices])) == dragged_polygon_vertex_ids:
                                 already_exists = True
                                 break
                        if not already_exists:
                            self.active_polygons.append(found_dragged_polygon)

                    # 多边形属性已更新

                except Exception as e:
                    print(f"拖动多边形结束时出错: {str(e)}")
                    # 尝试恢复原始颜色和填充状态
                    if self.dragged_object and hasattr(self.dragged_object, 'fill_color') and original_fill_color:
                        self.dragged_object.fill_color = original_fill_color
                    if self.dragged_object and hasattr(self.dragged_object, 'show_fill') and original_show_fill is not None:
                        self.dragged_object.show_fill = original_show_fill
                
            # if拖拽结束后需要更新交点 (放在属性恢复之后)
            if self.intersection_manager.show_intersections:
                self.intersection_manager.update_all_intersections()
        
        # 处理线段绘制完成
        elif self.drawing_line and self.temp_line_start:
            # 获取真实鼠标位置
            cursor_global_pos = self.cursor().pos()
            cursor_local_pos = self.mapFromGlobal(cursor_global_pos)
            
            # 转换为考虑画布偏移的坐标
            canvas_pos = QPoint(cursor_local_pos.x() - self.canvas_offset.x(), 
                                cursor_local_pos.y() - self.canvas_offset.y())
            
            # 查找终点
            end_point = self.find_point_at(canvas_pos)
            
            # if点击位置没有点，则创建新点
            if not end_point:
                point_pos = self.get_snap_position(canvas_pos) if self.snap_enabled else canvas_pos
                end_point = self.create_point_at(point_pos)
            
            # 防止创建自环（起点和终点相同）
            if end_point != self.temp_line_start:
                # 创建线段对象
                new_line = Line(self.temp_line_start, end_point)
                
                # 自动生成线段名称
                if self.temp_line_start.name and end_point.name:
                    # if两个端点都有名称，使用它们的名称创建线段名称
                    new_line.name = f"{self.temp_line_start.name}{end_point.name}"
                else:
                    # 否则生成一个序号命名
                    line_count = len([obj for obj in self.objects if isinstance(obj, Line)])
                    new_line.name = f"l{line_count+1}"
                
                self.add_object(new_line)
                
                # 选中新创建的线段
                if self.selected_object:
                    self.selected_object.selected = False
                self.selected_object = new_line
                new_line.selected = True
                self.object_selected.emit(new_line)
                
                # 更新交点
                if self.intersection_manager.show_intersections:
                    self.intersection_manager.update_all_intersections()
        
        # 处理连接点完成
        elif self.connecting and self.connect_start:
            # 获取真实鼠标位置
            cursor_global_pos = self.cursor().pos()
            cursor_local_pos = self.mapFromGlobal(cursor_global_pos)
            
            # 转换为考虑画布偏移的坐标
            canvas_pos = QPoint(cursor_local_pos.x() - self.canvas_offset.x(), 
                                cursor_local_pos.y() - self.canvas_offset.y())
            
            # 查找终点 - 先尝试找普通点
            end_point = self.find_point_at(canvas_pos)
            
            # if没找到点，检查是否点击了线段端点
            if not end_point:
                endpoint = self.find_line_endpoint_at(canvas_pos)
                if endpoint:
                    # 使用线段端点作为终点
                    end_point = endpoint[1]
            
            # if点击位置没有点，则创建新点
            if not end_point:
                point_pos = self.get_snap_position(canvas_pos) if self.snap_enabled else canvas_pos
                end_point = self.create_point_at(point_pos)
            
            # 防止创建自环（起点和终点相同）
            if end_point != self.connect_start:
                # 创建线段对象
                new_line = Line(self.connect_start, end_point)
                
                # 自动生成线段名称
                if self.connect_start.name and end_point.name:
                    # if两个端点都有名称，使用它们的名称创建线段名称
                    new_line.name = f"{self.connect_start.name}{end_point.name}"
                else:
                    # 否则生成一个序号命名
                    line_count = len([obj for obj in self.objects if isinstance(obj, Line)])
                    new_line.name = f"l{line_count+1}"
                
                self.add_object(new_line)
                
                # 选中新创建的线段
                if self.selected_object:
                    self.selected_object.selected = False
                self.selected_object = new_line
                new_line.selected = True
                self.object_selected.emit(new_line)
                
                # 更新交点
                if self.intersection_manager.show_intersections:
                    self.intersection_manager.update_all_intersections()
        
        # 清理拖拽状态
        self.dragging = False
        self.dragged_object = None
        self.dragged_line = None
        self.dragged_point = None
        
        # 更新约束系统
        if points_moved:
            self.constraint_manager.update_all_constraints()
        # 清理线段绘制状态
        self.drawing_line = False
        self.temp_line_start = None
        # 清理连接状态
        self.connecting = False
        self.connect_start = None
        
        # if有点被移动，需要更新垂足点 (放在拖动处理之后)
        if points_moved:
            # 导入函数
            from .draw import update_all_height_foot_points
            # 更新所有垂足点
            update_all_height_foot_points(self)
        
        self.update()
        
    def keyPressEvent(self, event):
        """键盘按下事件"""
        if event.key() == Qt.Key_Delete:
            # 删除选中对象
            if self.selected_object:
                self.remove_object(self.selected_object)
                self.selected_object = None
                self.update()
                
        elif event.key() == Qt.Key_F and self.selected_object:
            # 固定对象
            if isinstance(self.selected_object, Point):
                self.selected_object.toggle_fixed()
                print(f"键盘切换: 点{self.selected_object.name}固定状态为{self.selected_object.fixed}")
                self.update()
            elif isinstance(self.selected_object, Line):
                # 记录切换前的状态
                old_state = self.selected_object.fixed_length
                old_length = self.selected_object.length()
                
                # 切换固定长度状态
                self.selected_object.toggle_fixed_length()
                
                # 确保在固定长度时保存当前长度
                if self.selected_object.fixed_length:
                    print(f"键盘切换: 线段{self.selected_object.name}设为固定长度, 长度={self.selected_object._original_length}")
                else:
                    print(f"键盘切换: 线段{self.selected_object.name}取消固定长度, 长度={old_length}")
                    
                # 强制刷新画布
                self.update()
                
        elif event.key() == Qt.Key_Space:
            # 切换画布拖动模式
            self.is_canvas_drag_mode = not self.is_canvas_drag_mode
            
            # if通过工具栏进入了拖动模式，同步两个模式
            if self.drag_mode and not self.is_canvas_drag_mode:
                self.drag_mode = False
                
                # if父窗口有工具栏按钮，更新按钮状态
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'canvas_drag_action'):
                        parent.canvas_drag_action.setChecked(False)
                        break
                    parent = parent.parent()
            
            if self.is_canvas_drag_mode:
                self.setCursor(Qt.OpenHandCursor)  # 设置手型光标
            else:
                self.setCursor(Qt.ArrowCursor)  # 恢复默认光标
            self.update()
    
    def try_snap_endpoints(self, pos):
        """尝试吸附端点"""
        if not self.snap_enabled or not self.snap_highlight_pos:
            return False
            
        # 只在选中线段时执行吸附
        if not self.selected_object or not isinstance(self.selected_object, Line):
            return False
            
        # 获取被拖拽的点
        line = self.selected_object
        
        if self.dragged_point:
            # if拖拽的是线段的端点，且吸附目标是点对象
            if isinstance(self.snap_highlight_pos, Point):
                # 替换端点引用
                if self.dragged_point == line.p1:
                    line.p1 = self.snap_highlight_pos
                elif self.dragged_point == line.p2:
                    line.p2 = self.snap_highlight_pos
                return True
                
        return False
        
    def update_snap_highlight(self, pos):
        """更新吸附高亮"""
        if not self.snap_enabled:
            self.snap_highlight_pos = None
            return
            
        pos_point = QPointF(pos)
        
        # 使用更高效的方法查找最近的点，通过减少不必要的计算
        min_dist_squared = self.snap_threshold * self.snap_threshold
        closest_point = None
        
        for obj in self.objects:
            # 跳过当前拖动的对象
            if self.dragging and obj == self.dragged_object:
                continue
                
            # 对于点对象，快速计算距离平方而不是开平方根，提高性能
            if isinstance(obj, Point):
                # 使用距离平方比较，避免计算开方提高性能
                dist_squared = (pos.x() - obj.x)**2 + (pos.y() - obj.y)**2
                if dist_squared < min_dist_squared:
                    min_dist_squared = dist_squared
                    closest_point = obj
                    
        self.snap_highlight_pos = closest_point
        
    def get_snap_position(self, pos):
        """获取吸附位置"""
        if not self.snap_enabled or not self.snap_highlight_pos:
            return pos
            
        if isinstance(self.snap_highlight_pos, Point):
            return QPointF(self.snap_highlight_pos.x, self.snap_highlight_pos.y)
            
        return pos
        
    def select_object_at(self, pos):
        """选择指定位置的对象"""
        qpos = QPointF(pos)
        
        # 首先检查是否点击了任何点 - 点应该优先于线段
        for obj in reversed(self.objects):
            if isinstance(obj, Point) and obj.contains(qpos):
                if self.selected_object != obj:
                    self.selected_object = obj
                    self.object_selected.emit(obj)
                    self.update()
                return obj
                
        # if没有点击到点，再检查线段
        for obj in reversed(self.objects):
            if not isinstance(obj, Point) and not self._is_angle_object(obj) and obj.contains(qpos):
                # 检查是否点击了线段端点
                if isinstance(obj, Line):
                    near_point = obj.endpoint_near(qpos)
                    if near_point:
                        # if点击了线段端点，直接选择该端点而不是线段
                        if self.selected_object != near_point:
                            self.selected_object = near_point
                            self.object_selected.emit(near_point)
                            self.update()
                        return near_point
                
                if self.selected_object != obj:
                    self.selected_object = obj
                    self.object_selected.emit(obj)
                    self.update()
                return obj
                
        # 检查是否点击了角度对象
        try:
            from .oangle import Angle
            for obj in reversed(self.objects):
                if isinstance(obj, Angle):
                    # 确保所有点都存在
                    if not obj.p1 or not obj.p2 or not obj.p3:
                        continue
                        
                    # 计算角度弧线的半径
                    radius = min(
                        obj.p2.distance_to(obj.p1),
                        obj.p2.distance_to(obj.p3)
                    ) / 4
                    
                    # 确保半径在合理范围内
                    radius = max(20, min(50, radius))
                    
                    # 检查点击位置是否在角度顶点附近的区域
                    center = QPointF(obj.p2.x, obj.p2.y)
                    dist = math.sqrt((qpos.x() - center.x())**2 + (qpos.y() - center.y())**2)
                    
                    # if在角度顶点的2倍半径范围内，认为选中了角度
                    if dist <= radius * 2:
                        if self.selected_object != obj:
                            self.selected_object = obj
                            self.object_selected.emit(obj)
                            self.update()
                        return obj
        except (ImportError, AttributeError):
            # ifoangle模块不存在或Angle类不存在，忽略错误
            pass
                
        # if没有找到对象，取消选择
        if self.selected_object:
            self.selected_object = None
            self.update()
        return None
        
    def _is_angle_object(self, obj):
        """检查对象是否为角度对象"""
        try:
            from .oangle import Angle
            return isinstance(obj, Angle)
        except (ImportError, AttributeError):
            return False
        
    def find_point_at(self, pos, threshold=10):
        """查找指定位置的点
        
        参数:
        - pos: 要查找的位置
        - threshold: if没有精确匹配，使用的距离阈值
        
        返回:
        - 找到的点对象，或者None
        """
        if isinstance(pos, QPoint):
            qpos = QPointF(pos)
        elif isinstance(pos, QPointF):
            qpos = pos
        else:
            # 尝试转换自定义点对象
            try:
                qpos = QPointF(pos.x, pos.y)
            except AttributeError:
                return None
        
        # 先查找精确匹配
        for obj in reversed(self.objects):
            if isinstance(obj, Point) and obj.contains(qpos):
                return obj
                
        # if没有精确匹配，尝试使用距离阈值查找最近的点
        nearest = None
        min_dist = threshold
        
        for obj in self.objects:
            if isinstance(obj, Point):
                dist = math.sqrt((qpos.x() - obj.x)**2 + (qpos.y() - obj.y)**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest = obj
                    
        return nearest
        
    def find_nearest_point(self, pos, threshold=10):
        """查找最近的点，在阈值内
        
        注意：此方法已被优化的find_point_at方法替代，保留此方法以兼容现有代码
        """
        return self.find_point_at(pos, threshold=threshold)
        
    def add_object(self, obj, skip_intersection_update=False):
        """添加几何对象到画布"""
        self.mark_state_changed()  # 标记状态改变
        from .geometry import Line, Point  # 添加导入，避免未定义错误
        
        # 添加对象
        if obj not in self.objects:
            self.objects.append(obj)
        
        # 处理线段的端点
        if isinstance(obj, Line):
            # 确保线段的端点也被添加
            if obj.p1 not in self.objects:
                self.objects.append(obj.p1)
            if obj.p2 not in self.objects:
                self.objects.append(obj.p2)
                
            # 尝试使用已有点替换线段的端点
            for point in self.objects:
                if isinstance(point, Point):
                    if abs(point.x - obj.p1.x) < 0.001 and abs(point.y - obj.p1.y) < 0.001 and point != obj.p1:
                        obj.p1 = point
                    if abs(point.x - obj.p2.x) < 0.001 and abs(point.y - obj.p2.y) < 0.001 and point != obj.p2:
                        obj.p2 = point
                        
            # if线段连接的两个端点相同，跳过添加
            if obj.p1 == obj.p2:
                self.objects.remove(obj)
                return
        
        # if是多边形，添加到活跃多边形列表
        from .draw import Polygon
        if isinstance(obj, Polygon):
            if obj not in self.active_polygons:
                self.active_polygons.append(obj)
                # 确保多边形有正确的初始属性
                if not hasattr(obj, 'show_fill'):
                    obj.show_fill = True
                if not hasattr(obj, 'fill_color'):
                    obj.fill_color = QColor(230, 230, 255, 100)  # 默认填充颜色
                
                # if没有设置来源，默认为自动检测
                if not hasattr(obj, 'source'):
                    obj.source = 'auto'
            
            # 多边形属性通过JSON序列化完整保存
            # 新多边形已添加
        
        # 更新所有交点，但避免递归调用
        if self.intersection_manager.show_intersections and not skip_intersection_update:
            self.intersection_manager.update_all_intersections()
            
        # 添加后更新所有名称位置
        if hasattr(self, 'name_position_manager'):
            self.name_position_manager.update_all_name_positions()
            
        self.update()
        
    def remove_object(self, obj):
        """从画布中移除几何对象"""
        self.mark_state_changed()  # 标记状态改变
        if obj in self.objects:
            # if是点，先删除与之相连的所有线段，但保留其他端点
            from .geometry import Point, Line
            if isinstance(obj, Point):
                related_lines = [line for line in list(self.objects) if isinstance(line, Line) and (line.p1 == obj or line.p2 == obj)]
                for line in related_lines:
                    # 递归删除线段，这里不会删除另一个端点
                    self.remove_object(line)

            self.objects.remove(obj)
            
            # if移除的是线段，需要更新交点
            if isinstance(obj, Line) and self.intersection_manager.show_intersections:
                # 查找并移除与该线段相关的所有交点
                related_intersections = [i for i in self.intersection_manager.intersections
                                       if obj in i.parent_lines]
                for intersection in related_intersections:
                    self.intersection_manager.intersections.remove(intersection)
                    if intersection in self.objects:
                        self.objects.remove(intersection)
                
                # 更新所有交点
                self.intersection_manager.update_all_intersections()
            
            # if被选中的对象被移除，清除选中状态
            if self.selected_object == obj:
                self.selected_object = None
            
            self.update()
            return True
        return False
        
    def set_tool(self, tool_name):
        """设置当前工具"""
        self.current_tool = tool_name
        
        # 取消可能的临时操作
        if tool_name != "line" and self.drawing_line:
            self.drawing_line = False
            self.temp_line_start = None
            
        if tool_name != "connect" and self.connecting:
            self.connecting = False
            self.connect_start = None
            
        self.update()
        
    def toggle_snap(self, enabled):
        """切换吸附功能"""
        self.snap_enabled = enabled
        self.update()
        
    def show_context_menu(self, position):
        """显示右键菜单"""
        # 创建菜单
        menu = QMenu(self)
        
        # 添加画布拖动模式选项
        canvas_drag_action = QAction("画布拖动模式", self)
        canvas_drag_action.setCheckable(True)
        canvas_drag_action.setChecked(self.is_canvas_drag_mode)
        canvas_drag_action.triggered.connect(self._toggle_canvas_drag_mode)
        menu.addAction(canvas_drag_action)
        
        # 添加"显示网格"选项
        grid_action = QAction("显示网格", self)
        grid_action.setCheckable(True)
        grid_action.setChecked(self.show_grid)
        grid_action.triggered.connect(self.toggle_grid)
        menu.addAction(grid_action)
        
        # 添加"启用吸附"选项
        snap_action = QAction("启用吸附", self)
        snap_action.setCheckable(True)
        snap_action.setChecked(self.snap_enabled)
        snap_action.triggered.connect(self.toggle_snap)
        menu.addAction(snap_action)
        
        # 添加显示名称选项
        menu.addSeparator()
        
        # 显示点名称
        point_names_action = QAction("显示点名称", self)
        point_names_action.setCheckable(True)
        point_names_action.setChecked(self.show_point_names)
        point_names_action.triggered.connect(lambda checked: self.toggle_show_point_names(checked))
        menu.addAction(point_names_action)
        
        # 显示线段名称
        line_names_action = QAction("显示线段名称", self)
        line_names_action.setCheckable(True)
        line_names_action.setChecked(self.show_line_names)
        line_names_action.triggered.connect(lambda checked: self.toggle_show_line_names(checked))
        menu.addAction(line_names_action)
        
        # 显示交点
        intersections_action = QAction("显示交点", self)
        intersections_action.setCheckable(True)
        intersections_action.setChecked(self.intersection_manager.show_intersections)
        intersections_action.triggered.connect(lambda checked: self.toggle_show_intersections(checked))
        menu.addAction(intersections_action)
        
        # if有选中对象，添加对象相关菜单项
        if self.selected_object:
            menu.addSeparator()
            
            if isinstance(self.selected_object, Point):
                # if不是交点，可以固定位置
                if not (hasattr(self.selected_object, 'is_intersection') and self.selected_object.is_intersection):
                    # 切换点固定状态
                    fix_point_action = QAction("固定位置" if not self.selected_object.fixed else "取消固定", self)
                    fix_point_action.triggered.connect(self.toggle_point_fixed)
                    menu.addAction(fix_point_action)
            
            elif isinstance(self.selected_object, Line):
                # 切换线段固定长度状态
                fix_line_action = QAction("固定长度" if not self.selected_object.fixed_length else "取消固定长度", self)
                fix_line_action.triggered.connect(self.toggle_line_fixed)
                menu.addAction(fix_line_action)
                
            # 添加角度固定操作
            try:
                from .oangle import Angle
                if isinstance(self.selected_object, Angle):
                    # 切换角度固定状态
                    fix_angle_action = QAction("固定角度" if not self.selected_object.fixed else "取消固定角度", self)
                    fix_angle_action.triggered.connect(self.toggle_angle_fixed)
                    menu.addAction(fix_angle_action)
                    
                    # 设置角度值
                    if not self.selected_object.fixed:
                        set_angle_action = QAction("设置角度值", self)
                        set_angle_action.triggered.connect(self.set_angle_value)
                        menu.addAction(set_angle_action)
            except (ImportError, AttributeError):
                pass
            
        # 在点击位置显示菜单
        menu.exec_(self.mapToGlobal(position))
        
    def toggle_point_fixed(self):
        """切换点的固定状态"""
        if self.selected_object and isinstance(self.selected_object, Point):
            self.selected_object.toggle_fixed()
            self.update()
            
    def toggle_line_fixed(self):
        """切换线的固定长度状态"""
        if self.selected_object and isinstance(self.selected_object, Line):
            # 记录切换前的状态
            old_state = self.selected_object.fixed_length
            old_length = self.selected_object.length()
            
            # 切换固定长度状态
            self.selected_object.toggle_fixed_length()
            
            # 打印调试信息
            if self.selected_object.fixed_length:
                print(f"右键菜单切换: 线段{self.selected_object.name}设为固定长度, 长度={self.selected_object._original_length}")
            else:
                print(f"右键菜单切换: 线段{self.selected_object.name}取消固定长度, 长度={old_length}")
                
            self.update()
            
    def create_point_at(self, pos):
        """在指定位置创建一个新点"""
        # 确保pos不为None并且有x和y方法
        if pos is None:
            # 使用默认位置作为备用
            pos_x, pos_y = 100, 100  
        elif isinstance(pos, QPointF) or isinstance(pos, QPoint):
            # if是Qt点类型，直接使用x()和y()方法
            pos_x, pos_y = pos.x(), pos.y()
        else:
            # 尝试作为自定义点对象处理
            try:
                pos_x, pos_y = pos.x, pos.y
            except AttributeError:
                # if都不适用，使用默认位置
                pos_x, pos_y = 100, 100
        
        # 在此位置已转换为画布坐标，无需再计算偏移
        # 检查是否在这个位置已经有一个点，if有，直接返回那个点
        existing_point = self.find_point_at(QPointF(pos_x, pos_y), threshold=5)
        if existing_point:
            return existing_point
            
        # 检查是否有线段端点在这个位置，if有，直接返回那个端点
        endpoint_result = self.find_line_endpoint_at(QPointF(pos_x, pos_y), threshold=5)
        if endpoint_result:
            return endpoint_result[1]
        
        # if确实需要创建新点，创建一个
        point_name = f"P{len([obj for obj in self.objects if isinstance(obj, Point) and not hasattr(obj, 'is_intersection')])+1}"
        new_point = Point(float(pos_x), float(pos_y), point_name)
        self.add_object(new_point)
        
        # 检查新点是否与多边形边相交
        for polygon in self.active_polygons:
            polygon.check_edge_intersections(self)
            
        return new_point
        
    def toggle_grid(self):
        """切换网格显示"""
        self.show_grid = not self.show_grid
        self.update()
        
    def toggle_show_point_names(self, show=None):
        """切换显示点名称"""
        if show is None:
            self.show_point_names = not self.show_point_names
        else:
            self.show_point_names = show
        self.update()
        
    def toggle_show_line_names(self, show=None):
        """切换显示线段名称"""
        if show is None:
            self.show_line_names = not self.show_line_names
        else:
            self.show_line_names = show
        self.update()
        
    def toggle_show_intersections(self, show=None):
        """切换是否显示交点"""
        return self.intersection_manager.toggle_intersections()
        
    def get_intersection_state(self):
        """获取当前交点显示状态"""
        return self.intersection_manager.show_intersections
        
    def find_line_endpoint_at(self, pos, threshold=10):
        """查找在给定位置的线段端点
        
        返回:
        - None: 没有找到端点
        - (line, point): 找到的线段和端点
        """
        if isinstance(pos, QPoint):
            qpos = QPointF(pos)
        elif isinstance(pos, QPointF):
            qpos = pos
        else:
            # 尝试转换自定义点对象
            try:
                qpos = QPointF(pos.x, pos.y)
            except AttributeError:
                return None
                
        # 先精确查找
        for obj in reversed(self.objects):
            if isinstance(obj, Line):
                # 检查端点1
                if obj.p1.contains(qpos):
                    return obj, obj.p1
                    
                # 检查端点2
                if obj.p2.contains(qpos):
                    return obj, obj.p2
        
        # if没有精确匹配，则尝试使用距离阈值查找最近的端点
        min_dist = threshold
        nearest_endpoint = None
        nearest_line = None
        
        for obj in reversed(self.objects):
            if isinstance(obj, Line):
                # 计算到端点1的距离
                dx1 = qpos.x() - obj.p1.x
                dy1 = qpos.y() - obj.p1.y
                dist1 = math.sqrt(dx1*dx1 + dy1*dy1)
                
                # 计算到端点2的距离
                dx2 = qpos.x() - obj.p2.x
                dy2 = qpos.y() - obj.p2.y
                dist2 = math.sqrt(dx2*dx2 + dy2*dy2)
                
                # 更新最近的端点
                if dist1 < min_dist:
                    min_dist = dist1
                    nearest_endpoint = obj.p1
                    nearest_line = obj
                    
                if dist2 < min_dist:
                    min_dist = dist2
                    nearest_endpoint = obj.p2
                    nearest_line = obj
        
        if nearest_endpoint and nearest_line:
            return nearest_line, nearest_endpoint
                    
        return None
        
    def find_polygon_at(self, pos):
        """检测点击位置是否在多边形内"""
        # 先检查点是否在任何已有多边形内，避免不必要的多边形检测
        x, y = pos.x(), pos.y()
        check_point = QPointF(x, y)
        
        # 首先检查是否直接点击在现有多边形上，特别是手动创建的多边形
        for polygon in self.active_polygons:
            if polygon.contains_point(check_point):
                # if是手动创建的多边形或有保护标志，直接返回，不进行重新检测
                if (hasattr(polygon, 'source') and polygon.source == 'manual') or \
                   hasattr(polygon, '_preserve_attributes') and polygon._preserve_attributes:
                    return polygon
        
        # 只有在未找到或未保护的情况下，再进行自动检测
        # 获取所有需要保护的多边形（带有_preserve_attributes标志或手动创建的）
        protected_polygons = []
        for polygon in self.active_polygons:
            if (hasattr(polygon, 'source') and polygon.source == 'manual') or \
               (hasattr(polygon, '_preserve_attributes') and polygon._preserve_attributes):
                protected_polygons.append(polygon)
        
        # 强制刷新多边形检测，确保包含最新的交点
        from .draw import PolygonDetector
        detector = PolygonDetector(self)
        detected_polygons = detector.detect_polygons()
        
        # 确保保护的多边形被添加到检测结果中
        for protected_polygon in protected_polygons:
            if protected_polygon not in detected_polygons:
                detected_polygons.append(protected_polygon)
        
        # 保存已有多边形的属性
        polygon_attributes = {}
        if self.active_polygons:
            for polygon in self.active_polygons:
                # if是手动创建的多边形，确保保留在active_polygons中
                if hasattr(polygon, 'source') and polygon.source == 'manual':
                    if polygon not in detected_polygons:
                        detected_polygons.append(polygon)
                
                polygon_id = tuple(sorted([id(vertex) for vertex in polygon.vertices]))
                polygon_attributes[polygon_id] = {
                    'fill_color': polygon.fill_color,
                    'show_fill': polygon.show_fill,
                    'show_diagonals': polygon.show_diagonals,
                    'show_medians': polygon.show_medians,
                    'show_heights': polygon.show_heights,
                    'show_angle_bisectors': polygon.show_angle_bisectors,
                    'show_midlines': polygon.show_midlines,
                    'show_incircle': polygon.show_incircle,
                    'show_circumcircle': polygon.show_circumcircle,
                    'source': getattr(polygon, 'source', 'auto')  # 保存多边形来源（手动/自动）
                }
                # if是三角形，保存选择的高和角平分线
                if hasattr(polygon, 'selected_heights'):
                    polygon_attributes[polygon_id]['selected_heights'] = polygon.selected_heights.copy()
                if hasattr(polygon, 'selected_angles'):
                    polygon_attributes[polygon_id]['selected_angles'] = polygon.selected_angles.copy()
                # 保存高度垂足点信息
                if hasattr(polygon, 'height_feet'):
                    polygon_attributes[polygon_id]['height_feet'] = polygon.height_feet
        
        if detected_polygons:
            # 将属性从旧多边形复制到新检测到的多边形
            for new_polygon in detected_polygons:
                # 跳过手动创建的多边形和有保护标志的多边形，避免属性被覆盖
                if hasattr(new_polygon, 'source') and new_polygon.source == 'manual':
                    continue
                if hasattr(new_polygon, '_preserve_attributes') and new_polygon._preserve_attributes:
                    continue
                    
                new_vertices_ids = set([id(v) for v in new_polygon.vertices])
                best_match = None
                best_match_count = 0
                best_match_attrs = None
                
                # 查找匹配的旧多边形
                for old_polygon_id, attrs in polygon_attributes.items():
                    # 检查顶点是否匹配（通过比较ID集合的交集）
                    old_vertices_ids = set(old_polygon_id)
                    matching_vertices = len(new_vertices_ids & old_vertices_ids)
                    
                    # if匹配度更高，更新最佳匹配
                    if matching_vertices > best_match_count:
                        best_match_count = matching_vertices
                        best_match_attrs = attrs
                
                # if找到匹配，且匹配度超过50%，复制属性
                if best_match_attrs and best_match_count >= len(new_polygon.vertices) // 2:
                    # 复制属性
                    new_polygon.fill_color = best_match_attrs.get('fill_color', new_polygon.fill_color)
                    new_polygon.show_fill = best_match_attrs.get('show_fill', new_polygon.show_fill)
                    new_polygon.show_diagonals = best_match_attrs.get('show_diagonals', new_polygon.show_diagonals)
                    new_polygon.show_medians = best_match_attrs.get('show_medians', new_polygon.show_medians)
                    new_polygon.show_heights = best_match_attrs.get('show_heights', new_polygon.show_heights)
                    new_polygon.show_angle_bisectors = best_match_attrs.get('show_angle_bisectors', new_polygon.show_angle_bisectors)
                    new_polygon.show_midlines = best_match_attrs.get('show_midlines', new_polygon.show_midlines)
                    new_polygon.show_incircle = best_match_attrs.get('show_incircle', new_polygon.show_incircle)
                    new_polygon.show_circumcircle = best_match_attrs.get('show_circumcircle', new_polygon.show_circumcircle)
                    
                    # if有三角形特殊属性，也复制
                    if 'selected_heights' in best_match_attrs:
                        new_polygon.selected_heights = best_match_attrs['selected_heights'].copy()
                    if 'selected_angles' in best_match_attrs:
                        new_polygon.selected_angles = best_match_attrs['selected_angles'].copy()
                    # 复制高度垂足点信息
                    if 'height_feet' in best_match_attrs:
                        new_polygon.height_feet = best_match_attrs['height_feet']
            
            # 更新活跃多边形列表，确保保留手动创建的多边形和有保护标志的多边形
            preserved_polygons = [p for p in self.active_polygons if 
                               ((hasattr(p, 'source') and p.source == 'manual') or 
                                (hasattr(p, '_preserve_attributes') and p._preserve_attributes))]
            new_auto_polygons = [p for p in detected_polygons if 
                               (not hasattr(p, 'source') or p.source != 'manual') and
                               (not hasattr(p, '_preserve_attributes') or not p._preserve_attributes)]
            
            # 合并保护和自动多边形
            self.active_polygons = preserved_polygons + new_auto_polygons
            
            # 多边形属性已更新
        
        # 检查点是否在任何活跃多边形内
        for polygon in self.active_polygons:
            if polygon.contains_point(check_point):
                return polygon
        return None
        
    def check_fixed_lengths(self):
        """检查并强制维持所有固定长度线段的长度"""
        fixed_lines_changed = False
        for obj in self.objects:
            # 跳过当前正在被拖动的固定长度线段，避免冲突
            if self.dragging and self.dragged_line is not None and obj == self.dragged_line:
                continue
                
            if isinstance(obj, Line) and obj.fixed_length and hasattr(obj, '_force_maintain_length') and obj._force_maintain_length:
                current_length = obj.length()
                # if长度偏差超过阈值，调整线段长度
                if abs(current_length - obj._original_length) > 0.001:
                    # 使用不指定拖拽点的方式调整，保持中点不变
                    obj._enforce_fixed_length()
                    fixed_lines_changed = True
        
        # 检查并强制固定角度
        try:
            from .oangle import Angle
            for obj in self.objects:
                if isinstance(obj, Angle) and obj.fixed:
                    obj.enforce_angle()
                    fixed_lines_changed = True
        except (ImportError, AttributeError):
            # ifoangle模块不存在或Angle类不存在，忽略错误
            pass
            
        # if有线段或角度被调整，更新画布
        if fixed_lines_changed:
            self.update()
            
        # 更新自适应比例
        if self.auto_update_scales:
            self.update_all_line_scales()
        
    def toggle_angle_fixed(self):
        """切换角度固定状态"""
        try:
            from .oangle import Angle
            if isinstance(self.selected_object, Angle):
                self.selected_object.fixed = not self.selected_object.fixed
                
                # if设置为固定状态，确保有目标角度值
                if self.selected_object.fixed and self.selected_object.target_angle is None:
                    self.selected_object.target_angle = self.selected_object.calculate_angle()
                    
                # if设置为固定状态，立即应用角度
                if self.selected_object.fixed:
                    self.selected_object.enforce_angle()
                    
                self.update()
        except (ImportError, AttributeError):
            pass
            
    def set_angle_value(self):
        """设置选中角度的目标角度值"""
        try:
            from .oangle import Angle
            from PyQt5.QtWidgets import QInputDialog
            
            if isinstance(self.selected_object, Angle):
                current_angle = self.selected_object.calculate_angle()
                
                # 显示对话框让user输入角度值
                new_angle, ok = QInputDialog.getDouble(
                    self,
                    "设置角度值",
                    "请输入角度值(0-360度):",
                    current_angle,
                    0,
                    360,
                    1
                )
                
                if ok:
                    # 更新角度值并应用
                    self.selected_object.target_angle = new_angle
                    self.selected_object.fixed = True
                    self.selected_object.enforce_angle()
                    self.update()
        except (ImportError, AttributeError):
            pass

    def find_objects_in_selection_rect(self):
        """查找选择框内的所有对象"""
        if not self.selection_rect:
            return
            
        # 在选择对象前先保存所有多边形的属性
        polygon_attributes = {}
        for polygon in self.active_polygons:
            # 使用顶点ID元组作为键，确保能在后续操作中找到匹配的多边形
            polygon_id = tuple(sorted([id(vertex) for vertex in polygon.vertices]))
            polygon_attributes[polygon_id] = {
                'fill_color': polygon.fill_color,
                'show_fill': polygon.show_fill,
                'show_diagonals': polygon.show_diagonals,
                'show_medians': polygon.show_medians,
                'show_heights': polygon.show_heights,
                'show_angle_bisectors': polygon.show_angle_bisectors,
                'show_midlines': polygon.show_midlines,
                'show_incircle': polygon.show_incircle,
                'show_circumcircle': polygon.show_circumcircle,
                'source': getattr(polygon, 'source', 'auto'),  # 保存多边形来源（手动/自动）
                'name': getattr(polygon, 'name', '')  # 添加名称，帮助匹配
            }
            # if是三角形，保存选择的高和角平分线
            if hasattr(polygon, 'selected_heights'):
                polygon_attributes[polygon_id]['selected_heights'] = polygon.selected_heights.copy()
            if hasattr(polygon, 'selected_angles'):
                polygon_attributes[polygon_id]['selected_angles'] = polygon.selected_angles.copy()
            # 保存高度垂足点信息
            if hasattr(polygon, 'height_feet'):
                polygon_attributes[polygon_id]['height_feet'] = polygon.height_feet
            
        # 清空当前选择
        self.selected_objects = []
            
        # 检查所有对象
        for obj in self.objects:
            # 逐个判断不同类型的对象是否在选择框内
            if isinstance(obj, Point):
                # 点检查
                pos = QPointF(obj.x, obj.y)
                if self.selection_rect.contains(pos):
                    self.selected_objects.append(obj)
                    obj.selected = True
            elif isinstance(obj, Line):
                # 线段检查 - if线段的两个端点都在选择框内，则认为线段被选中
                p1 = QPointF(obj.p1.x, obj.p1.y)
                p2 = QPointF(obj.p2.x, obj.p2.y)
                if self.selection_rect.contains(p1) and self.selection_rect.contains(p2):
                    self.selected_objects.append(obj)
                    obj.selected = True
                    
                    # 确保端点也被选中
                    if obj.p1 not in self.selected_objects:
                        self.selected_objects.append(obj.p1)
                        obj.p1.selected = True
                    if obj.p2 not in self.selected_objects:
                        self.selected_objects.append(obj.p2)
                        obj.p2.selected = True
        
        # 选择操作准备就绪
        
        # 选择可能影响多边形，重新检测并恢复属性
        # 更新所有多边形
        moved_points = [obj for obj in self.selected_objects if isinstance(obj, Point)]
        if moved_points:
            # 保存当前活跃多边形列表，用于后续恢复
            old_active_polygons = self.active_polygons.copy()
            
            # 重新检测多边形
            from .draw import PolygonDetector
            detector = PolygonDetector(self)
            detected_polygons = detector.detect_polygons()
            
            if detected_polygons:
                # 使用恢复多边形属性的函数来保持属性
                restored_polygons = self.restore_polygon_attributes(old_active_polygons, detected_polygons)
                
                # 确保每个多边形的属性都正确保留
                for new_polygon in restored_polygons:
                    new_vertices_ids = set([id(v) for v in new_polygon.vertices])
                    
                    # 查找匹配度最高的原多边形
                    best_match_count = 0
                    best_match_attrs = None
                    
                    for old_polygon_id, attrs in polygon_attributes.items():
                        old_vertices_ids = set(old_polygon_id)
                        matching_count = len(new_vertices_ids & old_vertices_ids)
                        
                        # if匹配度更高，更新最佳匹配
                        if matching_count > best_match_count:
                            best_match_count = matching_count
                            best_match_attrs = attrs
                    
                    # if找到匹配，且匹配度超过50%，强制应用保存的属性
                    if best_match_attrs and best_match_count >= len(new_polygon.vertices) // 2:
                        # 复制属性，确保填充颜色和状态被正确应用
                        new_polygon.fill_color = best_match_attrs.get('fill_color', new_polygon.fill_color)
                        new_polygon.show_fill = best_match_attrs.get('show_fill', new_polygon.show_fill)
                        new_polygon.show_diagonals = best_match_attrs.get('show_diagonals', new_polygon.show_diagonals)
                        new_polygon.show_medians = best_match_attrs.get('show_medians', new_polygon.show_medians)
                        new_polygon.show_heights = best_match_attrs.get('show_heights', new_polygon.show_heights)
                        new_polygon.show_angle_bisectors = best_match_attrs.get('show_angle_bisectors', new_polygon.show_angle_bisectors)
                        new_polygon.show_midlines = best_match_attrs.get('show_midlines', new_polygon.show_midlines)
                        new_polygon.show_incircle = best_match_attrs.get('show_incircle', new_polygon.show_incircle)
                        new_polygon.show_circumcircle = best_match_attrs.get('show_circumcircle', new_polygon.show_circumcircle)
                            
                        # 恢复source属性，标记多边形来源（手动/自动）
                        new_polygon.source = best_match_attrs.get('source', 'auto')
                            
                        # 复制特殊属性
                        if 'selected_heights' in best_match_attrs:
                            new_polygon.selected_heights = best_match_attrs['selected_heights'].copy()
                        if 'selected_angles' in best_match_attrs:
                            new_polygon.selected_angles = best_match_attrs['selected_angles'].copy()
                        if 'height_feet' in best_match_attrs:
                            new_polygon.height_feet = best_match_attrs['height_feet'].copy()
                
                # 更新活跃多边形列表
                self.active_polygons = restored_polygons
                
                # 多边形属性已更新
                        
        # 检查框选结束后，是否有选中的对象
        if self.selected_objects:
            # if有选中的对象，将第一个选中的对象作为当前选中对象
            self.selected_object = self.selected_objects[0]
            self.object_selected.emit(self.selected_object)

    def update_selection_rect_from_objects(self):
        """根据所选对象更新选择框"""
        if not self.selected_objects:
            self.selection_rect = None
            return
            
        # 初始化边界值
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        # 计算所有选中对象的边界
        for obj in self.selected_objects:
            if isinstance(obj, Point):
                min_x = min(min_x, obj.x)
                min_y = min(min_y, obj.y)
                max_x = max(max_x, obj.x)
                max_y = max(max_y, obj.y)
            elif isinstance(obj, Line):
                min_x = min(min_x, obj.p1.x, obj.p2.x)
                min_y = min(min_y, obj.p1.y, obj.p2.y)
                max_x = max(max_x, obj.p1.x, obj.p2.x)
                max_y = max(max_y, obj.p1.y, obj.p2.y)
        
        # 在边界上添加一点边距
        padding = 10
        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding
        
        # 创建选择框矩形
        self.selection_rect = QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def restore_polygon_attributes(self, old_polygons, new_polygons):
        """确保新检测到的多边形保留原多边形的视觉属性，优先保留手动创建的多边形。"""
        if not old_polygons:
            return new_polygons
        
        # 1. 保存所有旧多边形的属性，并区分手动/自动
        polygon_attributes = {}
        manual_polygon_instances = {}  # 存储手动多边形的原始实例 {vertex_id_tuple: instance}
        
        for old_polygon in old_polygons:
            polygon_id_tuple = tuple(sorted([id(v) for v in old_polygon.vertices]))
            is_manual = getattr(old_polygon, 'source', 'auto') == 'manual'

            # 保存属性
            attributes = {
                'fill_color': old_polygon.fill_color,
                'show_fill': old_polygon.show_fill,
                'show_diagonals': old_polygon.show_diagonals,
                'show_medians': old_polygon.show_medians,
                'show_heights': old_polygon.show_heights,
                'show_angle_bisectors': old_polygon.show_angle_bisectors,
                'show_midlines': old_polygon.show_midlines,
                'show_incircle': old_polygon.show_incircle,
                'show_circumcircle': old_polygon.show_circumcircle,
                'name': getattr(old_polygon, 'name', ''),
                'source': getattr(old_polygon, 'source', 'auto')
            }
            if hasattr(old_polygon, 'selected_heights'):
                attributes['selected_heights'] = old_polygon.selected_heights.copy()
            if hasattr(old_polygon, 'selected_angles'):
                attributes['selected_angles'] = old_polygon.selected_angles.copy()
            if hasattr(old_polygon, 'height_feet'):
                attributes['height_feet'] = getattr(old_polygon, 'height_feet', {}).copy()
                
            polygon_attributes[polygon_id_tuple] = attributes

            # if是手动多边形，保存实例
            if is_manual:
                manual_polygon_instances[polygon_id_tuple] = old_polygon
                # 在控制台打印调试信息，帮助识别问题
                print(f"保存手动多边形: {old_polygon.name}, 顶点数: {len(old_polygon.vertices)}")

        # 2. 处理新检测到的多边形，尝试匹配并恢复属性
        restored_polygons = []
        matched_manual_ids = set()  # 记录已被新多边形匹配上的手动多边形ID

        for new_polygon in new_polygons:
            new_vertices_ids_tuple = tuple(sorted([id(v) for v in new_polygon.vertices]))
            
            # 检查是否与某个手动多边形完全匹配
            if new_vertices_ids_tuple in manual_polygon_instances:
                # 完全匹配手动多边形 - 直接使用手动多边形的实例，保证其所有属性不变
                manual_instance = manual_polygon_instances[new_vertices_ids_tuple]
                print(f"找到完全匹配的手动多边形: {manual_instance.name}")
                restored_polygons.append(manual_instance)
                matched_manual_ids.add(new_vertices_ids_tuple)
            else:
                # 对于没有完全匹配的，尝试模糊匹配
                if len(new_polygon.vertices) >= 3:
                    # 首先尝试匹配手动多边形
                    best_manual_match = None
                    best_manual_match_count = 0
                    best_match_ratio = 0
                    
                    # 获取新多边形顶点ID集合
                    new_vertices_set = set(id(v) for v in new_polygon.vertices)
                    
                    # 尝试匹配手动多边形
                    for manual_id, manual_instance in manual_polygon_instances.items():
                        if manual_id not in matched_manual_ids:  # 避免重复匹配
                            manual_vertices_set = set(manual_id)
                            # 计算匹配度
                            common_vertices = len(new_vertices_set & manual_vertices_set)
                            # 计算匹配比例
                            match_ratio = common_vertices / max(len(new_vertices_set), len(manual_vertices_set))
                            
                            if common_vertices > best_manual_match_count or \
                               (common_vertices == best_manual_match_count and match_ratio > best_match_ratio):
                                best_manual_match_count = common_vertices
                                best_manual_match = manual_instance
                                best_match_ratio = match_ratio
                    
                    # if有高匹配度的手动多边形，使用该实例
                    if best_manual_match and best_match_ratio >= 0.7:  # 至少70%的顶点匹配
                        print(f"找到模糊匹配的手动多边形: {best_manual_match.name}, 匹配度: {best_match_ratio:.2f}")
                        restored_polygons.append(best_manual_match)
                        # 将匹配到的手动多边形ID标记为已使用
                        matched_manual_ids.add(tuple(sorted([id(v) for v in best_manual_match.vertices])))
                        continue
                
                # 未匹配手动多边形，尝试匹配自动多边形
                best_match_count = 0
                best_match_attrs = None
                new_vertices_set = set(id(v) for v in new_polygon.vertices)
                
                for old_polygon_id, attrs in polygon_attributes.items():
                    # 只与自动多边形进行模糊匹配
                    if attrs.get('source') == 'auto':
                        old_vertices_set = set(old_polygon_id)
                        match_count = len(new_vertices_set & old_vertices_set)
                        
                        if match_count > best_match_count:
                            best_match_count = match_count
                            best_match_attrs = attrs
                
                # if找到匹配的属性，应用这些属性
                if best_match_attrs and best_match_count >= max(1, len(new_polygon.vertices) // 3):
                    new_polygon.fill_color = best_match_attrs.get('fill_color', new_polygon.fill_color)
                    new_polygon.show_fill = best_match_attrs.get('show_fill', new_polygon.show_fill)
                    new_polygon.show_diagonals = best_match_attrs.get('show_diagonals', new_polygon.show_diagonals)
                    new_polygon.show_medians = best_match_attrs.get('show_medians', new_polygon.show_medians)
                    new_polygon.show_heights = best_match_attrs.get('show_heights', new_polygon.show_heights)
                    new_polygon.show_angle_bisectors = best_match_attrs.get('show_angle_bisectors', new_polygon.show_angle_bisectors)
                    new_polygon.show_midlines = best_match_attrs.get('show_midlines', new_polygon.show_midlines)
                    new_polygon.show_incircle = best_match_attrs.get('show_incircle', new_polygon.show_incircle)
                    new_polygon.show_circumcircle = best_match_attrs.get('show_circumcircle', new_polygon.show_circumcircle)
                    new_polygon.source = best_match_attrs.get('source', 'auto')
                    if 'selected_heights' in best_match_attrs:
                        new_polygon.selected_heights = best_match_attrs['selected_heights'].copy()
                    if 'selected_angles' in best_match_attrs:
                        new_polygon.selected_angles = best_match_attrs['selected_angles'].copy()
                    if 'height_feet' in best_match_attrs:
                        new_polygon.height_feet = best_match_attrs['height_feet'].copy()
                    print(f"匹配到自动多边形属性: {new_polygon.name}")
                
                restored_polygons.append(new_polygon)

        # 3. 添加未被匹配上的原始手动多边形实例
        for manual_id, manual_instance in manual_polygon_instances.items():
            if manual_id not in matched_manual_ids:
                # 这个手动多边形没有被匹配，直接保留原始实例
                print(f"保留未匹配的手动多边形: {manual_instance.name}")
                restored_polygons.append(manual_instance)

        # 4. 去重：确保没有顶点完全相同的多边形重复，优先保留手动多边形
        unique_polygons = []
        seen_vertex_ids = set()
        
        # 首先添加所有手动多边形
        for polygon in restored_polygons:
            if getattr(polygon, 'source', 'auto') == 'manual':
                poly_id_tuple = tuple(sorted([id(v) for v in polygon.vertices]))
                if poly_id_tuple not in seen_vertex_ids:
                    unique_polygons.append(polygon)
                    seen_vertex_ids.add(poly_id_tuple)
        
        # 然后添加所有自动多边形
        for polygon in restored_polygons:
            if getattr(polygon, 'source', 'auto') != 'manual':
                poly_id_tuple = tuple(sorted([id(v) for v in polygon.vertices]))
                if poly_id_tuple not in seen_vertex_ids:
                    unique_polygons.append(polygon)
                    seen_vertex_ids.add(poly_id_tuple)

        print(f"恢复后多边形数量: {len(unique_polygons)}")
        
        # 多边形已生成
        
        return unique_polygons

    def _toggle_canvas_drag_mode(self, checked):
        """通过右键菜单切换画布拖动模式"""
        self.is_canvas_drag_mode = checked
        if self.is_canvas_drag_mode:
            self.setCursor(Qt.OpenHandCursor)  # 设置手型光标
            # 清除任何拖动提示消息
            self.clear_drag_message()
        else:
            self.setCursor(Qt.ArrowCursor)  # 恢复默认光标
    
    def _enforce_angle_constraints_during_drag(self):
        """在拖拽过程中实时强制角度约束"""
        if self._angle_enforcing or not self.dragged_object:
            return
        
        self._angle_enforcing = True
        try:
            # 查找所有固定角度
            from .oangle import Angle
            for obj in self.objects:
                if isinstance(obj, Angle) and obj.fixed and obj.target_angle is not None:
                    self._enforce_single_angle_constraint(obj)
        finally:
            self._angle_enforcing = False
    
    def _enforce_single_angle_constraint(self, angle):
        """强制单个角度约束"""
        if not angle.p1 or not angle.p2 or not angle.p3:
            return
        
        # 检查是否有相关点被拖拽
        dragged_point = self.dragged_object
        if not isinstance(dragged_point, Point):
            return
        
        # 确定哪个点被拖拽以及如何调整
        vertex = angle.p2  # 顶点
        point1 = angle.p1  # 第一个边点
        point2 = angle.p3  # 第二个边点
        
        # 检查拖拽的点是否与这个角度相关
        if dragged_point not in [vertex, point1, point2]:
            return
        
        if dragged_point == vertex:
            # 拖拽顶点时不调整角度
            return
        elif dragged_point == point1:
            # 拖拽第一个边点，调整第二个边点
            if not (hasattr(point2, 'fixed') and point2.fixed):  # 确保要调整的点不是固定的
                print(f"角度约束: 拖拽{point1.name}，调整{point2.name}以保持角度{angle.target_angle}°")
                self._adjust_point_for_angle(angle, point2, point1, vertex)
        elif dragged_point == point2:
            # 拖拽第二个边点，调整第一个边点
            if not (hasattr(point1, 'fixed') and point1.fixed):  # 确保要调整的点不是固定的
                print(f"角度约束: 拖拽{point2.name}，调整{point1.name}以保持角度{angle.target_angle}°")
                self._adjust_point_for_angle(angle, point1, point2, vertex)
    
    def _adjust_point_for_angle(self, angle, point_to_adjust, dragged_point, vertex):
        """调整点位置以保持固定角度"""
        import math
        
        # if要调整的点是固定的，不调整
        if hasattr(point_to_adjust, 'fixed') and point_to_adjust.fixed:
            return
        
        # 计算顶点到要调整点的距离（保持不变）
        distance = math.sqrt((point_to_adjust.x - vertex.x)**2 + (point_to_adjust.y - vertex.y)**2)
        
        # 计算被拖拽点相对于顶点的角度
        dragged_angle = math.atan2(dragged_point.y - vertex.y, dragged_point.x - vertex.x)
        
        # 目标角度（弧度）
        target_rad = math.radians(angle.target_angle)
        
        # 计算要调整点的新角度
        # 检查当前角度方向，保持原有的顺时针/逆时针关系
        current_adjust_angle = math.atan2(point_to_adjust.y - vertex.y, point_to_adjust.x - vertex.x)
        
        # 计算角度差
        angle_diff = current_adjust_angle - dragged_angle
        while angle_diff < 0:
            angle_diff += 2 * math.pi
        while angle_diff > 2 * math.pi:
            angle_diff -= 2 * math.pi
        
        # 根据当前方向决定新角度
        if angle_diff <= math.pi:
            # 当前是逆时针方向
            new_angle = dragged_angle + target_rad
        else:
            # 当前是顺时针方向
            new_angle = dragged_angle - target_rad
        
        # 计算新位置
        new_x = vertex.x + distance * math.cos(new_angle)
        new_y = vertex.y + distance * math.sin(new_angle)
        
        # 立即设置新位置
        point_to_adjust.x = new_x
        point_to_adjust.y = new_y

    def clear_drag_message(self):
        """清除拖动提示消息"""
        self.drag_message = ""
        self.update()
    
    def mark_state_changed(self):
        """标记状态已改变"""
        self.state_changed = True
    
    def perform_auto_save(self):
        """执行自动保存（现在只在手动调用时使用）"""
        if self.state_changed:
            try:
                if self.ui_state_manager.auto_save_ui_state():
                    self.state_changed = False
                    print("UI状态保存成功")
                else:
                    print("UI状态保存失败")
            except Exception as e:
                print(f"保存过程中出错: {e}")
    
    def clear_auto_save(self):
        """清除自动保存文件"""
        return self.ui_state_manager.clear_auto_save()
    
    def on_anomaly_detected(self, anomaly_type: str, obj):
        """处理检测到的异常"""
        # 可以在这里添加异常显示逻辑
        pass
    
    def on_anomaly_fixed(self, fix_type: str, obj):
        """处理异常修复"""
        # 异常修复后更新画布
        self.update()
    
    def clear_canvas(self):
        """清空画布"""
        # 清空所有对象
        self.objects.clear()
        self.selected_object = None
        if hasattr(self, 'selected_objects'):
            self.selected_objects.clear()
        if hasattr(self, 'active_polygons'):
            self.active_polygons.clear()
        
        # 清空交点
        if hasattr(self, 'intersection_manager'):
            self.intersection_manager.intersections.clear()
        
        # 清空异常记录
        if hasattr(self, 'geometry_checker'):
            self.geometry_checker.clear_anomaly_records()
        
        # 重置状态
        self.dragged_object = None
        self.dragging = False
        self.group_dragging = False
        self.selection_box = False
        self.selection_rect = None
        
        # 标记状态改变并更新显示
        self.mark_state_changed()
        self.update()
    
    def update_all_line_scales(self):
        """更新所有线段的自适应比例"""
        if not self.adaptive_line_scaling:
            return
            
        canvas_size = (self.width(), self.height())
        
        for obj in self.objects:
            if isinstance(obj, Line):
                # 确保属性存在，为旧对象添加缺失的属性
                if not hasattr(obj, 'adaptive_scale'):
                    obj.adaptive_scale = True
                if not hasattr(obj, '_display_scale'):
                    obj._display_scale = 1.0
                obj.update_display_scale(canvas_size)
    
    def toggle_adaptive_line_scaling(self, enabled):
        """切换线段自适应比例功能"""
        self.adaptive_line_scaling = enabled
        
        # 更新所有线段的adaptive_scale属性，为旧对象添加缺失的属性
        for obj in self.objects:
            if isinstance(obj, Line):
                # 确保属性存在，为旧对象添加缺失的属性
                if not hasattr(obj, 'adaptive_scale'):
                    obj.adaptive_scale = True
                if not hasattr(obj, '_display_scale'):
                    obj._display_scale = 1.0
                obj.adaptive_scale = enabled
                if enabled:
                    obj.update_display_scale((self.width(), self.height()))
                else:
                    obj._display_scale = 1.0
        
        self.update()
        print("画布已清空")