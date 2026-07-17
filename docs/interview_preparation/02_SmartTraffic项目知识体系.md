# SmartTraffic 项目知识体系

> 基于本轮修改前 `main@81a9730` 的 95 个面试知识点。每个结论都区分代码事实、测试事实和生产边界；编号与《03_SmartTraffic完整面试题库.md》末尾映射表一一对应。

## 目录

1. 项目定位与证据方法：K01–K04
2. 总体架构：K05–K08
3. 配置与基础设施契约：K09–K12
4. 视频输入与视觉产物：K13–K16
5. YOLO 检测：K17–K20
6. 目标跟踪：K21–K24
7. 轨迹与几何：K25–K30
8. Zone 与 Rule：K31–K34
9. 六类事件与证据：K35–K42
10. 告警与可视化证据：K43–K45
11. 数据、迁移与 artifact：K46–K51
12. Analysis Center 与前端：K52–K54
13. Review、漏报与 Bad Case：K55–K58
14. Evaluation：K59–K63
15. Reporting：K64–K66
16. Realtime Preview：K67
17. 交付、验证与安全：K68–K70
18. 性能与生产化：K71–K72
19. Python 与 FastAPI 基础：K73–K77
20. OpenCV 与视频基础：K78–K81
21. YOLO 原理：K82–K84
22. 多目标跟踪基础：K85–K87
23. React 与前端工程：K88–K89
24. 测试体系：K90–K91
25. 生产系统设计：K92–K95

## 第一章：项目定位与证据方法

### K01 本地验证平台的准确定位

- 概念：SmartTraffic 是本地视频分析与质量闭环平台，不是线上执法系统。
- 为什么重要：定位决定面试中哪些能力能讲成“已实现”，哪些只能讲成规划。
- 原理：以可运行入口、输出、调用方和测试构成最小证据闭环。
- SmartTraffic 实现：视频到事件、告警、复核、评测和报告的本地链路完整存在。
- 证据：`README.md`、`backend/app/api/`、`frontend/src/pages/`。
- 真实调用链：Video Center → process API → run artifacts → Analysis/Review/Evaluation/Report。
- 优点：端到端可演示，边界相对诚实。
- 缺点：容易因页面完整而被误认为生产成熟。
- 替代方案：只做算法 notebook，或直接建设生产流媒体平台。
- 当前限制：无生产用户、线上 SLA、真实 RTSP 和正式 benchmark 证据。
- 常见误区：把“功能页面齐全”当作“生产系统已上线”。
- 面试表达：“这是可测试的本地验证平台，工程闭环完整，但生产基础设施未完成。”
- 追问方向：为什么不是 demo；为什么又不是生产；如何分阶段上线。

### K02 证据优先级与事实冻结

- 概念：用固定 Git HEAD 建立事实快照，并设定证据优先级。
- 为什么重要：文档、标签、本机结果可能滞后或超前于代码。
- 原理：代码/配置/迁移/测试优先于 README，再优先于历史文档和忽略产物。
- SmartTraffic 实现：本材料以本轮修改前 `81a9730` 为事实修订基线，本机结果只标记为运行快照。
- 证据：`git ls-files`、`git status --ignored`、`git log`、当前测试输出。
- 真实调用链：结论 → 定位到入口 → 核心实现 → 输出 → 调用方 → 测试。
- 优点：可复核，避免过度包装。
- 缺点：审计成本高，不能仅复述 README。
- 替代方案：只按最新 tag 或演示截图介绍。
- 当前限制：Git 不能证明个人贡献和外部部署事实。
- 常见误区：把本机 ignored 的权重、视频和指标当成仓库基准。
- 面试表达：“我按当前 HEAD 做证据冻结，历史材料只作线索。”
- 追问方向：冲突事实如何裁决；如何证明某项功能真实被调用。

### K03 Analysis Run 作为聚合根

- 概念：一次输入、配置、结果和衍生业务动作由 run ID 关联。
- 为什么重要：可复现与可追溯需要稳定的分析边界。
- 原理：聚合根控制内部对象的身份、版本和生命周期。
- SmartTraffic 实现：`TrafficAnalysisRun` 关联 video、config snapshot、模型运行和各类结果。
- 证据：`backend/app/models/analysis.py`、`backend/app/services/traffic_analysis_service.py`。
- 真实调用链：process request → 新 run ID → artifacts/DB → analysis-run API → 报告。
- 优点：不同 rerun 并存，便于比较和审计。
- 缺点：当前未强制 artifact checksum 和完整引用约束。
- 替代方案：按 video 覆盖保存最新结果，或事件溯源模型。
- 当前限制：DB 与文件中的 run 不是原子提交。
- 常见误区：把 video ID、processing task ID 和 run ID 混为一谈。
- 面试表达：“run 是结果事实边界，rerun 生成新 run，不覆盖旧结果。”
- 追问方向：run 幂等；状态机；配置和模型版本如何绑定。

### K04 四层能力成熟度

- 概念：区分当前实现、测试覆盖、契约预留和未来能力。
- 为什么重要：接口存在并不代表真实业务链路完成。
- 原理：成熟度需要执行语义和运行证据，而非文件名判断。
- SmartTraffic 实现：事件/复核是当前实现；顶层 detections 与 RTSP 是契约或占位。
- 证据：`backend/app/api/detections.py`、`backend/app/realtime/worker.py`。
- 真实调用链：请求入口 → 返回 `not_implemented` 或占位 metadata → UI 展示。
- 优点：沟通精确，便于制定路线图。
- 缺点：同一模块可能同时含不同成熟度路径。
- 替代方案：用 alpha/beta/GA 标签，但仍需证据定义。
- 当前限制：仓库没有自动生成能力成熟度清单。
- 常见误区：测试 mock 通过就等于真实依赖通过。
- 面试表达：“我会先说明能力层级，再讲实现细节和验证范围。”
- 追问方向：如何设计 acceptance gate；什么条件能从预留升级为实现。

## 第二章：总体架构

### K05 分层视频分析流水线

- 概念：检测、跟踪、轨迹、事件和告警是逐层派生关系。
- 为什么重要：上游误差会传递，下游必须保留可解释中间结果。
- 原理：每层消费稳定契约并输出下一层所需特征。
- SmartTraffic 实现：YOLO detection → tracker → `TrajectoryEngine` → `EventEngine` → alert。
- 证据：`backend/app/api/videos.py`、`backend/app/cv/`、`backend/app/events/`。
- 真实调用链：视频帧 → bbox → track ID → 像素轨迹 → 规则事件 → 告警。
- 优点：模块职责清晰，可单测与替换。
- 缺点：同步串联导致延迟累积；错误级联。
- 替代方案：端到端事件模型，或消息驱动多 stage pipeline。
- 当前限制：没有异步 stage、模型 batch 和分布式状态。
- 常见误区：认为 Event Engine 直接读取原视频识别语义。
- 面试表达：“事件层消费轨迹和规则，不直接做视觉推理。”
- 追问方向：错误传播；stage contract；如何替换 tracker。

### K06 同步 HTTP 编排

- 概念：重处理在单次 API 请求线程内完成。
- 为什么重要：直接影响超时、并发、失败恢复和资源调度。
- 原理：路由创建 task，顺序调用 service，最后统一 commit/返回。
- SmartTraffic 实现：`POST /api/videos/{id}/process` 支持三种模式并同步运行。
- 证据：`backend/app/api/videos.py`。
- 真实调用链：pending → running → CV/trajectory/event/artifact → completed/failed。
- 优点：实现与调试简单，调用链直观。
- 缺点：长视频阻塞 worker，无取消、重试和背压。
- 替代方案：Celery/RQ/自建任务表 + worker，或流式消息处理。
- 当前限制：请求断开与残留文件缺自动补偿。
- 常见误区：看到 `ProcessingTask` 就认为已有异步队列。
- 面试表达：“task 是状态记录，不是后台任务执行器。”
- 追问方向：异步改造；幂等；超时；GPU 调度。

### K07 17 组路由与 87 个端点

- 概念：API 按资源和业务中心拆分路由模块。
- 为什么重要：说明系统能力面，也暴露契约一致性和维护成本。
- 原理：FastAPI `APIRouter` 组合进应用工厂。
- SmartTraffic 实现：health、videos、analysis、review、evaluation、reports 等 17 组共 87 个端点。
- 证据：`backend/app/main.py`、`backend/app/api/*.py`。
- 真实调用链：`create_app()` → `include_router()` → 前端 `frontend/src/api/client.ts` 调用。
- 优点：资源边界清晰，OpenAPI 自动生成。
- 缺点：部分顶层与 run 子资源重叠，存在契约预留端点。
- 替代方案：GraphQL、RPC 或更严格的 BFF。
- 当前限制：没有 API version prefix、runtime client schema 和公开兼容策略。
- 常见误区：把 87 个端点等同于 87 个独立业务功能。
- 面试表达：“端点数量说明接口面，不代表所有入口成熟度相同。”
- 追问方向：资源建模；分页；错误契约；版本升级。

### K08 前端轻量路由与十页面结构

- 概念：React 单页应用用 native History API 管理十个页面。
- 为什么重要：体现依赖取舍和路由复杂度边界。
- 原理：`pushState` 修改 URL，`popstate` 驱动页面状态。
- SmartTraffic 实现：`App.tsx` 映射 `/`、cameras、videos、analysis 等路径。
- 证据：`frontend/src/App.tsx`、`frontend/src/pages/`。
- 真实调用链：Sidebar 点击 → history 更新 → App 选择 page → page 请求后端。
- 优点：零路由依赖，MVP 简单。
- 缺点：参数、嵌套路由、404、导航守卫和测试能力较弱。
- 替代方案：React Router、TanStack Router 或服务端路由。
- 当前限制：`routeNames` 等局部清单可能与十页实际映射不同步。
- 常见误区：声称项目使用 React Router。
- 面试表达：“当前用原生 history，生产扩展时会引入类型安全路由。”
- 追问方向：深链接；刷新恢复；搜索参数；权限路由。

## 第三章：配置与基础设施契约

### K09 环境配置与默认值

- 概念：环境变量、dataclass settings 与请求参数共同决定运行配置。
- 为什么重要：模型路径、阈值、dry-run、目录和安全模式都受配置影响。
- 原理：启动时加载环境，服务层允许请求级 override。
- SmartTraffic 实现：`backend/app/core/config.py` 默认模型 `local_models/best.pt`；`.env.example` 示例为 `/app/local_models/yolov8n.pt`。
- 证据：`backend/app/core/config.py`、`.env.example`。
- 真实调用链：env → `get_settings()` → API/service → config snapshot。
- 优点：本地和容器可配置。
- 缺点：默认与示例路径不同可能引起认知偏差。
- 替代方案：Pydantic Settings、集中配置中心、schema-validated YAML。
- 当前限制：没有 secret manager 和环境配置发布审计。
- 常见误区：把 `.env.example` 当作实际运行值。
- 面试表达：“真实配置要看运行环境和 run snapshot，不能只看示例文件。”
- 追问方向：优先级；密钥；配置热更新；验证。

### K10 Configuration Snapshot

- 概念：每个 run 保存处理参数快照。
- 为什么重要：同一视频在不同阈值、stride 或规则下结果不同。
- 原理：将有效配置序列化并绑定 run，而不是只依赖当前全局配置。
- SmartTraffic 实现：processing request 与 settings 合并后进入 metadata/DB run config。
- 证据：`backend/app/services/processing_service.py`、`backend/app/analysis/artifact_writer.py`。
- 真实调用链：request config → service → run metadata/config snapshot → Analysis/Report。
- 优点：便于解释和比较 rerun。
- 缺点：未绑定输入哈希、代码 commit、模型 checksum 的完整 provenance。
- 替代方案：MLflow/DVC/自建不可变 experiment registry。
- 当前限制：JSON 配置字段的 schema evolution 治理有限。
- 常见误区：有 snapshot 就等于完全可复现。
- 面试表达：“它提供参数级可追溯，但还不是完整实验血缘。”
- 追问方向：模型/数据/代码版本；可重放；迁移。

### K11 Dry-run 与可测试降级

- 概念：无权重或无 tracker 依赖时，用确定性路径验证系统编排。
- 为什么重要：让 CI 和普通开发机可验证非模型逻辑。
- 原理：依赖边界可替换，输出契约保持稳定。
- SmartTraffic 实现：YOLO dry-run 返回空；tracker dry-run 使用 fallback。
- 证据：`cv/yolo_detector.py`、`cv/deepsort_tracker.py`、对应测试。
- 真实调用链：config dry_run → adapter 分支 → 契约输出 → artifacts/API。
- 优点：降低环境门槛，测试可重复。
- 缺点：不能证明真实模型效果，空检测也不会触发完整事件。
- 替代方案：小型固定模型 fixture、录制推理结果、容器化 GPU CI。
- 当前限制：默认 dry-run 容易掩盖缺依赖。
- 常见误区：把 dry-run 测试通过说成算法验证通过。
- 面试表达：“dry-run 验证编排和契约，真实效果需要独立 benchmark。”
- 追问方向：如何测试真实模型；fixture 漂移；降级告警。

### K12 Request ID、错误契约与脱敏

- 概念：为每个请求关联 ID，并统一异常响应。
- 为什么重要：跨前后端定位错误时需要稳定关联键和安全错误信息。
- 原理：middleware 设置 request state/header，exception handler 转换异常。
- SmartTraffic 实现：响应含 `error_code`、message/detail、request_id；敏感关键词触发脱敏。
- 证据：`backend/app/main.py`、`backend/app/core/errors.py`。
- 真实调用链：HTTP request → middleware → route/error → handler → `X-Request-ID`。
- 优点：本地排错和接口一致性更好。
- 缺点：关键词脱敏不是系统化 secret classification。
- 替代方案：OpenTelemetry trace/span、结构化日志和集中错误平台。
- 当前限制：前端 API client 未统一主动传 actor/request-id；无分布式 tracing。
- 常见误区：有 request ID 就说已具备完整可观测性。
- 面试表达：“这是 tracing 的基础，不是 tracing 系统本身。”
- 追问方向：日志字段；PII；错误分级；SLO。

## 第四章：视频输入与视觉产物

### K13 上传校验与信任边界

