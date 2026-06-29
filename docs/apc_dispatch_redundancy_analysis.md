# peip_inference_interface 调度 APC 算法的重复定义与重复操作分析

## 背景

当前 `peip_inference_interface` 在调度 APC 算法时，已经具备独立 REST 入口、APC 契约、注册表、dispatch 控制器和 wheel 适配层。整体链路可以工作，但 peip 侧对 APC 领域模型和算法控制器做了较厚的二次封装，导致输入输出对象、校验、注册表解析和 `to_dict/from_dict` 转换在多个层级重复出现。

当前主要调用链：

```text
/v1/apc/adjust
  -> DEFAULT_APC_CONTRACT_REGISTRY.match(payload)
  -> APCAdjustContract.to_graph_input(payload)
  -> validate_apc_adjust_request(payload)
  -> reasoning.domain.apc.APCInput.from_dict(canon)
  -> APCDispatchController.adjust(algorithm_id, apc_input)
  -> APCEngineController.adjust(apc_input)
  -> apc_engine.APCEngineController.adjust(apc_engine.APCInput)
  -> apc_engine.APCResult
  -> reasoning.domain.apc.APCResult
  -> response dict
```

## 重复类定义

### 1. `APCInput` 被 peip 与 wheel 各定义一套

peip 侧定义位置：

- `peip_inference_interface/src/reasoning/domain/apc.py`

wheel 侧定义位置：

- `APC_Backend/src/apc_engine/domain.py`

两者字段高度一致：

```python
machine_id: str
tube_id: str
target_p: float
p_data: dict
adj_data: dict
adjust_max_limit: int
process: str
```

这会形成“影子领域模型”：APC 算法包已经拥有自己的输入模型，peip 又维护一套几乎相同的模型。只要 wheel 侧字段、默认值或校验规则变化，peip 侧就需要同步修改，否则会出现行为漂移。

### 2. `APCResult` 被 peip 与 wheel 各定义一套，并且已经不一致

peip 侧当前结构：

```python
adjustments: list[float]
warning: bool
blocked_zones: list[int]
algorithm_id: str
```

wheel 侧当前结构：

```python
adjustments: dict[str, list[float]]
warning: bool
blocked_zones: list[int]
blocked_by_actuator: dict[str, list[int]]
algorithm_id: str
```

这里不是单纯重复，而是已经发生结构漂移。wheel 侧支持多 actuator，例如：

```json
{
  "adjustments": {
    "temperature": [0.1, 0.2],
    "flow": [0.01, 0.02]
  },
  "blocked_by_actuator": {
    "temperature": [1],
    "flow": [2]
  }
}
```

但 peip 侧仍假设 `adjustments` 是裸 `list[float]`，这会导致多 actuator 输出无法正确表达，甚至在转换时失败或丢失 `flow`、`blocked_by_actuator` 等信息。

### 3. `APCEngineController` 适配器与 wheel 控制器职责重叠

peip 侧位置：

- `peip_inference_interface/src/reasoning/adapters/apc_engine_controller.py`

wheel 侧位置：

- `APC_Backend/src/apc_engine/_adapter.py`

peip 侧 `APCEngineController` 的核心行为是：

```python
_input = _APCInput.from_dict(apc_input.to_dict() if apc_input else None)
_result = self._impl.adjust(_input)
return APCResult.from_dict(_result.to_dict())
```

也就是说，这一层主要在 peip 的 `APCInput/APCResult` 与 wheel 的 `APCInput/APCResult` 之间来回转换。若 peip 直接消费算法 wheel 暴露的统一算法能力，这层可以显著变薄，甚至被算法包自己的 `APCAlgorithm` 类替代。

## 重复操作

### 1. `algorithm_id` 重复校验

API 层 `_prepare_apc_adjust()` 中会先校验一次：

```python
algorithm_id = validate_apc_adjust_request(
    payload,
    registered_algorithm_ids=_registered_apc_algorithm_ids(),
)
```

随后 dispatch 层又会校验一次：

```python
resolved = self._registry.resolve_algorithm_id(algorithm_id)
```

其中 `_registered_apc_algorithm_ids()` 还会重新执行：

```python
build_apc_registry_from_env().algorithm_ids
```

这意味着一次请求在服务启动已存在 `app.state.apc_dispatch` 的情况下，仍可能重新读取 registry 文件、import class、构造 controller，只为了拿 `algorithm_ids` 做校验。

优化方向：

- `algorithm_id` 的存在性与未知 ID 校验集中放在 registry/dispatch 层。
- API 层只负责把异常转换为 HTTP 错误。
- API 层需要展示可选 ID 时，直接使用 `app.state.apc_dispatch.registry.algorithm_ids`，不要重新构建 registry。

### 2. APC payload 重复构造 `APCInput`

当前一次 `/v1/apc/adjust` 请求中，APC 输入可能经历多次构造：

1. `is_common_apc_payload()` 中调用 `apc_input_from_payload(payload).is_valid()`。
2. `APCAdjustContract.to_graph_input()` 中调用 `apc_input_from_payload(...).to_dict()`。
3. REST endpoint 中再次调用 `APCInput.from_dict(canon)`。
4. peip 适配器中再调用 `_APCInput.from_dict(apc_input.to_dict())` 转成 wheel 输入。

