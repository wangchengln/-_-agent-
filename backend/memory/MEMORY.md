# 长期记忆

> 此文件由 fufan OpenClaw 自动维护，记录跨会话的重要信息。

## 用户偏好

用户喜欢更加严谨的回答

## 重要事项

### 技能路径映射
- get_weather 技能的正确路径：skills/get_weather/SKILL.md
- 技能快照中的路径（./backend/skills/get_weather/SKILL.md）是错误的
- 下次调用 get_weather 时，应直接使用正确路径

### 新技能创建
- 创建了新的天气查询技能：get_weather_open
- 使用 OpenWeather API 替代 wttr.in，提供更稳定的天气信息
- 需要设置 OPENWEATHER_API_KEY 环境变量才能使用
- 技能文件位置：skills/get_weather_open/SKILL.md

### PDF转Markdown技能
- 创建了新的PDF处理技能：pdf_to_markdown
- 核心功能：将PDF文档转换为结构化Markdown格式
- 支持文本提取、格式保留和内容重组
- 技能文件位置：skills/pdf_to_markdown/SKILL.md
- 触发关键词：pdf转markdown、转换pdf、提取pdf文本、pdf转换
- 技术依赖：可能需要PyPDF2/pdfminer.six、pytesseract（OCR）、tabula-py等库

## 操作系统环境
- 当前运行环境：Windows 系统
- 注意：使用 Windows 命令行语法（dir, type, mkdir, del, rmdir）
- 文件路径分隔符使用反斜杠 \
- 环境变量格式：%变量名%
