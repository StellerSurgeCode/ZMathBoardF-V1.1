#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import re
import math
import subprocess
import time
import psutil
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QColor

class OllamaFunctionClient:
    """OLLAMA客户端，用于函数绘图AI助手"""
    
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = "qwen3:4b-instruct"
        self.ensure_ollama_running()
    
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
                print("无法启动OLLAMA服务，将使用内置响应")
                return False
        return True
    
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
            return self._fallback_response(prompt)
        except Exception as e:
            print(f"处理请求时出错: {str(e)}")
            return self._fallback_response(prompt)
    
    def _fallback_response(self, prompt: str) -> str:
        """当OLLAMA不可用时的备用响应"""
        prompt_lower = prompt.lower()
        
        if "半圆" in prompt:
            return '''好的，我来为您创建一个半圆函数。

```json
[
    {
        "expression": "sqrt(1 - x**2)",
        "color": "#0066CC",
        "x_min": -1,
        "x_max": 1,
        "line_width": 2,
        "name": "上半圆"
    }
]
```

这是一个上半圆函数，数学表达式为 y = √(1-x²)，定义域为 [-1, 1]。'''
        
        elif "正弦" in prompt or "sin" in prompt:
            return '''```json
[
    {
        "expression": "sin(x)",
        "color": "#FF0000",
        "x_min": -6.28,
        "x_max": 6.28,
        "line_width": 2,
        "name": "正弦函数"
    }
]
```'''
        
        elif "余弦" in prompt or "cos" in prompt:
            return '''```json
[
    {
        "expression": "cos(x)",
        "color": "#00AA00",
        "x_min": -6.28,
        "x_max": 6.28,
        "line_width": 2,
        "name": "余弦函数"
    }
]
```'''
        
        elif "二次" in prompt or "抛物线" in prompt or "x²" in prompt or "x**2" in prompt:
            return '''```json
[
    {
        "expression": "x**2",
        "color": "#AA0000",
        "x_min": -5,
        "x_max": 5,
        "line_width": 2,
        "name": "二次函数"
    }
]
```'''
        
        elif "指数" in prompt or "exp" in prompt:
            return '''```json
[
    {
        "expression": "exp(x)",
        "color": "#AA00AA",
        "x_min": -3,
        "x_max": 3,
        "line_width": 2,
        "name": "指数函数"
    }
]
```'''
        
        elif "对数" in prompt or "log" in prompt or "ln" in prompt:
            return '''```json
[
    {
        "expression": "log(x)",
        "color": "#00AAAA",
        "x_min": 0.1,
        "x_max": 10,
        "line_width": 2,
        "name": "对数函数"
    }
]
```'''
        
        else:
            return '''我理解您想要绘制函数图像。请使用以下格式：

```json
[
    {
        "expression": "x**2",
        "color": "#0066CC",
        "x_min": -10,
        "x_max": 10,
        "line_width": 2,
        "name": "示例函数"
    }
]
```

支持的函数类型：
- 半圆: sqrt(1 - x**2)
- 正弦: sin(x)
- 余弦: cos(x)
- 二次函数: x**2
- 指数函数: exp(x)
- 对数函数: log(x)

请告诉我您想要绘制什么具体的函数？'''

class FunctionCommand:
    """函数绘图命令类"""
    
    def __init__(self, expression: str, color: str = "#0066CC", x_min: float = -10, x_max: float = 10, 
                 line_width: int = 2, name: str = None):
        self.expression = expression
        self.color = color
        self.x_min = x_min
        self.x_max = x_max
        self.line_width = line_width
        self.name = name or f"f(x) = {expression}"
    
    def __repr__(self):
        return f"FunctionCommand({self.expression}, {self.color}, [{self.x_min}, {self.x_max}])"