实际链路相当于：

```text
dict
  -> peip APCInput
  -> dict
  -> peip APCInput
  -> dict
  -> wheel APCInput
```

优化方向：

- 只在一个边界做输入解析：`payload -> wheel APCInput`。
- 契约层只负责识别请求形状，不负责反复构造领域对象。
- 如果算法 wheel 提供 `create_algorithm(config)` 和 `APCAlgorithm.parse_input(payload)`，peip 可以直接委托算法类完成一次性解析与校验。

### 3. APC result 重复 `to_dict/from_dict`

当前结果链路可能是：

```text
wheel APCResult
  -> dict
  -> peip APCResult
  -> dict
  -> peip APCResult
  -> dict response
```

相关位置：

- `peip_inference_interface/src/reasoning/adapters/apc_engine_controller.py`
- `peip_inference_interface/src/reasoning/adapters/apc_dispatch.py`
- `peip_inference_interface/src/reasoning/api/rest.py`

重复转换不仅增加复杂度，也放大了模型结构不一致的风险。尤其当 wheel 侧 `APCResult.adjustments` 已经升级为 `dict[str, list[float]]` 时，peip 侧旧结构会成为信息丢失点。

优化方向：

- 算法执行后保持 wheel 原生 `APCResult`。
- `algorithm_id` 由算法类或 peip registry 统一补齐。
- 只在 HTTP 响应边界做一次 `result.to_dict()`。

### 4. `process` 与 `algorithm_id` 重复表达算法选择

当前配置中 `algorithm_id` 可能是：

```text
apc.r2r_controller.rb
```

registry cfg 中也配置：

```json
{
  "cfg": {
    "process": "RB"
  }
}
```

但请求体 `APCInput` 仍允许传：

```json
{
  "process": "RB"
}
```

这带来两个问题：

- `algorithm_id` 与 `process` 都在表达算法选择。
- 如果请求传 `algorithm_id=apc.r2r_controller.rb` 但 body 中 `process=LP`，当前语义不够清晰：到底以配置为准，还是以请求体为准。

优化方向：

- `process` 应该由 peip 配置中的算法身份决定。
- 请求体中的 `process` 可以作为兼容字段，但不应成为权威来源。
- 如果请求体 `process` 与 metadata/registry 中的 `process` 不一致，应返回 400 或至少记录 warning。

## 当前职责边界问题

当前 peip 同时承担了以下职责：

- HTTP 契约与错误语义
- algorithm_id 注册与分发
- APC 输入输出领域模型定义
- APC wheel controller 二次封装
- APC result 兼容转换
- process 选择

其中前两项是 peip 应该拥有的职责；后几项更适合由算法 wheel 或算法类拥有。

建议职责边界：

```text
算法 wheel:
  - APCInput
  - APCResult
  - controller / algorithm execution
  - create_algorithm(config)
  - metadata 描述自身能力

peip:
  - registry/config
  - algorithm_id 路由
  - HTTP 契约
  - 认证与权限
  - 错误码与响应包装
  - 算法能力统一管理
```

## 收敛方案

让算法 wheel 提供统一算法能力对象，例如 `algorithms/APC_Test` 中验证的模式：

```python
algorithm = create_algorithm(config)
result = algorithm.adjust(payload)
response = algorithm.to_response(result)
metadata = algorithm.metadata.to_dict()
```

其中：

- `create_algorithm(config)` 由 wheel 通过 entry point 暴露。
- `metadata` 提供 `algorithm_id`、`family`、`version`、`process`、`input_model`、`output_model`、`capabilities` 等信息。
- peip 负责读取自己的配置，按 `algorithm_id` 注册并调用算法。
- 算法 wheel 负责输入解析、算法执行和结果模型。

新的调用链可以收敛为：

```text
/v1/apc/adjust
  -> peip registry.require(algorithm_id)
  -> algorithm.adjust(payload)
  -> algorithm.to_response(result)
```

这样可以删除大多数中间 `to_dict/from_dict` 往返。

peip 可以通过自身配置加载：

```yaml
algorithms:
  apc.test.r2r_controller.rb:
    provider: apc_test
    entry_point_group: peip.algorithms
    entry_point_name: apc_test
    metadata:
      algorithm_id: apc.test.r2r_controller.rb
      family: apc
      version: "0.1.0"
      process: RB
    strict_process: true
```

这种方式能让算法包提供“能力”，peip 提供“管理”，避免 peip 复制每个算法 wheel 的领域模型和控制器。

## 结论

当前 `peip_inference_interface` 调度 APC 算法时的主要冗余包括：

- 重复定义 `APCInput`。
- 重复定义且已经漂移的 `APCResult`。
- peip controller 对 wheel controller 的二次封装过厚。
- `algorithm_id` 在 API 层和 dispatch 层重复校验。
- registry 在请求校验阶段重复构建。
- APC payload 多次 `from_dict/to_dict` 往返。
- APC result 多次 `to_dict/from_dict` 往返。
- `process` 与 `algorithm_id` 重复表达算法选择。

建议将 peip 的定位收敛为算法网关和能力管理层，将 APC 领域模型、算法执行和算法自身 metadata 交还给算法 wheel。这样可以降低维护成本，减少结构漂移风险，也更利于后续统一接入 OEE、APC 以及其他算法能力。
