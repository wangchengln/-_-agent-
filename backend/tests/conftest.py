"""Pytest 配置：确保测试可从 backend 根目录导入顶层模块。

测试文件已统一放在 backend/tests/ 下，但它们以 `from api...`、
`from recsys...`、`from domain...` 等顶层包方式导入。这里把 backend
根目录（本文件父目录的上一级）插入 sys.path，使导入在新位置仍然有效。
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