- 概念：用户上传文件是非可信输入，需限制路径、大小、格式与内容。
- 为什么重要：防止路径穿越、内存耗尽、恶意文件和数据串扰。
- 原理：basename、allowlist、大小/时长/codec 检查和失败清理。
- SmartTraffic 实现：扩展名、200 MB、600 秒、codec 配置；写后探测，失败删除。
- 证据：`backend/app/api/videos.py`、`.env.example`。
- 真实调用链：multipart → 读入 bytes → 本地写入 → OpenCV probe → DB create。
- 优点：具备基础边界检查。
- 缺点：整文件入内存、同名覆盖、无 MIME/病毒扫描和认证。
- 替代方案：分块直传对象存储 + checksum + 异步扫描。
- 当前限制：本地目录无租户隔离与配额。
- 常见误区：扩展名 allowlist 等于内容安全。
- 面试表达：“当前是本地 MVP 校验，生产上传链路需要重构。”
- 追问方向：大文件；断点续传；去重；恶意 codec。

### K14 OpenCV 元数据探测

- 概念：在处理前读取 FPS、宽高、帧数、fourcc 与时长。
- 为什么重要：决定采样、时间戳、资源估算和格式拒绝。
- 原理：`VideoCapture` 打开容器并读取 property；时长约为 frame_count/FPS。
- SmartTraffic 实现：`FrameReader`/probe 将元数据写入 Video。
- 证据：`backend/app/cv/frame_reader.py`、视频 API 测试。
- 真实调用链：本地 path → OpenCV capture → metadata → `Video` / response。
- 优点：依赖少，与后续帧读取一致。
- 缺点：某些 VFR/损坏容器的 metadata 不可靠。
- 替代方案：FFprobe/PyAV，再用 OpenCV 解码。
- 当前限制：未做逐帧完整性预扫描。
- 常见误区：容器声明帧数等于实际可解码帧数。
- 面试表达：“metadata 是处理提示，不是绝对真值。”
- 追问方向：VFR；codec；损坏帧；时间戳。

### K15 Frame stride 与 max frames

- 概念：通过跳帧和帧数上限控制处理成本。
- 为什么重要：CPU 本地推理需要在时延与事件完整性间取舍。
- 原理：generator 按 frame index 采样，并记录原帧索引/时间戳。
- SmartTraffic 实现：`frame_stride` 默认 1，示例可设 5；检测示例上限 120。
- 证据：`backend/app/cv/frame_reader.py`、`backend/app/schemas/processing.py`、`.env.example`。
- 真实调用链：VideoCapture → frame generator → detector/tracker → artifact frame_index。
- 优点：资源可控，演示快速。
- 缺点：越线、短时入侵和方向估计可能漏失或失真。
- 替代方案：自适应采样、关键帧、流式背压或 batch inference。
- 当前限制：没有按运动/场景动态调整 stride。
- 常见误区：stride=5 后仍把 frame delta 当连续一帧解释。
- 面试表达：“采样参数属于 run 配置，会改变事件时间分辨率。”
- 追问方向：阈值如何随 stride 标定；timestamp 优先级。

### K16 标注视频与关键帧

- 概念：将 detection、track、event/alert 证据绘制回源视频。
- 为什么重要：人工复核需要视觉上下文，而非只看 JSON。
- 原理：按帧读取源视频，叠加 bbox/label/事件，再用 codec 写出；指定事件帧截取图片。
- SmartTraffic 实现：`AnnotatedVideoWriter`、visual artifact builder、keyframe index。
- 证据：`backend/app/cv/video_writer.py`、`backend/app/analysis/visual_artifacts.py`。
- 真实调用链：run results + source video → overlay → MP4/JPEG → Analysis/Review/Report 引用。
- 优点：证据直观，artifact 可离线检查。
- 缺点：二次解码/编码昂贵，codec/源文件缺失会失败。
- 替代方案：前端实时 SVG overlay、按需生成、HLS sidecar metadata。
- 当前限制：无 checksum、签名、对象存储 URL 和多分辨率输出。
- 常见误区：关键帧存在就代表原始证据不可篡改。
- 面试表达：“可视化用于复核，不是取代结构化证据。”
- 追问方向：帧同步；坐标缩放；codec；存储成本。

## 第五章：YOLO 检测

### K17 Ultralytics YOLO 适配器

- 概念：用薄适配器隔离第三方模型 API 与项目 detection contract。
- 为什么重要：业务层不应依赖 Ultralytics result 的具体结构。
- 原理：懒加载模型，统一 `detect(frame)` 输出 bbox/class/confidence。
- SmartTraffic 实现：`YoloDetector` 调用 `YOLO.predict` 并格式化结果。
- 证据：`backend/app/cv/yolo_detector.py`、`backend/tests/test_yolo_detector_contract.py`。
- 真实调用链：numpy frame → Ultralytics → Boxes → project detection dict → tracker/artifact。
- 优点：依赖边界清晰，易 mock。
- 缺点：真实异常、模型线程安全和 device 生命周期治理较弱。
- 替代方案：ONNX Runtime/TensorRT 自建 adapter，或服务化推理。
- 当前限制：无仓库内训练/导出链路与权重。
- 常见误区：说项目自研了 YOLO 算法。
- 面试表达：“我复用了 Ultralytics 推理，在项目侧做契约与编排。”
- 追问方向：模型加载；并发；GPU；导出格式。

### K18 置信度、IoU、输入尺寸与类别过滤

- 概念：检测阈值决定候选框保留和目标类别范围。
- 为什么重要：precision/recall 与下游跟踪、事件误报直接相关。
- 原理：confidence 过滤低分框，IoU 参与 NMS，imgsz 影响精度和计算量。
- SmartTraffic 实现：示例默认 conf 0.25、IoU 0.45、imgsz 640，并过滤六类交通目标。
- 证据：`.env.example`、`backend/app/cv/yolo_detector.py`。
- 真实调用链：effective config → `predict` → parsed boxes → class allowlist → artifacts。
- 优点：可按 run 调参并记录快照。
- 缺点：全场景单阈值，缺 per-class/per-camera 校准。
- 替代方案：类别阈值、PR 曲线选点、温度校准或动态阈值。
- 当前限制：仓库无真实验证集指标支持默认值最优。
- 常见误区：conf=0.25 代表 25% 的真实概率。
- 面试表达：“阈值是工程 operating point，需要数据集校准。”
- 追问方向：NMS；PR；小目标；类别不平衡。

### K19 前处理与 NMS 的责任边界

- 概念：图像 resize/letterbox、归一化与 NMS 由模型库承担。
- 为什么重要：面试需准确区分调用第三方与自研实现。
- 原理：adapter 传入 source 和推理参数，Ultralytics 执行完整 pipeline。
- SmartTraffic 实现：项目代码没有独立 letterbox/NMS 函数。
- 证据：`backend/app/cv/yolo_detector.py`、`backend/requirements.txt`。
- 真实调用链：frame → `model.predict` → post-NMS `result.boxes` → 格式化。
- 优点：减少重复实现和数值错误。
- 缺点：对库版本行为有隐式依赖，可控性较低。
- 替代方案：导出 ONNX 后显式实现 preprocess/postprocess。
- 当前限制：无跨版本数值一致性测试。
- 常见误区：把参数传递描述为“自己实现 NMS”。
- 面试表达：“项目负责 adapter 与业务 contract，NMS 属于 Ultralytics。”
- 追问方向：letterbox 坐标还原；NMS vs Soft-NMS；版本锁定。

### K20 模型生命周期与可复现性

- 概念：模型需要路径、版本、checksum、运行参数和代码版本共同标识。
- 为什么重要：同名权重变化会让相同配置产生不同结果。
- 原理：不可变模型 artifact + manifest/provenance。
- SmartTraffic 实现：保存 model path/config 与 `ModelRun`，本机权重被忽略。
- 证据：`backend/app/models/model_run.py`、`.gitignore`、run metadata writer。
- 真实调用链：settings/request → model load → ModelRun/config snapshot → report/reference。
- 优点：已有模型运行记录入口。
- 缺点：缺 checksum、registry、签名和自动下载。
- 替代方案：MLflow Model Registry、DVC、OCI model image。
- 当前限制：当前 HEAD 无可复现真实权重。
- 常见误区：路径字符串等于模型版本。
- 面试表达：“模型路径被记录，但正式 provenance 还缺内容哈希。”
- 追问方向：模型回滚；A/B；供应链安全；license。

## 第六章：目标跟踪

### K21 DeepSortTracker 适配器与 fallback

- 概念：同一 tracker contract 下支持外部 DeepSORT 和本地确定性降级。
- 为什么重要：测试环境与真实环境依赖不同。
- 原理：启动/首次调用尝试 import，失败或 dry-run 时选择 fallback。
- SmartTraffic 实现：`DeepSortTracker` 输出统一 track ID、bbox、class、state。
- 证据：`backend/app/cv/deepsort_tracker.py`、`backend/tests/test_deepsort_tracker_contract.py`。
- 真实调用链：detections → adapter branch → tracks → trajectory engine。
- 优点：无额外包也可验证完整后续链路。
- 缺点：两条算法路径质量差异大，静默回落可能掩盖环境问题。
- 替代方案：强制依赖并 fail-fast，或显式两个 tracker 类型。
- 当前限制：`deep-sort-realtime` 不在 requirements。
- 常见误区：默认运行的就是真实 DeepSORT。
- 面试表达：“当前可复现路径是 fallback；真实 DeepSORT 是外部可选路径。”
- 追问方向：为何回落；如何暴露状态；依赖锁定。

### K22 Fallback 的 IoU/中心点贪心匹配

- 概念：用空间重叠或中心关系把当前 detection 匹配到历史 track。
- 为什么重要：它决定 ID 连续性和下游轨迹质量。
- 原理：按类别生成候选，计算分数并贪心选择不冲突匹配。
- SmartTraffic 实现：分数取 IoU/中心匹配的较优值，门槛由 `max_iou_distance` 转换。
- 证据：`backend/app/cv/deepsort_tracker.py`、tracker 单元测试。
- 真实调用链：frame detections + active tracks → candidate scores → match/new/lost。
- 优点：确定性、无 ReID、易测试。
- 缺点：交叉、遮挡、快速运动时易错配；贪心非全局最优。
- 替代方案：Hungarian + Kalman、ByteTrack、BoT-SORT、真实 DeepSORT。
- 当前限制：无 appearance feature 和运动预测。
- 常见误区：把贪心 IoU 说成 Hungarian assignment。
- 面试表达：“fallback 保障契约，不承担 SOTA 跟踪质量。”
- 追问方向：cost matrix；gating；遮挡；ID switch。

### K23 Track 生命周期

- 概念：track 在 tentative、confirmed、lost/deleted 状态间转换。
- 为什么重要：下游只应消费足够稳定的轨迹。
- 原理：命中次数达到 `n_init` 确认；连续未匹配超过 `max_age` 删除。
- SmartTraffic 实现：fallback 默认 `n_init=1`、`max_age=30`；TrajectoryEngine 默认只输出 confirmed。
- 证据：`.env.example`、tracker/trajectory contract tests。
- 真实调用链：new detection → tentative/confirmed → misses → lost → deleted。
- 优点：过滤短暂噪声并容忍少量漏检。
- 缺点：参数与 FPS/stride 耦合；lost track 的空间预测弱。
- 替代方案：时间戳状态机、自适应 max_age、Kalman prediction。
- 当前限制：跨视频/跨摄像头不保持身份。
- 常见误区：track ID 是车辆的全局真实身份。
- 面试表达：“ID 只在一次 tracker/run 语境内有效。”
- 追问方向：n_init 取舍；重识别；跨镜追踪。

### K24 DeepSORT 与 ByteTrack 的边界

- 概念：DeepSORT 使用运动和外观；ByteTrack 利用高低分检测的两阶段关联。
- 为什么重要：两者适用假设和依赖不同，不能因文档出现名称就声称已用。
- 原理：真实 DeepSORT 通常是 Kalman + assignment + ReID；ByteTrack 强调低分框关联。
- SmartTraffic 实现：只有 DeepSORT adapter/fallback；ByteTrack 仅在迁移历史语境出现。
- 证据：`backend/requirements.txt`、`backend/app/cv/deepsort_tracker.py`、`docs/migration_from_yolov8.md`。
- 真实调用链：当前 detection → `DeepSortTracker`；没有 ByteTrack 实例化路径。
- 优点：接口预留使未来替换可控。
- 缺点：命名容易使读者高估实际算法。
- 替代方案：正式引入并 benchmark ByteTrack/BoT-SORT/DeepSORT。
- 当前限制：无真实 tracker 对比数据。
- 常见误区：“从 YOLOv8 迁移”就意味着使用 ByteTrack。
- 面试表达：“当前没有 ByteTrack；我会用统一 contract 做数据驱动选型。”
- 追问方向：不同 tracker 指标；低分框；ReID 成本。

## 第七章：轨迹与几何

### K25 Center 与 Bottom-center 坐标

- 概念：bbox 中心和底边中心代表不同空间语义。
- 为什么重要：轨迹运动适合 center，落地区域判断通常更适合 bottom-center。
- 原理：center 为两轴中点；bottom-center 为水平中点和 bbox 底边。
- SmartTraffic 实现：轨迹点保存 center；规则默认可用 bottom-center 判断 zone。
- 证据：`backend/app/trajectory/geometry.py`、`backend/app/trajectory/engine.py`。
- 真实调用链：track bbox → center trajectory → callback 选择 point_type → polygon test。
- 优点：计算简单，可解释。
- 缺点：透视、遮挡和 bbox 抖动仍会偏移物理落点。
- 替代方案：关键点、分割 mask、地面接触点模型。
- 当前限制：没有相机标定和世界坐标投影。
- 常见误区：认为 center 在车道多边形内等于车辆真实接触地面在内。
- 面试表达：“运动与区域语义使用不同参考点，避免混用。”
- 追问方向：坐标缩放；overlay；分辨率变化。

### K26 像素速度

- 概念：相邻轨迹点欧氏距离除以帧或时间差。
- 为什么重要：违停、拥堵和逆行都依赖速度门槛。
- 原理：`sqrt(dx²+dy²)` 得 px/frame；有 timestamp/FPS 可换 px/s。
- SmartTraffic 实现：TrajectoryEngine 在更新 track history 时计算速度。
- 证据：`backend/app/trajectory/engine.py`、trajectory tests。
- 真实调用链：center history → delta → speed feature → parking/congestion/wrong-way callback。
- 优点：无需标定，适合固定视角规则 MVP。
- 缺点：透视导致同一物理速度在不同位置数值不同。
- 替代方案：homography + 地面坐标、光流或速度回归模型。
- 当前限制：不能输出可信 km/h。
- 常见误区：把 px/s 直接改单位为 km/h。
- 面试表达：“它是相对运动特征，用于规则阈值，不是测速。”
- 追问方向：标定；VFR；stride；平滑。

