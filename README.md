# ZMathJBoardF - 智能几何绘图板

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15.9-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-red.svg)](LICENSE)

ZMathJBoardF 是一款基于 PyQt5 开发的智能几何绘图软件，集成了 AI 辅助绘图功能，专为数学教学和几何学习设计。
<img width="132" height="132" alt="mathb" src="https://github.com/user-attachments/assets/be326bf2-3229-4712-920b-a690b8c8a1b5" />
## 作者说明
咱是一名来自深圳的初三在校生，这是我利用课余时间捣鼓的小项目～由于还在“学业+编程”双线作战，软件里可能藏着一些小 bug（毕竟没那么多时间逐行抠细节），还请大家多多包涵！另外，软件的动画部分目前还有些小缺陷，比如偶尔会有卡顿或过渡不流畅的情况，我会在后续更新中尽快优化，争取让动画效果更丝滑～

## 重要许可说明
除非得到作者（也就是我）的明确允许，否则 **严禁将本软件用于任何商业用途** 哦！如果您有商用的想法，欢迎通过邮箱 zjf20110511@qq.com 联系我～不过要提前说一声：工作日我得忙着应付作业和考试，可能没法及时回复，还请耐心等我周末上线~

## 主要功能

### 基础绘图功能
- 点绘制: 支持自由绘制点，可自定义颜色和大小
- 线段绘制: 连接两点绘制线段，支持固定长度约束
- 角度测量: 精确测量和显示角度
- 多边形绘制: 自动检测和绘制封闭图形
- 约束系统: 支持中点、比例点、垂直足等几何约束

### AI 智能助手
- 自然语言绘图: 通过文字描述自动生成几何图形
- 手拉手模型: 专门优化的等腰三角形手拉手模型生成
- 智能解析: 支持 JSON 格式和自然语言的绘图指令解析
- 实时反馈: AI 生成后可直接在画布上执行

### 函数图像绘制
- 数学函数: 支持常见数学函数绘制（二次函数、三角函数、指数函数等）
- 动态点: 支持在函数图像上添加动态点
- 坐标系统: 完整的坐标系和网格显示
- 缩放平移: 支持图像缩放和坐标轴平移

### 动画系统
- 路径动画: 支持点沿路径移动的动画效果
- 连接动画: 线段连接的动态效果
- 高级动画: 复杂的几何变换动画
- 动画控制: 播放、暂停、速度调节等控制功能

### 数据管理
- 状态保存: 自动保存绘图状态和界面设置
- 画布序列化: 完整的画布状态保存和恢复
- 导入导出: 支持多种格式的数据导入导出

## 安装说明

### 系统要求
- Windows 10/11
- Python 3.8 或更高版本
- 至少 4GB 内存


# ZMathJBoardF - Intelligent Geometry Drawing Board

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15.9-green.svg)](https://pypi.org/project/PyQt5/)
[![License](https://img.shields.io/badge/License-AGPL--3.0-red.svg)](LICENSE)

ZMathJBoardF is an intelligent geometry drawing software developed based on PyQt5, integrated with AI-assisted drawing functions, specifically designed for mathematics teaching and geometry learning.

## About the Author
I’m a 9th-grade student (junior high school) in Shenzhen, and this is a small project I tinkered with in my spare time! Since I’m juggling both schoolwork and programming, there might be some tiny bugs in the software (after all, I don’t have enough time to check every line of code in detail) — your understanding would be greatly appreciated! Additionally, the animation part of the software currently has some flaws, such as occasional lag or unsmooth transitions. I’ll optimize this as soon as possible in future updates to make the animation effects smoother.

## Important License Note
**Commercial use of this software is strictly prohibited unless explicitly permitted by the author (that’s me)!** If you have ideas for commercial use, feel free to contact me via email: zjf20110511@qq.com. But a heads-up: on weekdays, I’m busy with homework and exams, so I might not reply promptly. Please be patient and wait for me to “go online” on weekends!

## Key Features

### Basic Drawing Functions
- Point Drawing: Support freehand point drawing with customizable colors and sizes
- Line Segment Drawing: Connect two points to draw line segments, with support for fixed-length constraints
- Angle Measurement: Accurate measurement and display of angles
- Polygon Drawing: Automatic detection and drawing of closed shapes
- Constraint System: Support for geometric constraints such as midpoints, proportional points, and feet of perpendiculars

### AI Intelligent Assistant
- Natural Language Drawing: Automatically generate geometric shapes through text descriptions
- Hand-in-Hand Model: Optimized generation of isosceles triangle "hand-in-hand" models
- Intelligent Parsing: Support for parsing drawing instructions in JSON format and natural language
- Real-Time Feedback: AI-generated results can be directly executed on the canvas

### Function Graph Drawing
- Mathematical Functions: Support drawing of common mathematical functions (quadratic functions, trigonometric functions, exponential functions, etc.)
- Dynamic Points: Support adding dynamic points on function graphs
- Coordinate System: Complete coordinate system and grid display
- Zoom and Pan: Support for graph zooming and coordinate axis panning

### Animation System
- Path Animation: Support for animation effects of points moving along paths
- Connection Animation: Dynamic effects of line segment connections
- Advanced Animation: Complex geometric transformation animations
- Animation Control: Play, pause, speed adjustment, and other control functions

### Data Management
- State Saving: Automatically save drawing states and interface settings
- Canvas Serialization: Complete saving and restoration of canvas states
- Import and Export: Support for importing and exporting data in multiple formats

## Installation Instructions

### System Requirements
- Windows 10/11
- Python 3.8 or higher
- At least 4GB of RAM
