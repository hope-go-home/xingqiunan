"""pytest 全局配置：把 backend 目录加入 sys.path，保证 `app` 包可导入"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