### K27 方向角与一致性

- 概念：用最近轨迹窗口的运动向量估计方向及稳定程度。
- 为什么重要：单帧差分易受 bbox 抖动影响，逆行需要相对稳定方向。
- 原理：向量角 `atan2` 转 0–360°；单位向量均值表示一致性。
- SmartTraffic 实现：可配置 direction window，图像坐标系角度参与规则。
- 证据：`backend/app/trajectory/engine.py`、`geometry.py` 角度测试。
- 真实调用链：recent points → direction vector/angle → angle difference → wrong-way event。
- 优点：轻量、可解释、能抑制部分噪声。
- 缺点：低速、曲线道路、短轨迹时不稳定。
- 替代方案：Kalman velocity、Savitzky–Golay、轨迹分类模型。
- 当前限制：没有基于道路中心线的局部方向场。
- 常见误区：图像 0° 与真实北向等同。
- 面试表达：“角度只在图像与 zone 配置坐标系内有意义。”
- 追问方向：角度 wrap-around；曲线车道；一致性阈值。

### K28 驻留时间

- 概念：目标持续低速或持续处于区域内的累计时间。
- 为什么重要：区分短暂停留与违停/持续入侵。
- 原理：沿 track history 判断速度或 inside 状态，累加帧/时间。
- SmartTraffic 实现：trajectory 输出 dwell 与 zone history，parking 使用最小 dwell。
- 证据：`backend/app/trajectory/engine.py`、parking callback/tests。
- 真实调用链：speed history + timestamps → dwell → parking condition → evidence。
- 优点：规则直观，参数可配置。
- 缺点：track 断裂会重置，历史截断可影响累计。
- 替代方案：独立状态存储、track stitching、事件状态机。
- 当前限制：内存历史受 `max_history_points` 影响。
- 常见误区：把一帧低速判成违停。
- 面试表达：“违停需要区域、低速和持续时间共同成立。”
- 追问方向：红灯排队；遮挡；跨重启状态。

### K29 点在多边形与 Zone History

- 概念：判断目标参考点是否在配置多边形内，并保存连续 inside 统计。
- 为什么重要：四类事件和区域统计都依赖空间归属。
- 原理：ray casting 处理点—多边形关系；按帧更新 inside frames/duration。
- SmartTraffic 实现：geometry helper + TrajectoryEngine zone history。
- 证据：`backend/app/trajectory/geometry.py`、zone history tests。
- 真实调用链：bottom-center → point-in-polygon → zone history → intrusion/parking/congestion。
- 优点：计算轻量，区域可视化配置。
- 缺点：边界抖动、畸变、错误多边形会产生闪烁。
- 替代方案：buffer/hysteresis、mask intersection、地面坐标 GIS polygon。
- 当前限制：没有自动区域校准和边界迟滞。
- 常见误区：polygon 是真实地理区域。
- 面试表达：“当前 zone 是视频像素坐标配置。”
- 追问方向：边界点；多分辨率；区域版本。

### K30 线段相交与越线方向

- 概念：相邻轨迹段与 counting line 相交时判定越线。
- 为什么重要：流量计数需要事件时刻和方向。
- 原理：方向叉积判断相交，并比较点在线两侧的符号得到正/负方向。
- SmartTraffic 实现：geometry helper 输出 crossing 与 positive/negative/none。
- 证据：`backend/app/trajectory/geometry.py`、flow counting tests。
- 真实调用链：previous/current point → segment intersection → direction filter → flow event。
- 优点：确定性、可解释、无需学习数据。
- 缺点：触线、沿线移动、抖动和 ID switch 难处理。
- 替代方案：有宽度的计数带、状态机、虚拟闸门双线法。
- 当前限制：边界恰在线上可返回 none。
- 常见误区：bbox 与线重叠就一定算越线。
- 面试表达：“计数依据轨迹中心跨越，不是检测框瞬时覆盖。”
- 追问方向：去重；反复穿越；双向计数；stride。

## 第八章：Zone 与 Rule

### K31 Zone 配置契约

- 概念：Zone 将视频像素区域、方向和 counting line 结构化。
- 为什么重要：场景规则必须与具体摄像头/视频几何绑定。
- 原理：polygon 负责空间范围，direction/counting line 提供方向语义。
- SmartTraffic 实现：Zone ORM/Pydantic 支持类型、polygon、direction、counting_line、enabled、version。
- 证据：`backend/app/models/config.py`、`backend/app/schemas/zone.py`、ZoneEditor。
- 真实调用链：Zone page draw → zones API → DB → EventRuleService 注入 callback。
- 优点：业务人员可视化调参，规则可解释。
- 缺点：像素坐标依赖分辨率与镜头位置。
- 替代方案：归一化坐标、世界坐标/GIS、自动 lane segmentation。
- 当前限制：缺不可变版本发布与跨分辨率迁移。
- 常见误区：zone type 自动提供正确语义，无需人工校准。
- 面试表达：“Zone 是规则上下文，不是模型识别结果。”
- 追问方向：校验自交多边形；版本；摄像头变化。

### K32 EventRule 契约与版本

- 概念：事件类型、目标类、参数、区域、冷却和严重度组成规则。
- 为什么重要：把业务阈值从 callback 代码中分离。
- 原理：Pydantic/服务层验证后序列化存储，执行前归一化。
- SmartTraffic 实现：支持六类事件、low/medium/high、version 和 min_track_length。
- 证据：`backend/app/models/config.py`、`backend/app/schemas/event_rule.py`、`backend/app/services/event_rule_service.py`。
- 真实调用链：rule CRUD → DB rule → effective rule → EventEngine。
- 优点：可配置、可审计字段明确。
- 缺点：version 只是数值字段，不是完整发布历史。
- 替代方案：规则 DSL/CEP、GitOps 配置、不可变 rule revision 表。
- 当前限制：没有 canary、回滚和影响分析。
- 常见误区：修改 version 自动保存旧规则内容。
- 面试表达：“当前有版本字段，但还没有规则版本治理系统。”
- 追问方向：兼容性；审核；冲突；规则测试。

### K33 Zone 参数注入与 Callback Registry

- 概念：服务层把持久化 zone 转成 callback 可执行参数，并按 event type 找实现。
- 为什么重要：避免每个 callback 自行查询数据库，保持纯逻辑可测。
- 原理：rule normalization + registry dispatch + dependency data injection。
- SmartTraffic 实现：允许方向注入 wrong-way，counting line 注入 flow，congestion 标记 aggregate。
- 证据：`backend/app/services/event_rule_service.py`、`backend/app/events/rule_callbacks/__init__.py`。
- 真实调用链：DB rule/zone → effective dict → EventRule → registry callback。
- 优点：callback 更接近纯函数，测试容易。
- 缺点：注入字段与持久化 schema 之间存在隐式映射。
- 替代方案：策略对象 + typed context、依赖注入容器、规则 DSL。
- 当前限制：缺 schema version migration 和静态 exhaustive check。
- 常见误区：callback 会实时读取最新 zone。
- 面试表达：“执行时先形成 effective rule snapshot，再调用 callback。”
- 追问方向：新增事件类型步骤；类型安全；缓存。

### K34 Cooldown、去重与幂等

- 概念：抑制同一规则/轨迹或区域在短时间内重复发事件。
- 为什么重要：连续帧每帧命中会造成告警风暴和重复计数。
- 原理：构造 dedup key，比较最近触发时间/帧和 cooldown。
- SmartTraffic 实现：Event Engine 与 AlertService 各有稳定 ID/cooldown；flow 可每轨只计一次。
- 证据：`backend/app/events/engine.py`、`backend/app/alerts/`、cooldown tests。
- 真实调用链：callback matched → dedup key → cooldown check → emit/suppress。
- 优点：简单有效，ID 可确定性复现。
- 缺点：状态在内存，重启/多 worker 不共享；cooldown=0 可重复。
- 替代方案：数据库唯一键、Redis TTL、事件窗口/CEP。
- 当前限制：没有跨进程幂等和业务级 exactly-once。
- 常见误区：稳定 ID 自动保证不会重复写入。
- 面试表达：“当前是进程内抑制，不宣称分布式 exactly-once。”
- 追问方向：并发 race；时钟；事件更新还是新建。

## 第九章：六类事件与证据

### K35 Event Engine 执行模型

- 概念：统一执行逐轨与 aggregate 规则，记录成功、跳过和错误。
- 为什么重要：规则规模增加时需要一致过滤、异常隔离和可解释输出。
- 原理：normalize → filter → callback → cooldown → event/evidence/execution。
- SmartTraffic 实现：aggregate 每帧调用一次，track rule 对每条轨迹调用；callback 异常转 error execution。
- 证据：`backend/app/events/engine.py`、`backend/tests/test_event_engine.py`。
- 真实调用链：trajectory frame → enabled rules → callback registry → three output lists。
- 优点：统一契约、异常不击穿整批、支持 debug execution。
- 缺点：单进程内存状态，规则多时是朴素遍历。
- 替代方案：Rete/CEP、流处理、规则编译索引。
- 当前限制：无规则优先级、依赖图和跨事件组合。
- 常见误区：Event Engine 是深度学习事件模型。
- 面试表达：“这是轨迹特征驱动的规则执行器。”
- 追问方向：复杂度；异常策略；新增规则；状态持久化。

### K36 逆行规则

- 概念：比较目标运动方向与车道允许方向，判断反向行驶。
- 为什么重要：展示轨迹特征、区域配置和规则证据的组合。
- 原理：inside vehicle lane、最小速度、角差达到反向阈值，并可要求连续确认。
- SmartTraffic 实现：默认 allowed 0°、tolerance 45°、reverse threshold 135°、speed 1 px/frame。
- 证据：`backend/app/events/rule_callbacks/wrong_way.py`、对应测试。
- 真实调用链：track → direction/speed/zone history → callback → direction evidence/event。
- 优点：结果可解释，阈值可调。
- 缺点：曲线道路、慢车和镜头方向变化会误判。
- 替代方案：lane centerline direction field、轨迹分类模型。
- 当前限制：legacy `min_wrong_way_frames` 在部分上下文不受支持。
- 常见误区：仅看 bbox 朝向即可判断逆行。
- 面试表达：“判断的是运动方向，不是车辆外观朝向。”
- 追问方向：掉头；曲线；低速；角度阈值校准。

### K37 违停规则

- 概念：在禁停区持续低速/静止达到时间门槛。
- 为什么重要：需要区分短暂停顿与持续行为。
- 原理：vehicle class + inside no-parking zone + speed threshold + dwell threshold。
- SmartTraffic 实现：bottom-center、默认 1 px/frame、约 3000 ms，可配 max center shift。
- 证据：`backend/app/events/rule_callbacks/parking.py`、parking tests。
- 真实调用链：trajectory speed/zone/dwell → callback → dwell/speed/zone evidence。
- 优点：条件透明，便于复核。
- 缺点：排队、红灯、遮挡和 track reset 会影响结果。
- 替代方案：场景状态融合、车道/信号灯语义、停驻模型。
- 当前限制：无信号灯和合法临停上下文。
- 常见误区：低速一次就算违停。
- 面试表达：“违停是时空复合规则，不是单帧分类。”
- 追问方向：dwell 跨丢失；误报抑制；阈值单位。

### K38 危险区入侵规则

- 概念：目标进入危险多边形并满足持续条件。
- 为什么重要：是通用区域入侵的最小可解释模板。
- 原理：target class filter + point-in-polygon + min inside frames/seconds。
- SmartTraffic 实现：`danger_zone_intrusion` 使用 zone history 和 bottom-center。
- 证据：`backend/app/events/rule_callbacks/danger_zone.py`、对应测试。
- 真实调用链：trajectory point → danger zone → duration check → event/evidence。
- 优点：类别和持续时间可配置。
- 缺点：只知道几何进入，不理解风险语境。
- 替代方案：scene graph、PPE/动作识别、风险模型。
- 当前限制：危险程度由规则 severity 给定，不是模型估计。
- 常见误区：任何进入都等于真实安全事故。
- 面试表达：“输出是规则告警线索，需要人工复核。”
- 追问方向：边界抖动；多区域；优先级；人员隐私。

### K39 行人进入机动车道规则

- 概念：person 类目标进入 vehicle lane。
- 为什么重要：展示检测类别与场景区域语义的交叉约束。
- 原理：class==person、inside zone、最短持续条件。
- SmartTraffic 实现：`pedestrian_in_vehicle_lane` callback 复用 zone history。
- 证据：对应 callback 文件与测试。
- 真实调用链：YOLO person → tracker → bottom-center → vehicle lane → event。
- 优点：规则简洁、证据直观。
- 缺点：行人漏检、骑行者类别和人行横道上下文会影响判断。
- 替代方案：语义分割、场景图、行人意图模型。
- 当前限制：不识别人行横道、信号灯或合法通行时段。
- 常见误区：person bbox 触碰车道就必然命中。
- 面试表达：“用 bottom-center 和持续条件减少框边缘误判。”
- 追问方向：类别混淆；多人；遮挡；合法区域。

### K40 拥堵 Aggregate 规则

- 概念：按区域聚合多个车辆的数量与平均速度。
- 为什么重要：它不是单轨行为，而是群体状态。
- 原理：同帧 zone 内 vehicle count ≥ threshold 且 avg speed ≤ threshold，连续若干帧成立。
- SmartTraffic 实现：rule_mode=`aggregate`，event 的 track_id 可为 null。
- 证据：`events/rule_callbacks/congestion.py`、aggregate engine tests。
- 真实调用链：all trajectory points → zone grouping → count/avg speed → congestion event。
- 优点：计算轻量，区域级证据明确。
- 缺点：检测/跟踪误差直接影响统计；平均值掩盖分布。
- 替代方案：密度估计、时空模型、道路速度指数。
- 当前限制：`time_window_seconds` 不是真正 elapsed-time 滑窗，主要按连续帧。
- 常见误区：声称实现了复杂流处理时间窗口。
- 面试表达：“当前是连续帧 aggregate MVP，不是完整 CEP window。”
- 追问方向：窗口；分位数速度；车道容量；持续事件合并。

### K41 流量计数规则与聚合

