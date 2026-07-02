# OEE_Test

`OEE_Test` 是给 `peip_aihub` 使用的 OEE 传感器异常检测测试算法包。它参考 `APC_Test` 的 wheel 封装方式，基于 `peip-algorithms-core` 实现 metadata-aware wrapper，并采用“顶层聚合 + 子算法包”的结构。

当前提供两个算法：

- `oee.pressure_detector`
- `oee.temperature_detector`

这两个算法都不开放 HTTP API，只作为 `peip_aihub` 内部 capability 使用。

## 依赖关系

`OEE_Test` 依赖统一算法核心包 `peip-algorithms-core`（导入路径 `algorithms.core`），复用其中的：

- `BaseAlgorithmMetadata`：metadata 字段契约与序列化
- `BaseDetectAlgorithm`：检测类算法 wrapper 基类与 capability 校验
- `to_jsonable()`：响应序列化

核心包源码位于 `algorithms/algorithms/`，详细设计见 [algorithms/algorithms/README.md](../algorithms/README.md)。

`oee_engine.common` 仍保留对 `algorithms.core` 的兼容导出，旧代码可继续 `from oee_engine.common import BaseAlgorithmMetadata` 导入。

## 设计原则

当算法包内只有一个算法时，可以采用 `APC_Test` 的五文件模式：

```text
algorithm.py
controller.py
domain.py
factory.py
__init__.py
```

当算法包内包含多个算法时，`oee_engine` 顶层只保留聚合能力所需的最小代码；具体算法的 input、output、metadata、参数默认值和算法实现都放在各自子目录中。

## 当前结构

```text
src/oee_engine/
  __init__.py
  algorithm.py
  controller.py
  domain.py
  factory.py
  common/
    __init__.py
    algorithm.py      # 兼容导出，真实实现位于 algorithms.core.algorithm
    metadata.py       # 兼容导出，真实实现位于 algorithms.core.metadata
    domain.py         # BaseOeeInput / BaseOeeOutput / coerce_sensors
    scoring.py        # 伪评分与传感器数值工具
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

职责说明：

- `domain.py`：维护 `algorithm_id -> class_path` 路由，并提供 `get_supported_algorithms()`。
- `algorithm.py`：提供 `SensorAnalysisAlgorithm` wrapper 和 `SensorAnalysisAlgorithmMetadata` 路由逻辑。
- `controller.py`：根据 `algorithm_id` 动态加载对应子算法 controller，并委托 `process_data` / `detect`。
- `factory.py`：提供 `create_algorithm(config)`、`get_algorithm_metadata(config)`、`get_supported_algorithms()`。
- `common/domain.py`：OEE 输入输出基类、传感器标准化。
- `common/scoring.py`：共享伪评分与数值提取工具。
- `pressure/`、`temperature/`：各自维护模型、metadata 默认值、参数默认值和伪检测逻辑。

## Algorithm ID

`OEE_Test` 的 algorithm_id 采用和 `APC_Test` 类似的测试算法命名风格。

pressure：

```python
class PressureAlgorithmMetadata(BaseAlgorithmMetadata):
    algorithm_id: str = "oee.pressure_detector"
```

temperature：

```python
class TemperatureAlgorithmMetadata(BaseAlgorithmMetadata):
    algorithm_id: str = "oee.temperature_detector"
```

顶层 `domain.py` 只维护路由：

```python
ALGORITHM_CONTROLLERS = {
    "oee.temperature_detector": "oee_engine.temperature.TemperatureController",
    "oee.pressure_detector": "oee_engine.pressure.PressureController",
}
```

`get_supported_algorithms()` 返回当前 wheel 支持的全部 algorithm_id。

## Metadata

metadata 属于具体子算法，字段契约由 `algorithms.core.BaseAlgorithmMetadata` 统一管理。

标准字段：

- `algorithm_id`
- `family`
- `version`
- `provider`
- `description`
- `when_to_use`
- `capabilities`
- `input_model`
- `output_model`
- `tags`
- `class_path`

每个子算法提供自己的 metadata 子类，例如 `PressureAlgorithmMetadata` 与 `TemperatureAlgorithmMetadata`，用于声明 `algorithm_id`、模型路径、标签和适用场景等默认值。

顶层 `get_algorithm_metadata(config)` 会根据 `metadata.algorithm_id` 路由到对应子算法 metadata 类，再返回 `to_dict()` 结果。

示例：

```python
from oee_engine import get_algorithm_metadata, get_supported_algorithms

print(get_supported_algorithms())
# ['oee.pressure_detector', 'oee.temperature_detector']

metadata = get_algorithm_metadata({
    "algorithm_id": "oee.pressure_detector",
})
```

## Capability 调用

此算法包的能力必须以 capability 形式供 `peip_aihub` 使用。

公共算法抽象位于 `algorithms.core`：

```text
BaseAlgorithm
BaseDetectAlgorithm
BaseControlAlgorithm
```

`SensorAnalysisAlgorithm` 继承 `BaseDetectAlgorithm`，当前两个子算法都声明：

```text
process_data
detect
```

调用链：

```text
payload -> process_data(payload) -> processed_data -> detect(processed_data) -> events
```

推荐通过 `peip_aihub` 提供的 helper 调用：

```python
from app.algorithms.service import call_algorithm_capability