class AIFunctionParser:
    """AI函数绘图指令解析器"""
    
    @staticmethod
    def parse_function_commands(ai_response: str) -> List[FunctionCommand]:
        """解析AI回复中的函数绘图指令"""
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
                            if isinstance(item, dict) and "expression" in item:
                                commands.append(AIFunctionParser._create_function_command(item))
                    elif isinstance(data, dict) and "expression" in data:
                        commands.append(AIFunctionParser._create_function_command(data))
                except json.JSONDecodeError as e:
                    print(f"JSON解析错误: {e}")
                    continue
        except Exception as e:
            print(f"解析函数命令时出错: {e}")
        
        # if没有找到JSON，尝试解析自然语言描述
        if not commands:
            commands = AIFunctionParser._parse_natural_language(ai_response)
        
        return commands
    
    @staticmethod
    def _create_function_command(data: Dict[str, Any]) -> FunctionCommand:
        """从数据字典创建函数命令"""
        expression = data.get("expression", "x")
        color = data.get("color", "#0066CC")
        x_min = data.get("x_min", -10)
        x_max = data.get("x_max", 10)
        line_width = data.get("line_width", 2)
        name = data.get("name")
        
        return FunctionCommand(expression, color, x_min, x_max, line_width, name)
    
    @staticmethod
    def _parse_natural_language(text: str) -> List[FunctionCommand]:
        """解析自然语言描述的函数绘图指令"""
        commands = []
        
        # 函数表达式匹配模式
        function_patterns = [
            # f(x) = 表达式 格式
            r'f\s*\(\s*x\s*\)\s*[=＝]\s*([^，,。\n]+)',
            # y = 表达式 格式
            r'y\s*[=＝]\s*([^，,。\n]+)',
            # 直接的数学表达式
            r'(?:函数|画|绘制|图像)\s*[：:]\s*([^，,。\n]+)',
            # sin(x), cos(x) 等直接表达式
            r'\b((?:sin|cos|tan|log|exp|sqrt|abs)\s*\([^)]+\)(?:\s*[\+\-\*/]\s*(?:sin|cos|tan|log|exp|sqrt|abs|\d+|\w+)\s*\([^)]*\)|[\+\-\*/]\s*[\d\w\.]+)*)',
            # 多项式表达式 x^2, x**2 等
            r'\b(x\s*(?:\*\*|\^)\s*\d+(?:\s*[\+\-]\s*\d*\s*\*?\s*x(?:\s*(?:\*\*|\^)\s*\d+)?)*(?:\s*[\+\-]\s*\d+)?)',
            # 简单的 x, 2*x 等
            r'\b(\d*\s*\*?\s*x(?:\s*[\+\-]\s*\d+)?)\b'
        ]
        
        # 颜色匹配
        color_map = {
            "红色": "#FF0000", "绿色": "#00FF00", "蓝色": "#0000FF",
            "黄色": "#FFFF00", "紫色": "#800080", "橙色": "#FFA500",
            "粉色": "#FFC0CB", "青色": "#00FFFF", "棕色": "#A52A2A",
            "黑色": "#000000", "灰色": "#808080"
        }
        
        # 范围匹配
        range_patterns = [
            r'(?:从|范围)\s*(-?\d+(?:\.\d+)?)\s*(?:到|至)\s*(-?\d+(?:\.\d+)?)',
            r'x\s*∈\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]',
            r'\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]'
        ]
        
        expressions_found = set()  # 避免重复
        
        for pattern in function_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                expression = match.group(1).strip()
                
                # 清理表达式
                expression = AIFunctionParser._clean_expression(expression)
                
                # 避免重复
                if expression in expressions_found or not expression:
                    continue
                expressions_found.add(expression)
                
                # 默认值
                color = "#0066CC"
                x_min, x_max = -10, 10
                line_width = 2
                
                # 查找颜色
                for color_name, color_code in color_map.items():
                    if color_name in text:
                        color = color_code
                        break
                
                # 查找范围
                for range_pattern in range_patterns:
                    range_match = re.search(range_pattern, text)
                    if range_match:
                        try:
                            x_min = float(range_match.group(1))
                            x_max = float(range_match.group(2))
                            break
                        except (ValueError, IndexError):
                            continue
                
                # 检查是否提到无穷大
                if "无穷" in text or "无限" in text or "全域" in text:
                    x_min, x_max = -100, 100  # 使用较大范围
                
                commands.append(FunctionCommand(expression, color, x_min, x_max, line_width))
        
        return commands
    
    @staticmethod
    def _clean_expression(expression: str) -> str:
        """清理和标准化函数表达式"""
        if not expression:
            return ""
        
        # 移除多余的空格
        expression = re.sub(r'\s+', '', expression)
        
        # 替换常见的数学符号
        replacements = {
            '×': '*',
            '÷': '/',
            '²': '**2',
            '³': '**3',
            '√': 'sqrt',
            'π': 'pi',
            'e': 'e',
            '^': '**',
            '²': '**2',
            '³': '**3'
        }
        
        for old, new in replacements.items():
            expression = expression.replace(old, new)
        
        # 处理隐式乘法 (如 2x -> 2*x)
        expression = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expression)
        expression = re.sub(r'([a-zA-Z])(\d)', r'\1*\2', expression)
        
        # 处理sin cos等函数前的系数 (如 2sin(x) -> 2*sin(x))
        expression = re.sub(r'(\d)(sin|cos|tan|log|exp|sqrt|abs)', r'\1*\2', expression)
        
        # 移除无效字符
        expression = re.sub(r'[^\w\+\-\*\/\(\)\.\*\,]', '', expression)
        
        return expression