- 概念：越线事件是原子事实，flow count 是按时间/类别/方向聚合。
- 为什么重要：区分事件生成与报表统计职责。
- 原理：轨迹段跨线 → direction → per-track dedup → 60 秒 bucket 聚合。
- SmartTraffic 实现：flow callback 生成 event，artifact writer 生成 `flow_counts.json`。
- 证据：`backend/app/events/rule_callbacks/flow_counting.py`、`backend/app/analysis/artifact_writer.py`。
- 真实调用链：trajectory crossing → flow event → unique event aggregation → API/Report。
- 优点：原子证据可回查，汇总可重建。
- 缺点：ID switch、线边界、同轨回穿影响准确性。
- 替代方案：双线虚拟闸门、track stitching、专用计数模型。
- 当前限制：无真实标注大规模校准。
- 常见误区：把 bbox 数量直接称为交通流量。
- 面试表达：“计数依据唯一越线事件，而不是每帧检测框累加。”
- 追问方向：方向命名；重复计数；bucket；MAPE。

### K42 Event、Evidence、RuleExecution 三层模型

- 概念：事件事实、支持证据和规则执行日志分开保存。
- 为什么重要：既要给业务展示，也要解释为何匹配或为何失败。
- 原理：Event 描述 what，Evidence 描述 why/data，Execution 描述 how/status。
- SmartTraffic 实现：三个 ORM/JSONL 类型，证据类型含 trajectory/zone/speed/direction 等。
- 证据：`backend/app/models/event.py`、`backend/app/events/contracts.py`。
- 真实调用链：callback result → build event/evidence/execution → DB/artifacts → Analysis/Review。
- 优点：可解释、可调试、可扩展。
- 缺点：多文件/多表一致性复杂；证据 schema 较松。
- 替代方案：单一 event payload、事件溯源、typed evidence union。
- 当前限制：snapshot 可缺失，证据无签名和 checksum。
- 常见误区：RuleExecution matched 就等于人工确认。
- 面试表达：“规则命中与人工真实性结论是两个层次。”
- 追问方向：schema evolution；证据防篡改；失败记录量。

## 第十章：告警与可视化证据

### K43 告警是事件的派生物

- 概念：事件描述算法/规则事实，告警描述需要操作的业务项。
- 为什么重要：避免把告警逻辑与检测逻辑混在一起。
- 原理：按事件 severity、规则和 cooldown 生成稳定 alert ID。
- SmartTraffic 实现：`AlertService` 从 run events 生成并持久化告警。
- 证据：`backend/app/alerts/`、`backend/app/services/alert_service.py`。
- 真实调用链：Event → generate alerts → Alert DB/JSONL → Alert Center。
- 优点：可独立管理生命周期和重复抑制。
- 缺点：当前 alert 仍强依赖 event 质量，没有外部通知通道。
- 替代方案：消息总线 + notification policy engine。
- 当前限制：无短信、邮件、Webhook、升级策略和 on-call。
- 常见误区：告警由另一个 AI 模型生成。
- 面试表达：“告警是事件到处置流程的业务投影。”
- 追问方向：风暴抑制；优先级；通知失败。

### K44 告警生命周期

- 概念：告警可从未处理进入 acknowledged、resolved 或 ignored。
- 为什么重要：操作状态与事件事实需要解耦并可审计。
- 原理：状态变更接口验证 allowed transition 并记录 actor/time。
- SmartTraffic 实现：Alert API 支持 list/detail/ack/resolve/ignore。
- 证据：`backend/app/api/alerts.py`、alert lifecycle tests。
- 真实调用链：Alert Center action → API → service/repository → commit → refreshed list。
- 优点：形成最小处置闭环。
- 缺点：权限身份不可信，状态机约束较轻。
- 替代方案：工单系统、显式 workflow engine、append-only audit log。
- 当前限制：无 SLA、升级和再打开策略。
- 常见误区：resolved 等于事件为真；它只是处置状态。
- 面试表达：“事件真实性由 review，告警状态描述处置进度。”
- 追问方向：状态转换；并发更新；审计。

### K45 Visual Evidence 状态降级

- 概念：关键帧/标注视频可处于 available、empty、missing 或 error。
- 为什么重要：系统应显式表达证据缺失，而不是伪造路径。
- 原理：构建器捕获源视频缺失、无事件和编码异常，更新 manifest 状态。
- SmartTraffic 实现：visual artifact service + keyframe index + relative refs。
- 证据：`backend/app/analysis/visual_artifacts.py`、visual artifact tests。
- 真实调用链：event/alert refs → source frame draw → artifact status → UI fallback。
- 优点：失败可观察，结构化结果仍可用。
- 缺点：生成失败后没有后台重试和修复队列。
- 替代方案：按需渲染服务、对象存储事件触发器。
- 当前限制：本地 codec 和源视频生命周期影响可用性。
- 常见误区：manifest 路径存在就等于文件可读。
- 面试表达：“artifact availability 是一等状态，不用空链接掩盖失败。”
- 追问方向：重建；checksum；缓存；权限 URL。

## 第十一章：数据、迁移与 Artifact

### K46 SQLAlchemy Session 与事务边界

- 概念：repository flush，API/CLI 外层 commit，session 负责单次工作单元。
- 为什么重要：决定写入原子性、异常回滚和可测试性。
- 原理：`sessionmaker` + dependency；`flush` 获取 ID，不代表持久提交。
- SmartTraffic 实现：默认 SQLite，`autoflush=False`、`expire_on_commit=False`。
- 证据：`backend/app/db/session.py`、`backend/app/repositories/base.py`。
- 真实调用链：route `get_db` → repo create/flush → service → route commit/rollback path。
- 优点：事务边界可由用例控制，测试可替换 DB。
- 缺点：提交散落在路由，文件 I/O 不在事务内。
- 替代方案：Unit of Work、service transaction decorator、outbox。
- 当前限制：`get_db` 关闭 session，但不自动统一 commit/rollback。
- 常见误区：`flush()` 等同 `commit()`。
- 面试表达：“DB 原子性止于 session，不能覆盖外部文件写入。”
- 追问方向：nested transaction；rollback；并发锁。

### K47 21 个 ORM 模型的取舍

- 概念：用规范化实体保存输入、运行、算法结果和质量闭环。
- 为什么重要：支持查询、状态更新和报告聚合。
- 原理：字符串主键、外键字段、索引和 JSON 扩展字段。
- SmartTraffic 实现：Camera/Video/Run/Detection/Track/Event/Alert/BadCase/Evaluation 等 21 类。
- 证据：`backend/app/models/`。
- 真实调用链：API schema → ORM → repository/service → response/artifact。
- 优点：领域边界可见，查询比纯 JSONL 更方便。
- 缺点：无 ORM relationship/cascade，组合唯一约束不足，JSON 可失去类型约束。
- 替代方案：更严格关系模型、document DB、event store。
- 当前限制：引用完整性和重复写主要靠服务层。
- 常见误区：有 ForeignKey 就自动提供级联与对象导航。
- 面试表达：“模型保留 FK，但刻意/暂时未建立 relationship；这是当前技术债。”
- 追问方向：索引；N+1；删除；JSON schema。

### K48 Alembic 迁移策略

- 概念：数据库结构按版本可升级/回退。
- 为什么重要：模型变化不能依赖运行时自动建表。
- 原理：revision 链执行 upgrade/downgrade。
- SmartTraffic 实现：4 个版本；`0002` 用 `Base.metadata.create_all/drop_all`，后两版增 processing/camera 字段。
- 证据：`backend/alembic/versions/`。
- 真实调用链：container start → `alembic upgrade head` → Uvicorn。
- 优点：已有版本入口且 Compose 自动升级。
- 缺点：metadata create/drop 迁移不够显式，downgrade 可能破坏所有表。
- 替代方案：每版显式 `op.create_table`/batch alter + migration CI。
- 当前限制：无生产数据迁移演练、备份和回滚验证。
- 常见误区：Alembic 文件存在就代表迁移安全。
- 面试表达：“迁移机制已接入，但早期 baseline 需要重构为可审计 DDL。”
- 追问方向：SQLite alter；零停机；数据 backfill；回滚。

### K49 数据库与文件双写一致性

- 概念：同一 run 的结构化结果同时写 SQLite 和本地 artifact。
- 为什么重要：双写失败会产生孤儿文件、缺失行或内容分歧。
- 原理：两个非事务资源需要顺序、幂等、补偿和一致性检查。
- SmartTraffic 实现：处理先产 artifact，再创建/import DB 结果并由路由 commit。
- 证据：`backend/app/api/videos.py`、`backend/app/analysis/artifact_compatibility.py`。
- 真实调用链：pipeline output → run files → DB bulk import → commit → unified read。
- 优点：文件便于调试/交换，DB 便于查询。
- 缺点：没有原子事务与自动 reconciliation。
- 替代方案：DB 为唯一真相后异步导出；对象存储 + metadata DB + outbox。
- 当前限制：SQLite 与本地 artifact 非原子；失败可能留残余文件，读路径需 fallback。
- 常见误区：路由 commit 成功就证明文件与 DB 完全一致。
- 面试表达：“这是兼容性取舍，生产化要明确单一权威源和补偿机制。”
- 追问方向：写入顺序；幂等导入；孤儿清理；checksum。

### K50 Manifest 与 Artifact Index

- 概念：manifest 描述产物是否必需、可选、计划和当前状态；index 提供路径索引。
- 为什么重要：目录中文件存在与业务可用不是同一回事。
- 原理：每项记录 path、status、record count、错误或 availability。
- SmartTraffic 实现：run 生成 `manifest.json` 与 `artifact_index.json`。
- 证据：`backend/app/analysis/artifact_writer.py`、manifest tests。
- 真实调用链：artifact write → status update → analysis manifest API → UI artifact panel。
- 优点：可发现、可降级、兼容分阶段输出。
- 缺点：无强校验和；manifest 自身可能与文件漂移。
- 替代方案：content-addressed manifest、对象存储 catalog、Parquet dataset metadata。
- 当前限制：部分旧 run 需要读取时补生成。
- 常见误区：planned 表示文件已经存在。
- 面试表达：“manifest 同时表达契约与 availability，不只列文件名。”
- 追问方向：schema version；原子发布；校验；垃圾回收。

### K51 DB-first、Artifact Fallback 与幂等导入

- 概念：优先读取数据库，缺失时兼容旧文件；也可将文件导入数据库。
- 为什么重要：项目从文件结果演进到 DB 查询，需要平滑兼容。
- 原理：read-through 检查 DB 是否有数据，再解析 CSV/JSONL；导入用稳定 ID 避免重复。
- SmartTraffic 实现：Analysis/Alert 等 service 与 `scripts/import_artifacts_to_db.py`。
- 证据：`backend/tests/test_artifact_compatibility.py`。
- 真实调用链：analysis API → DB query → empty fallback file → normalized response；CLI → dry-run/import。
- 优点：旧 run 仍可展示，迁移可渐进。
- 缺点：两个源可能不一致，fallback 会隐藏 DB 丢失。
- 替代方案：一次性强迁移后移除 fallback，或数据虚拟化层。
- 当前限制：某些 read-through 会生成派生文件，读操作非严格只读。
- 常见误区：DB-first 意味着 DB 永远完整。
- 面试表达：“fallback 是兼容策略，不应长期替代数据治理。”
- 追问方向：冲突裁决；导入幂等；损坏 JSONL；迁移结束条件。

## 第十二章：Analysis Center 与前端

### K52 Analysis Center 聚合读取

- 概念：以 run 为单位统一返回摘要、明细、统计和证据。
- 为什么重要：前端不应了解每个 artifact 的存储差异。
- 原理：service 组合 DB repository、artifact discovery 与 summary builder。
- SmartTraffic 实现：11 个 analysis-run endpoints 覆盖 manifest、flow、zone、detections、tracks、trajectory、events、alerts。
- 证据：`backend/app/api/analysis_runs.py`、`traffic_analysis_service.py`。
- 真实调用链：Analysis page run ID → parallel fetch → normalized payload → overlay/tables。
- 优点：对前端提供统一 BFF 式接口。
- 缺点：service 责任较大，兼容逻辑复杂。
- 替代方案：GraphQL run graph、预计算 read model、typed artifact gateway。
- 当前限制：分页/大文件读取和缓存能力有限。
- 常见误区：顶层 `/api/detections` 是真实查询入口。
- 面试表达：“真实明细入口是 analysis-run 子资源。”
- 追问方向：大 run；分页；缓存；一致快照。

### K53 视频 Overlay 坐标映射

- 概念：将原视频坐标的 bbox/轨迹/zone 映射到响应式显示尺寸。
- 为什么重要：坐标错位会让复核证据失真。
- 原理：SVG viewBox 或按原始宽高比例缩放；视频时间驱动当前帧选择。
- SmartTraffic 实现：frontend overlay components 叠加 detection、track 和 zone。
- 证据：`frontend/src/components/`、Analysis Detail page/tests。
- 真实调用链：video metadata + current time/frame → filter records → SVG overlay。
- 优点：无需把所有标注烧录进视频，交互灵活。
- 缺点：VFR、letterbox、CSS resize 和 frame rounding 可能错位。
- 替代方案：后端烧录视频、Canvas/WebGL、HLS timed metadata。
- 当前限制：无浏览器像素级 E2E/视觉回归。
- 常见误区：TypeScript 类型正确就能保证视觉坐标正确。
- 面试表达：“结构化 overlay 与预渲染视频互补，并需独立视觉验证。”
- 追问方向：object-fit；DPR；frame sync；性能。

### K54 前端 API Client 的静态类型边界

- 概念：TypeScript generic cast 只在编译期存在，不验证运行时 JSON。
- 为什么重要：后端 schema 漂移可能在页面运行时才暴露。
- 原理：`fetch` 检查 HTTP 状态后把 JSON cast 为 `T`。
- SmartTraffic 实现：`frontend/src/api/client.ts` 无 Zod/io-ts、retry、abort 或统一 actor header。
- 证据：`frontend/src/api/client.ts`、page call sites。
- 真实调用链：page → generic request<T> → fetch → cast → component render。
- 优点：轻量、调用代码简洁。
- 缺点：运行时不安全，错误信息较泛，慢请求不能取消。
- 替代方案：OpenAPI generated client + runtime validator、TanStack Query。
- 当前限制：无集中缓存、请求去重和 schema compatibility test。
- 常见误区：`as T` 会验证响应字段。
- 面试表达：“当前类型提供开发提示，不是边界验证。”
- 追问方向：错误模型；取消；重试；缓存；OpenAPI 生成。

## 第十三章：Review、漏报与 Bad Case

### K55 Review Center 的人工真值层

