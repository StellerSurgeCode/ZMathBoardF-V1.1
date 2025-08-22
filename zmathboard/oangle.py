#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QCheckBox, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath

from .geometry import GeometryObject, Point

class Angle(GeometryObject):
    """角度对象，用于表示三个点之间的角度"""
    
    def __init__(self, p1=None, p2=None, p3=None, name=""):
        """
        初始化角度对象
        p1: 第一个点
        p2: 顶点
        p3: 第三个点
        角度定义为 p1-p2-p3 形成的角度
        """
        super().__init__(name)
        self.p1 = p1  # 第一个点
        self.p2 = p2  # 顶点
        self.p3 = p3  # 第三个点
        self.color = QColor(255, 0, 0)  # 角度颜色
        self.fixed = False  # 是否固定角度
        self.target_angle = None  # 目标角度（度数）
        self.draggable = False  # 角度对象本身不可直接拖动
        
    def calculate_angle(self):
        """计算角度（返回度数）"""
        if not self.p1 or not self.p2 or not self.p3:
            return 0
        
        # 计算向量
        vector1_x = self.p1.x - self.p2.x
        vector1_y = self.p1.y - self.p2.y
        vector2_x = self.p3.x - self.p2.x
        vector2_y = self.p3.y - self.p2.y
        
        # 计算点积
        dot_product = vector1_x * vector2_x + vector1_y * vector2_y
        
        # 计算向量模长
        magnitude1 = math.sqrt(vector1_x ** 2 + vector1_y ** 2)
        magnitude2 = math.sqrt(vector2_x ** 2 + vector2_y ** 2)
        
        # 避免除零错误
        if magnitude1 == 0 or magnitude2 == 0:
            return 0
        
        # 计算夹角余弦值，并确保在[-1, 1]范围内
        cos_angle = dot_product / (magnitude1 * magnitude2)
        cos_angle = max(-1, min(1, cos_angle))
        
        # 计算角度（弧度）
        angle_rad = math.acos(cos_angle)
        
        # 转换为度数（内角，0-180度范围内）
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg
    
    def draw(self, painter):
        """绘制角度"""
        if not self.visible or not self.p1 or not self.p2 or not self.p3:
            return
        
        # 设置画笔
        pen = QPen(self.color)
        pen.setWidth(2)
        if self.selected:
            pen.setWidth(3)
            pen.setColor(QColor(255, 165, 0))  # 选中时使用橙色
        
        painter.setPen(pen)
        
        # 计算内角（0-180度）
        angle_deg = self.calculate_angle()
        
        # 确定弧线半径（根据线段长度的一小部分）
        radius = min(
            self.p2.distance_to(self.p1),
            self.p2.distance_to(self.p3)
        ) / 10  # 将半径改得更小，从1/8改为1/10
        
        # 设置更小的范围
        radius = max(10, min(20, radius))  # 改为10-20范围，更小更精细
        
        # 计算向量的角度和单位向量
        # 从顶点(p2)指向其他两点的向量
        vec1_x = self.p1.x - self.p2.x
        vec1_y = self.p1.y - self.p2.y
        vec2_x = self.p3.x - self.p2.x
        vec2_y = self.p3.y - self.p2.y
        
        # 计算单位向量
        norm1 = math.sqrt(vec1_x**2 + vec1_y**2)
        norm2 = math.sqrt(vec2_x**2 + vec2_y**2)
        
        if norm1 < 0.001 or norm2 < 0.001:  # 避免除以非常小的数
            return
            
        unit_vec1_x = vec1_x / norm1
        unit_vec1_y = vec1_y / norm1
        unit_vec2_x = vec2_x / norm2
        unit_vec2_y = vec2_y / norm2
        
        # 计算向量的角度
        angle1 = math.atan2(vec1_y, vec1_x)
        angle2 = math.atan2(vec2_y, vec2_x)
        
        # 转换为度数
        start_angle_deg = math.degrees(angle1)
        end_angle_deg = math.degrees(angle2)
        
        # 确保角度在0-360范围内
        if start_angle_deg < 0:
            start_angle_deg += 360
        if end_angle_deg < 0:
            end_angle_deg += 360
            
        # 计算扫过的角度
        span_angle = end_angle_deg - start_angle_deg
        if span_angle < 0:
            span_angle += 360
            
        # 确保使用内角
        if span_angle > 180:
            span_angle = 360 - span_angle
            # 交换起始和结束角度
            start_angle_deg, end_angle_deg = end_angle_deg, start_angle_deg
            # 交换单位向量
            unit_vec1_x, unit_vec2_x = unit_vec2_x, unit_vec1_x
            unit_vec1_y, unit_vec2_y = unit_vec2_y, unit_vec1_y
            
        # 检查是否为直角（90度角）
        is_right_angle = abs(angle_deg - 90) < 1.0  # 允许1度误差
        
        center = QPointF(self.p2.x, self.p2.y)
        
        if is_right_angle:
            # 绘制直角标记（小正方形）
            square_size = radius * 0.8
            
            # 直角符号位置逻辑：
            # 1. 沿着两条边分别前进square_size距离
            # 2. 从其中一个点出发，沿着另一条边的方向再前进square_size距离，形成直角
            
            # 计算两条边上的点
            edge1_point = QPointF(
                center.x() + unit_vec1_x * square_size,
                center.y() + unit_vec1_y * square_size
            )
            
            edge2_point = QPointF(
                center.x() + unit_vec2_x * square_size,
                center.y() + unit_vec2_y * square_size
            )
            
            # 计算第三个点（直角处）
            corner_point = QPointF(
                edge1_point.x() + unit_vec2_x * square_size,
                edge1_point.y() + unit_vec2_y * square_size
            )
            
            # 绘制直角符号
            painter.drawLine(edge1_point, corner_point)
            painter.drawLine(corner_point, edge2_point)
        else:
            # 对于非直角，绘制弧线
            qt_start_angle = int(start_angle_deg * 16)
            qt_span_angle = int(span_angle * 16)
            
            # 绘制角度弧线
            painter.drawArc(
                int(center.x() - radius),
                int(center.y() - radius),
                int(radius * 2),
                int(radius * 2),
                qt_start_angle,
                qt_span_angle
            )
        
        # 计算角度值文本的位置
        bisector_angle_rad = math.radians(start_angle_deg + span_angle / 2)
        text_distance = radius * 1.8  # 调整文本距离
        
        text_x = center.x() + text_distance * math.cos(bisector_angle_rad)
        text_y = center.y() + text_distance * math.sin(bisector_angle_rad)
        
        # 格式化角度值文本
        angle_text = "90.0°" if is_right_angle else f"{angle_deg:.1f}°"
        
        # if角度已固定，修改文本显示方式
        if self.fixed:
            # 添加固定标记到文本中，而不是绘制蓝色点
            angle_text = f"{angle_text}*"  # 添加星号表示固定
            
        # 设置文本颜色 - 固定角度时使用蓝色，否则使用原色
        if self.fixed:
            text_pen = QPen(QColor(0, 0, 255))  # 蓝色文本表示固定
            painter.setPen(text_pen)
        
        # 检查是否应该显示角度值
        canvas = self._find_canvas()
        should_show_angle_values = True
        if canvas and hasattr(canvas, 'show_angle_values'):
            should_show_angle_values = canvas.show_angle_values
        
        # 绘制角度值（if启用了显示）
        if should_show_angle_values:
            painter.drawText(
                QPointF(text_x, text_y),
                angle_text
            )
        
        # 重置画笔为原来的颜色
        if self.fixed:
            painter.setPen(pen)
        
    def contains(self, point):
        """检查点是否包含在对象中"""
        if not self.p1 or not self.p2 or not self.p3:
            return False
            
        # 检查点击是否在角度标记范围内
        # 计算点到顶点的距离
        center = QPointF(self.p2.x, self.p2.y)
        
        # 使用与draw方法相同的半径计算
        radius = min(
            self.p2.distance_to(self.p1),
            self.p2.distance_to(self.p3)
        ) / 10
        
        radius = max(10, min(20, radius))  # 使用与绘制相同的范围限制
        
        # 增加一些容错距离，使得更容易选中
        selection_radius = radius * 2.5
        
        # 计算点击位置到顶点的距离
        if isinstance(point, QPointF):
            dx = point.x() - center.x()
            dy = point.y() - center.y()
        else:
            dx = point.x - center.x()
            dy = point.y - center.y()
            
        dist_to_center = math.sqrt(dx*dx + dy*dy)
        
        # 检查点击是否在角度标记的半径范围内
        return dist_to_center <= selection_radius
    
    def drag_to(self, new_pos):
        """拖拽到新位置
        
        角度对象本身不支持拖动，这个方法总是返回False
        """
        return False
        
    def get_bounds_rect(self, margin=0):
        """获取对象的边界矩形"""
        if not self.p1 or not self.p2 or not self.p3:
            return QRectF(0, 0, 0, 0)
            
        # 计算包含三个点的最小矩形
        min_x = min(self.p1.x, self.p2.x, self.p3.x) - margin
        min_y = min(self.p1.y, self.p2.y, self.p3.y) - margin
        max_x = max(self.p1.x, self.p2.x, self.p3.x) + margin
        max_y = max(self.p1.y, self.p2.y, self.p3.y) + margin
        
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        
    def enforce_angle(self):
        """强制将当前三点调整为目标角度。
        
        - 优先移动 p3；若 p3 为固定点，则改为移动 p1。
        - 若没有设置 target_angle 或任一点缺失，则直接返回。
        - 与拖拽实时机制互补：此方法用于立即校正（例如从UI勾选固定角度时）。
        """
        if not self.fixed or self.target_angle is None:
            return
        if not self.p1 or not self.p2 or not self.p3:
            return

        # 若画布正在拖拽顶点，则不在此处强制，避免与拖拽冲突
        canvas = self._find_canvas()
        if canvas and getattr(canvas, 'dragging', False) and getattr(canvas, 'dragged_object', None) == self.p2:
            return

        # 选择要调整的点
        point_to_move = None
        if not getattr(self.p3, 'fixed', False):
            point_to_move = 'p3'
        elif not getattr(self.p1, 'fixed', False):
            point_to_move = 'p1'
        else:
            # 两个可调点都固定，无法调整
            return

        if point_to_move == 'p3':
            self._adjust_p3_to_match_angle()
        else:
            self._adjust_p1_to_match_angle()
        
        # 立即更新画布
        if canvas:
            canvas.update()
            
    def _adjust_p3_to_match_angle(self):
        """调整p3的位置以匹配目标角度，使用平滑插值"""
        # 保持p1和p2不变，调整p3
        # 计算p2到p3的距离
        distance = self.p2.distance_to(self.p3)
        
        # 计算p1-p2向量的角度
        ref_angle = math.atan2(self.p1.y - self.p2.y, self.p1.x - self.p2.x)
        
        # 目标角度（弧度）
        target_rad = math.radians(self.target_angle)
        
        # 计算当前p3的角度
        p3_angle = math.atan2(self.p3.y - self.p2.y, self.p3.x - self.p2.x)
        
        # 确定p3应该在p1的哪一侧（保持原来的方向）
        current_span = p3_angle - ref_angle
        if current_span < 0:
            current_span += 2 * math.pi
            
        # 决定新位置方向
        if current_span <= math.pi:
            # p3在p1逆时针方向
            new_p3_angle = ref_angle + target_rad
        else:
            # p3在p1顺时针方向
            new_p3_angle = ref_angle - target_rad
            
        # 直接使用新角度，不再使用平滑插值
        # 计算p3的新位置
        new_x = self.p2.x + distance * math.cos(new_p3_angle)
        new_y = self.p2.y + distance * math.sin(new_p3_angle)
        
        # 更新p3位置
        self.p3.set_position(new_x, new_y)
        
    def _adjust_p1_to_match_angle(self):
        """调整p1的位置以匹配目标角度，使用平滑插值"""
        # 保持p3和p2不变，调整p1
        # 计算p2到p1的距离
        distance = self.p2.distance_to(self.p1)
        
        # 计算p3-p2向量的角度
        ref_angle = math.atan2(self.p3.y - self.p2.y, self.p3.x - self.p2.x)
        
        # 目标角度（弧度）
        target_rad = math.radians(self.target_angle)
        
        # 计算当前p1的角度
        p1_angle = math.atan2(self.p1.y - self.p2.y, self.p1.x - self.p2.x)
        
        # 确定p1应该在p3的哪一侧（保持原来的方向）
        current_span = p1_angle - ref_angle
        if current_span < 0:
            current_span += 2 * math.pi
            
        # 决定新位置方向
        if current_span <= math.pi:
            # p1在p3逆时针方向
            new_p1_angle = ref_angle + target_rad
        else:
            # p1在p3顺时针方向
            new_p1_angle = ref_angle - target_rad
            
        # 直接使用新角度，不再使用平滑插值
        # 计算p1的新位置
        new_x = self.p2.x + distance * math.cos(new_p1_angle)
        new_y = self.p2.y + distance * math.sin(new_p1_angle)
        
        # 更新p1位置
        self.p1.set_position(new_x, new_y)
        
    def _find_canvas(self):
        """查找包含此对象的画布"""
        try:
            from PyQt5.QtWidgets import QApplication
            from .canvas import Canvas  # 正确导入Canvas类
            for widget in QApplication.topLevelWidgets():
                for canvas in widget.findChildren(Canvas):  # 使用Canvas类而不是object
                    if hasattr(canvas, 'objects') and self in canvas.objects:
                        return canvas
        except Exception:
            pass
        return None