class AIFunctionThread(QThread):
    """AI函数处理线程"""
    
    response_ready = pyqtSignal(str)
    commands_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, prompt: str, context: str = ""):
        super().__init__()
        self.prompt = prompt
        self.context = context
        self.ollama_client = OllamaFunctionClient()
    
    def run(self):
        try:
            # 构建完整的提示词
            full_prompt = self._build_prompt(self.prompt)
            
            # 获取AI回复
            response = self.ollama_client.chat(full_prompt)
            self.response_ready.emit(response)
            
            # 解析函数指令
            commands = AIFunctionParser.parse_function_commands(response)
            self.commands_ready.emit(commands)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _build_prompt(self, user_input: str) -> str:
        """构建完整的提示词"""
        system_prompt = """专业数学函数绘图助手，生成Python可执行的函数表达式。

支持的函数类型：
- 多项式函数: x**2, x**3, 2*x + 1
- 三角函数: sin(x), cos(x), tan(x), asin(x), acos(x), atan(x)
- 指数对数: exp(x), log(x), log10(x), sqrt(x)
- 复合函数: sin(x)*exp(-x/5), x**2 + sin(x)
- 其他函数: abs(x), floor(x), ceil(x)

表达式语法规则：
- 使用**表示幂运算 (如x**2, x**3)
- 乘法必须显式写出 (如2*x, 不能写2x)
- 常数: pi, e
- 变量: x (小写)

颜色设置：
- 红色: #FF0000, 绿色: #00FF00, 蓝色: #0000FF
- 黄色: #FFFF00, 紫色: #800080, 橙色: #FFA500
- 粉色: #FFC0CB, 青色: #00FFFF, 棕色: #A52A2A

范围设置：
- ifuser未指定范围，使用[-10, 10]
- if提到"无穷"、"全域"，使用[-100, 100]
- 支持自定义范围，如[-5, 5], [0, 2*pi]

标准输出格式：
```json
[
    {
        "expression": "sin(x)",
        "color": "#FF0000",
        "x_min": -10,
        "x_max": 10,
        "line_width": 2,
        "name": "正弦函数"
    }
]
```

注意事项：
1. 表达式必须是Python可执行的数学表达式
2. 只使用支持的函数和语法
3. 确保表达式语法正确
4. ifuser要求多个函数，用不同颜色区分

"""

        # if有上下文，添加到提示词中
        if self.context:
            system_prompt += f"\n当前画布状态：\n{self.context}\n\n"
        
        system_prompt += "user需求："
        
        return system_prompt + user_input
