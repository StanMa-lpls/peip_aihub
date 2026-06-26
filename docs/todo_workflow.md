# 算法 Workflow 编排 TODO

本文档记录在 `peip_aihub` 中结合已安装算法包、LangGraph 与 LLM 进行算法 workflow 编排的推荐方式和后续待办。

## 当前定位

`peip_aihub` 已经具备算法包加载、metadata 补齐、输入输出模型解析和动态 API 生成能力。

当前 APC 算法采用统一服务模式：

- 算法包 `apc-engine` 提供 `APCAlgorithm`、`APCInput`、`APCResult`。
- `APCAlgorithm` 是综合 APC 算法服务类。
- 具体工序由请求体中的 `APCInput.process` 决定。
- peip 通过 `configs/algorithms.yaml` 注册算法；只有显式配置 `api_path` 和 `call` 时才开放 HTTP API。

### 情况一：需要开放 HTTP API

当算法能力需要暴露给前端或外部系统时，在 `metadata.api_path` 中配置 API 路径，并在 `call` 中配置该 API 实际调用的算法方法。

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

上述配置会开放：

```text
POST /api/v1/algorithms/apc/adjust
```

其中 `call.method=adjust` 表示该 API 会调用 `APCAlgorithm.adjust()`。

### 情况二：只注册算法能力，不开放 HTTP API

如果算法只供内部 LangGraph workflow 或其他后端流程调用，可以不配置 `metadata.api_path` 和 `call`。

```yaml
algorithms:
  apc.r2r_controller:
    package: apc-engine
    class_path: apc_engine.create_algorithm
    metadata:
      algorithm_id: apc.r2r_controller
```

这种情况下不会生成动态 HTTP API，但算法包 metadata 中的 `capabilities` 仍然会被加载，例如：

```text
adjust
process_data
control
```

workflow 可以根据 `capabilities` 选择调用对应方法。

## 推荐使用方式

不要让 LLM 直接 import 或调用 `apc_engine` 中的类。

推荐把算法能力封装成 LangGraph node 或 tool，由 workflow 根据 metadata 中的 `capabilities` 明确选择要调用的算法方法。

API 开放和 workflow 编排需要分离：

- API 层负责把某个算法能力暴露给前端或外部系统，例如 `POST /api/v1/algorithms/apc/adjust`。
- Workflow 层负责内部编排，不依赖 API 路由是否存在，也不通过 HTTP 回调本服务。
- Workflow 调用算法时应通过 `AlgorithmRegistry.require()` 获取算法实例，再按 capability 调用具体方法。

## 内部调用指定 Capability

当不考虑 API 注册模式时，workflow 可以直接通过 `AlgorithmRegistry` 获取算法 handle，再根据 metadata 中的 `capabilities` 选择调用算法类上的某个方法。

基础模式：

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

    result = method(payload)
    return to_jsonable(result)
```

APC 示例：

```python
payload = {
    "machine_id": "M01",
    "tube_id": "T01",
    "target_p": 100.0,
    "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
    "adj_data": {},
    "adjust_max_limit": 2,
    "process": "RB",
}

features = call_algorithm_capability(
    "apc.r2r_controller",
    "process_data",
    payload,
)

result = call_algorithm_capability(
    "apc.r2r_controller",
    "adjust",
    payload,
)
```

如果需要调用 `control()`，应传入 `process_data()` 的输出，而不是原始 `APCInput` payload：

```python
control_result = call_algorithm_capability(
    "apc.r2r_controller",
    "control",
    features,
)
```

注意：这种直接调用 capability 的方式会绕过 `AlgorithmHandle.invoke()` 中基于配置的默认 `call` 策略，但仍然复用 `AlgorithmRegistry` 的加载、缓存和 metadata 管理能力。若 workflow 对输入输出规范要求较高，建议为具体 capability 封装专用 tool，在 tool 内显式完成输入模型解析和输出规范化。

## LangGraph Node 示例

```python
def apc_adjust_node(state: dict) -> dict:
    payload = {
        "machine_id": state["machine_id"],
        "tube_id": state["tube_id"],
        "target_p": state["target_p"],
        "p_data": state["p_data"],
        "adj_data": state.get("adj_data", {}),
        "adjust_max_limit": state.get("adjust_max_limit", 2),
        "process": state.get("process", "RB"),
    }

    result = call_algorithm_capability(
        "apc.r2r_controller",
        "adjust",
        payload,
    )

    return {
        **state,
        "apc_result": result,
    }
```

## LLM 职责边界

LLM 适合负责：

- 理解用户意图。
- 判断是否需要调用 APC 算法。
- 从上下文中抽取或补齐 `APCInput` 所需字段。
- 解释 `APCResult`。
- 编排多步骤 workflow。

LLM 不应该负责：

- 直接拼接算法类路径。
- 直接 import wheel 内部类。
- 手写算法输入输出模型转换。
- 绕过 `AlgorithmRegistry` 调用算法实例。

## 分层职责

算法包负责：

- 提供真实算法能力。
- 定义输入输出领域模型。
- 暴露 `create_algorithm(config)`。
- 暴露 `get_algorithm_metadata(config)`。

`peip_aihub` 负责：

- 根据 `algorithms.yaml` 注册算法。
- 从 wheel metadata 自动补齐能力描述。
- 动态加载算法实例。
- 解析输入模型并规范化输出模型。
- 自动生成 FastAPI/OpenAPI 文档。

LangGraph 负责：

- 将 LLM、算法节点、规则节点、人工确认节点组合成 workflow。
- 维护 workflow state。
- 控制节点跳转和错误恢复。

## TODO

- [ ] 新增 `app/workflows` 目录，用于放置 LangGraph workflow。
- [ ] 新增 `app/workflows/tools.py`，将 `AlgorithmRegistry.invoke()` 封装为可复用工具。
- [ ] 支持 workflow 根据算法 metadata 中的 `capabilities` 选择并调用指定能力方法。
- [ ] 新增 APC workflow 示例：`LLM -> 构造 APCInput -> 调用 apc.r2r_controller -> 解释 APCResult`。
- [ ] 为 workflow state 定义 Pydantic 模型，避免 dict 字段漂移。
- [ ] 增加 workflow API，例如 `POST /api/v1/workflows/apc/adjust`。
- [ ] 将 `GET /api/v1/algorithms/instruction/{algorithm_id}` 返回的 metadata 暴露给 LLM tool 选择逻辑。
- [ ] 增加算法调用失败时的错误包装和 LLM 可读错误信息。
- [ ] 补充 workflow 层测试，覆盖正常调用、缺字段、算法异常和未知工序等场景。