- 概念：人工对事件做 confirm、false-positive、ignore、resolve 和评论。
- 为什么重要：规则命中不是业务真值，必须显式记录人工结论。
- 原理：事件事实保持不变，review state 作为独立业务投影。
- SmartTraffic 实现：11 个 review endpoints 和 review artifacts/DB comments。
- 证据：`backend/app/api/review.py`、`backend/app/services/review_service.py`。
- 真实调用链：Review page → action API → review state/comment → list/detail refresh。
- 优点：不覆盖原始算法结果，保留审计语义。
- 缺点：actor header 未认证，状态并发控制较弱。
- 替代方案：工作流/工单系统、双人复核、append-only audit event。
- 当前限制：无一致性评分、分配队列、SLA 和 reviewer agreement。
- 常见误区：confirm 会修改模型或自动重训。
- 面试表达：“Review 产出标签和处置状态，但训练闭环尚未自动化。”
- 追问方向：审核冲突；权限；审计；标注质量。

### K56 False Negative 显式登记

- 概念：对系统未产出的真实事件，由人工补录漏报。
- 为什么重要：只复核已检测事件只能看到误报，看不到召回缺口。
- 原理：独立 false-negative record 保存时间、类型、区域、说明和证据引用。
- SmartTraffic 实现：Review API 支持创建/列表漏报，并可转 Bad Case。
- 证据：`backend/app/schemas/review.py`、`backend/app/api/review.py`、false-negative tests。
- 真实调用链：reviewer 查视频 → create false negative → artifact/DB → Bad Case。
- 优点：质量闭环同时覆盖 precision 与 recall 问题。
- 缺点：高度依赖人工发现和标注一致性。
- 替代方案：全量标注集、主动学习、抽样复核。
- 当前限制：无 frame-level annotation tool 和多人一致性检查。
- 常见误区：failed case 全部来自系统误报。
- 面试表达：“漏报必须有独立入口，否则评测会有选择偏差。”
- 追问方向：抽样策略；成本；漏报 ground truth。

### K57 Bad Case 资产化

- 概念：把误报、漏报或评测失败沉淀为可筛选、可更新的问题样本。
- 为什么重要：一次修复只有进入回归集才有长期价值。
- 原理：记录 source、case type、module、status、tags、run/evidence 引用和审计。
- SmartTraffic 实现：手工、from-review、from-failed-case 三种创建路径；DB + JSONL。
- 证据：`backend/app/services/bad_case_service.py`、stage8 bad-case tests。
- 真实调用链：review/eval failed → BadCase create/dedup → triage/update → regression。
- 优点：统一问题入口，支持模块和状态筛选。
- 缺点：没有图像数据版本、责任人、优先级和训练集审批。
- 替代方案：Label Studio/CVAT + issue tracker + dataset registry。
- 当前限制：本地存储和稳定 ID 去重能力有限。
- 常见误区：Bad Case 自动成为训练样本。
- 面试表达：“当前完成问题资产化，尚未自动接入训练数据发布。”
- 追问方向：去重；隐私；状态机；数据漂移。

### K58 Regression Replay 的真实含义

- 概念：对存储规则 fixture / Bad Case 状态做确定性重放与状态建议。
- 为什么重要：验证规则修复是否覆盖已知问题。
- 原理：加载 case 输入和 expected，重新调用规则或检查 replay data，产出 fixed/reopened/unchanged 建议。
- SmartTraffic 实现：evaluation type=`regression`，可选 `apply_updates`。
- 证据：`backend/app/services/evaluation_service.py`、`backend/tests/test_regression_metrics.py`。
- 真实调用链：Bad Case filter → replay fixture → regression metrics → optional status update。
- 优点：快速、确定性、无需重跑大视频。
- 缺点：不能发现模型/解码/tracker 层新回归。
- 替代方案：完整视频 pipeline replay、golden dataset CI。
- 当前限制：缺 replay data 时不会伪造通过，但覆盖面受 fixture 限制。
- 常见误区：regression 等于所有原视频重推理。
- 面试表达：“这是规则/坏例级重放，不是全链路模型回归。”
- 追问方向：apply update 风险；golden data；版本绑定。

## 第十四章：Evaluation

### K59 事件匹配与 Precision/Recall/F1

- 概念：将 actual event 与 expected event 按类型、可选 track/zone 和帧容差匹配。
- 为什么重要：量化事件漏报与误报，而不是只数事件总量。
- 原理：一对一匹配得到 TP/FP/FN，再算 precision、recall、F1；accuracy 采用 TP/expected。
- SmartTraffic 实现：默认 frame tolerance 5，输出 per-event-type 和 failed cases。
- 证据：`backend/app/services/evaluation_service.py`、event metric tests。
- 真实调用链：expected JSON + run events → matcher → metrics/failed cases → UI/Report。
- 优点：适合事件检测 MVP，错误样本可追溯。
- 缺点：无 TN，`accuracy` 命名容易误解；贪心/规则匹配策略影响结果。
- 替代方案：区间 IoU matching、event detection benchmark protocol。
- 当前限制：仓库没有正式真实数据结果。
- 常见误区：F1=1 的 toy case 等于泛化准确率 100%。
- 面试表达：“toy 指标验证实现，不代表真实场景性能。”
- 追问方向：匹配冲突；容差；macro/micro；置信区间。

### K60 流量误差、MAE 与 MAPE

- 概念：比较预期和实际计数的绝对误差与相对误差。
- 为什么重要：计数任务不能只用分类 F1 表示。
- 原理：AE=`|actual-expected|`，MAE 为平均 AE，MAPE 除以 expected。
- SmartTraffic 实现：总量及 per class/direction 输出 flow metrics。
- 证据：evaluation service、flow metric tests、`demo_expected_counts.json`。
- 真实调用链：expected counts + flow_counts → align keys → errors → evaluation results。
- 优点：业务含义直观，可定位类别/方向偏差。
- 缺点：expected=0 时 MAPE 不稳定；小分母放大误差。
- 替代方案：WAPE、sMAPE、Poisson deviance、按时段误差分布。
- 当前限制：tracked toy expected 只有 2 个计数记录。
- 常见误区：MAPE 适合所有零流量时间段。
- 面试表达：“我会同时报告绝对误差和对零值稳健的指标。”
- 追问方向：零分母；时间 bucket；置信区间。

### K61 Detection AP@0.5 的边界

- 概念：按单一 IoU=0.5 计算 VOC 风格 AP。
- 为什么重要：避免把轻量 AP 宣传为 COCO mAP。
- 原理：按 confidence 排序，一对一 IoU 匹配，积分 precision-recall 曲线。
- SmartTraffic 实现：evaluation type detection 的自定义 metric。
- 证据：`backend/app/services/evaluation_service.py`、detection metric tests。
- 真实调用链：GT boxes + detections → IoU match → class metrics/AP → results。
- 优点：依赖少，能验证基本 detection 评测链路。
- 缺点：单阈值、无 small/medium/large、无 COCO protocol。
- 替代方案：pycocotools、FiftyOne、MMEval。
- 当前限制：仓库无 tracked detection annotation dataset/result。
- 常见误区：AP@0.5 等于 mAP@[.5:.95]。
- 面试表达：“这是 MVP AP50，不称 COCO mAP。”
- 追问方向：IoU；PR 插值；类别平均；置信度阈值。

### K62 Lightweight Tracking Metrics

- 概念：帧内用贪心 IoU 关联预测和 GT，再统计 IDF1、MOTA、ID switch、lost segment。
- 为什么重要：跟踪必须同时评估检测与身份连续性。
- 原理：逐帧匹配后累计 FP/FN/IDSW，并根据公式计算近似指标。
- SmartTraffic 实现：evaluation type tracking 的轻量实现。
- 证据：evaluation service、tracking metric tests。
- 真实调用链：GT/pred tracks → frame grouping → greedy match → identity counters → metrics。
- 优点：零额外依赖，测试小数据方便。
- 缺点：不是官方 TrackEval；匹配策略和边界处理可能不同。
- 替代方案：TrackEval、motmetrics、HOTA benchmark。
- 当前限制：无正式 MOT 数据和真实 DeepSORT 路径结果。
- 常见误区：输出 IDF1/MOTA 就自动等于官方实现。
- 面试表达：“指标名相同，但实现是轻量近似，正式报告应接标准工具。”
- 追问方向：MOTA 负值；HOTA；ID switch；匹配阈值。

### K63 Trajectory 描述统计与 Regression 边界

- 概念：trajectory evaluation 当前是点数、速度、方向可用率等描述；regression 是 fixture 重放。
- 为什么重要：接口叫 evaluation 不代表都有 ground-truth accuracy。
- 原理：无 GT 时只能描述 coverage/health，不能估计空间误差。
- SmartTraffic 实现：trajectory 与 regression 两个 metric family 分开输出。
- 证据：evaluation service、stage8 evaluation tests、regression tests。
- 真实调用链：run trajectory/bad cases → metric family → summary/failed cases。
- 优点：在数据不足时仍能做管道健康检查。
- 缺点：不能回答轨迹位置精度和完整视频回归。
- 替代方案：ADE/FDE、MOT trajectory GT、全链路 golden replay。
- 当前限制：无世界坐标 GT 和正式 trajectory benchmark。
- 常见误区：方向可用率高等于方向准确率高。
- 面试表达：“coverage metric 不是 correctness metric。”
- 追问方向：ADE/FDE；GT 构建；漂移；回归层级。

## 第十五章：Reporting

### K64 DB-first 报告聚合

- 概念：报告从 run、事件、告警、流量、区域、坏例和评测构建统一摘要。
- 为什么重要：面向业务的结论需要跨多个领域对象。
- 原理：优先查询 DB，必要时读取 artifacts，并归一化为 report summary。
- SmartTraffic 实现：`ReportService` 组合 counts、top events、alert status、latest evaluation。
- 证据：`backend/app/services/report_service.py`、report tests。
- 真实调用链：report summary API → service loaders → normalized summary → Web/export。
- 优点：多个格式共享核心字段，兼容旧 run。
- 缺点：双源一致性与“大查询”性能风险。
- 替代方案：预计算 report read model、OLAP/warehouse。
- 当前限制：没有跨 run 趋势和正式签发流程。
- 常见误区：报告是独立重新计算全部算法。
- 面试表达：“报告聚合已有事实，不改变原始 run 结果。”
- 追问方向：缓存；版本；重算；一致快照。

### K65 JSON、CSV、PDF 与 Bundle 的差异

- 概念：不同导出格式服务于机器交换、表格分析和人工阅读。
- 为什么重要：格式一致性与能力边界容易被高估。
- 原理：full JSON 保留结构；CSV 按 section 展平；PDF 渲染摘要；bundle 列引用。
- SmartTraffic 实现：六类 CSV、JSON、手写 PDF 1.4、bundle metadata。
- 证据：reports API、report service/PDF tests。
- 真实调用链：Report page → export endpoint → renderer → download response。
- 优点：无额外 PDF 依赖，导出覆盖常用场景。
- 缺点：PDF Latin-1/英文为主；bundle 不含实际文件且不是 zip。
- 替代方案：WeasyPrint/ReportLab、HTML print、真正 zip manifest package。
- 当前限制：Web/PDF 只共享核心 summary，不是逐字内容一致。
- 常见误区：把 bundle endpoint 说成完整归档下载。
- 面试表达：“bundle 是元数据清单；PDF 是轻量摘要。”
- 追问方向：中文字体；大数据 CSV；公式注入；签名。

### K66 Latest Evaluation 选择

- 概念：报告选择某 run 最新完成的评测结果进行摘要。
- 为什么重要：同一 run 可有多次、多个类型的 evaluation。
- 原理：按 finished/start/created timestamp 排序，并优先可解释的 event-type 结果。
- SmartTraffic 实现：当前 HEAD 最近修复了 latest metric summary 计算。
- 证据：`backend/app/services/report_service.py`、recent commits、report tests。
- 真实调用链：run → evaluation results list → latest completed selection → report metrics。
- 优点：报告展示最新质量信号。
- 缺点：latest 不一定是 approved/best；跨 metric family 不可直接比较。
- 替代方案：显式 evaluation_run_id pin、发布审批、版本标签。
- 当前限制：报告没有强制绑定经批准的 dataset/model/config 版本。
- 常见误区：最新评测就是正式基准。
- 面试表达：“latest 是展示策略，生产报告应 pin 已批准评测。”
- 追问方向：并列时间；失败运行；多数据集；审批。

## 第十六章：Realtime Preview

### K67 Mock/File/RTSP 占位预览

- 概念：当前 realtime 模块验证生命周期和 UI 契约，不做持续流处理。
- 为什么重要：这是最容易被过度宣传的模块。
- 原理：创建 preview state 与伪 task；worker 根据 source type 返回确定性 metadata。
- SmartTraffic 实现：mock 三帧；file 仅检查路径；RTSP 明确不连接；缓存最多 20 条。
- 证据：`backend/app/realtime/worker.py`、`backend/app/services/realtime_service.py`、realtime tests。
- 真实调用链：Camera page start → realtime API → preview service → placeholder recent data → stop。
- 优点：先验证 camera UI、状态和 API 契约，无网络依赖。
- 缺点：没有解码、推理、线程、断线重连和低延迟保证。
- 替代方案：FFmpeg/GStreamer ingest + async worker + WebRTC/HLS。
- 当前限制：状态主要在单进程内存，多实例不可用。
- 常见误区：camera source 字段或 RTSP URL 存在就等于已拉流。
- 面试表达：“这是 realtime contract preview，不是实时分析实现。”
- 追问方向：延迟；背压；重连；GPU；流协议。

## 第十七章：交付、验证与安全

### K68 Docker Compose 本地交付

- 概念：用容器定义后端和前端的本地可复现启动方式。
- 为什么重要：降低演示环境差异并固定启动顺序。
- 原理：backend image 安装 Python 依赖、升级 DB、跑 Uvicorn；frontend Node 容器跑 Vite dev。
- SmartTraffic 实现：两个服务，挂载 videos/models/results/evals/samples，CPU 默认。
- 证据：`backend/Dockerfile`、`docker-compose.yml`。
- 真实调用链：compose up → Alembic → backend readiness → frontend dev server → API。
- 优点：本地启动直观，数据目录外置。
- 缺点：无 Nginx、worker、Postgres、Redis、GPU 和生产镜像前端。
- 替代方案：production multi-stage image、Kubernetes/Compose profiles。
- 当前限制：前端容器每次 `npm ci` 且运行 dev server。
- 常见误区：Compose 能启动就等于 production-ready。
- 面试表达：“Compose 是本地交付，不是高可用部署架构。”
- 追问方向：镜像体积；healthcheck；GPU；volume 权限。

