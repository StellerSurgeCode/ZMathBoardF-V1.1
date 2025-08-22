#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QSplitter, QFrame, QScrollArea,
    QWidget, QMessageBox, QProgressBar, QGroupBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
from .ai_function_assistant import AIFunctionThread, FunctionCommand

class FunctionCanvasAnalyzer:
    """函数画布分析器"""
    
    def __init__(self, function_canvas):
        self.function_canvas = function_canvas
    
    def generate_context_description(self) -> str:
        """生成画布上下文描述"""
        if not self.function_canvas.functions:
            return "画布上暂无函数图像。"
        
        context = f"当前画布上有 {len(self.function_canvas.functions)} 个函数图像：\n\n"
        
        for i, func in enumerate(self.function_canvas.functions, 1):
            context += f"{i}. {func.name}\n"
            context += f"   表达式: f(x) = {func.expression}\n"
            context += f"   颜色: {func.color.name()}\n"
            context += f"   定义域: [{func.x_min:.2f}, {func.x_max:.2f}]\n"
            context += f"   可见性: {'显示' if func.visible else '隐藏'}\n\n"
        
        # 视图信息
        context += f"当前视图范围: X[{self.function_canvas.x_min:.2f}, {self.function_canvas.x_max:.2f}], "
        context += f"Y[{self.function_canvas.y_min:.2f}, {self.function_canvas.y_max:.2f}]\n"
        
        return context

class AIFunctionChatDialog(QDialog):
    """AI函数绘图对话助手"""
    
    # 信号：当user请求执行函数绘制命令时发出
    execute_function_commands = pyqtSignal(list)
    
    def __init__(self, function_canvas, parent=None):
        super().__init__(parent)
        self.function_canvas = function_canvas
        self.setup_ui()
        self.ai_thread = None
        self.pending_commands = []
        self.current_context = ""
        
    def setup_ui(self):
        """设置user界面"""
        self.setWindowTitle("AI函数绘图助手")
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
        title_label = QLabel("AI函数绘图助手")
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
        
        # 函数命令预览区域
        commands_group = QGroupBox("函数命令预览")
        commands_layout = QVBoxLayout(commands_group)
        
        self.commands_display = QTextEdit()
        self.commands_display.setReadOnly(True)
        self.commands_display.setMaximumHeight(150)
        self.commands_display.setPlaceholderText("AI生成的函数绘制命令将在这里显示...")
        commands_layout.addWidget(self.commands_display)
        
        # 执行按钮
        execute_layout = QHBoxLayout()
        self.execute_button = QPushButton("绘制函数")
        self.execute_button.setEnabled(False)
        self.execute_button.clicked.connect(self.execute_function_drawing)
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
        self.analyze_button = QPushButton("分析当前函数")
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
        self.input_field.setPlaceholderText("描述你想要绘制的函数，例如：画一个正弦函数，用红色，范围从-π到π...")
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
            "• 画一个二次函数 y = x²\n"
            "• 绘制正弦函数，用红色，范围-2π到2π\n"
            "• 画指数函数 e^x，绿色\n"
            "• 创建对数函数 ln(x)，范围0.1到10\n"
            "• 画一个复合函数 sin(x)*exp(-x/5)"
        )
        suggestions_text.setStyleSheet("color: #95a5a6; font-size: 10px; margin-left: 10px;")
        input_layout.addWidget(suggestions_text)
        
        layout.addWidget(input_group)
        
        # 设置分割器比例
        splitter.setSizes([300, 150, 200])
        
        # 初始化对话
        self.add_to_history("系统", "欢迎使用AI函数绘图助手！您可以描述想要绘制的数学函数，或点击\"分析当前函数\"按钮让我了解现有函数后进行修改。", "#27ae60")
    
    def analyze_canvas(self):
        """分析当前函数画布状态"""
        if not self.function_canvas:
            QMessageBox.warning(self, "错误", "未找到函数画布引用")
            return
        
        try:
            analyzer = FunctionCanvasAnalyzer(self.function_canvas)
            context_description = analyzer.generate_context_description()
            self.current_context = context_description
            
            # 显示分析结果
            self.add_to_history("系统", "函数画布分析完成！", "#27ae60")
            self.add_to_history("画布分析", context_description, "#2980b9")
            self.add_to_history("系统", "现在您可以基于当前函数状态提出需求，例如：\"添加一个与现有函数互补的函数\"、\"画一个不同颜色的cos函数\"等。", "#27ae60")
            
        except Exception as e:
            QMessageBox.critical(self, "分析错误", f"分析函数画布时出错：{str(e)}")
            print(f"函数画布分析错误: {str(e)}")
        
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
        self.ai_thread = AIFunctionThread(user_input, self.current_context)
        self.ai_thread.response_ready.connect(self.on_ai_response)
        self.ai_thread.commands_ready.connect(self.on_commands_ready)
        self.ai_thread.error_occurred.connect(self.on_ai_error)
        self.ai_thread.start()
    
    def on_ai_response(self, response):
        """处理AI回复"""
        self.add_to_history("AI助手", response, "#e74c3c")
        
    def on_commands_ready(self, commands):
        """处理函数绘制命令"""
        self.set_loading_state(False)
        self.pending_commands = commands
        
        if commands:
            # 显示命令预览
            commands_text = "检测到以下函数绘制命令：\n\n"
            for i, cmd in enumerate(commands, 1):
                commands_text += f"{i}. {self.format_function_command(cmd)}\n"
            
            self.commands_display.setText(commands_text)
            self.execute_button.setEnabled(True)
        else:
            self.commands_display.setText("未检测到有效的函数绘制命令。请尝试更明确的描述。")
            self.execute_button.setEnabled(False)
    
    def on_ai_error(self, error_msg):
        """处理AI错误"""
        self.set_loading_state(False)
        self.add_to_history("系统", f"错误：{error_msg}", "#e74c3c")
        QMessageBox.warning(self, "AI助手错误", error_msg)
    
    def format_function_command(self, cmd: FunctionCommand) -> str:
        """格式化函数命令显示"""
        return (f"函数: f(x) = {cmd.expression}\n"
                f"     颜色: {cmd.color}, 范围: [{cmd.x_min}, {cmd.x_max}], 线宽: {cmd.line_width}")
    
    def execute_function_drawing(self):
        """执行函数绘制命令"""
        if not self.pending_commands:
            return
            
        try:
            # 发出执行命令信号
            self.execute_function_commands.emit(self.pending_commands)
            
            # 清空命令显示
            self.commands_display.setText("函数已绘制！")
            self.execute_button.setEnabled(False)
            self.pending_commands = []
            
            # 添加执行成功消息
            self.add_to_history("系统", "✅ 函数绘制命令执行成功！", "#27ae60")
            
        except Exception as e:
            QMessageBox.critical(self, "执行错误", f"执行函数绘制命令时出错：{str(e)}")
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