def show_angle_dialog(canvas):
    """显示角度设置对话框"""
    dialog = AngleDialog(canvas)
    dialog.exec_()

class AngleDialog(QDialog):
    """角度设置对话框"""
    
    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        self.setWindowTitle("角度设置")
        self.setMinimumWidth(300)
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout()
        
        # 顶部说明
        info_label = QLabel("请选择三个点形成一个角度，第二个点为顶点")
        layout.addWidget(info_label)
        
        # 点选择部分
        points_layout = QHBoxLayout()
        
        # 第一个点选择
        self.point1_combo = QComboBox()
        self.populate_point_combo(self.point1_combo)
        points_layout.addWidget(QLabel("第一个点:"))
        points_layout.addWidget(self.point1_combo)
        
        # 顶点选择
        self.vertex_combo = QComboBox()
        self.populate_point_combo(self.vertex_combo)
        points_layout.addWidget(QLabel("顶点:"))
        points_layout.addWidget(self.vertex_combo)
        
        # 第三个点选择
        self.point3_combo = QComboBox()
        self.populate_point_combo(self.point3_combo)
        points_layout.addWidget(QLabel("第三个点:"))
        points_layout.addWidget(self.point3_combo)
        
        layout.addLayout(points_layout)
        
        # 连接点选择变更信号
        self.point1_combo.currentIndexChanged.connect(self.update_angle_preview)
        self.vertex_combo.currentIndexChanged.connect(self.update_angle_preview)
        self.point3_combo.currentIndexChanged.connect(self.update_angle_preview)
        
        # 角度值显示
        angle_layout = QHBoxLayout()
        self.angle_label = QLabel("角度: 0.0°")
        angle_layout.addWidget(self.angle_label)
        
        # 目标角度设置
        self.target_angle_spin = QDoubleSpinBox()
        self.target_angle_spin.setRange(0, 360)
        self.target_angle_spin.setSingleStep(1)
        self.target_angle_spin.setDecimals(1)
        self.target_angle_spin.setSuffix("°")
        angle_layout.addWidget(QLabel("目标角度:"))
        angle_layout.addWidget(self.target_angle_spin)
        
        layout.addLayout(angle_layout)
        
        # 固定角度选项
        self.fixed_checkbox = QCheckBox("固定角度")
        layout.addWidget(self.fixed_checkbox)
        
        # 按钮部分
        buttons_layout = QHBoxLayout()
        
        apply_button = QPushButton("应用")
        apply_button.clicked.connect(self.apply_angle)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addWidget(apply_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
        
        self.setLayout(layout)
        
    def populate_point_combo(self, combo):
        """填充点选择下拉框"""
        combo.clear()
        combo.addItem("请选择", None)
        
        # 遍历画布上的所有点
        from .geometry import Point
        for i, obj in enumerate(self.canvas.objects):
            if isinstance(obj, Point):
                point_name = obj.name if obj.name else f"点{i+1}"
                combo.addItem(point_name, obj)
                
    def update_angle_preview(self):
        """更新角度预览"""
        p1 = self.point1_combo.currentData()
        p2 = self.vertex_combo.currentData()
        p3 = self.point3_combo.currentData()
        
        if p1 and p2 and p3:
            angle = Angle(p1, p2, p3)
            angle_value = angle.calculate_angle()
            self.angle_label.setText(f"角度: {angle_value:.1f}°")
            self.target_angle_spin.setValue(angle_value)
        else:
            self.angle_label.setText("角度: 0.0°")
            
    def apply_angle(self):
        """应用角度设置"""
        p1 = self.point1_combo.currentData()
        p2 = self.vertex_combo.currentData()
        p3 = self.point3_combo.currentData()
        
        if not p1 or not p2 or not p3:
            QMessageBox.warning(self, "错误", "请选择三个点")
            return
            
        if p1 == p2 or p2 == p3 or p1 == p3:
            QMessageBox.warning(self, "错误", "请选择三个不同的点")
            return
            
        # 创建角度对象
        angle = Angle(p1, p2, p3)
        
        # 设置是否固定角度
        angle.fixed = self.fixed_checkbox.isChecked()
        
        # if固定角度，则设置目标角度
        if angle.fixed:
            angle.target_angle = self.target_angle_spin.value()
            # 立即应用目标角度
            angle.enforce_angle()
            
        # 将角度对象添加到画布
        self.canvas.add_object(angle)
        
        # 更新画布
        self.canvas.update()
        
        self.accept()

# 扩展Canvas类的check_fixed_lengths方法
def extend_check_fixed_lengths(original_method):
    """扩展Canvas.check_fixed_lengths方法，添加角度固定检查"""
    def extended_method(self):
        # 调用原始方法
        original_method(self)
        
        # 检查并强制固定角度
        from .oangle import Angle
        for obj in self.objects:
            if isinstance(obj, Angle) and obj.fixed:
                obj.enforce_angle()
                
    return extended_method