### K69 自动化验证结构与证据

- 概念：用单元、API/集成、契约、构建和配置检查降低回归。
- 为什么重要：面试中的“做完”要有可重复验证标准。
- 原理：后端临时 SQLite 隔离；前端 Node tests；TypeScript build；Compose/danger gate。
- SmartTraffic 实现：487 后端、90 前端，本次全部通过；4 条 Starlette deprecation warning。
- 证据：`backend/tests/`、`frontend/tests/`、`Makefile`、本次输出。
- 真实调用链：pytest fixture → temp DB → API/service assertions；Node → utility/source contracts。
- 优点：领域规则、几何、API、artifact 和指标覆盖广。
- 缺点：无 CI、浏览器 E2E、真实模型/RTSP、负载和容灾测试。
- 替代方案：GitHub Actions + Playwright + GPU nightly + benchmark suite。
- 当前限制：测试通过主要证明代码契约，不证明业务泛化与生产容量。
- 常见误区：487 个测试等于 487 个端到端用户场景。
- 面试表达：“Verified 是本机当前 HEAD 的测试结论，生产部分仍 Not Verified。”
- 追问方向：测试金字塔；flaky；fixture；CI gate。

### K70 身份、权限与数据安全边界

- 概念：认证确认“你是谁”，授权确认“你能做什么”，审计确认“做过什么”。
- 为什么重要：交通视频与复核动作可能涉及敏感数据和高风险决策。
- 原理：强身份 token、RBAC/ABAC、租户隔离、不可抵赖审计、secret 管理。
- SmartTraffic 实现：默认 permissive；strict 仅检查未验证 actor/role headers；错误做关键词脱敏。
- 证据：`backend/app/core/identity.py`、`docs/security_ops.md`、`.env.example`。
- 真实调用链：headers → identity helper → permission check/bypass → route → logger audit。
- 优点：已有权限契约和本地开发开关。
- 缺点：不是认证；header 可伪造；审计只是应用日志。
- 替代方案：OIDC/JWT + policy engine + append-only audit store + KMS。
- 当前限制：无多租户、加密/保留策略和合规流程。
- 常见误区：strict 模式等于安全登录系统。
- 面试表达：“当前只有授权接口预览，生产必须先接可信身份。”
- 追问方向：JWT 验签；RBAC；视频隐私；secret rotation。

## 第十八章：性能与生产化

### K71 性能、并发与容量瓶颈

- 概念：视频解码、逐帧推理、跟踪、二次渲染、文件/DB 双写共同决定吞吐。
- 为什么重要：单视频可运行不代表多视频并发可承载。
- 原理：总时延近似各 stage 累加；同步 worker 和共享 CPU/GPU 构成队头阻塞。
- SmartTraffic 实现：逐帧 `detect_batch`、同步 process、SQLite、本地 MP4 重编码。
- 证据：CV/service 实现与 Compose CPU 配置；无 benchmark 文件。
- 真实调用链：HTTP worker → decode → inference → artifacts → visual second pass → response。
- 优点：路径简单，易 profile。
- 缺点：无资源队列、batch、缓存、并行 stage 和容量保护。
- 替代方案：异步任务、GPU batching、多级缓存、分片对象存储、预览按需生成。
- 当前限制：没有可引用的吞吐、P95、峰值内存或并发压测数据。
- 常见误区：用视频时长或本机一次耗时推断生产 QPS。
- 面试表达：“我先画 critical path，再用 profiling/benchmark 决定优化，而不虚构性能。”
- 追问方向：CPU/GPU profile；backpressure；batch；容量估算。

### K72 生产化路线与诚实叙事

- 概念：从 MVP 到生产需同时升级执行、存储、安全、评测和运维。
- 为什么重要：架构判断力体现在知道当前边界与优先级，而非罗列技术名词。
- 原理：先定义 SLO/风险，再按单一真相、异步执行、可信身份和可观测性逐步迁移。
- SmartTraffic 实现：当前提供清晰模块边界、run contract、质量闭环和测试基线作为演进基础。
- 证据：全仓库调用链、已验证测试、已知限制清单。
- 真实调用链：现状审计 → risk ranking → async worker/storage/auth/observability → benchmark gate。
- 优点：路线与真实缺口对应，避免过度设计。
- 缺点：需要业务优先级、预算、数据和团队信息才能落地。
- 替代方案：重写为云原生平台；或保持本地工具并限定使用范围。
- 当前限制：个人角色、周期、规模和收益必须 `【本人待补充】`。
- 常见误区：把未来架构说成当前已实现，或用“大模型/微服务”掩盖基础缺口。
- 面试表达：“我先讲 Verified 的当前能力，再讲按风险排序的生产化方案。”
- 追问方向：第一阶段交付；数据迁移；回滚；成本；团队协作。

## 第十九章：Python 与 FastAPI 基础

### K73 类型注解、dataclass、Enum/Literal 与验证边界

- 概念：类型注解描述预期类型，`dataclass` 生成数据容器样板，`Enum`/`Literal` 收窄允许值；Pydantic 才会在 API 边界执行运行时解析与部分校验。
- 为什么重要：静态可读性、编辑器检查和运行时信任边界不能混为一谈。
- 原理：Python 注解默认不阻止错误对象进入函数；`Literal` 主要服务静态检查，FastAPI 通过 Pydantic 才把 schema 应用于请求。
- SmartTraffic 实现：`Settings` 和多个 service config 使用 frozen dataclass；schema 用 `Literal` 限制 review、bad-case、evaluation 等状态，ORM 仍以字符串保存。
- 证据：`backend/app/core/config.py`、`backend/app/services/processing_service.py`、`backend/app/schemas/review.py`、`bad_case.py`。
- 真实调用链：JSON request → Pydantic schema → typed route argument → service/dataclass → ORM/JSON artifact。
- 优点：契约清晰、补全友好、状态拼写错误更早暴露。
- 缺点：注解可被绕过；`Literal` 不等于数据库约束；dataclass 不自动验证业务语义。
- 替代方案：运行时 `Enum`、Pydantic model、数据库 CHECK constraint、mypy/pyright。
- 当前限制：前端 `as T` 没有运行时 schema；后端部分复杂 JSON 仍由服务层手工解释。
- 常见误区：看到 `str | None` 或 `Literal` 就认为任意调用路径都会自动拒绝坏值。
- 面试表达：“注解负责表达，Pydantic 负责 API 解析，业务规则和持久化约束还要在各自边界验证。”
- 追问方向：dataclass vs Pydantic；Enum vs Literal；静态检查；DB constraint。

### K74 FastAPI 应用工厂与 APIRouter

- 概念：应用工厂集中创建 FastAPI 实例、middleware、异常处理和路由；`APIRouter` 按资源拆分端点。
- 为什么重要：启动配置与业务路由解耦后，测试、替换依赖和模块演进更可控。
- 原理：`create_app()` 每次可构造独立应用对象，`include_router()` 将模块路由注册到统一 ASGI app。
- SmartTraffic 实现：`create_app()` 安装 request logging、exception handlers、CORS，并注册 health、videos、analysis、review、evaluation 等 17 组 router。
- 证据：`backend/app/main.py`、`backend/app/core/errors.py`、`backend/app/api/`。
- 真实调用链：Uvicorn import → `create_app()` → middleware/handlers/router registration → request route。
- 优点：入口清楚，路由按领域拆分，`TestClient` 可复用同一契约。
- 缺点：当前模块导入仍共享部分缓存/全局对象，不是完全隔离容器。
- 替代方案：单文件 app、class-based container、其他 ASGI framework。
- 当前限制：没有 lifespan 资源治理、API versioning 和自动生成 client 的发布流程。
- 常见误区：把应用工厂等同于微服务，或认为 router 数量代表功能质量。
- 面试表达：“工厂负责装配，router 负责 HTTP 资源边界，service 承担业务编排。”
- 追问方向：lifespan；middleware 顺序；dependency override；OpenAPI 分组。

### K75 Depends 与 Session 生命周期

- 概念：FastAPI `Depends` 在请求范围解析依赖；yield dependency 可在响应后执行清理。
- 为什么重要：数据库 Session 若泄漏、跨请求共享或事务归属不清，会造成连接与一致性问题。
- 原理：`get_db()` 创建 Session，`yield` 给 route，`finally` 关闭；关闭资源不等于自动 commit 或 rollback 业务事务。
- SmartTraffic 实现：`get_db` 使用 `SessionLocal()`；repository 多做 `flush/refresh`，route/CLI 决定 commit，失败路径显式 rollback 或状态提交。
- 证据：`backend/app/db/session.py`、`backend/app/repositories/`、`backend/app/api/videos.py`。
- 真实调用链：request → `Depends(get_db)` → Session → repository/service → route commit/rollback → dependency close。
- 优点：每请求独立 Session，测试可以 dependency override。
- 缺点：事务分散在 route；文件写入不受 Session rollback 控制。
- 替代方案：Unit of Work、transaction middleware、async SQLAlchemy session。
- 当前限制：SQLite + sync Session；没有跨 worker 的事务协调或 outbox。
- 常见误区：认为 `yield db` 会在请求成功时自动提交，或 `flush` 等于 commit。
- 面试表达：“Depends 管生命周期，不替业务决定事务；commit/rollback 仍是调用方责任。”
- 追问方向：request scope；streaming response；nested transaction；测试 override。

### K76 同步、异步、阻塞 I/O 与 Generator

- 概念：`async def` 只有在等待可让出控制权的 async I/O 时才提升并发；generator 用 `yield` 惰性地产生元素。
- 为什么重要：视频解码、模型推理、同步 SQLAlchemy 和编码都可能阻塞事件循环或占住 worker。
- 原理：把同步函数改名为 `async def` 不会自动把 OpenCV/YOLO 变成非阻塞；generator 降低一次性内存占用，但计算仍在消费者线程执行。
- SmartTraffic 实现：`iter_frames()` 逐帧 `yield` frame/timestamp，process route 仍同步消费并执行 OpenCV、Ultralytics 与 sync DB。
- 证据：`backend/app/cv/frame_reader.py`、`backend/app/services/detection_service.py`、`backend/app/api/videos.py`。
- 真实调用链：HTTP worker → `iter_frames` lazy decode → detector/tracker → artifact/DB → response。
- 优点：逐帧读取避免把完整解码帧集装入内存；同步链易调试。
- 缺点：长任务仍占 worker；generator 不提供队列、重试、取消或背压。
- 替代方案：durable queue + worker、process pool、GPU inference service、受控 async streaming。
- 当前限制：没有独立 worker；请求断开与任务执行生命周期未解耦。
- 常见误区：把 generator 当并行处理，或认为加 `async` 就解决 GPU/OpenCV 阻塞。
- 面试表达：“generator 解决内存遍历方式，worker 解决任务执行与可靠性，两者不是同一问题。”
- 追问方向：event loop；thread/process pool；GIL；取消传播；backpressure。

### K77 Adapter、Mock、Fake、Dry-run、Fallback 与真实 Backend

- 概念：adapter 统一第三方接口；mock 验证交互；fake 是可运行简化实现；dry-run 跳过真实副作用；fallback 在主路径不可用时降级；真实 backend 执行正式能力。
- 为什么重要：这些词决定测试证据与算法能力的强弱，混用会直接导致项目夸大。
- 原理：adapter 不保证背后 provider 存在；fallback 应可观察且受策略约束；mock/fake 的通过不能替代真实模型验收。
- SmartTraffic 实现：`YoloDetector` 是 Ultralytics adapter，默认 dry-run 返回空；`DeepSortTracker` 是 adapter，默认 deterministic fallback；realtime mock 返回固定三帧。
- 证据：`backend/app/cv/yolo_detector.py`、`backend/app/cv/deepsort_tracker.py`、`backend/app/realtime/worker.py`、requirements。
- 真实调用链：config → adapter → real provider（条件满足）或 explicit dry-run/fallback → standardized output。
- 优点：无权重/可选依赖环境也能验证 API、artifact 和状态机。
- 缺点：若生产静默降级，可能返回“成功”却没有真实算法含义。
- 替代方案：启动时强校验 provider、feature flag、依赖注入的 test double、生产 fail-closed。
- 当前限制：真实 DeepSORT 依赖未入 requirements；仓库无正式权重；ByteTrack/BoT-SORT 未实现。
- 常见误区：把 fallback 叫 mock、把 adapter 叫已集成、把 dry-run 测试叫真实准确率测试。
- 面试表达：“当前默认可复现的是 dry-run/fallback 编排，不是正式模型效果；生产应禁止静默降级。”
- 追问方向：contract test；provider health；fail-open/fail-closed；测试金字塔。

## 第二十章：OpenCV 与视频基础

### K78 RGB、BGR 与图像显示

- 概念：RGB 与 BGR 是颜色通道顺序；OpenCV 默认 NumPy frame 为 BGR，浏览器 Canvas/常见图像接口通常按 RGB/RGBA 解释。
- 为什么重要：通道顺序错误不会改变 bbox 坐标，却会让颜色、模型输入或保存结果异常。
- 原理：同一三个通道若按不同顺序解释，红蓝互换；转换常用 `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`。
- SmartTraffic 实现：OpenCV frame 直接传给 Ultralytics adapter和绘制函数，annotated video 由 OpenCV 写出；前端展示视频/overlay，不直接传原始 NumPy frame。
- 证据：`backend/app/cv/frame_reader.py`、`yolo_detector.py`、`video_writer.py`、`frontend/src/components/VideoPlayerWithOverlay.tsx`。
- 真实调用链：VideoCapture BGR frame → YOLO/draw → VideoWriter；浏览器解码 video → Canvas/SVG overlay。
- 优点：保持 OpenCV 原生 BGR 可少一次后端拷贝。
- 缺点：接入 Pillow、Matplotlib 或自定义前端帧接口时容易产生隐式错色。
- 替代方案：在模块边界统一 RGB，并在 adapter 内转换回 provider 需要的格式。
- 当前限制：仓库没有跨库颜色一致性的像素级 golden test。
- 常见误区：认为 JPG/MP4 文件“本身就是 BGR”，或对坐标问题盲目做颜色转换。
- 面试表达：“先确认解码库与消费方的通道约定；SmartTraffic 当前后端主链保持 OpenCV BGR。”
- 追问方向：RGBA；颜色空间；复制成本；模型预处理。

