# APC_Test

`APC_Test` 是用于验证 `peip_aihub` 算法接入方式的示例 APC wheel。它不实现真实 APC 算法，`APCEngineController` 内部只保留伪逻辑；目标是演示算法包如何提供统一算法服务、metadata、capabilities、输入输出模型和 factory。

## 当前设计

`APC_Test` 提供一个统一 APC 算法服务类：`APCAlgorithm`。

它不再按工序拆分为多个算法，也不再在 metadata 中保存固定 `process`。具体工序由请求体中的 `APCInput.process` 决定。

算法包负责提供：

- `apc_engine.APCInput`
- `apc_engine.APCResult`
- `apc_engine.APCEngineController`
- `apc_engine.APCAlgorithm`
- `apc_engine.create_algorithm(config)`
- `apc_engine.get_algorithm_metadata(config)`

`peip_aihub` 负责：

- 注册算法。
- 加载 wheel。
- 合并 metadata。
- 根据 `api_path + call` 决定是否开放 HTTP API。
- 在 workflow 中按 `capabilities` 调用算法能力。

## 能力边界

`APCAlgorithm` 当前提供三个 capability：

```text
adjust
process_data
control
```

调用链示例：

```text
peip config -> apc_engine.create_algorithm(config)
        -> APCAlgorithm.adjust(payload)
        -> APCInput.from_payload(payload)
        -> APCEngineController.adjust(APCInput)
        -> APCResult
        -> APCAlgorithm.to_response(APCResult)
```

如果 workflow 需要更细粒度编排，也可以分别调用：

```text
APCAlgorithm.process_data(payload) -> features
APCAlgorithm.control(features) -> APCResult
```

## Metadata

`get_algorithm_metadata(config)` 会返回算法包默认 metadata，并允许 peip 通过 config 覆盖部分字段。

默认 metadata 包括：

- `algorithm_id`
- `family`
- `version`
- `provider`
- `description`
- `when_to_use`
- `capabilities`
- `input_model`
- `output_model`
- `result_model`
- `tags`

示例：

```python
from apc_engine import get_algorithm_metadata

metadata = get_algorithm_metadata({
    "algorithm_id": "apc.r2r_controller",
})
```

## 输入输出模型

`APCInput` 和 `APCResult` 是算法包自己的领域模型，`peip_aihub` 不应重复定义。

`APCInput` 使用 Pydantic `BaseModel`，字段中包含 `description` 和 `examples`，可被 FastAPI/OpenAPI 直接展示。

关键字段：

- `machine_id`
- `tube_id`
- `target_p`
- `p_data`
- `adj_data`
- `adjust_max_limit`
- `process`

其中 `process` 表示本次 APC 请求的工艺类型，例如 `RB` 或 `LP`。

## peip_aihub 配置示例

如果需要开放 HTTP API，peip 配置 `metadata.api_path` 和 `call`：

```yaml
algorithms:
  apc.r2r_controller:
    package: apc-engine
    class_path: apc_engine.create_algorithm
    metadata:
      algorithm_id: apc.r2r_controller
      api_path: /apc/adjust
    call:
      mode: method
      method: adjust
```

上述配置会在 `peip_aihub` 中开放：

```text
POST /api/v1/algorithms/apc/adjust
```

如果只希望算法供内部 workflow 调用，不需要开放 HTTP API，则不配置 `api_path` 和 `call`：

```yaml
algorithms:
  apc.r2r_controller:
    package: apc-engine
    class_path: apc_engine.create_algorithm
    metadata:
      algorithm_id: apc.r2r_controller
```

这种情况下算法仍会注册到 `AlgorithmRegistry`，workflow 可以按 metadata 中的 `capabilities` 调用 `adjust`、`process_data` 或 `control`。

## 直接调用 Demo

```python
from apc_engine import create_algorithm

algorithm = create_algorithm({
    "metadata": {
        "algorithm_id": "apc.r2r_controller",
    }
})

payload = {
    "machine_id": "M01",
    "tube_id": "T01",
    "target_p": 100.0,
    "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
    "adj_data": {},
    "adjust_max_limit": 2,
    "process": "RB",
}

result = algorithm.adjust(payload)
response = algorithm.to_response(result)
```

`response` 示例：

```json
{
  "adjustments": {
    "temperature": [0.03, 0.0315, 0.033, 0.0345, 0.036, 0.0375]
  },
  "warning": false,
  "blocked_zones": [],
  "blocked_by_actuator": {},
  "algorithm_id": "apc.r2r_controller"
}
```

## Workflow 调用 Demo

不通过 HTTP API 时，可以由 workflow 获取算法实例并按 capability 调用：

```python
from app.algorithms.handle import to_jsonable
from app.algorithms.service import get_algorithm_registry


def call_algorithm_capability(algorithm_id: str, capability: str, payload: dict) -> dict:
    registry = get_algorithm_registry()
    handle = registry.require(algorithm_id)

    capabilities = set(handle.spec.metadata.get("capabilities", []))
    if capability not in capabilities:
        raise ValueError(f"{algorithm_id} does not support capability: {capability}")

    method = getattr(handle.instance, capability, None)
    if not callable(method):
        raise ValueError(f"{algorithm_id} capability is not callable: {capability}")

    return to_jsonable(method(payload))
```

## Wheel 打包和安装

在 `APC_Test` 项目根目录执行：

```powershell
cd D:\lpls_wspace\peip_aihub\algorithms\APC_Test
python -m pip install --upgrade build
python -m build --wheel
```

构建完成后会生成：

```text
dist/
  apc_engine-0.1.0-py3-none-any.whl
```

也可以使用一键脚本构建、复制到 `peip_aihub/wheels` 并安装到当前 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\APC_Test\scripts\build_and_import_wheel.ps1"
```

如果 `peip_aihub` 运行在指定 conda 环境，需要确保脚本使用该环境的 Python，例如：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\APC_Test\scripts\build_and_import_wheel.ps1" -Python "C:\tools\miniconda3\envs\peip_aihub\python.exe"
```

## Entry Point

`pyproject.toml` 中声明了 peip 可发现的算法 factory：

```toml
[project.entry-points."peip.algorithms"]
apc_engine = "apc_engine.factory:create_algorithm"
```

当前 `peip_aihub` 主要通过 `class_path: apc_engine.create_algorithm` 加载算法；entry point 可作为后续包发现机制使用。

## 验证

安装后验证包是否可导入：

```powershell
python -c "from apc_engine import create_algorithm, get_algorithm_metadata; print(get_algorithm_metadata({'algorithm_id': 'apc.r2r_controller'})); print(create_algorithm({'metadata': {'algorithm_id': 'apc.r2r_controller'}}).metadata.to_dict())"
```

运行包内烟测：

```powershell
python scripts\smoke_apc_test.py
```

运行测试：

```powershell
python -m pytest
```
