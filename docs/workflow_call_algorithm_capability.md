# Workflow 调用算法 Capability 设计

本文档说明 `peip_aihub` 中 workflow / LangGraph 如何调用已注册算法能力。

## 设计原则

**workflow 统一走 `call_algorithm_capability`，不使用算法模块开放的 Web API。**

- workflow / LangGraph 节点**禁止**通过 HTTP 调用 `POST /api/v1/algorithms/...`（包括回调本服务）。
- workflow **禁止**直接 `import` wheel 内部类。
- 算法 Web API（`api_path` + `call`）仅面向**前端或外部系统**；与 workflow 调用路径完全分离。
- workflow 唯一合法入口：`call_algorithm_capability(algorithm_id, capability, payload)`。

即使某算法在 `algorithms.yaml` 中配置了 `api_path`，workflow 仍应走 capability 直调，而不是复用该 HTTP 路由。

## 设计目标

- 以 metadata 中的 `capabilities` 作为编排粒度，支持单步调用与多步编排。
- 复用 `AlgorithmRegistry` 的注册、metadata 合并与实例缓存，避免重复加载。
- 同一算法可同时开放 Web API（给外部）和供 workflow 按 capability 编排（给内部）。

## 两条调用路径（调用方不同，workflow 只走右侧）

| 场景 | 配置 | 入口 | 调用方式 |
|------|------|------|----------|
| 前端 / 外部系统 | `api_path` + `call` | `POST /api/v1/algorithms/...` | `registry.invoke()` → `handle.invoke()` |
| **workflow / LangGraph** | 仅注册即可 | **`call_algorithm_capability()`** | `handle.invoke_capability()` |
### HTTP API 路径

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

调用链：

```text
HTTP Request
  → Dynamic API Route
  → registry.invoke(algorithm_id, payload)
  → handle.invoke()
  → parse_input → CallAdapter(call) → normalize_output → to_jsonable
```

### Workflow capability 路径（workflow 唯一入口）

```yaml
algorithms:
  apc.r2r_controller:
    package: apc-engine
    class_path: apc_engine.create_algorithm
    metadata:
      algorithm_id: apc.r2r_controller
```

workflow 侧**不需要**也**不应该**依赖 `api_path` / `call` 配置；是否开放 Web API 不影响 workflow 调用方式。
调用链：

```text
call_algorithm_capability(algorithm_id, capability, payload)
  → get_algorithm_registry()          # 进程内单例
  → registry.invoke_capability(...)
  → handle.invoke_capability(capability, payload)
  → 校验 capabilities → getattr 调方法 → to_jsonable
```

capability 直调会绕过 `call` 配置，但仍复用 registry 的加载、metadata 合并与实例缓存。

## 代码分层

```text
app/algorithms/handle.py
  AlgorithmHandle.invoke_capability()     # 核心：校验 + 反射调用

app/algorithms/registry.py
  AlgorithmRegistry.invoke_capability()   # algorithm_id 级封装

app/algorithms/service.py
  invoke_algorithm_capability(registry, ...)   # 显式注入 registry（测试 / API）
  call_algorithm_capability(...)             # 默认 registry（workflow 常用）

app/workflows/
  re-export call_algorithm_capability
```

## 推荐用法

workflow 中统一从 `app.algorithms.service` 导入 `call_algorithm_capability`：

### workflow 常规调用
```python
from app.algorithms.service import call_algorithm_capability

payload = {
    "machine_id": "M01",
    "tube_id": "T01",
    "target_p": 100.0,
    "p_data": {"p1_mean": [96.0, 97.0, 98.0]},
    "process": "RB",
}

result = call_algorithm_capability("apc.r2r_controller", "adjust", payload)
```

### 细粒度编排（APC 示例）

APC metadata 声明三个 capability：`adjust`、`process_data`、`control`。

```python
features = call_algorithm_capability("apc.r2r_controller", "process_data", payload)
result = call_algorithm_capability("apc.r2r_controller", "control", features)
```

注意：`control` 的输入是 `process_data` 的输出，不是原始 `APCInput` payload。

### LangGraph Node 示例

```python
def apc_adjust_node(state: dict) -> dict:
    result = call_algorithm_capability(
        "apc.r2r_controller",
        "adjust",
        {
            "machine_id": state["machine_id"],
            "tube_id": state["tube_id"],
            "target_p": state["target_p"],
            "p_data": state["p_data"],
            "process": state.get("process", "RB"),
        },
    )
    return {**state, "apc_result": result}
```

### 测试注入 registry

```python
from app.algorithms.service import call_algorithm_capability

result = call_algorithm_capability(
    "apc.fake",
    "adjust",
    payload,
    registry=fake_registry,
)
```

## AlgorithmRegistry 定位

`AlgorithmRegistry` 是进程内算法注册与调度中心：

- `_specs`：`algorithm_id → AlgorithmSpec`（来自 `algorithms.yaml`，合并 wheel metadata）
- `_handles`：`algorithm_id → AlgorithmHandle`（首次 `require()` 时懒加载，默认 `cache=True`）

生产环境通过 `get_algorithm_registry()`（`@lru_cache`）每个进程维护一份实例。

## LLM 职责边界

**LLM 负责：**

- 理解用户意图
- 判断是否需要调用某算法
- 抽取 / 补齐输入字段
- 解释算法输出
- 选择 capability 与编排步骤

**LLM 不负责：**

- 直接 import wheel 内部类
- 拼接 `class_path`
- 绕过 `AlgorithmRegistry` 调算法
- 通过 HTTP 请求算法 Web API

能力发现（非算法执行）可读取 instruction metadata：
```text
GET /api/v1/algorithms/instruction/{algorithm_id}
```

返回 `description`、`when_to_use`、`capabilities` 等 metadata，供 LLM 选择 capability；**执行时仍走 `call_algorithm_capability`，不走 Web API。**
## 与 invoke() 的差异

| 项目 | `invoke()` | `invoke_capability()` |
|------|------------|------------------------|
| 驱动 | `call` 配置（method/pipeline/auto） | metadata 中的 `capabilities` |
| 输入处理 | `parse_input`（按 `input_model`） | 直接传给算法方法（由 wheel 自行解析） |
| 输出处理 | `normalize_output`（按 `output_model`） | `to_jsonable` |
| 典型调用方 | 前端 / 外部 HTTP 客户端 | workflow / LangGraph（仅 `call_algorithm_capability`） |
若 workflow 对 IO 规范要求较高，可为具体 capability 封装专用 tool，在 tool 内显式调用 `parse_input` / `normalize_output`。