### K79 Frame、FPS、Timestamp 与 Timebase

- 概念：frame index 是离散序号，FPS 是帧率，PTS 是 presentation timestamp；CFR 固定帧间隔，VFR 的真实间隔会变化。
- 为什么重要：驻留、速度、事件容差和前端 seek 都依赖“时间从哪里来”。
- 原理：CFR 可近似 `t = frame_index / FPS`；VFR 应优先使用容器/解码器提供的 timestamp/PTS，而不是假定等间隔。
- SmartTraffic 实现：`iter_frames()` 读取 `CAP_PROP_POS_MSEC`；轨迹优先用 timestamp/FPS 计算 `px/s`，同时保留 frame index 和 `px/frame`。
- 证据：`backend/app/cv/frame_reader.py`、`backend/app/trajectory/engine.py`、`frontend/src/utils/eventTimeline.ts`。
- 真实调用链：VideoCapture → frame index + timestamp_ms → trajectory/event artifact → API → video seek/overlay。
- 优点：同时保存帧和时间便于调试与兼容。
- 缺点：OpenCV 的 timestamp 精度依赖 backend/codec；stride 会改变观测间隔。
- 替代方案：FFmpeg/PyAV 直接读取 stream time_base 与 PTS，规范化为单调时钟。
- 当前限制：没有对 VFR、丢帧、非单调 PTS 的系统验收；拥堵仍主要按连续帧。
- 常见误区：把 FPS 当每帧真实时间，或抽帧后仍用相邻处理帧当 1 frame 时间。
- 面试表达：“帧号适合索引，PTS 适合真实时长；速度和 dwell 应优先使用可靠 timestamp。”
- 追问方向：CFR/VFR；time_base；seek；stride；RTSP jitter。

### K80 Container、Codec、FourCC 与 VideoCapture/VideoWriter

- 概念：MP4/MKV 是 container，H.264/HEVC/MPEG-4 是 codec；FourCC 是 codec/像素格式标识；Capture 解封装解码，Writer 编码封装。
- 为什么重要：扩展名只说明容器候选，不保证内容安全、codec 可用或本机能编码。
- 原理：container 存多路 stream 与时间信息，codec 定义压缩；OpenCV 实际能力取决于其 FFmpeg/GStreamer build。
- SmartTraffic 实现：上传扩展名 allowlist 后由 `VideoCapture` 探测 FPS、尺寸、帧数和 FourCC；`AnnotatedVideoWriter` 默认 `mp4v`。
- 证据：`backend/app/cv/frame_reader.py`、`video_writer.py`、`backend/app/api/videos.py`、视频测试。
- 真实调用链：uploaded bytes → extension/size checks → VideoCapture probe/decode → processing → VideoWriter annotated MP4。
- 优点：OpenCV API 简单，适合本地 MVP 和测试小视频。
- 缺点：metadata 可能不可靠；codec 缺失、损坏帧、尺寸变化或 writer backend 均可失败。
- 替代方案：ffprobe 校验 + FFmpeg transcoding sandbox；对象存储隔离原始与规范化视频。
- 当前限制：没有 MIME/恶意媒体扫描、分块上传、codec 矩阵或跨平台编码验收。
- 常见误区：“文件名是 `.mp4` 所以一定是 H.264 且可安全解码。”
- 面试表达：“扩展名是第一层过滤，真正兼容性要看容器、codec、backend 和实际 probe/decode。”
- 追问方向：FourCC；关键帧；损坏帧；硬件解码；转码策略。

### K81 Resize、Letterbox 与坐标还原

- 概念：resize 直接缩放，letterbox 保持宽高比并填充；模型坐标必须还原到原图，前端还要映射到显示尺寸。
- 为什么重要：任一层忽略 scale/padding，bbox、轨迹、Zone 和点击 seek 都会错位。
- 原理：直接缩放用独立 `scale_x/scale_y`；letterbox 先减 padding 再除统一 scale；overlay 再按视频原尺寸到 DOM 尺寸缩放。
- SmartTraffic 实现：YOLO 前处理、NMS 和结果坐标恢复由 Ultralytics 完成，项目解析 post-NMS `xyxy` 原图坐标；前端 `inferOverlaySize`/mapping 负责显示映射。
- 证据：`backend/app/cv/yolo_detector.py`、`frontend/src/utils/analysisDetailMapping.ts`、`VideoPlayerWithOverlay.tsx`。
- 真实调用链：OpenCV original frame → Ultralytics letterbox/inference/NMS → original-space bbox → artifact/API → display-space overlay。
- 优点：复用成熟 provider，项目不重复实现易错预后处理。
- 缺点：adapter 依赖第三方坐标契约；前端若缺原始尺寸会使用推断值。
- 替代方案：项目显式保存 transform matrix；统一 normalized coordinates。
- 当前限制：没有自研 letterbox/NMS，也没有覆盖所有响应式布局的真实浏览器视觉回归。
- 常见误区：声称 SmartTraffic 自己实现 letterbox/NMS，或把原图坐标直接当 CSS 像素。
- 面试表达：“模型层还原到原图坐标，UI 层再做一次显示坐标映射，两层责任分开。”
- 追问方向：padding；normalized bbox；DPR；object-fit；旋转元数据。

## 第二十一章：YOLO 原理

### K82 One-stage Detection、Bounding Box 与 Confidence

- 概念：YOLO 是 one-stage detector，在密集特征上直接预测类别与框；two-stage 方法先生成 proposal 再分类/回归。bbox 常用 `xyxy`/`xywh`，confidence 是模型排序分数，不是真实世界概率保证。
- 为什么重要：理解输出含义才能正确设阈值、解释误差并避免把分数当确定性事实。
- 原理：单阶段通常延迟低、端到端；最终 score 由具体模型头和训练定义，需校准后才可讨论概率语义。
- SmartTraffic 实现：Ultralytics 返回 post-NMS `xyxy`、class id/name 与 confidence，adapter 再按六类目标过滤。
- 证据：`backend/app/cv/yolo_detector.py::_format_result`、Ultralytics `predict` 调用。
- 真实调用链：frame → Ultralytics YOLO → boxes/conf/classes → target-class filter → detection artifact。
- 优点：适合视频逐帧目标检测，provider 生态成熟。
- 缺点：小目标、遮挡、域偏移和阈值选择会造成漏检/误检。
- 替代方案：Faster R-CNN 等 two-stage、DETR 系列或任务专用 detector。
- 当前限制：仓库无训练代码、正式权重、概率校准或真实场景 benchmark。
- 常见误区：confidence 0.9 等于“90% 一定正确”，或 one-stage 等于“一次只看一帧”。
- 面试表达：“confidence 是用于排序和阈值决策的模型分数，效果必须在目标数据集上校准。”
- 追问方向：one/two-stage；anchor；calibration；class imbalance；small object。

### K83 IoU、NMS 与阈值责任

- 概念：IoU 是两框交并比；NMS 按分数保留框并抑制高重叠候选。
- 为什么重要：confidence threshold 控制候选质量，NMS IoU threshold 控制重复框，两者对 downstream tracking/event 影响不同。
- 原理：`IoU = intersection / union`；经典 NMS 迭代选择最高分框，移除与它 IoU 超阈值的同类候选。
- SmartTraffic 实现：adapter 将 `conf` 与 `iou` 传给 `model.predict`；NMS 由 Ultralytics 执行，项目只解析 post-NMS 结果。
- 证据：`backend/app/cv/yolo_detector.py::detect_frame`、`get_model_info`。
- 真实调用链：raw model candidates → Ultralytics confidence filter/NMS → adapter formatting → tracker。
- 优点：减少重复检测并暴露部署阈值。
- 缺点：拥挤遮挡场景可能互相抑制；过低 threshold 增加 FP 与跟踪负担。
- 替代方案：Soft-NMS、class-agnostic NMS、WBF、end-to-end NMS-free detector。
- 当前限制：项目不保存 raw pre-NMS predictions，无法从 artifact 重放 NMS 策略。
- 常见误区：把 detection IoU threshold 与 tracker matching IoU、evaluation IoU 当成同一个参数。
- 面试表达：“NMS 是 Ultralytics 的责任；项目配置阈值但没有自研该算法。”
- 追问方向：Soft-NMS；拥挤场景；class-aware；threshold sweep。

### K84 Precision、Recall、AP/mAP 与检测误差级联

- 概念：precision 衡量预测中有多少正确，recall 衡量 GT 中找回多少；AP 是 PR 曲线下的面积，mAP 对类别或 IoU 阈值聚合。
- 为什么重要：部署 confidence threshold 的单点结果不能替代整条 PR 曲线，也不能把 AP@0.5 叫 COCO mAP@[.5:.95]。
- 原理：按 score 排序并在指定 IoU matching 下累计 TP/FP 得到 PR；不同评测协议的插值、类别和 IoU 集合不同。
- SmartTraffic 实现：detection evaluation 使用单 IoU=0.5 的轻量 VOC-style AP；漏检会导致断轨/不完整轨迹/事件漏报，误检会生成假 track/假事件/告警误报。
- 证据：`backend/app/analysis/detection_metrics.py`、`backend/tests/test_detection_metrics.py`、tracking/event pipeline。
- 真实调用链：detection scores + GT → AP@0.5；detections → tracker → trajectory → event → alert/evaluation。
- 优点：轻量指标便于验证协议和失败样本格式。
- 缺点：单 IoU、toy data 与自写 evaluator 不足以代表正式模型质量。
- 替代方案：COCO evaluator、分场景 PR/calibration、end-to-end event attribution。
- 当前限制：仓库没有正式 detection GT、权重与可复现 benchmark result。
- 常见误区：toy F1/AP=1 就说准确率 100%，或只优化 detector 而忽略级联影响。
- 面试表达：“先说明评测协议，再报指标；当前只能称 AP@0.5 轻量验证，不能称 COCO mAP。”
- 追问方向：PR tradeoff；AP interpolation；error propagation；threshold calibration。

## 第二十二章：多目标跟踪基础

### K85 Tracking-by-detection 与 Kalman Filter

- 概念：tracking-by-detection 先逐帧检测，再通过运动/外观关联维持 ID；Kalman Filter 用状态转移和观测更新估计位置与速度。
- 为什么重要：检测间歇缺失时，运动预测可维持短期轨迹并缩小关联候选。
- 原理：predict 根据运动模型外推状态与协方差，update 用检测修正；噪声假设和状态设计影响遮挡恢复。
- SmartTraffic 实现：整个跟踪链属于 tracking-by-detection；可选真实 DeepSORT backend 内部可使用 Kalman，但当前 deterministic fallback 只保留最后 bbox 并做贪心匹配，没有 Kalman。
- 证据：`backend/app/cv/deepsort_tracker.py`、`backend/app/services/tracking_service.py`、requirements。
- 真实调用链：detections per frame → real DeepSORT（可选）或 fallback → track states → trajectory。
- 优点：检测器与 tracker 解耦，适配器可替换 backend。
- 缺点：性能上限受 detector 影响；当前 fallback 对遮挡与交叉运动脆弱。
- 替代方案：ByteTrack、BoT-SORT、joint detection and tracking、optical flow 辅助。
- 当前限制：真实 DeepSORT 未形成仓库可复现默认能力；没有保存 motion state/covariance。
- 常见误区：看到类名 `DeepSortTracker` 就断言当前默认路径用了 Kalman。
- 面试表达：“标准 DeepSORT 有 Kalman；当前 fallback 没有，不能把理论原理冒充实现事实。”
- 追问方向：state vector；process noise；gating；occlusion；detector recall。

### K86 Hungarian Algorithm、Cost Matrix 与 ReID

- 概念：Hungarian algorithm 在二分图 cost matrix 上求全局最优一对一匹配；ReID embedding 用外观特征衡量目标身份相似度。
- 为什么重要：局部贪心可能抢占最佳匹配，纯运动匹配又难处理交叉与长遮挡，外观信息可补充但带来偏差和隐私风险。
- 原理：cost 可组合 motion、IoU 与 appearance distance，并用 gating 排除不可能配对；Hungarian 最小化全局总 cost。
- SmartTraffic 实现：可选 `deep-sort-realtime` provider 负责标准关联；当前 fallback 遍历 detection/track 取最佳 IoU/center score，是贪心，不是 Hungarian，也不保存 ReID embedding。
- 证据：`backend/app/cv/deepsort_tracker.py::_match_detection_to_track`、`_load_real_tracker`。
- 真实调用链：tracks × detections → cost/gating（理论真实 backend）或 greedy score（当前 fallback）→ assignment → ID update。
- 优点：Hungarian 避免部分局部冲突；ReID 提升遮挡后身份恢复候选。
- 缺点：全局最优只相对于 cost 定义；ReID 存在域偏移、计算成本、隐私和跨摄像头误关联风险。
- 替代方案：greedy、min-cost flow、learned association、IoU-only tracker。
- 当前限制：artifact 不含 embedding；没有跨摄像头 ID 或 ReID 质量评测。
- 常见误区：Hungarian 自动保证正确 ID，或把 appearance embedding 当人脸识别同义词。
- 面试表达：“关联质量取决于 cost 与 gating；当前 fallback 是确定性贪心，没有 Hungarian/ReID。”
- 追问方向：cost normalization；gating；privacy；cross-camera；complexity。

### K87 ID Switch、Fragmentation、MOTA/IDF1/HOTA 与 Tracker 比较

- 概念：ID switch 是同一 GT 身份的预测 ID 改变，fragmentation 是轨迹中断；MOTA 偏检测错误聚合，IDF1 偏身份一致性，HOTA 平衡 detection/association。
- 为什么重要：一个 tracker 可能框得准却 ID 不稳，不同指标和场景会给出不同结论。
- 原理：标准 MOT 评测需要跨帧 GT association 与严格匹配；DeepSORT 强调 Kalman+appearance，ByteTrack 利用高低分检测，BoT-SORT 融合运动、外观及相机运动补偿等策略。
- SmartTraffic 实现：tracking evaluation 是帧内贪心 IoU 的轻量 IDF1/MOTA/ID switch/lost-segment 近似；当前代码没有 ByteTrack 或 BoT-SORT，比较仅属知识与未来选型。
- 证据：`backend/app/analysis/tracking_metrics.py`、`backend/tests/test_tracking_metrics.py`、CV tracker 文件。
- 真实调用链：tracking expected + actual → lightweight matcher → approximate metrics；生产候选需统一 TrackEval protocol 对比。
- 优点：当前实现可验证数据契约并暴露部分失败类型。
- 缺点：不是官方 TrackEval/HOTA，无法公平证明 tracker 优劣。
- 替代方案：MOTChallenge 格式 + TrackEval，同一 detector/数据/阈值/硬件下比较 DeepSORT、ByteTrack、BoT-SORT。
- 当前限制：无正式 MOT GT、真实 backend 锁定或 HOTA 结果。
- 常见误区：把理论比较写成已实现三种 tracker，或只看 MOTA 忽略 IDF1/HOTA。
- 面试表达：“当前只做轻量契约评测；tracker 选型必须在同一检测输入与官方协议下比较。”
- 追问方向：metric tradeoff；low-score association；camera motion；fair benchmark。

