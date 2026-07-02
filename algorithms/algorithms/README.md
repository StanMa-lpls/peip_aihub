# 统一算法模块封装架构

`peip-algorithms-core` 提供算法 wheel 共用的封装基类、metadata 契约和响应序列化工具。各业务算法包只需要保留自己的输入输出模型、controller、wrapper 和 factory，通过 `algorithms.core` 复用统一管理能力。

## 设计目标

- 统一算法对 `peip_aihub` 暴露的对象形态：metadata-aware algorithm wrapper。
- 统一 metadata 字段、类型转换、配置覆盖和 JSON 输出行为。
- 统一 `process_data`、`detect`、`control` 等 capability 校验规则。
- 让输入输出 domain model 仍归具体算法包所有，避免平台侧重复定义影子模型。
- 支持单算法包和多算法聚合包采用一致的 factory / metadata / capability 接入方式。

## 当前包结构

```text
algorithms/
  pyproject.toml
  src/
    algorithms/
      __init__.py
      core/
        __init__.py
        algorithm.py
        metadata.py
        serialization.py
```

职责说明：

- `algorithms.core.algorithm`：定义 `BaseAlgorithm`、`BaseDetectAlgorithm`、`BaseControlAlgorithm`，负责算法 wrapper 基类和 capability 校验。
- `algorithms.core.metadata`：定义 `BaseAlgorithmMetadata`，负责算法注册、发现、编排和管理所需的稳定 metadata 契约。
- `algorithms.core.serialization`：定义 `to_jsonable()`，负责把算法返回值转换为 JSON 友好的基础数据结构。
- `algorithms.__init__` / `algorithms.core.__init__`：提供稳定公共导出入口。

推荐导入方式：

```python
from algorithms.core import (
    BaseAlgorithmMetadata,
    BaseDetectAlgorithm,
    BaseControlAlgorithm,
    to_jsonable,
)
```

## 核心抽象

### BaseAlgorithm

`BaseAlgorithm` 是所有算法 wrapper 的最小基类，定义统一对外接口：

- `metadata`：返回算法 metadata 对象。
- `algorithm_id`：从 `metadata.algorithm_id` 派生的唯一算法 ID。
- `process_data(payload)`：算法数据预处理入口。
- `to_response(result)`：默认使用 `to_jsonable()` 输出响应数据。
- `validate_capabilities()`：校验 metadata 中声明的 capability 是否真实可调用。

### BaseDetectAlgorithm

`BaseDetectAlgorithm` 适用于检测、识别、异常发现、事件生成类算法。

它要求：

- `metadata.capabilities` 中必须包含 `"detect"`。
- 子类必须实现真实的 `detect(data)` 方法，不能只继承基类占位实现。

### BaseControlAlgorithm

`BaseControlAlgorithm` 适用于控制、调参、动作建议、优化输出类算法。

它要求：

- `metadata.capabilities` 中必须包含 `"control"`。
- 子类必须实现真实的 `control(data)` 方法，不能只继承基类占位实现。

如果一个算法同时支持检测和控制，可以直接继承 `BaseAlgorithm`，并同时实现 `detect()`、`control()`，再在 `metadata.capabilities` 中声明对应能力。

## Metadata 契约

`BaseAlgorithmMetadata` 使用 Pydantic `BaseModel` 封装，并开启 `frozen=True`，用于保证 metadata 对象不可变且具备稳定的字段转换行为。

标准字段：

- `algorithm_id`：算法唯一 ID。
- `family`：算法族，例如 `apc`、`oee`。
- `version`：算法包版本。
- `provider`：算法包或实现提供方。
- `description`：一句话说明算法用途。
- `when_to_use`：说明 workflow 或路由何时应该选择该算法。
- `capabilities`：可被 `peip_aihub` 编排调用的方法名。
- `input_model`：算法包公开的输入模型路径。
- `output_model`：算法包公开的输出模型路径。
- `tags`：用于检索、分组和管理的标签。
- `class_path`：该 `algorithm_id` 对应的算法实现类路径。

保留的兼容 API：

```python
metadata = BaseAlgorithmMetadata.from_dict(config)
metadata_dict = metadata.to_dict()
```

`to_dict()` 使用 `model_dump(mode="json")`，因此 `capabilities`、`tags` 等 tuple 字段会输出为 list，便于注册表、配置和 API 返回使用。

业务算法可以通过继承覆盖默认值：

```python
from algorithms.core import BaseAlgorithmMetadata


class PressureAlgorithmMetadata(BaseAlgorithmMetadata):
    algorithm_id: str = "oee.pressure_detector"
    family: str = "oee"
    provider: str = "oee_engine"
    description: str = "OEE 压力异常检测器"
    when_to_use: str = "当需要根据压力时序数据检测异常时使用。"
    capabilities: tuple[str, ...] = ("process_data", "detect")
    input_model: str = "oee_engine.pressure.PressureInput"
    output_model: str = "oee_engine.pressure.PressureEvent"
    tags: tuple[str, ...] = ("oee", "pressure")
    class_path: str = "oee_engine.pressure.PressureController"
```

## Capability 原则

`capabilities` 是 workflow 编排契约，不是文档注释。

要求：

