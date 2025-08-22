#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import re
import subprocess
import time
import psutil
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtCore import QThread, pyqtSignal

class OllamaClient:
    """OLLAMA客户端，用于与本地OLLAMA服务通信"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen3:4b-instruct"
        self.ensure_ollama_running()
    
    def chat(self, prompt: str) -> str:
        """发送聊天请求到OLLAMA"""
        try:
            url = f"{self.base_url}/api/chat"
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except requests.exceptions.RequestException as e:
            print(f"连接OLLAMA服务失败: {str(e)}")
            return "抱歉，当前AI服务不可用。您可以使用手动绘图功能，或等待管理员配置AI服务。"
        except Exception as e:
            print(f"处理请求时出错: {str(e)}")
            return "抱歉，处理AI请求时出现错误。建议使用手动绘图功能。"
    
    def is_ollama_running(self) -> bool:
        """检查OLLAMA服务是否运行"""
        try:
            # 检查进程
            for proc in psutil.process_iter(['pid', 'name']):
                if 'ollama' in proc.info['name'].lower():
                    return True
            
            # 尝试连接服务
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def start_ollama_service(self):
        """启动OLLAMA服务"""
        try:
            print("正在启动OLLAMA服务...")
            # 在Windows上启动ollama服务
            subprocess.Popen(['ollama', 'serve'], 
                           creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
            
            # 等待服务启动
            max_wait = 30  # 最多等待30秒
            for i in range(max_wait):
                time.sleep(1)
                if self.is_ollama_running():
                    print("OLLAMA服务启动成功！")
                    return True
                print(f"等待OLLAMA服务启动... ({i+1}/{max_wait})")
            
            print("OLLAMA服务启动超时")
            return False
            
        except FileNotFoundError:
            print("错误: 未找到ollama命令。请确保已安装OLLAMA。")
            print("下载地址: https://ollama.ai/download")
            return False
        except Exception as e:
            print(f"启动OLLAMA服务时出错: {e}")
            return False
    
    def ensure_ollama_running(self):
        """确保OLLAMA服务运行"""
        if not self.is_ollama_running():
            print("OLLAMA服务未运行，正在启动...")
            if not self.start_ollama_service():
                print("无法启动OLLAMA服务，AI功能将不可用")
                return False
        return True

class DrawingCommand:
    """绘图命令类"""
    
    def __init__(self, command_type: str, params: Dict[str, Any]):
        self.command_type = command_type
        self.params = params
    
    def __repr__(self):
        return f"DrawingCommand({self.command_type}, {self.params})"

class AIDrawingParser:
    """AI绘图指令解析器"""
    
    @staticmethod
    def parse_drawing_commands(ai_response: str) -> List[DrawingCommand]:
        """解析AI回复中的绘图指令"""
        commands = []
        
        # 尝试解析JSON格式的指令
        try:
            # 查找JSON代码块
            json_pattern = r'```json\s*(.*?)\s*```'
            json_matches = re.findall(json_pattern, ai_response, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "type" in item:
                                # 验证并清理命令
                                cmd_type = item["type"]
                                if cmd_type in ["isosceles_triangle", "equilateral_triangle", "right_triangle"]:
                                    # 跳过不支持的复合命令
                                    print(f"跳过不支持的命令类型: {cmd_type}")
                                    continue
                                commands.append(DrawingCommand(cmd_type, item))
                    elif isinstance(data, dict) and "type" in data:
                        cmd_type = data["type"]
                        if cmd_type not in ["isosceles_triangle", "equilateral_triangle", "right_triangle"]:
                            commands.append(DrawingCommand(cmd_type, data))
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    continue
        except Exception as e:
            print(f"解析命令时出错: {e}")
        
        # if没有找到JSON，尝试解析自然语言描述
        if not commands:
            commands = AIDrawingParser._parse_natural_language(ai_response)
        
        return commands
    
    @staticmethod
    def _parse_natural_language(text: str) -> List[DrawingCommand]:
        """解析自然语言描述的绘图指令"""
        commands = []
        
        # 点的匹配模式
        point_patterns = [
            r'(?:创建|画|绘制|添加).*?点\s*(\w+).*?坐标\s*[（(]?\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[)）]?',
            r'点\s*(\w+)\s*[：:]\s*[（(]?\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[)）]?',
            r'在\s*[（(]?\s*(-?\d+(?:\.\d+)?)\s*[,，]\s*(-?\d+(?:\.\d+)?)\s*[)）]?\s*(?:处|位置|画|创建).*?点\s*(\w+)?'
        ]
        
        for pattern in point_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                if len(groups) == 3:
                    if groups[0] and groups[1] and groups[2]:  # 名称在前
                        name = groups[0]
                        x, y = float(groups[1]), float(groups[2])
                    elif groups[2]:  # 名称在后
                        name = groups[2]
                        x, y = float(groups[0]), float(groups[1])
                    else:
                        name = f"P{len(commands) + 1}"
                        x, y = float(groups[0]), float(groups[1])
                    
                    commands.append(DrawingCommand("point", {
                        "type": "point",
                        "name": name,
                        "x": x,
                        "y": y,
                        "color": "#000000"
                    }))
        
        # 线段的匹配模式
        line_patterns = [
            r'(?:连接|画|绘制|创建).*?(?:线段|直线)\s*(\w+)\s*(?:连接|从)\s*(\w+)\s*(?:到|至)\s*(\w+)',
            r'从\s*(\w+)\s*(?:到|至)\s*(\w+)\s*(?:画|绘制|创建).*?(?:线段|直线)\s*(\w+)?',
            r'(?:线段|直线)\s*(\w+)\s*[：:]\s*(\w+)\s*(?:到|至|-)\s*(\w+)'
        ]
        
        for pattern in line_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    if len(groups) == 3 and groups[0] and not any(c.isdigit() for c in groups[0]):
                        # 第一个是线段名称
                        line_name = groups[0]
                        start_point = groups[1]
                        end_point = groups[2]
                    elif len(groups) == 3 and groups[2]:
                        # 第三个是线段名称
                        start_point = groups[0]
                        end_point = groups[1]
                        line_name = groups[2]
                    else:
                        # 没有明确线段名称
                        start_point = groups[0]
                        end_point = groups[1]
                        line_name = f"L{len([c for c in commands if c.command_type == 'line']) + 1}"
                    
                    commands.append(DrawingCommand("line", {
                        "type": "line",
                        "name": line_name,
                        "start_point": start_point,
                        "end_point": end_point,
                        "color": "#000000",
                        "width": 2
                    }))
        
        # 三角形匹配模式
        triangle_patterns = [
            r'(?:画|绘制|创建).*?三角形\s*(\w+)?\s*(?:顶点|由)\s*(\w+)\s*[,，]\s*(\w+)\s*[,，]\s*(\w+)',
            r'三角形\s*(\w+)?\s*[：:]\s*(\w+)\s*[,，]\s*(\w+)\s*[,，]\s*(\w+)'
        ]
        
        for pattern in triangle_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 3:
                    triangle_name = groups[0] if groups[0] else f"T{len([c for c in commands if c.command_type == 'triangle']) + 1}"
                    if len(groups) == 4:
                        points = [groups[1], groups[2], groups[3]]
                    else:
                        points = [groups[0], groups[1], groups[2]]
                        triangle_name = f"T{len([c for c in commands if c.command_type == 'triangle']) + 1}"
                    
                    commands.append(DrawingCommand("triangle", {
                        "type": "triangle",
                        "name": triangle_name,
                        "points": points,
                        "color": "#000000",
                        "fill_color": "#FFCCCC"
                    }))
        
        return commands

class AIThread(QThread):
    """AI处理线程"""
    
    response_ready = pyqtSignal(str)
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, prompt: str, context: str = ""):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.ollama_client = OllamaClient()
    
    def run(self):
        try:
            # 构建完整的提示词
            full_prompt = self._build_prompt(self.prompt)
            
            # 获取AI回复
            response = self.ollama_client.chat(full_prompt)
            self.response_ready.emit(response)
            
            # 解析绘图指令
            commands = AIDrawingParser.parse_drawing_commands(response)
            self.commands_ready.emit(commands)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _build_prompt(self, user_input: str) -> str:
        """构建完整的提示词"""
        system_prompt = """专业几何绘图助手，生成标准手拉手模型。

