# OEE_Test

`OEE_Test` 是给 `peip_aihub` 使用的 OEE 传感器异常检测测试算法包。它参考 `APC_Test` 的 wheel 封装方式，但因为当前包含多个算法，所以采用“顶层聚合 + 子算法包”的结构。

当前提供两个算法：

- `oee.pressure_detector`
- `oee.temperature_detector`

这两个算法都不开放 HTTP API，只作为 `peip_aihub` 内部 capability 使用。

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
    io.py
    scoring.py
  pressure/
    __init__.py
    domain.py
    controller.py
  temperature/
    __init__.py
    domain.py
    controller.py
```

职责说明：

- `domain.py`：只保存最小聚合路由 `algorithm_id -> class_path`。
- `algorithm.py`：提供 `peip_aihub` 看到的 `SensorAnalysisAlgorithm` wrapper 和 metadata 合并逻辑。
- `controller.py`：根据 `algorithm_id` 加载对应子算法 controller，并委托 `process_data` / `detect`。
- `factory.py`：提供 `create_algorithm(config)`、`get_algorithm_metadata(config)`、`get_supported_algorithms()`。
- `common/`：放共享输入基类、事件基类、JSON 化、传感器标准化和伪评分工具。
- `pressure/`：压力算法自己的模型、metadata、参数默认值和伪检测逻辑。
- `temperature/`：温度算法自己的模型、metadata、参数默认值和伪检测逻辑。

## Algorithm ID

`OEE_Test` 的 algorithm_id 采用和 `APC_Test` 类似的测试算法命名风格。

pressure：

```python
class PressureController:
    DEFAULT_ALGORITHM_ID = "oee.pressure_detector"

    @property
    def algorithm_id(self) -> str:
        return self.DEFAULT_ALGORITHM_ID
```

temperature：

```python
class TemperatureController:
    DEFAULT_ALGORITHM_ID = "oee.temperature_detector"

    @property
    def algorithm_id(self) -> str:
        return self.DEFAULT_ALGORITHM_ID
```

顶层 `domain.py` 只维护路由：

```python
ALGORITHM_CONTROLLERS = {
    "oee.temperature_detector": "oee_engine.temperature.TemperatureController",
    "oee.pressure_detector": "oee_engine.pressure.PressureController",
}
```

## Metadata

metadata 属于具体算法 controller，而不是顶层聚合层。

每个子算法 controller 自己定义：

- `DEFAULT_ALGORITHM_ID`
- `family`
- `version`
- `provider`
- `description`
- `when_to_use`
- `capabilities`
- `tags`
- `input_model`
- `output_model`
- `class_path`
- `metadata_defaults()`

顶层 `get_algorithm_metadata(config)` 会根据 `metadata.algorithm_id` 找到对应子算法 controller，再读取它的 `metadata_defaults()`。

示例：

```python
from oee_engine import get_algorithm_metadata

metadata = get_algorithm_metadata({
    "algorithm_id": "oee.pressure_detector",
})
```

返回的关键字段包括：

```text
algorithm_id
family
version
provider
description
when_to_use
capabilities
input_model
output_model
tags
class_path
```

## Capability 调用

此算法包的能力必须以 capability 形式供 `peip_aihub` 使用。

两个算法当前都声明：

```text
process_data
detect
```

调用链：

```text
payload -> process_data(payload) -> processed_data -> detect(processed_data) -> events
```

推荐通过 `call_algorithm_capability()`：

```python
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

`detect(processed_data)` 返回事件列表，经 `peip_aihub` JSON 化后为 `list[dict]`。

## 伪算法说明

当前 pressure 和 temperature 都是伪实现，仅用于验证封装模式和 `peip_aihub` capability 编排链路：

- pressure：按采样值相对均值的漂移生成异常分数，默认阈值较低。
- temperature：按温度波动相对均值的漂移生成异常分数，默认阈值较高。

这些逻辑不代表真实 OEE 算法效果。

## 打包和安装

在 `OEE_Test` 项目根目录执行：

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

也可以使用脚本构建、复制到 `peip_aihub/wheels` 并安装到当前 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\OEE_Test\scripts\build_and_import_wheel.ps1"
```

指定 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\OEE_Test\scripts\build_and_import_wheel.ps1" -Python "C:\tools\miniconda3\envs\peip_aihub\python.exe"
```

## 验证

运行包内烟测：

```powershell
python scripts\smoke_oee_test.py
```

运行测试：

```powershell
python -m pytest
```
