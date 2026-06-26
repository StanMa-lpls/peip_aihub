# APC_Test

`APC_Test` 是一个用于验证 peip 算法能力接入方式的示例 APC wheel。它不实现真实 APC 算法，`APCEngineController` 内部只使用伪逻辑占位；真实目标是演示算法包如何向 peip 暴露统一能力、metadata、输入输出模型和 factory。

`APC_Test` 只负责算法包内应该拥有的信息：

- `apc_engine.APCInput`
- `apc_engine.APCResult`
- `apc_engine.APCEngineController`
- `apc_engine.APCAlgorithm`
- `apc_engine.create_algorithm`
- `apc_engine.get_algorithm_metadata`

peip 负责注册表、路由、HTTP 契约、部署配置和算法选择，不应该由算法 wheel 内置这些配置。

## 设计边界

期望调用链：

```text
peip config -> apc_engine.create_algorithm(config)
        -> APCAlgorithm.parse_input(payload)
        -> APCEngineController.adjust(APCInput)
        -> APCResult
        -> APCAlgorithm.to_response(APCResult)
```

这样 peip 不需要重复定义 `APCInput/APCResult`，也不需要反复 `dict -> peip APCInput -> dict -> wheel APCInput` 转换。算法包是领域模型和算法能力的来源，peip 是算法网关和配置管理方。

## Wheel 打包过程

在 `APC_Test` 项目根目录执行：

```powershell
cd D:\lpls_wspace\peip_aihub\algorithms\APC_Test
python -m pip install --upgrade build
python -m build
```

构建完成后会生成：

```text
dist/
  apc_engine-0.1.0-py3-none-any.whl
  apc_engine-0.1.0.tar.gz
```

本地安装 wheel：

```powershell
python -m pip install --force-reinstall .\dist\apc_engine-0.1.0-py3-none-any.whl
```

安装后验证包是否可导入：

```powershell
python -c "from apc_engine import create_algorithm; print(create_algorithm({'metadata': {'algorithm_id': 'apc.test.r2r_controller.rb', 'process': 'RB'}}).metadata.to_dict())"
```

运行包内烟测：

```powershell
python scripts\smoke_apc_test.py
```

运行测试：

```powershell
python -m pytest
```

## Entry Point

`pyproject.toml` 中声明了 peip 可发现的算法 factory：

```toml
[project.entry-points."peip.algorithms"]
apc_engine = "apc_engine.factory:create_algorithm"
```

安装 wheel 后，peip 可以通过 Python package metadata 发现 `peip.algorithms` 组里的 `apc_engine`，得到 `create_algorithm(config)` 这个工厂函数。

## peip 使用 Demo

peip 的配置应放在 peip 自己的配置文件中，例如：

```yaml
algorithms:
  apc.test.r2r_controller.rb:
    provider: apc_engine
    entry_point_group: peip.algorithms
    entry_point_name: apc_engine
    metadata:
      algorithm_id: apc.test.r2r_controller.rb
      family: apc
      version: "0.1.0"
      process: RB
      description: "APC_Test 伪 RB 控制器"
      tags:
        - test
        - pseudo
        - rb
    strict_process: true
```

peip 侧可以按配置加载并调用：

```python
from importlib.metadata import entry_points


def load_algorithm_from_peip_config(config: dict):
    group = config.get("entry_point_group", "peip.algorithms")
    name = config["entry_point_name"]
    matches = entry_points(group=group)
    factory = next(ep.load() for ep in matches if ep.name == name)
    return factory(config)


peip_config = {
    "provider": "apc_engine",
    "entry_point_group": "peip.algorithms",
    "entry_point_name": "apc_engine",
    "metadata": {
        "algorithm_id": "apc.test.r2r_controller.rb",
        "family": "apc",
        "version": "0.1.0",
        "process": "RB",
        "description": "APC_Test 伪 RB 控制器",
        "tags": ["test", "pseudo", "rb"],
    },
    "strict_process": True,
}

payload = {
    "algorithm_id": "apc.test.r2r_controller.rb",
    "machine_id": "M01",
    "tube_id": "T01",
    "target_p": 100.0,
    "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
    "adj_data": {},
    "adjust_max_limit": 2,
    "process": "RB",
}

algorithm = load_algorithm_from_peip_config(peip_config)
result = algorithm.adjust(payload)
response = algorithm.to_response(result)
metadata = algorithm.metadata.to_dict()
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
  "algorithm_id": "apc.test.r2r_controller.rb"
}
```

## 直接调用 Demo

如果不通过 entry point，也可以直接导入 factory：

```python
from apc_engine import create_algorithm

algorithm = create_algorithm({
    "metadata": {
        "algorithm_id": "apc.test.r2r_controller.rb",
        "version": "0.1.0",
        "process": "RB",
    },
    "strict_process": True,
})

result = algorithm.adjust(payload)
response = algorithm.to_response(result)
```