基础命令：
- point: 创建点
- line: 创建线段  
- fixed_length_line: 创建固定长度线段
- fixed_angle: 创建固定角度
- fixed_point: 固定点位置（防止拖拽移动）
- midpoint: 创建中点

命名规范：
- 点: O, A, B, C, D (单字母简洁命名)
- 线段: L1, L2, L3, L4 (L+数字)
- 角度: A1, A2, A3 (A+数字)
- 系统会自动检测重复命名并生成唯一名称

手拉手模型要求：
1. 中心点O，外围点A、B、C、D
2. 两个等腰三角形OAB和OCD，但边长不同(如OA=OB=160, OC=OD=240)
3. 固定所有关键角度(如∠AOB=70°, ∠COD=80°)
4. 连接AC、BD形成手拉手连线
5. 创建顺序：点→线段→固定角度→固定基础三角形点位置
6. 固定中心点O和一个基础点A的位置，确保模型稳定不移动

手拉手模型标准格式：
```json
[
    {"type": "point", "name": "O", "x": 400, "y": 300, "color": "#FF0000"},
    {"type": "point", "name": "A", "x": 240, "y": 220, "color": "#0000FF"},
    {"type": "point", "name": "B", "x": 560, "y": 220, "color": "#0000FF"}, 
    {"type": "point", "name": "C", "x": 280, "y": 460, "color": "#00FF00"},
    {"type": "point", "name": "D", "x": 520, "y": 460, "color": "#00FF00"},
    {"type": "fixed_length_line", "name": "L1", "start_point": "O", "end_point": "A", "length": 160, "color": "#000000"},
    {"type": "fixed_length_line", "name": "L2", "start_point": "O", "end_point": "B", "length": 160, "color": "#000000"},
    {"type": "fixed_length_line", "name": "L3", "start_point": "O", "end_point": "C", "length": 240, "color": "#000000"},
    {"type": "fixed_length_line", "name": "L4", "start_point": "O", "end_point": "D", "length": 240, "color": "#000000"},
    {"type": "line", "name": "L5", "start_point": "A", "end_point": "B", "color": "#000000"},
    {"type": "line", "name": "L6", "start_point": "C", "end_point": "D", "color": "#000000"},
    {"type": "line", "name": "L7", "start_point": "A", "end_point": "C", "color": "#FF0000"},
    {"type": "line", "name": "L8", "start_point": "B", "end_point": "D", "color": "#FF0000"},
    {"type": "fixed_angle", "name": "A1", "vertex": "O", "point1": "A", "point2": "B", "angle": 70},
    {"type": "fixed_angle", "name": "A2", "vertex": "O", "point1": "C", "point2": "D", "angle": 80},
    {"type": "fixed_point", "point": "O"},
    {"type": "fixed_point", "point": "A"}
]
```

"""

        # if有上下文，添加到提示词中
        if self.context:
            system_prompt += f"\n{self.context}\n\n"
        
        system_prompt += "user需求："
        
        return system_prompt + user_input
