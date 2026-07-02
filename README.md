# PEIP AI Hub

`peip_aihub` 是 PEIP 的算法能力网关，用于统一加载 wheel 形式发布的算法包，并基于算法包提供的 metadata 自动生成 FastAPI 接口、OpenAPI 文档和 workflow 编排能力。

当前已接入三类算法包：

- `peip-algorithms-core`：统一算法封装基类、metadata 契约和序列化工具
- `apc-engine`（`APC_Test`）：伪 APC 控制器，开放 HTTP API
- `oee-engine`（`OEE_Test`）：压力/温度传感器异常检测，仅作为内部 capability 使用

APC 示例采用统一算法服务模式：`APCAlgorithm` 作为一个综合算法服务类对外暴露，具体工序由请求体中的 `APCInput.process` 决定。

## 启动方式

### 1. 安装运行依赖

```powershell
cd D:\lpls_wspace\peip_aihub
pip install -r requirements.txt
```

`requirements.txt` 默认从 `wheels/` 安装 `apc-engine`。若本地 wheel 尚未构建，或需要安装全部算法包，请先执行下一步。

### 2. 构建并安装算法 wheel

推荐使用批量脚本，按顺序构建核心包和业务算法包，并安装到当前 Python 环境：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\build_and_install_wheels.ps1"
```

指定 conda 环境或 Python 解释器：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\build_and_install_wheels.ps1" -Python "C:\tools\miniconda3\envs\peip_aihub\python.exe"
```

构建产物会复制到 `wheels/`：

```text
wheels/
  peip_algorithms_core-0.1.0-py3-none-any.whl
  apc_engine-0.1.0-py3-none-any.whl
  oee_engine-0.1.0-py3-none-any.whl
```

各算法包的详细说明见：

- [algorithms/algorithms/README.md](algorithms/algorithms/README.md)
- [algorithms/APC_Test/README.md](algorithms/APC_Test/README.md)
- [algorithms/OEE_Test/README.md](algorithms/OEE_Test/README.md)

### 3. 配置环境变量

复制并编辑 `configs/.env`（示例见 `configs/.env.example`）：

```powershell
copy configs\.env.example configs\.env
```

### 4. 启动 API 服务

```powershell
cd D:\lpls_wspace\peip_aihub
python -m uvicorn app.application:app --host 0.0.0.0 --port 8000 --reload
```

前端 API 文档地址：

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 配置方式

项目运行配置位于 `configs/.env`，算法注册配置位于 `configs/algorithms.yaml`。

peip 只需要声明算法加载入口、API 路径和默认调用方法；算法描述、输入输出模型、capabilities 等信息由 wheel 中的 `get_algorithm_metadata()` 自动提供。

### APC：开放 HTTP API

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

上述配置会生成动态算法接口：

`POST /api/v1/algorithms/apc/adjust`

### OEE：仅内部 capability

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
    constructor:
      kwargs:
        params:
          score_threshold: 0.01
          max_events: 1
```

OEE 算法不配置 `api_path` 和 `call`，仅供 workflow 或内部服务通过 capability 调用。

## API 概览

### 算法管理

- `GET /api/v1/algorithms`：列出已注册算法
- `GET /api/v1/algorithms/instruction/{algorithm_id}`：查询算法 metadata

### 动态算法接口

根据 `algorithms.yaml` 中配置了 `api_path` 的算法自动生成，例如：

- `POST /api/v1/algorithms/apc/adjust`

### Workflow

- `POST /api/v1/workflows/apc/adjust`：执行 APC 调整 workflow（调用 APC capability 后由本地 Ollama 解释结果）

Workflow 依赖 `configs/.env` 中的 Ollama 配置（`OLLAMA_BASE_URL`、`OLLAMA_MODEL` 等）。

## 算法接入规则

算法包推荐基于 `peip-algorithms-core` 实现，并提供以下公共入口：

- `create_algorithm(config)`：创建算法服务实例
- `get_algorithm_metadata(config)`：返回算法身份、说明、capabilities、输入输出模型等 metadata
- wheel 自有的输入输出模型，例如 `apc_engine.APCInput`、`oee_engine.pressure.PressureInput`

peip 不重复定义算法领域模型，只通过 metadata 中的 `input_model` 和 `output_model` 自动加载模型，用于请求校验、响应规范化和 OpenAPI 文档生成。

### Capability 调用

workflow 或内部服务通过 `capabilities` 编排算法能力，而不是直接调用 HTTP API：

```python
from app.algorithms.service import call_algorithm_capability

result = call_algorithm_capability("apc.r2r_controller", "adjust", payload)

features = call_algorithm_capability("oee.pressure_detector", "process_data", payload)
events = call_algorithm_capability("oee.pressure_detector", "detect", features)
```

## 项目结构

```text
peip_aihub/
  app/
    application.py              # FastAPI 应用入口
    api/
      router.py                 # API 总路由
      routes/
        algorithm_route.py      # 算法列表和 instruction 查询
        algorithm_dynamic_route.py # 基于 metadata 自动注册动态 API
        workflow_route.py       # workflow API
      models/
        algorithm_model.py      # 通用响应模型
        workflow_model.py       # workflow 请求模型
    algorithms/
      specs.py                  # algorithms.yaml 配置解析
      registry.py               # 算法注册表与 metadata 补齐
      loader.py                 # 动态导入和实例化算法
      handle.py                 # 统一调用适配
      service.py                # call_algorithm_capability 等业务入口
      io.py                     # 输入解析、输出规范化、模型描述
      importing.py              # dotted path 导入工具
      exceptions.py             # 算法相关异常
    workflows/
      runner.py                 # workflow 执行器
      state.py                  # workflow 状态定义
      graphs/apc_adjust.py      # APC adjust LangGraph 编排
      nodes/                    # workflow 节点（apc、explain 等）
      llm/ollama.py             # 本地 Ollama 调用
    core/
      settings.py               # .env 与运行配置读取
    common/
      response.py               # 统一响应封装
  algorithms/
    algorithms/                 # peip-algorithms-core 核心包
    APC_Test/                   # 示例 APC wheel
    OEE_Test/                   # 示例 OEE wheel
    build_and_install_wheels.ps1
  configs/
    .env
    .env.example
    algorithms.yaml
  wheels/                       # 构建产物目录
  tests/
    test_algorithm_api.py
    test_algorithm_registry.py
    test_apc_workflow.py
    test_local_llm.py
```

## 验证

运行平台测试：

```powershell
cd D:\lpls_wspace\peip_aihub
python -m pytest tests
```

运行全部测试（含算法包内测试）：

```powershell
python -m pytest tests algorithms/APC_Test/tests algorithms/OEE_Test/tests
```

开发依赖：

```powershell
pip install -r requirements-dev.txt
```