features = call_algorithm_capability(
    "oee.pressure_detector",
    "process_data",
    payload,
)

events = call_algorithm_capability(
    "oee.pressure_detector",
    "detect",
    features,
)
```

或通过 `AlgorithmRegistry.invoke_capability()`：

```python
from app.algorithms.service import get_algorithm_registry

registry = get_algorithm_registry()

features = registry.invoke_capability(
    "oee.temperature_detector",
    "process_data",
    payload,
)

events = registry.invoke_capability(
    "oee.temperature_detector",
    "detect",
    features,
)
```

不要通过 HTTP 调用本服务算法 API，也不要直接 import 子算法内部类绕过 `AlgorithmRegistry`。

## peip_aihub 注册方式

在 `peip_aihub/configs/algorithms.yaml` 中注册：

```yaml
algorithms:
  oee.temperature_detector:
    package: oee-engine
    class_path: oee_engine.create_algorithm
    metadata:
      algorithm_id: oee.temperature_detector

  oee.pressure_detector:
    package: oee-engine
    class_path: oee_engine.create_algorithm
    metadata:
      algorithm_id: oee.pressure_detector
```

注意：

- 不配置 `metadata.api_path`。
- 不配置 `call`。
- 不配置算法参数时，会使用各自 Input 模型中的默认值。
- workflow 执行时通过 capability 调用。

如需在 `peip_aihub` 配置中覆盖默认参数，可以增加 `constructor.kwargs.params`：

```yaml
algorithms:
  oee.pressure_detector:
    package: oee-engine
    class_path: oee_engine.create_algorithm
    metadata:
      algorithm_id: oee.pressure_detector
    constructor:
      kwargs:
        params:
          score_threshold: 0.01
          max_events: 1
```

参数合并顺序为：`cfg.params` → `constructor.kwargs.params` → 顶层 `params`，最后再由 payload 中的 `params` 覆盖。

## 输入输出模型

pressure：

- `oee_engine.pressure.PressureInput`
- `oee_engine.pressure.PressureEvent`
- 默认参数：`{"score_threshold": 0.02, "max_events": 1}`

temperature：

- `oee_engine.temperature.TemperatureInput`
- `oee_engine.temperature.TemperatureEvent`
- 默认参数：`{"score_threshold": 0.3, "max_events": 3}`

输入支持单传感器形式：

```python
payload = {
    "alarm_index": "pressure_alarm",
    "alarm_reason": "炉管压力波动",
    "conventional_solution": "检查压力传感器和阀门状态",
    "sensor_name": "tube_pressure",
    "coordinate": "Tube-1",
    "timestamps": ["2026-05-14 20:03:51", "2026-05-14 20:03:52"],
    "values": [1.0, 20.0],
}
```

也支持标准多传感器形式：

```python
payload = {
    "alarm_index": "temperature_alarm",
    "sensors": [
        {
            "name": "zone_1_temperature",
            "coordinate": "Tube-1/Zone-1",
            "timestamps": ["2026-05-14 20:03:51", "2026-05-14 20:03:52"],
            "values": [700.0, 735.0],
        }
    ],
}
```

`process_data(payload)` 返回标准化后的中间态 `dict`。

`detect(processed_data)` 返回事件列表，经 `to_jsonable()` 后为 `list[dict]`。

## 伪算法说明

当前 pressure 和 temperature 都是伪实现，仅用于验证封装模式和 `peip_aihub` capability 编排链路：

- pressure：按采样值相对均值的漂移生成异常分数，默认阈值较低。
- temperature：按温度波动相对均值的漂移生成异常分数，默认阈值较高。

这些逻辑不代表真实 OEE 算法效果。

## 打包和安装

`OEE_Test` 依赖 `peip-algorithms-core`，建议优先使用仓库根目录下的批量脚本，它会先构建核心包，再构建业务算法包：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\build_and_install_wheels.ps1"
```

指定 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\build_and_install_wheels.ps1" -Python "C:\tools\miniconda3\envs\peip_aihub\python.exe"
```

仅构建 `OEE_Test` 时，在 `OEE_Test` 项目根目录执行：

```powershell
cd D:\lpls_wspace\peip_aihub\algorithms\OEE_Test
python -m pip install --upgrade build
python -m build --wheel
```

构建完成后会生成：

```text
dist/
  oee_engine-0.1.0-py3-none-any.whl
```

也可以使用单包脚本构建、复制到 `peip_aihub/wheels` 并安装到当前 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\OEE_Test\scripts\build_and_import_wheel.ps1"
```

单包脚本不会自动安装 `peip-algorithms-core`；若环境中尚未安装核心包，请先执行批量脚本，或手动从 `wheels/` 安装 `peip_algorithms_core-0.1.0-py3-none-any.whl`。

## Entry Point

`pyproject.toml` 中声明了 peip 可发现的算法 factory：

```toml
[project.entry-points."peip.algorithms"]
oee_engine = "oee_engine.factory:create_algorithm"
```

## 验证

安装后验证包是否可导入：

```powershell
python -c "from oee_engine import get_algorithm_metadata, get_supported_algorithms; print(get_supported_algorithms()); print(get_algorithm_metadata({'algorithm_id': 'oee.pressure_detector'}))"
```

运行包内烟测：

```powershell
python scripts\smoke_oee_test.py
```

运行测试：

```powershell
python -m pytest
```
