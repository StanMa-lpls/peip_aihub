"""
zh: OEE_Test metadata 基类兼容导出模块。
    真实实现已迁移到 algorithms.core.metadata，本模块保留旧导入路径以兼容现有代码。
en: Compatibility export module for the OEE_Test metadata base class.
    The real implementation lives in algorithms.core.metadata; this module keeps the previous import path stable.
version: 0.1.0
author: stan ma
date: 2026-07-01
mail: botao.ma@laplace-tech.com
"""

from algorithms.core.metadata import BaseAlgorithmMetadata

__all__ = [
    "BaseAlgorithmMetadata",
]
