# 算法类封装与 Metadata 基准

## 基准目标

算法包对 `peip_aihub` 暴露的对象应是一个 metadata-aware algorithm wrapper，而不是裸 controller。

这个 wrapper 负责：

- 持有稳定的 `algorithm_id`、`family`、`version`、`provider`、`description`、`when_to_use`、`capabilities`、`input_model`、`output_model`、`tags` 等管理 metadata。
- 对外提供 capabilities 中声明的方法，例如 `adjust`、`process_data`、`control` 或 `detect`。
- 在输入输出边界使用算法包自己的 domain model，而不是让 `peip_aihub` 重复定义影子模型。
- 通过 `to_response()` 或等价 JSON 化逻辑，把算法结果转换成 `peip_aihub` 可返回、可编排的数据。

`APC_Test` 的基准入口是：

```text
apc_engine.create_algorithm(config) -> APCAlgorithm
apc_engine.get_algorithm_metadata(config) -> dict
```

## Metadata 基准

算法 metadata 应有稳定默认值，并允许 `peip_aihub` 通过配置覆盖。

必备字段：

- `algorithm_id`：算法唯一 ID，必须由 wrapper 的 `algorithm_id` 和输出结果保持一致。
- `family`：算法族，例如 `apc`、`oee`。
- `version`：算法包语义版本，默认与 wheel 版本保持一致。
- `provider`：算法包或实现提供方，例如 `apc_engine`、`oee_engine`。
- `description`：一句话说明算法用途。
- `when_to_use`：说明 workflow 或路由何时应该选择该算法。
- `capabilities`：可被 `peip_aihub` 编排调用的方法名列表。
- `input_model`：算法包公开的输入模型路径。
- `output_model`：算法包公开的输出模型路径。
- `tags`：用于检索、分组和管理的标签。
- `class_path`：该 `algorithm_id` 对应的算法实现类路径；单算法包指向固定 controller，多算法聚合包指向实际子 controller。

可选字段：

- `api_path`、`call`：只有需要开放 HTTP API 时才在 `peip_aihub` 配置中声明；内部 workflow-only 算法不要默认携带。

## Factory 基准

factory 是 `peip_aihub` 加载算法 wheel 的稳定入口。

基准行为：

```python
def create_algorithm(config):
    metadata = AlgorithmMetadata.from_dict(config.get("metadata") or config)
    return Algorithm(metadata, config=config)


def get_algorithm_metadata(config):
    config = dict(config or {})
    return AlgorithmMetadata.from_dict(config.get("metadata") or config).to_dict()
```

要求：

- `create_algorithm()` 和 `get_algorithm_metadata()` 对配置形态的理解必须一致。
- 既支持直接传 metadata：`{"algorithm_id": "..."}`。
- 也支持 registry 完整配置：`{"metadata": {"algorithm_id": "..."}, ...}`。
- `get_algorithm_metadata()` 不应构造或调用真实算法逻辑，只做 metadata 解析。

## 单算法包基准

单算法包采用 `APC_Test` 模式：

```text
algorithm.py
controller.py
domain.py
factory.py
__init__.py
<core algorithm process>
```

职责划分：

- `domain.py`：定义输入输出模型，是算法包的数据契约来源。
- `controller.py`：实现算法内部流程和伪逻辑。
- `algorithm.py`：实现 metadata dataclass 和对 `peip_aihub` 暴露的 wrapper。
- `factory.py`：提供 `create_algorithm()` 和 `get_algorithm_metadata()`。
- `__init__.py`：导出公共 API。
- `<dir>`: 算法实现空间

单算法包可以把 metadata 默认值直接放在 metadata dataclass 中。

## 多算法聚合包基准

多算法包采用 `OEE_Test` 模式：

```text
algorithm.py
controller.py
domain.py
factory.py
common/
pressure/
temperature/
```

职责划分：

- 顶层 `domain.py` 只维护 `algorithm_id -> class_path` 路由。
- 顶层 `algorithm.py` 提供统一 wrapper 和 metadata 合并逻辑。
- 顶层 `controller.py` 根据 `algorithm_id` 加载并委托具体子算法。
- 子算法目录拥有自己的 domain model、controller、metadata 默认值和参数默认值。

多算法聚合包可以把通用默认值放在 metadata dataclass 中，把算法特有默认值放在子 controller 的 `metadata_defaults()` 中。最终对外返回的 metadata 必须与单算法包保持同等字段完整性。

## Capability 原则

`capabilities` 是 workflow 编排契约，不是文档注释。

原则：

- capabilities 中声明的方法必须在 wrapper 上可调用。
- wrapper 应负责输入转换、输出 JSON 化和 algorithm_id 对齐。
- controller 可以保留内部方法，但未声明为 capability 的方法不应被 workflow 直接依赖。
- HTTP API 由 `metadata.api_path + call` 决定，不能仅因存在 capability 就自动开放。

`APC_Test` 示例：

```text
adjust = process_data + control
capabilities = ["adjust", "process_data", "control"]
```

`OEE_Test` 示例：

```text
detect = process_data 后的异常事件检测
capabilities = ["process_data", "detect"]
```

## 配置覆盖原则

配置覆盖应遵循从默认到显式的顺序：

```text
模型默认参数 < cfg.params < constructor.kwargs.params < 顶层 params < payload.params
```

其中：

- 模型默认参数属于算法包，可独立运行。
- `constructor.kwargs.params` 是 `algorithms.yaml` 中推荐的算法实例参数覆盖方式。
- 顶层 `params` 可兼容 registry 或测试场景直接传参。
- `payload.params` 是单次请求覆盖，优先级最高。

## 验收基准

新增或修改算法包时，至少验证：

- `get_algorithm_metadata({"algorithm_id": id})` 返回正确算法的完整 metadata。
- `get_algorithm_metadata({"metadata": {"algorithm_id": id}})` 与直接传 metadata 行为一致。
- `create_algorithm({"metadata": {"algorithm_id": id}}).algorithm_id == id`。
- metadata 中声明的每个 capability 都能被 wrapper 调用。
- 输出结果中的 `algorithm_id` 与 wrapper metadata 一致。
- 不开放 HTTP API 的内部算法不携带默认 `api_path` 和 `call`。
- 配置中的 `constructor.kwargs.params` 能覆盖算法默认参数。