- metadata 中声明的方法必须在 wrapper 上真实存在且可调用。
- `BaseDetectAlgorithm` 会强制要求 `"detect"`。
- `BaseControlAlgorithm` 会强制要求 `"control"`。
- `process_data`、`detect`、`control` 如果只是继承基类占位实现，会被视为未实现。
- 自定义 capability 也可以声明，但 wrapper 必须提供同名可调用方法。

示例：

```python
class MyDetector(BaseDetectAlgorithm):
    def __init__(self, metadata: BaseAlgorithmMetadata) -> None:
        self._metadata = metadata
        self.validate_capabilities()

    @property
    def metadata(self) -> BaseAlgorithmMetadata:
        return self._metadata

    def process_data(self, payload=None) -> dict:
        return {"payload": payload}

    def detect(self, data=None) -> list:
        return []
```

## 算法包推荐结构

### 单算法包

单算法包适合一个 wheel 只暴露一个算法，例如 APC 控制器。

```text
src/<engine>/
  __init__.py
  algorithm.py
  controller.py
  domain.py
  factory.py
```

职责：

- `domain.py`：定义输入输出模型，是算法包自己的数据契约来源。
- `controller.py`：实现算法内部流程和核心逻辑。
- `algorithm.py`：实现 metadata 子类和对 `peip_aihub` 暴露的 wrapper。
- `factory.py`：提供 `create_algorithm()` 和 `get_algorithm_metadata()`。
- `__init__.py`：导出公共 API。

### 多算法聚合包

多算法聚合包适合一个 wheel 内包含多个同类算法，例如 OEE pressure / temperature 检测器。

```text
src/<engine>/
  __init__.py
  algorithm.py
  controller.py
  domain.py
  factory.py
  common/
  pressure/
    __init__.py
    domain.py
    metadata.py
    controller.py
  temperature/
    __init__.py
    domain.py
    metadata.py
    controller.py
```

职责：

- 顶层 `domain.py`：维护 `algorithm_id -> class_path` 路由。
- 顶层 `algorithm.py`：提供统一 wrapper 和 metadata 合并逻辑。
- 顶层 `controller.py`：根据 `algorithm_id` 加载并委托具体子算法。
- 子算法目录：维护自己的 domain model、metadata 默认值、参数默认值和算法实现。
- `common/`：只放该算法包内部共享的业务模型、评分函数或兼容导出，不再承载跨算法包的通用基类。

## Factory 基准

算法包需要提供两个稳定入口：

```python
def create_algorithm(config):
    config = dict(config or {})
    metadata = AlgorithmMetadata.from_dict(config.get("metadata") or config)
    return Algorithm(metadata, config=config)


def get_algorithm_metadata(config):
    config = dict(config or {})
    return AlgorithmMetadata.from_dict(config.get("metadata") or config).to_dict()
```

要求：

- `create_algorithm()` 和 `get_algorithm_metadata()` 对配置形态的解析必须一致。
- 支持直接传 metadata：`{"algorithm_id": "..."}`。
- 支持 registry 完整配置：`{"metadata": {"algorithm_id": "..."}, ...}`。
- `get_algorithm_metadata()` 不应构造或调用真实算法逻辑，只做 metadata 解析。

## 输入输出模型边界

统一核心包不定义具体业务输入输出模型。输入输出模型属于算法包本身，例如：

- APC：`apc_engine.APCInput`、`apc_engine.APCResult`
- OEE：`oee_engine.pressure.PressureInput`、`oee_engine.pressure.PressureEvent`

推荐使用 Pydantic 定义 domain model，并提供：

- `from_payload()`：处理配置、请求体或已有模型对象。
- `from_dict()`：处理普通字典输入。
- `to_dict()`：输出 JSON 友好字典。
- `validate_*()`：执行领域约束校验。

## 序列化规则

`to_jsonable()` 会按以下顺序转换算法返回值：

- 优先调用对象的 `to_dict()`。
- 其次调用 Pydantic 模型的 `model_dump(mode="json")`。
- 对普通对象使用 `vars()`。
- 对 `Mapping` 递归转换 key/value。
- 对 list / tuple 递归转换元素。
- 对 str / int / float / bool / None 原样返回。
- 其他对象转换为字符串。

算法 wrapper 的 `to_response()` 默认使用该函数，业务 wrapper 可以按需覆盖。

## 构建和依赖

业务算法包依赖统一核心包：

```toml
dependencies = [
    "pydantic>=2",
    "peip-algorithms-core>=0.1.0",
]
```

本地测试时可以在 `pyproject.toml` 中加入核心包源码路径：

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src", "../algorithms/src"]
```

批量构建脚本会优先构建 `algorithms` 核心包，并通过本地 `wheels` 目录解析业务算法包对 `peip-algorithms-core` 的依赖。

## 接入检查清单

新增或改造算法包时，至少验证：

- `get_algorithm_metadata({"algorithm_id": id})` 返回完整 metadata。
- `get_algorithm_metadata({"metadata": {"algorithm_id": id}})` 与直接传 metadata 行为一致。
- `create_algorithm({"metadata": {"algorithm_id": id}}).algorithm_id == id`。
- metadata 中声明的每个 capability 都能在 wrapper 上调用。
- wrapper 构造阶段调用 `validate_capabilities()`。
- 输出结果中的 `algorithm_id` 与 wrapper metadata 一致。
- 不开放 HTTP API 的内部算法不默认携带 `api_path` 和 `call`。
- 运行算法包自己的 tests / smoke tests。