## 第二十三章：React 与前端工程

### K88 React State、Effect、Polling 与 Stale Response

- 概念：state 驱动渲染，effect 同步外部系统；polling 周期请求状态，stale response 是旧请求晚到后覆盖新状态。
- 为什么重要：run 切换、组件卸载和网络延迟会产生竞态、重复请求与内存泄漏式更新。
- 原理：effect cleanup 取消 timer/请求；`AbortController` 或 request token 防止过期响应提交；polling 要有 completed/failed/cancelled 停止条件和退避。
- SmartTraffic 实现：页面用 `useState/useEffect` 加载 run、事件、评测等数据；当前处理同步返回，未实现通用 polling、AbortController 或 stale-response guard。
- 证据：`frontend/src/pages/AnalysisDetailPage.tsx`、`VideoCenterPage.tsx`、`frontend/src/api/client.ts`。
- 真实调用链：selected run state → effect → API promises → state update → render；目标态才是 task polling。
- 优点：当前数据流直接，适合本地同步 MVP。
- 缺点：快速切换 run 时旧响应可能覆盖新选择；长期任务没有自动状态刷新。
- 替代方案：SWR/React Query、AbortController、sequence id、SSE/WebSocket。
- 当前限制：不能声称已有稳健 polling 或实时 push；API client 也没有 retry/abort。
- 常见误区：依赖数组为空就一定安全，或 `async` response 一定按发出顺序返回。
- 面试表达：“当前是 effect 驱动的一次加载；异步任务化后必须补取消、过期响应保护和停止条件。”
- 追问方向：cleanup；race condition；SSE vs polling；cache key；backoff。

### K89 Loading/Error/Empty 与编译时/运行时类型

- 概念：loading、error、empty 是不同 UI 状态；TypeScript 类型在编译后消失，`as T` 不会验证 JSON。
- 为什么重要：dry-run 的合法空数组不能显示成系统错误，后端错误也不能伪装成“暂无数据”；坏响应必须在运行时被识别。
- 原理：用显式状态机或 discriminated union 表达请求状态；在信任边界用 schema parser 校验 unknown JSON。
- SmartTraffic 实现：多个页面分别渲染 loading/error/empty；`apiGet<T>` 等直接将 `response.json()` cast 为 `T`，没有 Zod/OpenAPI runtime validation。
- 证据：`frontend/src/pages/DashboardPage.tsx`、`AnalysisDetailPage.tsx`、`frontend/src/api/client.ts`。
- 真实调用链：fetch → HTTP status check → unchecked JSON cast → page state → loading/error/empty/result branch。
- 优点：已有基本三态，dry-run 空结果可被解释。
- 缺点：状态变量分散；响应字段变化可能在深层渲染才暴露。
- 替代方案：OpenAPI generated client + runtime schema、Zod、React Query state machine。
- 当前限制：没有统一 error boundary、运行时响应 schema 或浏览器 E2E。
- 常见误区：empty 就是失败，或 TypeScript interface 能阻止服务端返回坏 JSON。
- 面试表达：“空是有效业务状态，错是契约/请求失败；`as T` 只让编译器相信，不会校验运行时。”
- 追问方向：unknown vs any；schema evolution；error boundary；accessibility live region。

## 第二十四章：测试体系

### K90 Pytest Fixture、隔离与测试层级

- 概念：fixture 提供可复用前置/清理；unit 隔离函数，API integration 穿过路由/依赖/DB，browser E2E 验证真实浏览器与系统协作。
- 为什么重要：不同层证明不同强度，数量不能替代真实边界覆盖。
- 原理：测试应隔离状态与副作用，依赖覆盖把生产 DB 替换为临时实例；越接近真实系统越慢但能发现更多集成问题。
- SmartTraffic 实现：autouse fixture 用 `tmp_path` SQLite 创建 schema并 override `get_db`；现有测试以 unit、API、artifact/源码契约为主。
- 证据：`backend/tests/conftest.py`、`backend/tests/test_db_foundation.py`、`frontend/tests/`。
- 真实调用链：pytest fixture → temp SQLite/dependency override → TestClient/service → assertion → cleanup。
- 优点：避免污染真实 `smarttraffic.db`，测试可重复且失败定位快。
- 缺点：SQLite 测试不能代表 PostgreSQL、并发、浏览器、GPU 或 RTSP。
- 替代方案：Testcontainers、Playwright/Cypress、真实 provider integration environment。
- 当前限制：没有真实浏览器系统 E2E、CI、GPU/真实 YOLO/DeepSORT 或流媒体验收。
- 常见误区：把 TestClient API 测试叫端到端，或把 487/90 数量当质量结论。
- 面试表达：“我先说测试层级和隔离范围，再说它没证明什么。”
- 追问方向：fixture scope；transaction rollback；parallel tests；contract/E2E pyramid。

### K91 Golden Video、Real-model Acceptance 与 Benchmark Leakage

- 概念：golden acceptance 固定代码/容器、权重、输入与期望；benchmark leakage 是 test 信息泄漏进训练、调参或选择过程；toy dataset 只验证逻辑。
- 为什么重要：mock/dry-run 可以证明编排，却不能证明真实 detector/tracker/event 效果。
- 原理：可复现验收需版本化输入与 GT、隔离 final test、记录 checksum/环境，并对 detection/tracking/event 分层归因。
- SmartTraffic 实现：仓库跟踪少量 toy expected JSON，权重、真实视频和结果被忽略；本机 ignored 结果不能作为正式 benchmark。
- 证据：`evals/expected/`、`.gitignore`、`backend/app/analysis/*_metrics.py`、现有评测测试。
- 真实调用链：fixed container + checksumed weights/video → full pipeline → detection/MOT/event GT → standard evaluator → archived result。
- 优点：golden 集能发现 provider、codec、阈值和级联回归。
- 缺点：维护成本高；场景过窄会过拟合；含隐私视频需授权治理。
- 替代方案：分层 synthetic/unit fixtures + 独立真实 acceptance set + shadow production monitoring。
- 当前限制：没有仓库可复现的 real-model golden video acceptance。
- 常见误区：toy F1=1 或本机一次成功等于生产准确率，或用 mock 取代 provider 验收。
- 面试表达：“toy 验证 evaluator，golden 验证固定真实链路，独立 test set 才能支持泛化结论。”
- 追问方向：data split；checksum；flaky tolerance；privacy；leakage detection。

## 第二十五章：生产系统设计

### K92 RTSP Ingest 与 FFmpeg/GStreamer

- 概念：RTSP 是会话/传输控制协议，FFmpeg/GStreamer 提供解封装、解码、buffer、重连和 pipeline 能力。
- 为什么重要：真实流会出现断线、抖动、时间戳异常、codec 变化和读取速度与处理速度不匹配。
- 原理：ingest 独立维护连接与 jitter buffer，把解码帧通过有界队列交给分析；超载时必须定义丢帧、降采样或拒绝策略。
- SmartTraffic 实现：当前 realtime worker 对 RTSP 明确返回未连接，只有 mock 三帧和 file 路径检查；以下均为生产演进知识。
- 证据：`backend/app/realtime/worker.py`、`backend/app/services/realtime_service.py`、`docs/realtime.md`。
- 真实调用链：当前 camera preview contract → RTSP not connected；目标态 RTSP → FFmpeg/GStreamer → bounded buffer → worker。
- 优点：专用媒体工具比同步 `VideoCapture` 更适合协议、重连和 timestamp 治理。
- 缺点：部署、codec、硬件解码、网络和安全运维复杂。
- 替代方案：边缘 NVR 拉流、WebRTC gateway、托管媒体服务。
- 当前限制：无真实 RTSP 连接、持续推理、soak test 或密钥轮换。
- 常见误区：有 Camera 页面和 RTSP URL 字段就等于已实时拉流。
- 面试表达：“当前只验证 preview contract；生产第一步是单路 RTSP 稳定 ingest，而不是直接承诺多路实时。”
- 追问方向：TCP/UDP；reconnect；jitter；PTS；frame dropping；secret manager。

### K93 Durable Job、Queue、Worker 与任务生命周期

- 概念：durable job 持久化任务意图，queue 分发，worker 执行；heartbeat/lease 检测失联，retry/cancel/idempotency 管理失败与重复。
- 为什么重要：视频任务长、昂贵且会部分写入，不能依赖 HTTP 连接或进程内状态保证完成。
- 原理：API 先提交 job/outbox，再由 worker at-least-once 消费；幂等键、状态机与 artifact publish/reconciliation 处理重复和部分失败。
- SmartTraffic 实现：当前 `ProcessingTask` 只是同步请求内的状态记录，没有 durable worker、queue、retry、cancel 或 heartbeat；本知识点是目标态设计。
- 证据：`backend/app/api/videos.py`、processing schemas/models、`docker-compose.yml` 无 queue/worker service。
- 真实调用链：当前 request → processing inline；目标态 API → job/outbox → queue → worker lease/heartbeat → staged artifact → commit/publish。
- 优点：请求与执行解耦，可恢复、扩容、限流和观测。
- 缺点：引入重复投递、状态竞争、补偿和运维复杂度。
- 替代方案：数据库任务表轮询、云任务服务、workflow engine。
- 当前限制：不能声称已有 Celery/Redis/worker 或 exactly-once。
- 常见误区：数据库有 `ProcessingTask` 就是异步系统，或 retry 可以不做幂等。
- 面试表达：“目标是 at-least-once + idempotency + reconciliation，不追求口头上的 exactly-once。”
- 追问方向：lease；poison job；retry policy；cancel token；outbox；artifact atomic publish。

### K94 GPU Worker Pool、Backpressure、存储与多摄像头拓扑

- 概念：GPU pool 管理显存与模型实例；backpressure 在输入超过处理能力时限制、排队或降级；生产存储通常以 PostgreSQL 管元数据、对象存储管大文件，并可采用边缘 ingest/中心编排。
- 为什么重要：多路摄像头如果无容量保护会造成队列无限增长、OOM、延迟失控和本地盘不一致。
- 原理：按模型/显存调度 worker，设置有界队列和 admission control；元数据保存对象 version/checksum，边缘处理网络敏感帧，中心汇总事件与治理。
- SmartTraffic 实现：当前默认 CPU、SQLite、本地 artifacts、单机同步请求；没有 GPU pool、对象存储、多摄像头调度，以下为生产目标态。
- 证据：`docker-compose.yml`、`backend/app/core/config.py`、本地 path 与 DB 配置。
- 真实调用链：目标态 cameras/edge → ingest buffer → scheduler → GPU workers → object storage + PostgreSQL → events/review。
- 优点：资源可控、artifact 可扩展、故障域与数据流更清晰。
- 缺点：成本、调度、网络、数据驻留和跨源一致性显著增加。
- 替代方案：每摄像头边缘盒、共享推理服务、serverless batch inference。
- 当前限制：没有容量数据，不能承诺摄像头路数、QPS、P95 或 GPU 利用率。
- 常见误区：加 GPU 就自动实时，或把 DB 与对象存储双写称为强一致单一真相。
- 面试表达：“先用 benchmark 定义单 worker 容量，再用有界队列、准入和降级保护 SLO。”
- 追问方向：batching；model warmup；fair scheduling；edge/cloud；object version；reconciliation。

### K95 SLO、RPO、RTO、监控与灾备

- 概念：SLO 定义可用性/延迟/正确性目标；RPO 是可容忍数据丢失窗口，RTO 是可容忍恢复时间。
- 为什么重要：没有目标就无法决定队列、备份、冗余、监控和恢复演练投入。
- 原理：从用户旅程定义 SLI 与 error budget；按 RPO/RTO 设计备份、复制、恢复顺序，并通过演练验证而非只写文档。
- SmartTraffic 实现：当前只有 request ID、日志、readiness `SELECT 1` 和本地文件/SQLite；无正式 SLO、metrics、灾备或恢复演练。
- 证据：`backend/app/core/logging.py`、health API、`docs/security_ops.md`、Compose。
- 真实调用链：当前 request/log/readiness；目标态 metrics/traces/logs → alerts/runbook → backup/restore/reconciliation exercise。
- 优点：把“高可用”转成可测指标与响应流程。
- 缺点：指标、冗余和演练有持续成本，错误 SLO 会驱动错误架构。
- 替代方案：若继续作为本地工具，明确较低 SLO 并优先可靠导出/备份而非 HA。
- 当前限制：没有生产流量、on-call、RPO/RTO 数值或灾备证据。
- 常见误区：readiness 通过等于服务健康，备份存在等于能够恢复。
- 面试表达：“先定义 SLO/RPO/RTO，再用监控和恢复演练证明，而不是先堆 HA 名词。”
- 追问方向：SLI；error budget；backup consistency；restore order；chaos exercise。

## 岗位复习路线

### 第一轮必学

K01–K12、K17–K42、K52、K55–K66，以及新增基础中的 K73–K77、K79、K82–K87、K90–K95。第一轮目标是能同时讲清当前调用链、证据强度和生产边界。

### CV 岗专项

K14–K30、K35–K42、K59–K63、K78–K87。重点覆盖 YOLO、tracking、trajectory、geometry、six events、evaluation 和 detection → tracking → event 的误差传播。

### 后端专项

K03、K05–K12、K46–K52、K64–K72、K73–K77、K90、K93–K95。重点覆盖 FastAPI、Session、API、artifact、transaction、worker、consistency 与 reporting。

### 全栈专项

K05–K08、K52–K54、K64–K66、K74、K78–K81、K88–K90。重点覆盖 React、API client、overlay、polling、download、runtime validation 与 error states。

### 系统设计专项

K06、K12、K49–K51、K67–K72、K77、K91–K95。重点覆盖 RTSP、queue、GPU worker、storage、multi-camera、SLO、security、RPO/RTO 与灾备。
