#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QSplitter, QFrame, QScrollArea,
    QWidget, QMessageBox, QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
from .ai_assistant import AIThread, DrawingCommand
from .geometry import Point, Line
from .canvas_analyzer import CanvasAnalyzer

class AIDialog(QDialog):
    """AI助手对话框"""
    
    # 信号：当user请求执行绘图命令时发出
    execute_commands = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.ai_thread = None
        self.pending_commands = []
        self.canvas = None  # 画布引用
        self.current_context = ""  # 当前画布上下文
        
    def setup_ui(self):
        """设置user界面"""
        self.setWindowTitle("AI绘图助手")
        self.setMinimumSize(600, 500)
        self.resize(700, 600)
        
        # 设置样式
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
                font-family: 楷体, KaiTi, "Kaiti SC", STKaiti, SimKai;
            }
            QTextEdit {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
                font-size: 12px;
            }
            QLineEdit {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
                background-color: white;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
            QGroupBox {
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #2c3e50;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 标题
        title_label = QLabel("AI绘图助手")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)
        
        # 对话历史区域
        history_group = QGroupBox("对话历史")
        history_layout = QVBoxLayout(history_group)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setMinimumHeight(200)
        self.chat_history.setPlaceholderText("AI助手将在这里显示对话内容...")
        history_layout.addWidget(self.chat_history)
        
        splitter.addWidget(history_group)
        
        # 命令预览区域
        commands_group = QGroupBox("绘图命令预览")
        commands_layout = QVBoxLayout(commands_group)
        
        self.commands_display = QTextEdit()
        self.commands_display.setReadOnly(True)
        self.commands_display.setMaximumHeight(150)
        self.commands_display.setPlaceholderText("AI生成的绘图命令将在这里显示...")
        commands_layout.addWidget(self.commands_display)
        
        # 执行按钮
        execute_layout = QHBoxLayout()
        self.execute_button = QPushButton("执行绘图命令")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.execute_drawing_commands)
        execute_layout.addStretch()
        execute_layout.addWidget(self.execute_button)
        execute_layout.addStretch()
        commands_layout.addLayout(execute_layout)
        
        splitter.addWidget(commands_group)
        
        # 输入区域
        input_group = QGroupBox("输入区域")
        input_layout = QVBoxLayout(input_group)
        
        # 分析画布按钮
        analyze_layout = QHBoxLayout()
        self.analyze_button = QPushButton("分析当前画布")
        self.analyze_button.clicked.connect(self.analyze_canvas)
        self.analyze_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
        """)
        analyze_layout.addStretch()
        analyze_layout.addWidget(self.analyze_button)
        analyze_layout.addStretch()
        input_layout.addLayout(analyze_layout)
        
        # 输入框和发送按钮
        input_container = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("描述你想要绘制或修改的图形，例如：在这个三角形上添加中点...")
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.send_message)
        
        input_container.addWidget(self.input_field)
        input_container.addWidget(self.send_button)
        input_layout.addLayout(input_container)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 无限进度条
        input_layout.addWidget(self.progress_bar)
        
        # 示例建议
        suggestions_label = QLabel("💡 示例：")
        suggestions_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        input_layout.addWidget(suggestions_label)
        
        suggestions_text = QLabel(
            "• 画一个等边三角形\n"
            "• 创建三个点A、B、C并连接它们\n"
            "• 在坐标(100,100)处画一个点A\n"
            "• 画一个正方形ABCD"
        )
        suggestions_text.setStyleSheet("color: #95a5a6; font-size: 10px; margin-left: 10px;")
        input_layout.addWidget(suggestions_text)
        
        layout.addWidget(input_group)
        
        # 设置分割器比例
        splitter.setSizes([300, 150, 200])
        
        # 初始化对话
        self.add_to_history("系统", "欢迎使用AI绘图助手！您可以描述想要绘制的图形，或点击\"分析当前画布\"按钮让我了解现有图形后进行修改。", "#27ae60")
    
    def set_canvas(self, canvas):
        """设置画布引用"""
        self.canvas = canvas
    
    def analyze_canvas(self):
        """分析当前画布状态"""
        if not self.canvas:
            QMessageBox.warning(self, "错误", "未找到画布引用")
            return
        
        try:
            analyzer = CanvasAnalyzer(self.canvas)
            context_description = analyzer.generate_context_description()
            self.current_context = context_description
            
            # 显示分析结果
            self.add_to_history("系统", "画布分析完成！", "#27ae60")
            self.add_to_history("画布分析", context_description, "#2980b9")
            self.add_to_history("系统", "现在您可以基于当前画布状态提出修改需求，例如：\"在三角形上添加中线\"、\"连接两个中点\"等。", "#27ae60")
            
        except Exception as e:
            QMessageBox.critical(self, "分析错误", f"分析画布时出错：{str(e)}")
            print(f"画布分析错误: {str(e)}")
        
    def send_message(self):
        """发送消息给AI"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return
            
        # 添加user消息到历史
        self.add_to_history("user", user_input, "#3498db")
        self.input_field.clear()
        
        # 显示加载状态
        self.set_loading_state(True)
        
        # 创建AI线程，包含当前画布上下文
        self.ai_thread = AIThread(user_input, self.current_context)
        self.ai_thread.response_ready.connect(self.on_ai_response)
        self.ai_thread.commands_ready.connect(self.on_commands_ready)
        self.ai_thread.error_occurred.connect(self.on_ai_error)
        self.ai_thread.start()
    
    def on_ai_response(self, response):
        """处理AI回复"""
        self.add_to_history("AI助手", response, "#e74c3c")
        
    def on_commands_ready(self, commands):
        """处理绘图命令"""
        self.set_loading_state(False)
        self.pending_commands = commands
        
        if commands:
            # 显示命令预览
            commands_text = "检测到以下绘图命令：\n\n"
            for i, cmd in enumerate(commands, 1):
                commands_text += f"{i}. {self.format_command(cmd)}\n"
            
            self.commands_display.setText(commands_text)
            self.execute_button.setEnabled(True)
        else:
            self.commands_display.setText("未检测到有效的绘图命令。请尝试更明确的描述。")
            self.execute_button.setEnabled(False)
    
    def on_ai_error(self, error_msg):
        """处理AI错误"""
        self.set_loading_state(False)
        self.add_to_history("系统", f"错误：{error_msg}", "#e74c3c")
        QMessageBox.warning(self, "AI助手错误", error_msg)
    
    def format_command(self, cmd: DrawingCommand) -> str:
        """格式化命令显示"""
        if cmd.command_type == "point":
            return f"创建点 {cmd.params.get('name', '')} 在坐标 ({cmd.params.get('x', 0)}, {cmd.params.get('y', 0)})"
        elif cmd.command_type == "line":
            return f"创建线段 {cmd.params.get('name', '')} 连接 {cmd.params.get('start_point', '')} 和 {cmd.params.get('end_point', '')}"
        elif cmd.command_type == "triangle":
            points = cmd.params.get('points', [])
            return f"创建三角形 {cmd.params.get('name', '')} 由点 {', '.join(points)} 组成"
        else:
            return f"未知命令类型: {cmd.command_type}"
    
    def execute_drawing_commands(self):
        """执行绘图命令"""
        if not self.pending_commands:
            return
            
        try:
            # 发出执行命令信号
            self.execute_commands.emit(self.pending_commands)
            
            # 清空命令显示
            self.commands_display.setText("命令已执行！")
            self.execute_button.setEnabled(False)
            self.pending_commands = []
            
            # 添加执行成功消息
            self.add_to_history("系统", "✅ 绘图命令执行成功！", "#27ae60")
            
        except Exception as e:
            QMessageBox.critical(self, "执行错误", f"执行绘图命令时出错：{str(e)}")
            self.add_to_history("系统", f"❌ 执行错误：{str(e)}", "#e74c3c")
    
    def add_to_history(self, sender: str, message: str, color: str = "#000000"):
        """添加消息到对话历史"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(cursor.End)
        
        # 添加发送者标签
        cursor.insertHtml(f'<p><span style="color: {color}; font-weight: bold;">[{sender}]:</span> ')
        
        # 添加消息内容
        cursor.insertText(message)
        cursor.insertHtml('</p>')
        
        # 滚动到底部
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()
    
    def set_loading_state(self, loading: bool):
        """设置加载状态"""
        self.progress_bar.setVisible(loading)
        self.send_button.setEnabled(not loading)
        self.input_field.setEnabled(not loading)
        
        if loading:
            self.send_button.setText("处理中...")
        else:
            self.send_button.setText("发送")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.terminate()
            self.ai_thread.wait()
        event.accept()
