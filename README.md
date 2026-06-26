# PEIP AI Hub

`peip_aihub` 是 PEIP 的算法能力网关，用于统一加载 wheel 形式发布的算法包，并基于算法包提供的 metadata 自动生成 FastAPI 接口和 OpenAPI 文档。

当前 APC 示例采用统一算法服务模式：`APCAlgorithm` 作为一个综合算法服务类对外暴露，具体工序由请求体中的 `APCInput.process` 决定。

## 启动方式

建议先安装运行依赖和算法 wheel：

```powershell
cd D:\lpls_wspace\peip_aihub
python -m pip install -r requirements.txt
```

如果修改了 `algorithms/APC_Test`，需要重新构建并安装 wheel：

```powershell
powershell -ExecutionPolicy Bypass -File "D:\lpls_wspace\peip_aihub\algorithms\APC_Test\scripts\build_and_import_wheel.ps1"
```

启动 API 服务：

```powershell
cd D:\lpls_wspace\peip_aihub
python -m uvicorn app.application:app --host 0.0.0.0 --port 8000 --reload
```

前端 API 文档地址：

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- ReDoc: `http://127.0.0.1:8000/redoc`

## 配置方式

项目运行配置位于 `configs/.env`，示例配置位于 `configs/.env.example`：

算法注册配置位于 `configs/algorithms.yaml`。peip 只需要声明算法加载入口、API 路径和默认调用方法；算法描述、输入输出模型、capabilities 等信息由 wheel 中的 `get_algorithm_metadata()` 自动提供：

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

同时保留通用管理接口：

- `GET /api/v1/algorithms`
- `GET /api/v1/algorithms/instruction/{algorithm_id}`

## 算法接入规则

算法包推荐提供以下公共入口：

- `create_algorithm(config)`：创建算法服务实例。
- `get_algorithm_metadata(config)`：返回算法身份、说明、capabilities、输入输出模型等 metadata。
- wheel 自有的输入输出模型，例如 `apc_engine.APCInput`、`apc_engine.APCResult`。

peip 不重复定义算法领域模型，只通过 metadata 中的 `input_model` 和 `output_model` 自动加载模型，用于请求校验、响应规范化和 OpenAPI 文档生成。

## 项目结构

```text
peip_aihub/
  app/
    application.py              # FastAPI 应用入口
    api/
      router.py                 # API 总路由
      routes/
        algorithm_route.py      # 算法列表和 instruction 查询接口
        algorithm_dynamic_route.py # 基于算法 metadata 自动注册动态 API
      models/
        algorithm_model.py      # 通用响应模型
    algorithms/
      specs.py                  # algorithms.yaml 配置解析
      registry.py               # 算法注册表与 metadata 补齐
      loader.py                 # 动态导入和实例化算法
      handle.py                 # 统一调用适配
      io.py                     # 输入解析、输出规范化、模型描述
      importing.py              # dotted path 导入工具
      exceptions.py             # 算法相关异常
    core/
      settings.py               # .env 与运行配置读取
  algorithms/
    APC_Test/                   # 示例 APC wheel 项目
      src/apc_engine/
        algorithm.py            # APCAlgorithm 和 metadata
        domain.py               # APCInput/APCResult
        controller.py           # 伪 APC 控制逻辑
        factory.py              # wheel 公共 factory
      scripts/
        build_and_import_wheel.ps1
  configs/
    .env
    .env.example
    algorithms.yaml
  tests/
    test_algorithm_api.py
    test_algorithm_registry.py
```

## 验证

运行核心测试：

```powershell
cd D:\lpls_wspace\peip_aihub
python -m pytest tests algorithms/APC_Test/tests
```
