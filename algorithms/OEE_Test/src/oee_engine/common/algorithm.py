"""
zh: OEE_Test 算法基类兼容导出模块。
    真实实现已迁移到 algorithms.core.algorithm，本模块保留旧导入路径以兼容现有代码。
en: Compatibility export module for OEE_Test algorithm base classes.
    The real implementation lives in algorithms.core.algorithm; this module keeps the previous import path stable.
version: 0.1.0
author: stan ma
date: 2026-07-01
mail: botao.ma@laplace-tech.com
"""

from algorithms.core.algorithm import BaseAlgorithm, BaseControlAlgorithm, BaseDetectAlgorithm

__all__ = [
    "BaseAlgorithm",
    "BaseControlAlgorithm",
    "BaseDetectAlgorithm",
]
