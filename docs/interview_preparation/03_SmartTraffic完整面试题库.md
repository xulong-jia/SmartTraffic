# SmartTraffic 完整面试题库

> 审计基线：`main@5616945`。共 150 道不重复问题；Q001–Q045 为完整答题模板，Q046–Q150 为紧凑深挖模板。回答中的个人经历、团队、周期、数据规模和业务结果必须使用 `【本人待补充】` 后再按真实情况填写。

## 使用方法

- 先练 Q001–Q015，保证项目定位和算法边界不失真；
- 再按岗位选择 CV、后端、全栈、质量方向题；
- 每个回答先给结论，再给调用链、证据、取舍和限制；
- 压力题不要防御，主动承认当前边界并给出验证或演进方案；
- 不背路径清单，要能从入口讲到输出和测试。

## 第一部分：核心题完整模板（Q001–Q045）

### Q001 请用 30 秒介绍 SmartTraffic

- 类别：项目定位。
- 问题：请用 30 秒介绍 SmartTraffic。
- 考察点：能否快速讲清问题、方案、技术和边界。
- 30 秒回答：SmartTraffic 是本地交通视频分析与质量闭环平台，以 analysis run 串起视频上传、YOLO 检测、跟踪、轨迹、六类规则事件、告警、复核、坏例、评测和报告。后端用 FastAPI/SQLAlchemy/OpenCV/Ultralytics，前端用 React/TypeScript。当前 487 个后端和 90 个前端测试通过，但默认模型与 tracker 是 dry-run/fallback，RTSP 预览也是占位，所以它是验证平台，不是生产执法系统。
- 90 秒回答：补充 run 的 config snapshot、manifest、event/evidence/execution、DB-first/artifact fallback 与 Review→BadCase→Evaluation 闭环，并说明同步处理、SQLite、本地文件和弱认证是生产边界。
- 深挖回答：真正差异不是 YOLO bbox，而是算法结果如何被解释、复核、再评测和报告；成熟度应分当前实现、测试覆盖、契约预留、未来能力。
- 常见追问：目标用户是谁；与普通 YOLO demo 有什么不同；为什么不是生产系统。
- 证据：`README.md`、`backend/app/api/videos.py`、`frontend/src/pages/`、测试目录。
- 易错点：说成实时 RTSP、生产上线、自研 YOLO 或准确率 100%。
- 事实边界：真实用户、个人贡献、业务指标为 `【本人待补充】`。

### Q002 这个项目解决的核心问题是什么

- 类别：产品与业务。
- 问题：检测车辆已有成熟模型，为什么还要做这个项目？
- 考察点：能否从模型能力上升到系统价值。
- 30 秒回答：核心问题不是“能不能框出车”，而是一次分析能否复现、事件为什么命中、谁复核过、错误如何沉淀、指标怎么计算、报告如何回到证据。SmartTraffic 用 run、artifact、规则证据和质量闭环解决这些断点。
- 90 秒回答：从配置快照、轨迹/事件中间产物、告警处置、人工漏报、Bad Case、六类评测和报告逐层说明；强调这些链路均有当前代码入口和测试，但没有外部业务收益证据。
- 深挖回答：算法服务化的关键是 provenance、human-in-the-loop 与 feedback assetization，而不是堆页面；当前实现仍缺数据版本和自动训练反馈。
- 常见追问：目标用户；怎样衡量价值；为何不用现成平台。
- 证据：`backend/app/models/analysis.py`、`backend/app/models/event.py`、Review/BadCase/Evaluation/Report services。
- 易错点：虚构客户、节省多少人力或线上告警效果。
- 事实边界：用户研究与 ROI 为 `【本人待补充】`。

### Q003 请画出总体架构

- 类别：系统架构。
- 问题：SmartTraffic 的总体架构和模块边界是什么？
- 考察点：能否讲清数据流而非只背技术栈。
- 30 秒回答：React UI 调 FastAPI；process 路由同步串联 detector、tracker、trajectory、event、alert 和 artifact builder；结果写 SQLite 与 run 文件；Analysis 统一读取，Review/BadCase/Evaluation/Report 在结果之上形成质量闭环。
- 90 秒回答：补充 17 组路由、10 个页面、21 个 ORM、87 个端点；说明 realtime 是独立占位契约，顶层 detections 也是预留。
- 深挖回答：主路径是 layered pipeline，业务中心是 run read model；当前 DB/文件双源和同步请求是最重要的架构债。
- 常见追问：为什么不微服务；为何同时用 DB 和文件；模块如何替换。
- 证据：`backend/app/main.py`、`api/`、`services/`、`frontend/src/App.tsx`。
- 易错点：画出不存在的 Redis、Celery、Nginx、Kafka 或 Kubernetes。
- 事实边界：只画当前实现；未来架构用虚线或明确称规划。

### Q004 完整视频处理调用链是什么

- 类别：核心调用链。
- 问题：从用户点击处理到页面看到结果，逐步发生什么？
- 考察点：是否真正读过入口、事务和输出。
- 30 秒回答：Video Center 调 `POST /api/videos/{id}/process`，路由创建 task 并标 running，按模式执行 detector/tracker/trajectory，完整模式再跑 rules、alerts 和 visual artifacts；随后创建 run、导入 DB、提交事务，Analysis page 通过 run 子资源读取。
- 90 秒回答：补充三种 mode、run 新 ID、config snapshot、CSV/JSONL/manifest/keyframe/annotated video，以及失败时 task/video 状态和非原子文件残留。
- 深挖回答：task 只是状态记录，执行仍在 HTTP worker；DB commit 不能回滚已写文件，生产需要异步任务与补偿。
- 常见追问：失败如何处理；是否可重试；rerun 是否覆盖旧结果。
- 证据：`backend/app/api/videos.py`、processing/tracking/artifact services。
- 易错点：说任务进入消息队列或后台 worker。
- 事实边界：没有 cancel、retry、backpressure、幂等键。

### Q005 为什么以 Analysis Run 为核心

- 类别：领域建模。
- 问题：为什么不直接把所有结果挂在 Video 上？
- 考察点：对可复现、版本与聚合边界的理解。
- 30 秒回答：同一视频可用不同模型、阈值、stride、zone 和 rule 多次处理。run 为每次执行提供独立 ID、状态、配置快照和 artifact 目录，避免覆盖旧结果并支持对比、复核和报告。
- 90 秒回答：区分 video、processing task、run、evaluation run；解释 ModelRun 和各结果实体如何引用 run。
- 深挖回答：当前 run 尚未绑定输入/模型/artifact checksum，因此是参数级可追溯而非完全可复现。
- 常见追问：如何保证幂等；如何清理旧 run；如何 pin 正式版本。
- 证据：`backend/app/models/analysis.py`、`backend/app/models/model_run.py`、traffic analysis service。
- 易错点：把 task ID 当 run ID，或声称同配置自动去重。
- 事实边界：rerun 创建新 ID，旧结果保留。

### Q006 为什么处理是同步的，问题是什么

- 类别：后端架构。
- 问题：为什么没有 Celery，当前同步方式能撑住吗？
- 考察点：能否解释 MVP 取舍与生产改造。
- 30 秒回答：同步实现让本地 MVP 的调用链、错误和测试更直接，但视频解码、推理、artifact 和重编码会占住 Uvicorn worker，缺超时、取消、重试和背压，不能按生产并发承诺。
- 90 秒回答：说明 task 状态并非异步执行；给出任务表/outbox、队列、CPU/GPU worker、幂等键、heartbeat、cancel token、retry policy 的迁移顺序。
- 深挖回答：DB 写入、对象存储发布与任务 ACK 需设计 at-least-once 下的幂等，而不是追求虚假的 exactly-once。
- 常见追问：队列选型；重复任务；worker 崩溃；优先级。
- 证据：`backend/app/api/videos.py`、`backend/app/schemas/processing.py`、Compose 无 queue service。
- 易错点：因为有 `ProcessingTask` 就说已有异步 worker。
- 事实边界：当前并发容量未压测。

### Q007 87 个 API 如何组织

- 类别：API 设计。
- 问题：接口很多，怎样保持边界一致？
- 考察点：资源建模、契约成熟度和可维护性。
- 30 秒回答：17 个 `APIRouter` 按 videos、analysis-runs、events、alerts、review、evaluation 等资源拆分，由应用工厂统一注册；run 结果主要作为 analysis-run 子资源读取。
- 90 秒回答：解释 Pydantic schema、repository/service、统一 error/request ID；指出顶层 detections 返回 contract-only，不能把所有端点看成同等成熟。
- 深挖回答：未来应增加 API versioning、OpenAPI generated client、runtime schema、pagination 和兼容性测试。
- 常见追问：为什么不是 GraphQL；如何处理 breaking change；错误码。
- 证据：`backend/app/main.py`、`backend/app/api/`、`schemas/`。
- 易错点：把端点数量当功能数量或质量证明。
- 事实边界：没有正式 API version prefix/发布策略。

### Q008 前端为什么没用 React Router

- 类别：前端架构。
- 问题：十个页面如何路由，为什么这样设计？
- 考察点：依赖取舍与扩展边界。
- 30 秒回答：`App.tsx` 用 `window.history.pushState` 和 `popstate` 管理路径，MVP 依赖少、逻辑直观；但嵌套参数、404、守卫、数据 loader 和类型安全较弱，规模扩大应迁移到成熟 router。
- 90 秒回答：列出十页，说明 page 直接通过 API client 加载；指出 static `as T` 不做运行时响应验证。
- 深挖回答：迁移时先建立 route config 和 URL state contract，再处理深链接、query schema、错误边界和权限。
- 常见追问：刷新是否丢状态；如何传 run ID；如何测路由。
- 证据：`frontend/src/App.tsx`、`frontend/src/api/client.ts`、pages。
- 易错点：声称用了 React Router 或前端有 E2E。
- 事实边界：90 个前端测试主要不是浏览器 E2E。

### Q009 视频上传有什么安全风险

- 类别：输入安全。
- 问题：上传接口是否安全，怎样生产化？
- 考察点：信任边界、资源限制和数据治理。
- 30 秒回答：当前有 basename、扩展名、200 MB、600 秒和 codec 校验，失败会清理；但整文件读入内存、同名覆盖、无 MIME/病毒扫描、认证、配额和对象存储隔离，只适合本地 MVP。
- 90 秒回答：生产改为预签名分块上传、内容哈希、隔离 bucket、异步 AV/ffprobe 扫描、配额、保留策略和可信身份，状态从 uploading 到 scanned/ready/rejected。
- 深挖回答：仅检查扩展名不是内容验证；解码器本身也是攻击面，扫描进程需沙箱与资源上限。
- 常见追问：路径穿越；大文件；重复文件；上传中断。
- 证据：`backend/app/api/videos.py`、`.env.example`。
- 易错点：说当前已流式写入或有病毒扫描。
- 事实边界：本机视频不等于公开安全数据集。

### Q010 YOLO 检测是怎么实现的

- 类别：计算机视觉。
- 问题：从一帧到 detection contract 的过程是什么？
- 考察点：第三方库边界和参数理解。
- 30 秒回答：`YoloDetector` 懒加载 Ultralytics `YOLO`，把 frame、conf、IoU、imgsz、device 传给 `predict`，解析 post-NMS boxes 的 xyxy、class 和 confidence，再按交通目标类过滤。
- 90 秒回答：说明 dry-run 返回空；`detect_batch` 是逐帧循环；letterbox、模型前处理和 NMS 由 Ultralytics 负责；项目侧负责 adapter 与 artifacts。
- 深挖回答：阈值是 operating point，需要真实验证集做 per-class PR 校准；模型应通过 checksum、registry 和 runtime version 固化。
- 常见追问：NMS；输入尺寸；置信度含义；小目标。
- 证据：`backend/app/cv/yolo_detector.py`、`.env.example`、detector tests。
- 易错点：说自研 YOLO/NMS、完成训练或已有仓库权重。
- 事实边界：真实推理效果未由 tracked benchmark 验证。

### Q011 为什么默认 YOLO dry-run

- 类别：测试与依赖。
- 问题：dry-run 有什么价值，又有什么风险？
- 考察点：测试替身与真实验证的区分。
- 30 秒回答：它让没有权重/GPU的环境仍能验证上传、任务、artifact、API 和空状态契约；代价是不能证明检测、事件效果，默认空输出还可能让人误以为系统正常完成了真实分析。
- 90 秒回答：建议显式在 UI/manifest 标记 execution mode，生产环境禁用 silently fallback，并建立小模型 fixture 或 GPU nightly test。
- 深挖回答：测试金字塔应把 deterministic contract test 与 real-model acceptance 分层，二者都不能替代另一方。
- 常见追问：怎样在 CI 测模型；权重如何分发；失败是否降级。
- 证据：`.env.example`、`yolo_detector.py`、tests。
- 易错点：将 dry-run passed 转写为 inference passed。
- 事实边界：本次 487 tests 未证明真实 YOLO 精度。

### Q012 项目真的用了 DeepSORT 吗

- 类别：跟踪真相题。
- 问题：你的 tracker 到底是什么？
- 考察点：是否诚实阅读依赖与 fallback。
- 30 秒回答：代码有 `DeepSortTracker` adapter；关闭 dry-run且外部安装 `deep-sort-realtime` 才走真实库。该包不在 requirements，默认 dry-run true，因此当前可复现路径是确定性 fallback。
- 90 秒回答：解释真实路径和 fallback 的统一 contract、导入失败回落原因、为什么测试可以独立运行；指出 production 应 fail-fast 或显式展示 backend 类型。
- 深挖回答：真实 DeepSORT 预期包含运动与外观关联，但不能把 adapter 名称当作算法运行证据。
- 常见追问：为何不加入 dependency；如何验证真实路径；fallback 质量。
- 证据：`cv/deepsort_tracker.py`、`backend/requirements.txt`、tracker tests。
- 易错点：直接回答“用了完整 DeepSORT”。
- 事实边界：没有 tracked 真实 DeepSORT benchmark。

### Q013 Fallback tracker 怎样匹配

- 类别：跟踪算法。
- 问题：没有 DeepSORT 时如何保持 track ID？
- 考察点：匹配、生命周期和局限。
- 30 秒回答：fallback 按类别建立 detection-track 候选，用 IoU/中心关系得分，贪心选择不冲突匹配；未匹配 detection 新建 track，未匹配 track 累加 missed，命中 `n_init` 后 confirmed，超过 `max_age` 删除。
- 90 秒回答：说明门槛由 `max_iou_distance` 变换；没有 Kalman、Hungarian 或 ReID，所以遮挡、交叉、快速运动易 ID switch。
- 深挖回答：如要改进，先用标准 MOT 数据和 TrackEval 比较 IoU+Hungarian、ByteTrack、DeepSORT，而不是凭偏好选型。
- 常见追问：贪心与 Hungarian；center match；max_age。
- 证据：`backend/app/cv/deepsort_tracker.py`、单元测试。
- 易错点：声称用了 ReID 或 Kalman。
- 事实边界：fallback 是 contract/test path，不是 SOTA claim。

### Q014 为什么没有 ByteTrack

- 类别：技术选型。
- 问题：YOLOv8 常配 ByteTrack，项目为什么不用？
- 考察点：是否会用证据回答，而非编故事。
- 30 秒回答：当前代码和依赖没有 ByteTrack，只有历史迁移文档语境；不能虚构当时选型原因。工程上可在统一 tracker contract 下用数据对比 ByteTrack、DeepSORT 和 fallback，再按 IDF1/HOTA、延迟和部署成本选择。
- 90 秒回答：解释 ByteTrack 的高低分两阶段关联和 DeepSORT 的外观特征取舍；给出建立固定验证集与标准工具的实验计划。
- 深挖回答：低分检测对遮挡召回有帮助，但也可能引入错误关联；摄像头视角、密度和算力决定结果。
- 常见追问：你更推荐谁；如何替换；指标是什么。
- 证据：requirements、tracker adapter、`docs/migration_from_yolov8.md`。
- 易错点：捏造“测试后 DeepSORT 更准”的未证实结论。
- 事实边界：历史决策者与实验数据为 `【本人待补充】`。

### Q015 轨迹速度如何计算，能否输出 km/h

- 类别：轨迹。
- 问题：速度公式是什么，精度如何？
- 考察点：坐标系、时间尺度和标定。
- 30 秒回答：相邻 bbox center 的欧氏距离得到 px/frame，有 timestamp/FPS 时得到 px/s；它只用于低速、驻留和拥堵等相对规则，不能称为 km/h。
- 90 秒回答：解释 stride、VFR、透视和 bbox jitter；若要 km/h，需要相机内外参或地面 homography、道路尺度、轨迹平滑和标定验证。
- 深挖回答：同一物理速度在画面远近位置像素位移不同，可按地面平面投影后用真实时间差估算并给置信区间。
- 常见追问：为什么 center；如何平滑；FPS 不准怎么办。
- 证据：`backend/app/trajectory/engine.py`、geometry/trajectory tests。
- 易错点：将 px/s 直接乘常数称真实速度。
- 事实边界：当前无相机标定或 km/h 输出。

### Q016 方向角与逆行判断如何抗抖

- 类别：轨迹/事件。
- 问题：单帧 bbox 抖动会不会误判逆行？
- 考察点：窗口特征和低速处理。
- 30 秒回答：项目用近期轨迹窗口估计方向和一致性，并要求最低像素速度、车道内和角差阈值；这能抑制一部分抖动，但低速、曲线道路和短轨迹仍是风险。
- 90 秒回答：说明 `atan2` 图像坐标、0–360 wrap-around、angle difference、允许方向来自 zone，必要时配置 confirm frames。
- 深挖回答：生产可用 lane centerline direction field、Kalman velocity、迟滞和场景校准，而不是单个全局角度。
- 常见追问：角度 359 与 1；掉头；曲线。
- 证据：trajectory geometry、wrong-way callback/tests。
- 易错点：把图像角度说成地理方位。
- 事实边界：当前没有道路中心线方向场。

### Q017 Zone 为什么用 bottom-center

- 类别：几何建模。
- 问题：为什么不直接判断 bbox 是否与区域相交？
- 考察点：物体落地点语义。
- 30 秒回答：bottom-center 更接近车辆/行人与地面的接触位置，能减少高框或框边缘碰到 polygon 造成的误判；轨迹运动仍保存 center，二者职责不同。
- 90 秒回答：解释 ray casting、边界抖动、分辨率和镜头变更；建议归一化坐标、buffer/hysteresis 或 homography。
- 深挖回答：bbox-mask intersection 可表达占用面积，但代价更高且仍受分割质量影响；应按业务语义选择参考点。
- 常见追问：边界点；polygon 自交；object-fit。
- 证据：`backend/app/trajectory/geometry.py`、`backend/app/trajectory/engine.py`、zone tests。
- 易错点：说所有逻辑都用 bottom-center。
- 事实边界：实际轨迹点是 center；规则可选择 point type。

### Q018 Event Engine 如何执行规则

- 类别：规则引擎。
- 问题：六类事件怎样共享一个框架？
- 考察点：抽象、异常隔离和执行记录。
- 30 秒回答：引擎先归一化规则，分逐轨与 aggregate，做 enabled、类别、最短轨迹过滤，调用 registry callback，再做 cooldown；输出 Event、Evidence、RuleExecution，callback 异常转 error execution。
- 90 秒回答：说明 aggregate 可 `track_id=null`，record_not_matched 用于 debug，状态在内存且 reset 清理 callback state。
- 深挖回答：新增事件需定义 contract、callback、registry、schema validation、service 注入与测试；复杂 CEP 需求会超出当前朴素遍历。
- 常见追问：规则优先级；冲突；多 worker；异常策略。
- 证据：`backend/app/events/engine.py`、`backend/app/events/rule_callbacks/`、engine tests。
- 易错点：称其为机器学习事件分类器。
- 事实边界：没有跨进程状态和规则 DSL。

### Q019 逆行事件的精确条件是什么

- 类别：事件规则。
- 问题：逆行规则怎样减少误报？
- 考察点：多条件组合与参数含义。
- 30 秒回答：目标需是配置车辆类、轨迹足够长、在 vehicle lane、速度高于阈值，近期方向与允许方向角差达到反向阈值，并通过 cooldown/可选确认帧。
- 90 秒回答：默认 allowed 0°、tolerance 45°、reverse threshold 135°、1 px/frame；输出 direction、zone、trajectory evidence。
- 深挖回答：曲线道路应使用位置相关方向场；低速或方向一致性低时应返回不确定而非命中。
- 常见追问：angle tolerance 与 reverse threshold；掉头；镜头旋转。
- 证据：`backend/app/events/rule_callbacks/wrong_way.py` 与测试。
- 易错点：说根据车辆车头朝向识别。
- 事实边界：legacy 多帧参数在部分上下文不完整支持。

### Q020 违停怎样与红灯停车区分

- 类别：事件规则。
- 问题：低速驻留是否会把排队当违停？
- 考察点：规则局限和场景上下文。
- 30 秒回答：当前只组合 no-parking zone、车辆类、低像素速度、驻留和可选中心漂移，不读取信号灯或道路状态，因此红灯/排队是已知误报来源，必须靠区域配置、阈值和人工复核。
- 90 秒回答：说明 track 断裂和 history truncation 对 dwell 的影响；生产可融合信号灯、车道类型、时段和队列状态。
- 深挖回答：把持续事件设计成状态机，使用进入/候选/确认/解除迟滞，并记录 cause features。
- 常见追问：dwell 单位；遮挡；临停。
- 证据：`backend/app/events/rule_callbacks/parking.py`、trajectory dwell 与 tests。
- 易错点：声称已识别交通信号灯。
- 事实边界：当前是规则线索，不是执法结论。

### Q021 危险区入侵如何工作

- 类别：事件规则。
- 问题：危险区入侵是视觉模型还是空间规则？
- 考察点：类别、区域与持续条件。
- 30 秒回答：它是空间规则：目标类别先由 EventRule 过滤，bottom-center 进入 danger zone 并满足 inside frames/seconds 后命中，证据包括 zone 和轨迹。
- 90 秒回答：解释区域本身由人工配置，severity 由规则指定；系统不理解“危险”的真实语境。
- 深挖回答：生产可加入边界迟滞、场景语义、访问时段、人员权限和多传感器确认。
- 常见追问：边界怎么处理；一帧是否命中；任何类别都可配置吗。
- 证据：`backend/app/events/rule_callbacks/danger_zone.py`、zone history tests。
- 易错点：说模型自动识别危险区域。
- 事实边界：默认风险等级不是概率。

### Q022 行人进入机动车道如何判断

- 类别：事件规则。
- 问题：该事件与危险区入侵有什么不同？
- 考察点：复用与语义差异。
- 30 秒回答：几何机制相似，但它强制目标 class 为 person、区域 type 为 vehicle lane，表达特定交通语义；同样可要求持续帧/时间。
- 90 秒回答：上游 person 漏检、类别混淆、区域标注和人行横道上下文都会影响准确性。
- 深挖回答：可用 lane segmentation、crosswalk/signal phase 和 pedestrian intent 做上下文融合。
- 常见追问：骑车人；多人；bbox 边缘。
- 证据：`backend/app/events/rule_callbacks/pedestrian_lane.py` 与测试。
- 易错点：说支持行人意图预测或斑马线识别。
- 事实边界：当前只做类别+区域规则。

### Q023 拥堵规则是不是时间窗口算法

- 类别：事件规则/压力。
- 问题：代码参数有 `time_window_seconds`，是否真正实现滑窗？
- 考察点：能否识别命名与实现的差异。
- 30 秒回答：不应这样声称。当前 aggregate callback 按帧统计 zone 内车辆数和平均像素速度，并用连续帧状态确认；`time_window_seconds` 只影响部分默认帧要求，不是按 elapsed time 维护的完整滑窗。
- 90 秒回答：说明 event `track_id=null`、zone-level cooldown 和 zone_statistics evidence；真实时间窗需 timestamp deque、窗口清理和迟滞。
- 深挖回答：生产还要考虑车道容量、速度分布、采样频率变化和持续事件合并。
- 常见追问：平均速度为什么；stride 改变怎么办；拥堵解除。
- 证据：`congestion.py`、EventRuleService、aggregate tests。
- 易错点：为了好听说成 CEP sliding window。
- 事实边界：这是连续帧 MVP。

### Q024 流量计数如何去重

- 类别：事件规则。
- 问题：目标在线附近抖动会不会重复计数？
- 考察点：越线、方向、per-track 状态和 cooldown。
- 30 秒回答：相邻轨迹段跨 counting line 才生成 flow event；可设 direction 和 `count_once_per_track`，同轨状态与 engine cooldown 抑制重复，汇总再按唯一 flow event 聚合。
- 90 秒回答：指出触线边界可为 none、ID switch 仍会重复、轨迹断裂可能漏计；60 秒 bucket 是后处理聚合。
- 深挖回答：更稳健可用双线虚拟闸门和进入—离开状态机，并以 TrackEval/计数 GT 联合评测。
- 常见追问：正负方向；回穿；同一车多次经过。
- 证据：`flow_counting.py`、geometry、artifact writer、tests。
- 易错点：说每帧检测框数量相加。
- 事实边界：没有真实路口计数 benchmark。

### Q025 为什么分 Event、Evidence、RuleExecution

- 类别：可解释性。
- 问题：一个 JSON payload 不够吗？
- 考察点：业务事实、证据和执行诊断的分离。
- 30 秒回答：Event 回答发生了什么，Evidence 保存方向/区域/速度等支持数据，RuleExecution 记录规则匹配、跳过或异常。分层后 UI、复核和调试可以各取所需，也不把“规则执行”误当“人工真值”。
- 90 秒回答：说明三类 ORM/JSONL、稳定 ID、相对 snapshot refs 和 callback 异常隔离。
- 深挖回答：未来可把 evidence 建模为 typed union、加 schema version/checksum/签名，并建立引用完整性。
- 常见追问：一致性；存储成本；未命中是否全记录。
- 证据：`backend/app/models/event.py`、`backend/app/events/contracts.py`、engine tests。
- 易错点：说 evidence 一定有关键帧。
- 事实边界：visual snapshot 可能 unavailable。

### Q026 告警与事件有什么区别

- 类别：业务建模。
- 问题：为什么事件生成后还要告警层？
- 考察点：事实与处置状态解耦。
- 30 秒回答：事件是算法/规则输出，告警是需要人工处置的业务投影；告警有级别、dedup/cooldown 和 acknowledge/resolve/ignore 生命周期，不应修改原事件事实。
- 90 秒回答：说明 alert ID、severity mapping、Alert Center 到 Review 的跳转，以及无外部 notification channel。
- 深挖回答：生产可拆 notification policy 与 delivery attempt，避免发送失败污染告警事实。
- 常见追问：resolved 是否等于 true positive；告警风暴。
- 证据：`backend/app/alerts/`、alerts API/tests。
- 易错点：称告警由独立模型预测。
- 事实边界：当前没有短信/邮件/Webhook。

### Q027 Analysis Center 为什么 DB-first 又支持文件回退

- 类别：兼容架构。
- 问题：两个事实源不是反模式吗？
- 考察点：演进取舍和债务识别。
- 30 秒回答：项目早期产物以 CSV/JSONL 为主，后续加入 DB 查询；DB-first + artifact fallback 让旧 run 继续可读，导入脚本支持渐进迁移。代价是双源一致性复杂，fallback 不应长期替代治理。
- 90 秒回答：说明损坏文件 warning、幂等导入、manifest discovery 和顶层 detections 预留。
- 深挖回答：设迁移完成 gate 后应明确权威源；用 checksum/reconciliation/outbox 处理偏差。
- 常见追问：冲突时信谁；读操作会不会写；如何清理 fallback。
- 证据：`backend/app/services/traffic_analysis_service.py`、`backend/app/analysis/artifact_compatibility.py`、compatibility tests。
- 易错点：说 DB 与文件强一致。
- 事实边界：部分兼容读取可能补写派生产物。

### Q028 DB 与文件双写失败怎么办

- 类别：一致性/压力。
- 问题：artifact 已写完但 DB commit 失败，系统是否一致？
- 考察点：事务边界和补偿思维。
- 30 秒回答：当前不能保证一致；DB transaction 不覆盖文件 I/O，失败可能留下孤儿目录，反向也可能有 DB 行但文件缺失。现状靠状态、fallback 和人工/导入兼容，生产需幂等任务、发布状态、checksum、reconciliation 与垃圾回收。
- 90 秒回答：给出 staging dir → fsync/checksum → DB commit metadata → atomic publish/mark ready，或 DB outbox 驱动对象存储导出的方案。
- 深挖回答：不声称跨资源 exactly-once；选择单一权威源并用可重放操作实现最终一致。
- 常见追问：写入顺序；补偿失败；并发 rerun。
- 证据：process route、artifact writer、repository/session。
- 易错点：只回答“捕获异常 rollback”。
- 事实边界：当前没有自动 reconciliation worker。

### Q029 Review Center 的价值是什么

- 类别：Human-in-the-loop。
- 问题：有评测了，为什么还要人工复核？
- 考察点：线上/本地输出与 ground truth 的区别。
- 30 秒回答：评测依赖已有 expected data，而实际 run 仍需人工确认、误报、忽略、解决和评论。Review 保留原事件事实，新增人工状态，为 Bad Case 和后续数据闭环提供来源。
- 90 秒回答：说明事件列表/详情、review state、评论、actor header 与 status semantics。
- 深挖回答：生产应加入任务分配、盲审、多人一致性、审计签名与抽样策略。
- 常见追问：谁有权限；多人冲突；是否修改原事件。
- 证据：review API/service/schemas/tests。
- 易错点：声称 review 自动修正模型。
- 事实边界：身份 header 未认证。

### Q030 为什么要单独登记漏报

- 类别：质量闭环。
- 问题：只标记 false positive 不够吗？
- 考察点：选择偏差和 recall。
- 30 秒回答：只展示系统产出的事件，人工永远看不到“没产出的真事件”，会高估召回。False Negative 入口让复核者按时间、类型、区域补录漏报，并可转 Bad Case。
- 90 秒回答：说明漏报发现仍依赖人工扫描或抽样，当前没有全量标注工具；真正 recall 需要独立 ground truth。
- 深挖回答：可用主动学习、随机负样本抽检和双人标注降低发现偏差。
- 常见追问：漏报如何取证；成本；如何去重。
- 证据：review schema/API/tests。
- 易错点：把没有告警的帧都当 true negative。
- 事实边界：当前漏报记录不自动成为正式 GT。

### Q031 Bad Case 如何形成回归资产

- 类别：质量工程。
- 问题：误报标完后如何防止再次出现？
- 考察点：问题资产化和回归层级。
- 30 秒回答：Review 或 Evaluation failed case 可转为带 source、module、status、tags、run/evidence 的 Bad Case；regression evaluation 可重放规则 fixture 并建议 fixed/reopened，形成最小回归闭环。
- 90 秒回答：说明 dedup、DB+JSONL、手工 update 与 `apply_updates` 风险；没有自动训练数据发布。
- 深挖回答：成熟系统需 dataset version、owner、severity、acceptance expectation、全链路 replay 和 CI gate。
- 常见追问：何时关闭；修复后如何验证；数据泄露。
- 证据：bad case service、evaluation regression tests。
- 易错点：说所有 Bad Case 会自动重新训练。
- 事实边界：当前 regression 主要是规则/fixture 级。

### Q032 Event Evaluation 怎样匹配

- 类别：评测。
- 问题：两个事件怎样判断为同一个？
- 考察点：匹配规则与指标含义。
- 30 秒回答：按事件类型，并可结合 track、zone 与默认 5 帧容差做一对一匹配，得到 TP/FP/FN，再算 precision、recall、F1、accuracy 和 false-alarm rate，并输出 per-type failed cases。
- 90 秒回答：说明没有 TN，accuracy 是 TP/expected 的项目定义；匹配顺序和容差影响结果。
- 深挖回答：区间事件可改用 temporal IoU 与 bipartite matching，并报告 macro/micro 和置信区间。
- 常见追问：多个 actual 匹配一个 expected；track ID 不稳定；容差怎么定。
- 证据：evaluation service、event metric tests。
- 易错点：把 toy F1=1 说成模型准确率 100%。
- 事实边界：仓库无正式 event benchmark result。

### Q033 Detection 评测是不是 COCO mAP

- 类别：评测/压力。
- 问题：你的 detection 指标为什么叫 AP，是否标准？
- 考察点：指标诚实性。
- 30 秒回答：不是 COCO mAP。当前是自定义单 IoU=0.5 的 VOC 风格 AP，能验证匹配和 PR 链路，但没有 IoU 0.5:0.95、多尺度和 pycocotools 协议。
- 90 秒回答：解释 confidence 排序、一对一 IoU matching、per-class AP；正式评测应导出 COCO format 并用标准实现。
- 深挖回答：阈值前的 ranking metric 与部署 operating point 指标应同时报告，且要 pin dataset/model。
- 常见追问：AP 插值；mAP；IoU；小目标。
- 证据：evaluation service、detection metric tests。
- 易错点：说“mAP50-95”。
- 事实边界：没有 tracked detection annotations/results。

### Q034 Tracking 指标是不是官方 TrackEval

- 类别：评测/压力。
- 问题：有 IDF1/MOTA 就说明跟踪评测标准吗？
- 考察点：实现协议与指标名称的区分。
- 30 秒回答：不是。当前逐帧用贪心 IoU 匹配 GT/pred，再近似计算 IDF1、MOTA、ID switch、lost segment；没有调用 TrackEval，也没有 HOTA，因此只能称轻量 MVP 指标。
- 90 秒回答：说明 MOTA 综合 FP/FN/IDSW 可能为负，IDF1更关注身份；正式比较要转换 MOT 格式并用标准工具。
- 深挖回答：评测 matcher 本身会改变指标，必须固定阈值、ignore regions、class filters 和 sequence protocol。
- 常见追问：HOTA；IDSW；遮挡；MOTA 缺点。
- 证据：evaluation service、tracking metric tests、requirements。
- 易错点：把输出字段名当标准认证。
- 事实边界：无真实 tracker benchmark。

### Q035 Regression Evaluation 会重跑模型吗

- 类别：评测/真相题。
- 问题：回归评测覆盖到哪一层？
- 考察点：测试层级与范围。
- 30 秒回答：当前主要加载 Bad Case/规则 fixture 做确定性 replay，并计算 fixed/reopened 等建议；不会自动重新解码原视频、跑 YOLO、tracker 和全部下游。
- 90 秒回答：说明无 replay data 时不会伪造 pass，`apply_updates` 可改状态但应谨慎；完整回归需 golden videos、固定 weights/container 和标准 metrics。
- 深挖回答：按 unit rule replay、artifact replay、full pipeline replay、production shadow 四层建设，成本和信号不同。
- 常见追问：如何接 CI；模型非确定性；数据版本。
- 证据：`backend/tests/test_regression_metrics.py`、evaluation service。
- 易错点：说已做端到端视频回归。
- 事实边界：当前 regression 是轻量规则级。

### Q036 报告的 Web、JSON、CSV、PDF 是否一致

- 类别：报告。
- 问题：不同格式会不会给出不同结论？
- 考察点：共享数据模型与渲染边界。
- 30 秒回答：它们共享 ReportService 的关键 summary，但内容粒度不同：full JSON 最完整，CSV 分六个 section，PDF 是英文 Latin-1 摘要，bundle 只是 metadata，不是 zip。因此只能说核心字段一致，不能说逐字一致。
- 90 秒回答：解释 latest evaluation 选择、PDF 非 Latin 字符替换和 source-of-truth 风险。
- 深挖回答：生产应版本化 report schema、pin evaluation run、做 golden rendering 和签名归档。
- 常见追问：中文；大数据；bundle；法规用途。
- 证据：reports API、report service/PDF tests。
- 易错点：说 PDF 完整复制 Web 或 bundle 下载全部资产。
- 事实边界：报告明确非执法结论。

### Q037 Camera Center 是否真的支持实时 RTSP

- 类别：实时/压力。
- 问题：页面有 Camera 和 RTSP，为什么不算实时系统？
- 考察点：是否检查 worker 实现。
- 30 秒回答：因为 worker 对 RTSP 明确不连接；mock 只返回固定三帧，file 只检查路径，服务维护单进程内存状态和伪 task。它只验证预览 API/UI 生命周期。
- 90 秒回答：真实实现需 FFmpeg/GStreamer ingest、独立 worker、缓冲与背压、断线重连、timestamp、GPU 调度和 WebRTC/HLS 输出。
- 深挖回答：端到端延迟要分 ingest、decode、inference、event、delivery，并用 SLO 测量。
- 常见追问：为何保留；如何第一步实现；多路摄像头。
- 证据：`realtime/worker.py`、realtime preview service/tests。
- 易错点：说已经连接过 RTSP 或持续推理。
- 事实边界：当前是 contract preview。

### Q038 当前鉴权安全吗

- 类别：安全/压力。
- 问题：设置 strict auth 后能否生产使用？
- 考察点：认证、授权、审计差异。
- 30 秒回答：不能。默认 permissive 会 bypass；strict 只是从未验证的 `X-SmartTraffic-Actor/Role` header 做权限映射，header 可伪造；日志 audit 也不是不可抵赖审计。
- 90 秒回答：生产需 OIDC/JWT 验签、issuer/audience、RBAC/ABAC、租户隔离、secret manager、append-only audit 和视频数据保留策略。
- 深挖回答：服务间身份、下载 URL、对象级授权和管理员操作需要单独 threat model。
- 常见追问：CORS 是否安全；JWT 存哪里；角色怎么设计。
- 证据：`backend/app/core/identity.py`、`.env.example`、`docs/security_ops.md`。
- 易错点：说 strict 就是完整登录。
- 事实边界：当前权限契约只适合本地预览。

### Q039 Docker Compose 做了什么，没做什么

- 类别：交付。
- 问题：项目如何一键启动，是否可生产部署？
- 考察点：容器事实与生产边界。
- 30 秒回答：Compose 只有 backend 和 frontend；后端 Python 3.12 slim，启动先 Alembic 再 Uvicorn，挂载本地资源；前端 Node 20 跑 `npm ci && npm run dev`。它没有 Nginx、Postgres、Redis、worker、GPU 或 HA。
- 90 秒回答：说明 readiness、volumes、CPU 默认和前端 dev server；生产应 multi-stage 静态构建、反向代理、不可变镜像和外部持久服务。
- 深挖回答：模型与 codec 会影响镜像体积/供应链，GPU 需 runtime、driver 和资源声明。
- 常见追问：数据库迁移并发；volume 权限；healthcheck。
- 证据：`backend/Dockerfile`、`docker-compose.yml`。
- 易错点：说用了 Nginx/K8s/GPU。
- 事实边界：本次只验证 `docker compose config -q`，未做完整容器启动验收。

### Q040 测试覆盖证明了什么

- 类别：验证。
- 问题：487+90 个测试能否证明系统可靠？
- 考察点：证据强度判断。
- 30 秒回答：它证明当前 HEAD 的规则、几何、API、artifact、评测和前端契约在隔离环境下通过；后端 487/487、前端 90/90、build/Compose/danger check 通过。但不证明真实模型精度、浏览器 E2E、RTSP、性能和生产可靠性。
- 90 秒回答：说明 tmp SQLite fixture、无 pytest cache、4 个 Starlette deprecation warning、仓库无 CI。
- 深挖回答：建立 CI 后按 unit/API/E2E/model benchmark/load/chaos 分层，分别定义 gate。
- 常见追问：最重要测试；flaky；为什么无 E2E。
- 证据：`backend/tests/conftest.py`、tests、Makefile、本次验证输出。
- 易错点：把所有测试称端到端或说 CI green。
- 事实边界：这是本机 Verified，不是远端 CI 结论。

### Q041 你解决过最难的问题是什么

- 类别：行为面试。
- 问题：讲一个最难的技术问题和你的贡献。
- 考察点：STAR、个人边界、验证与复盘。
- 30 秒回答：`【本人待补充】`（真实问题、个人动作、结果）。可从 DB/artifact 兼容、规则状态、报告最新评测或视觉证据中选择本人确实负责的案例。
- 90 秒回答：Situation 讲约束；Task 讲本人目标；Action 讲定位调用链、方案取舍、测试与 diff；Result 只给可验证结果；Reflection 讲遗留边界。
- 深挖回答：展示失败尝试与证据变化，而不是把团队成果全归个人。
- 常见追问：为什么难；你亲自写了什么；若重做；谁评审。
- 证据：对应 commit/diff/test/issue `【本人待补充】`。
- 易错点：背仓库架构代替个人案例，或虚构性能数字。
- 事实边界：Git 仓库不能自动证明个人职责。

### Q042 项目中最关键的技术权衡是什么

- 类别：架构决策。
- 问题：选一个你最认可或最想改的权衡。
- 考察点：利弊、上下文和演进判断。
- 30 秒回答：可讲 DB+artifact：本地调试、兼容旧 run 和导出很方便，但带来双源一致性；当前用 DB-first/fallback/幂等导入缓解，生产应明确单一权威源并加 checksum/outbox/reconciliation。
- 90 秒回答：也可选规则法 vs 学习法、同步 vs 异步、dry-run vs fail-fast，必须说明当时约束与退出条件。
- 深挖回答：好权衡不是永久选择，而是有衡量指标、risk budget 和迁移触发器。
- 常见追问：为什么不一开始做正确架构；代价是否发生。
- 证据：相关 service、tests、设计文档。
- 易错点：只列优点或把未来方案说成已完成。
- 事实边界：个人决策权和历史背景为 `【本人待补充】`。

### Q043 一次处理失败后会发生什么

- 类别：可靠性。
- 问题：模型异常、文件损坏或 DB 错误如何体现？
- 考察点：状态、事务、错误和残留。
- 30 秒回答：路由把 task/video 标 failed，记录错误并提交，已知输入/运行错误返回统一 400 类响应；callback 错误则转 RuleExecution error，visual 失败会降级 artifact 状态。但已经写出的文件不一定回滚。
- 90 秒回答：区分 stage-local failure 和 whole-process failure；说明 request ID、脱敏、manifest status、无自动 retry/reconciliation。
- 深挖回答：生产用 stage checkpoint、idempotent retry、dead-letter、cleanup/reconciliation 和可恢复状态机。
- 常见追问：commit 失败；worker 崩溃；半成品如何读。
- 证据：process route、error handlers、EventEngine、visual builder。
- 易错点：说所有失败都自动回滚且无残留。
- 事实边界：无故障注入或恢复演练。

### Q044 如果给你两周生产化，优先做什么

- 类别：生产化。
- 问题：资源有限时如何排序？
- 考察点：风险驱动、可交付与非功能需求。
- 30 秒回答：先限定一个真实本地视频 use case 和 SLO；第一周把同步任务拆到可恢复 worker、固定模型/依赖版本、引入可信认证和单一持久化；第二周做真实标注集 acceptance、监控告警、E2E 和失败恢复演练。RTSP 若是核心，则替换占位 worker 并先做单路稳定性。
- 90 秒回答：按安全/数据丢失、可用性、准确性、性能排序；不在两周内承诺全功能云原生重写。
- 深挖回答：设置 go/no-go gates：身份可信、任务可恢复、结果可追溯、指标达到阈值、SLO 被测量。
- 常见追问：为何先做认证；是否换 PostgreSQL；如何 rollback。
- 证据：当前限制清单、architecture/services/Compose。
- 易错点：罗列 Kafka/K8s/微服务而没有风险和验收。
- 事实边界：实际团队、预算与业务优先级为 `【本人待补充】`。

### Q045 你本人做了什么，AI 做了什么

- 类别：贡献与诚信。
- 问题：哪些代码是你写的，是否使用 AI？
- 考察点：所有权、验证责任和透明度。
- 30 秒回答：我的角色与模块是 `【本人待补充】`；AI 使用情况是 `【本人待补充】`。无论是否用 AI，我只认领本人完成并能用 commit/diff/test 解释的部分，最终由我审查事实、边界和验证结果。
- 90 秒回答：按“输入约束—AI/工具辅助—人工判断—测试/diff—评审”讲一个真实例子；明确未负责模块只表示理解，不冒充贡献。
- 深挖回答：AI 生成内容属于不可信草案，尤其安全、迁移和评测结论必须回到代码与运行证据。
- 常见追问：离开 AI 能否实现；如何发现 hallucination；代码 review。
- 证据：个人 commit、PR、工作记录 `【本人待补充】`。
- 易错点：隐瞒 AI，或把整个仓库说成个人独立开发。
- 事实边界：仓库事实与个人事实必须分开。

## 第二部分：架构、CV、事件与全栈深挖（Q046–Q105）

### Q046 [架构] 为什么当前是模块化单体而不是微服务

- 30 秒：模块化单体适合本地 MVP，事务、调试和部署简单；当前规模没有证据证明微服务收益高于网络、运维和一致性成本。
- 深挖：先按 async worker、storage、auth 的真实伸缩/隔离需求拆，不按名词拆。
- 证据：单 FastAPI 应用、单 SQLite、两个 Compose service。
- 边界：个人历史选型原因 `【本人待补充】`。

### Q047 [架构] API、Service、Repository 如何分工

- 30 秒：API 做 HTTP/schema/commit，Service 编排领域用例，Repository 封装 ORM 查询与 flush。
- 深挖：当前部分 service 很重且 commit 在路由，未来可引入 Unit of Work 收紧事务边界。
- 证据：`backend/app/api/`、`backend/app/services/`、`backend/app/repositories/base.py`。
- 边界：文件 I/O 不受 repository transaction 保护。

### Q048 [架构] 为什么使用应用工厂

- 30 秒：`create_app()` 集中 middleware、exception handler、CORS 和 routers，也方便测试创建独立应用实例。
- 深挖：配置缓存和全局 service 状态仍需避免跨测试/多实例污染。
- 证据：`backend/app/main.py`。
- 边界：应用工厂不自动解决全局 singleton 问题。

### Q049 [后端] 统一错误码如何设计

- 30 秒：将 domain/input/not-found/internal exception 映射为稳定 `error_code`、message、detail、request_id，敏感信息脱敏。
- 深挖：生产还需错误 taxonomy、可重试标记、日志 severity 和 trace correlation。
- 证据：`core/errors.py`、应用 exception handlers。
- 边界：关键词脱敏不是完整 DLP。

### Q050 [配置] 环境变量和请求配置冲突时信谁

- 30 秒：全局 settings 给默认，处理请求允许显式 override，最终有效值应写入 run config snapshot。
- 深挖：定义字段级 allowlist，避免用户覆盖安全/目录配置，并返回 effective config。
- 证据：`backend/app/core/config.py`、processing schema/service。
- 边界：`.env.example` 不是实际运行配置。

### Q051 [处理] 三种 processing mode 有什么区别

- 30 秒：`detection_only` 只检测；`detection_tracking` 增加 track；`detection_tracking_trajectory` 再生成轨迹，并在开关允许时执行事件、告警和视觉产物。
- 深挖：mode 应形成显式 stage DAG 与 artifact requirement，避免分支散落。
- 证据：`api/videos.py`、processing schema。
- 边界：完整事件不在前两种模式运行。

### Q052 [处理] 同一个视频重复处理会怎样

- 30 秒：每次生成新 processing task/run ID，旧 run 保留；当前没有按 input+config 自动幂等去重。
- 深挖：生产可用内容哈希+effective config+model version 构造幂等 key，并允许 force rerun。
- 证据：process route 的 ID 生成与 run writer。
- 边界：同名上传文件与同视频 rerun 是两类问题。

### Q053 [领域] 为什么很多 ID 用稳定哈希

- 30 秒：event/alert/evidence 使用稳定输入生成 ID，便于重建、去重和 artifact/DB 对齐。
- 深挖：稳定 ID 只有在 canonical input 明确时有效，hash collision 与 schema change 仍需版本化。
- 证据：event/alert contracts。
- 边界：稳定 ID 不等于数据库唯一约束或 exactly-once。

### Q054 [架构] 内存 registry 有什么问题

- 30 秒：处理/实时/规则状态若只在进程内，多 worker 不共享，重启丢失，API 看到的状态可能不一致。
- 深挖：将 durable state 放 DB/Redis，把内存只作为可丢缓存并带 version/TTL。
- 证据：realtime preview cache、EventEngine callback state。
- 边界：当前本地单进程路径可用。

### Q055 [可靠性] 如何设计更严格的处理状态机

- 30 秒：`pending→running→completed/failed` 是起点；生产还需 queued、cancel_requested、cancelled、retrying、publishing、ready，并限制合法转换。
- 深挖：每次转换用 optimistic version、actor/reason/timestamp，worker heartbeat 检测僵尸任务。
- 证据：`ProcessingTask` 模型/schema。
- 边界：当前没有取消和 retry 状态。

### Q056 [视频] codec allowlist 为什么不够

- 30 秒：容器扩展名、fourcc 和真实可解码内容可能不一致，恶意或损坏文件仍可进入解码器。
- 深挖：隔离进程用 ffprobe/实际抽帧，限制 CPU/内存/时长并扫描内容。
- 证据：videos API、FrameReader。
- 边界：当前仅基础校验。

### Q057 [视频] VFR 视频怎样影响 timestamp

- 30 秒：用 frame_index/FPS 推时间对可变帧率可能不准，驻留和速度应优先使用解码器真实 PTS。
- 深挖：统一 timebase，artifact 同时保存 frame index 与 timestamp，规则用 elapsed time。
- 证据：FrameReader/trajectory timestamp fallback。
- 边界：当前 OpenCV metadata 无法保证 VFR 精确。

### Q058 [视频] stride 改变后规则阈值要不要改

- 30 秒：要评估；px/frame、连续帧数、max_age 和 cooldown frames 都与采样步长耦合，最好转为 timestamp/px/s 语义。
- 深挖：run snapshot 保存 stride，按真实帧差归一化运动，并分场景重新校准。
- 证据：frame reader、trajectory/event parameters。
- 边界：当前部分规则仍以帧阈值为主。

### Q059 [YOLO] 懒加载模型有什么并发风险

- 30 秒：首次请求延迟大，多线程同时首次调用可能重复初始化，GPU context/模型对象线程安全也需确认。
- 深挖：startup warmup + lock + health state，或独立 inference service。
- 证据：`YoloDetector` lazy model property。
- 边界：当前无并发模型加载测试。

### Q060 [YOLO] `detect_batch` 真的是 batch inference 吗

- 30 秒：不是，当前只是 Python 循环逐帧调用 detect，没有把多帧作为一个模型 batch。
- 深挖：真实 batching 需权衡显存、等待窗口、视频顺序和 tracker latency。
- 证据：`backend/app/cv/yolo_detector.py`。
- 边界：不能据函数名声称 GPU batching。

### Q061 [YOLO] 为什么只保留六类目标

- 30 秒：下游规则只消费交通相关 vehicle/person 类，前置过滤减少噪声和存储。
- 深挖：类别映射需随模型版本验证，per-rule target classes 可进一步收窄。
- 证据：detector defaults、EventRule target classes。
- 边界：类别集合可配置，不代表模型只训练了六类。

### Q062 [YOLO] 如何选择 confidence threshold

- 30 秒：在代表性验证集上画 per-class PR/成本曲线，按误报与漏报业务成本选 operating point，而非沿用 0.25。
- 深挖：检测阈值与 tracker 接纳低分框、事件 cooldown 联合优化。
- 证据：`.env.example` 默认值只是配置证据。
- 边界：仓库无阈值最优实验。

### Q063 [YOLO] 怎样保证模型版本可复现

- 30 秒：记录权重 SHA256、模型 config、Ultralytics/Torch/CUDA、代码 commit、输入哈希和推理参数。
- 深挖：把模型作为不可变 registry artifact，以 approved alias 发布。
- 证据：当前 `ModelRun`/config snapshot 是不完整基础。
- 边界：本机 ignored `yolov8n.pt` 不属于 HEAD。

### Q064 [性能] CPU 和 GPU 路径如何选择

- 30 秒：当前示例 device=cpu、Compose 无 GPU；生产按单帧延迟、吞吐、并发、显存和成本 benchmark 后选择。
- 深挖：GPU batching 与多视频公平调度、warmup、OOM 回退都需指标。
- 证据：`.env.example`、Compose。
- 边界：没有 GPU 性能数据。

### Q065 [Tracker] 静默 fallback 有什么危险

- 30 秒：配置要求真实 DeepSORT却因缺包回落，用户可能无感知地得到不同质量结果。
- 深挖：生产应 fail-fast 或在 manifest/UI 标明 tracker backend/fallback reason，并设 deployment gate。
- 证据：`deepsort_tracker.py` fallback reason。
- 边界：当前回落有利于测试，但不适合无提示生产。

### Q066 [Tracker] 为什么轨迹默认只消费 confirmed

- 30 秒：tentative/lost 更可能是噪声或预测状态，过滤后能降低规则误触发。
- 深挖：`n_init` 增大提高精度但增加事件延迟和短目标漏失。
- 证据：TrajectoryEngine contract tests。
- 边界：默认 `n_init=1` 时确认很快。

### Q067 [Tracker] `max_age` 和 `n_init` 如何调

- 30 秒：按 FPS/stride 和遮挡时长转成时间语义；`max_age` 过小导致断轨，过大导致错误延续；`n_init` 过大漏短轨。
- 深挖：用 MOT sequences 做 grid search，并按 IDF1/HOTA/业务计数误差联合选。
- 证据：`.env.example` tracker settings。
- 边界：当前无调参 benchmark。

### Q068 [Tracker] track ID 能跨摄像头吗

- 30 秒：不能；ID 是单 tracker/run 内局部身份，没有跨镜 ReID、时间同步或拓扑。
- 深挖：跨镜需 embedding、时空 gating、camera calibration、隐私与阈值评测。
- 证据：tracker state 生命周期与 run scope。
- 边界：不要把 ID 当车牌或真实身份。

### Q069 [Tracker] 如何公平比较三种 tracker

- 30 秒：固定 detector outputs、数据集、class/threshold 和硬件，用 TrackEval 报 IDF1/HOTA/MOTA/IDSW，同时量延迟、显存和下游计数误差。
- 深挖：再做真实端到端 detector+tracker 联合实验，分密度/遮挡场景。
- 证据：当前 evaluation 只提供轻量近似。
- 边界：没有现成对比结论。

### Q070 [隐私] ReID 会带来什么风险

- 30 秒：外观 embedding 可能形成可关联个人/车辆表征，需限定用途、保留期、访问权限和跨镜合法性。
- 深挖：尽量本地化、短期匿名 ID、加密、审计和 data protection impact assessment。
- 证据：当前 fallback 无 ReID；安全边界文档。
- 边界：这是未来风险，不宣称当前存储 embedding。

### Q071 [轨迹] 为什么 center 存轨迹、bottom-center 判区域

- 30 秒：center 对 bbox 抖动与运动差分直观，bottom-center 更接近地面接触点；分工比统一一个点更符合语义。
- 深挖：生产可在 schema 同时保存两者和 coordinate space/version。
- 证据：trajectory engine/geometry。
- 边界：透视问题仍存在。

### Q072 [几何] 多边形边界点怎样处理

- 30 秒：当前 geometry 有边界测试，但连续帧在边界抖动仍可能 inside/outside 切换。
- 深挖：使用内外双 buffer、迟滞或连续帧门槛，并记录边界距离。
- 证据：`test_trajectory_geometry.py`。
- 边界：像素 polygon 不是 GIS 法定边界。

### Q073 [几何] 目标恰好触线怎么办

- 30 秒：有向侧为零时方向可返回 `none`，避免把触碰误当明确正/负越线。
- 深挖：用计数带/双线状态机区分进入、穿越和离开。
- 证据：line crossing geometry tests。
- 边界：当前边界策略可能漏计恰好沿线的轨迹。

### Q074 [轨迹] 历史截断会影响什么

- 30 秒：`max_history_points` 限制内存，但可能截断 dwell、方向稳定性和长期区域状态所需信息。
- 深挖：将累计统计与原始点 deque 分离，前者不随窗口丢失。
- 证据：TrajectoryEngine state/config。
- 边界：当前是进程内历史。

### Q075 [轨迹] 角度 359° 和 1° 差多少

- 30 秒：圆周最小角差是 2°，不能直接绝对相减得 358°。
- 深挖：项目 geometry 有 wrap-around 测试；零向量应返回无方向。
- 证据：`test_trajectory_geometry.py::test_angle_difference_wraparound`。
- 边界：角度仍在图像坐标系。

### Q076 [Zone] 分辨率变化如何迁移区域

- 30 秒：当前 polygon 是像素坐标，分辨率/裁剪变化会错位；应保存 reference width/height 或归一化坐标并在渲染/执行时转换。
- 深挖：镜头位置变化即使同分辨率也需重新标定和版本发布。
- 证据：Zone schema 与视频 metadata。
- 边界：当前无自动迁移。

### Q077 [Rule] version 字段能否回滚

- 30 秒：不能单凭 version 数值回滚；当前没有保存每次不可变 revision 和发布状态。
- 深挖：建立 rule_revision、effective_from、created_by、approval、rollback pointer。
- 证据：EventRule ORM/schema。
- 边界：不要称已有完整规则版本控制。

### Q078 [Rule] 新增一种事件需要改哪些地方

- 30 秒：定义 event type/schema validation、callback 和 registry，处理 zone 参数注入，更新 evidence/summary/API/UI，并补正反例测试。
- 深挖：检查逐轨还是 aggregate、state reset、cooldown key 和 artifact compatibility。
- 证据：rule callbacks、EventRuleService、tests patterns。
- 边界：不要只加一个函数忽略契约链。

### Q079 [Event] Aggregate 和逐轨规则为何分开

- 30 秒：逐轨规则消费单个 track，拥堵消费同帧全体轨迹，track ID 可为空；统一逐轨循环会重复计算群体事件。
- 深挖：aggregate 需要 zone-level dedup key 和独立 state。
- 证据：EventEngine aggregate tests。
- 边界：当前只有拥堵使用 aggregate 注入。

### Q080 [Event] 多 worker 下 cooldown 是否有效

- 30 秒：不可靠；状态在各进程内，各 worker 可同时发重复事件。
- 深挖：使用数据库唯一窗口键或 Redis atomic set-if-absent + TTL，并处理时钟/重试。
- 证据：EventEngine in-memory maps。
- 边界：当前单进程本地演示可用。

### Q081 [逆行] 曲线道路怎样支持

- 30 秒：单 allowed angle 不够，应按 lane centerline/位置建立局部切线方向，轨迹投影后比较沿路方向。
- 深挖：需要 lane topology、相机标定和曲线采样平滑。
- 证据：当前 callback 只读取一个允许角。
- 边界：未来方案，不是当前能力。

### Q082 [违停] 如何处理队列停车

- 30 秒：结合 lane/stop-line/signal phase、上游群体速度和 no-parking zone 精细配置；单目标低速驻留不足。
- 深挖：引入 context features 和事件解除迟滞，再以 FP 场景集验证。
- 证据：当前 parking/congestion rules 分离。
- 边界：项目未识别红绿灯。

### Q083 [入侵] severity 是如何得出的

- 30 秒：由 EventRule 配置 low/medium/high，不是概率模型输出。
- 深挖：生产可按目标类别、区域风险、持续时间和时段做 policy mapping，并保留原因。
- 证据：EventRule schema/callback result。
- 边界：不能解释为事故发生概率。

### Q084 [行人] 骑自行车的人算哪类事件

- 30 秒：当前规则要求 class `person`，若 detector 输出 bicycle 则不会按行人入机动车道命中，除非新增/调整业务规则。
- 深挖：需要明确 rider ontology 与复合对象关联，而非随意扩类别。
- 证据：pedestrian callback、detector target classes。
- 边界：当前无 rider association。

### Q085 [拥堵] 为什么平均速度可能误导

- 30 秒：少量高速目标会抬高均值，或大量静止目标掩盖不同车道；分位数、密度和占有率更稳健。
- 深挖：按车道/类别分组并用持续窗口，结合道路容量校准。
- 证据：当前 congestion 使用 count + average speed。
- 边界：无车道容量模型。

### Q086 [流量] positive/negative 如何变成 in/out

- 30 秒：几何只给相对线方向，业务 in/out 需 counting line 配置约定并固化坐标方向。
- 深挖：UI 显示箭头和示例轨迹，保存 line orientation/version。
- 证据：Zone counting_line 与 flow aggregation。
- 边界：错误画线会反转语义。

### Q087 [Event] 持续事件是一条还是每帧一条

- 30 秒：当前 callback/cooldown 可能生成离散命中，未形成完整 start-update-end 持续事件状态机。
- 深挖：生产定义 candidate/active/resolved，合并区间并记录 last_seen。
- 证据：Event Engine cooldown 与 event fields。
- 边界：不要声称已有复杂事件合并。

### Q088 [Evidence] 为什么 JSON 字段有风险

- 30 秒：扩展快，但数据库不能强约束不同 evidence type 的字段，查询和迁移也更难。
- 深挖：用 discriminated union schema、schema_version 和 validation-on-read/write。
- 证据：EventEvidence ORM/contracts。
- 边界：当前 Pydantic/服务层承担部分验证。

### Q089 [RuleExecution] 是否保存所有未命中

- 30 秒：默认可只保留关键执行；`record_not_matched` 是 debug 开关，否则全量逐轨逐规则记录会爆炸。
- 深挖：采样或聚合 skipped reason，错误全保留。
- 证据：EventEngine tests for record_not_matched。
- 边界：不能用缺失 skipped record 推断规则未执行。

### Q090 [视觉证据] 关键帧生成失败还能复核吗

- 30 秒：结构化事件/轨迹仍可读，manifest 标 visual missing/error；UI 应降级显示原因，但视觉复核能力受限。
- 深挖：提供后台按需重建和源视频保留检查。
- 证据：visual artifact service/tests。
- 边界：不伪造 available 状态。

### Q091 [数据库] SQLite 的并发边界是什么

- 30 秒：适合单机本地，写锁与文件存储限制多 worker 写吞吐和 HA；生产应评估 PostgreSQL。
- 深挖：先测实际写模式，再迁移 JSON/index/transaction，并处理 artifact metadata。
- 证据：默认 DB URL、Compose 无 DB service。
- 边界：没有并发 benchmark。

### Q092 [ORM] 没有 relationship 有什么影响

- 30 秒：仍有 FK 字段可查，但失去对象导航、cascade 和 eager loading 配置，服务层手工 join/query 更多。
- 深挖：补 relationship 时要明确 delete-orphan、ondelete 和 N+1。
- 证据：`backend/app/models/` 无 `relationship()`。
- 边界：不是说数据库完全没有 FK。

### Q093 [迁移] `metadata.drop_all` 为什么危险

- 30 秒：downgrade 可能删除整个 schema，而非只撤销本 revision，对有数据环境破坏性极大。
- 深挖：用显式 DDL、备份、迁移演练和 downgrade policy。
- 证据：Alembic `0002`。
- 边界：不要在真实数据环境随意执行 downgrade。

### Q094 [事务] flush 和 commit 区别

- 30 秒：flush 把 SQL 发到当前事务并获得 ID，仍可 rollback；commit 才结束事务并使其持久可见。
- 深挖：`expire_on_commit=False` 让对象保留值，但不改变一致性语义。
- 证据：BaseRepository/session config。
- 边界：文件写入不随 rollback 撤销。

### Q095 [API] GET 为什么可能写文件

- 30 秒：兼容旧 run 时 service 可能补生成 manifest/flow/zone 派生 artifact，所以“读取接口”在文件系统层并非严格无副作用。
- 深挖：把 repair/materialization 移到显式 job 或写 side-effect audit。
- 证据：TrafficAnalysisService compatibility paths。
- 边界：HTTP 语义与内部缓存写需要明确区分。

### Q096 [Artifact] JSONL 损坏怎么办

- 30 秒：兼容层返回 warning/错误而非伪造数据，测试覆盖 parse failure；系统仍可尝试 DB 数据或其他 artifact。
- 深挖：逐行 checksum、atomic rename、quarantine 和 repair tool。
- 证据：artifact compatibility tests。
- 边界：当前无自动修复。

### Q097 [导入] Artifact 导入如何幂等

- 30 秒：使用稳定记录 ID和已存在检查，重复导入不应重复新增；CLI 先支持 dry-run。
- 深挖：批量事务、冲突报告、内容 hash 与 source manifest version。
- 证据：`scripts/import_artifacts_to_db.py`、idempotency tests。
- 边界：幂等不自动解决源内容改变。

### Q098 [Manifest] required/optional/planned 有何区别

- 30 秒：required 是该 stage 应产生；optional 依配置/数据；planned 是契约预留；它们再分别有 available/empty/missing/error。
- 深挖：acceptance 应按执行模式动态计算 required 集合。
- 证据：artifact writer/manifest tests。
- 边界：planned 不是已实现。

### Q099 [性能] 大 JSONL 如何分页

- 30 秒：当前本地读取适合小中型 run；大 run 应流式解析、建立 DB/Parquet 索引，API 用 cursor 按 frame/time 分页。
- 深挖：避免每次 summary 扫全文件，预计算列式统计。
- 证据：artifact format 与 analysis API。
- 边界：无大规模性能数据。

### Q100 [API] 列表分页如何稳定

- 30 秒：使用确定性排序键，如 timestamp+ID，并在 filters 后分页；offset 在数据变动时会漂移，cursor 更稳。
- 深挖：定义 snapshot/version 和 total count 成本。
- 证据：analysis run list/filter tests。
- 边界：各资源分页契约并非完全统一。

### Q101 [API] Pydantic 能阻止所有坏输入吗

- 30 秒：只能验证声明 schema；文件内容、跨实体引用、polygon 语义和业务权限还需服务层/DB检查。
- 深挖：区分 syntactic、semantic、authorization、trust-boundary validation。
- 证据：schemas 与 API validation tests。
- 边界：测试有 4 条 Starlette 422 常量弃用 warning。

### Q102 [前端] `as T` 为什么不安全

- 30 秒：TypeScript 类型在运行时擦除，后端缺字段或类型错仍会被 cast，直到渲染失败。
- 深挖：用 OpenAPI generated types 加 Zod 等边界验证，错误进入统一 error boundary。
- 证据：`frontend/src/api/client.ts`。
- 边界：当前 build 通过不证明响应兼容。

### Q103 [前端] 视频时间与 frame index 如何同步

- 30 秒：用视频 currentTime/FPS 映射帧并选择邻近记录，但 VFR、stride 和 rounding 会造成偏差。
- 深挖：后端输出精确 timestamp，前端按时间索引而非假定固定 FPS。
- 证据：Analysis Detail/overlay utilities。
- 边界：无浏览器视觉 E2E。

### Q104 [前端] 怎样设计 loading/error/empty 状态

- 30 秒：三者语义不同：loading 不能操作，error 给重试/请求 ID，empty 解释无数据可能是 dry-run/未生成，而不是报错。
- 深挖：并行子资源应局部降级，避免一个 artifact 失败清空全页。
- 证据：pages/components 与前端 tests。
- 边界：当前 accessibility/视觉回归未系统验证。

### Q105 [前端] 下载报告如何避免内存和安全问题

- 30 秒：使用流式响应、正确 Content-Type/Disposition、文件名净化、授权检查，CSV 防公式注入，较大 bundle 异步生成。
- 深挖：预签名短期 URL、checksum 和审计下载。
- 证据：reports endpoints/frontend Report page。
- 边界：当前 bundle 只是 metadata，不是大文件 zip。

## 第三部分：质量、评测、交付与压力面（Q106–Q150）

### Q106 [Review] Review status 与 Alert status 是否重复

- 30 秒：不重复；Alert status 是处置进度，Review status 是对事件真实性/复核结论的记录。
- 深挖：可建立显式映射但不要让一个状态覆盖另一个事实。
- 证据：alerts/review schemas 与 API。
- 边界：resolved 不自动表示 true positive。

### Q107 [Review] 两个复核者同时操作怎么办

- 30 秒：当前缺强并发控制，可能 last-write-wins；生产应加 version/ETag、optimistic locking 和冲突响应。
- 深挖：需要 review assignment、双人裁决和 append-only action history。
- 证据：Review service/ORM 当前字段。
- 边界：actor header 未认证。

### Q108 [Review] 评论能否作为合规审计

- 30 秒：不能；评论和应用日志可追踪本地动作，但身份不可信、记录可变且无不可抵赖签名。
- 深挖：append-only audit、可信身份、时间戳、hash chain/外部归档和保留策略。
- 证据：ReviewComment、security ops。
- 边界：不要宣称满足法规审计。

### Q109 [Bad Case] 从多个来源创建如何去重

- 30 秒：可依据 source reference/run/event/failed-case 构造稳定键，当前服务对特定来源有 dedup 测试。
- 深挖：内容相似去重还需 frame hash/embedding，并保留 merge provenance。
- 证据：stage8 bad-case tests。
- 边界：手工 case 不一定可自动判重。

### Q110 [Bad Case] fixed 和 verified 有什么区别

- 30 秒：fixed 表示修复候选已通过某次 replay，verified 应表示按批准协议复验；当前状态语义仍是轻量工作流。
- 深挖：定义 owner、verification run、dataset/model version 和 reopen condition。
- 证据：BadCase schema、regression metrics。
- 边界：状态不代表生产长期无回归。

### Q111 [Evaluation] Dataset Registry 保存什么

- 30 秒：保存 dataset ID、类型、路径/metadata 等登记信息，让 evaluation run 引用 expected data。
- 深挖：正式 registry 还要不可变版本、checksum、license、标注 schema、split 和审批。
- 证据：EvaluationDataset ORM/schema/service。
- 边界：tracked `evals/datasets` 没有正式数据集。

### Q112 [Evaluation] 评测 CLI 是只读的吗

- 30 秒：不是；即使 `--no-write-db`，运行评测仍会写 eval artifact，`--write-db` 还会提交数据库。
- 深挖：dry-run/preview 应与真正 execution 分开，并显式输出目标目录。
- 证据：`scripts/run_evals.py`、EvaluationService。
- 边界：本次审计没有对用户本机 run 执行评测。

### Q113 [Evaluation] expected 与 actual 的 track ID 不一致怎么办

- 30 秒：track constraint 应可选；跨 tracker/run 的局部 ID 不稳定，优先用事件类型、zone 和时间区间，必要时建立轨迹匹配。
- 深挖：temporal/spatial bipartite matching 比直接 ID equality 更稳。
- 证据：event matcher 支持可选 track/zone。
- 边界：当前简单匹配协议有限。

### Q114 [Evaluation] 为什么 accuracy 名称可能误导

- 30 秒：项目事件 accuracy 近似 TP/expected，没有 TN，和分类 `(TP+TN)/all` 不同。
- 深挖：报告中应展示公式，优先 precision/recall/F1 和 count error。
- 证据：EvaluationService metric formula/tests。
- 边界：不能跨任务直接比较 accuracy。

### Q115 [Evaluation] expected=0 时 MAPE 怎么算

- 30 秒：标准 MAPE 分母为零不可定义，需跳过、特殊报告或改用 WAPE/sMAPE/absolute error。
- 深挖：同时报告零流量 bucket 数，避免选择性忽略。
- 证据：flow metric implementation/tests。
- 边界：toy expected 没覆盖所有零值场景。

### Q116 [Evaluation] Detection GT 应怎样组织

- 30 秒：每帧 image/video ID、class、xyxy/xywh、ignore/crowd 与分辨率，并 pin dataset version。
- 深挖：优先兼容 COCO format，做 annotation QA 和 split leakage 检查。
- 证据：当前 evaluation detection input contract。
- 边界：仓库没有 tracked 正式 detection GT。

### Q117 [Evaluation] MOTA 高但 IDF1 低说明什么

- 30 秒：检测总体错误可能少，但身份连续性差、ID switch 多；对轨迹事件和流量去重仍可能有严重影响。
- 深挖：联合看 HOTA、IDSW、fragmentation 和下游事件误差。
- 证据：lightweight tracking metrics fields。
- 边界：当前不是官方 TrackEval 结果。

### Q118 [Evaluation] 轨迹准确率怎样真正评

- 30 秒：需要 GT 轨迹，用 ADE/FDE、点到轨迹距离、coverage、fragmentation，并在像素或标定世界坐标报告。
- 深挖：时间对齐、遮挡 ignore、采样率和 track association 必须固定。
- 证据：当前 trajectory evaluation 只有描述统计。
- 边界：direction availability 不是 accuracy。

### Q119 [Report] 为什么不直接选分数最高的评测

- 30 秒：选最高会产生 cherry-picking；当前选 latest 是简单策略，正式报告应 pin 经批准的 evaluation run/dataset/model。
- 深挖：发布审批与 immutable report manifest。
- 证据：ReportService latest selection。
- 边界：latest 也不自动等于 approved。

### Q120 [Report] 手写 PDF 的局限是什么

- 30 秒：Helvetica/Latin-1 导致中文替换，布局和分页能力有限，适合轻量英文摘要。
- 深挖：可改 HTML→PDF/ReportLab 并嵌字体、做 golden render 和 accessibility。
- 证据：report PDF renderer/tests。
- 边界：当前 PDF 不是完整 Web 镜像。

### Q121 [Report] CSV 导出有什么安全问题

- 30 秒：以 `= + - @` 开头的用户字段可能触发表格公式注入，应转义/前缀处理并用正确编码。
- 深挖：同时防 delimiter/newline 注入和超大导出内存。
- 证据：CSV report sections 与用户可编辑字段。
- 边界：当前是否覆盖全部公式注入需额外安全测试。

### Q122 [Report] 真正的证据 bundle 应包含什么

- 30 秒：versioned manifest、summary、原始结构化结果、关键帧/视频引用或副本、checksums、config/model/input provenance 和签名。
- 深挖：按权限/保留策略生成 zip/TAR 或对象存储快照。
- 证据：当前 bundle endpoint 只返回 metadata。
- 边界：不要把当前接口称归档包。

### Q123 [Report] 为什么强调非执法结论

- 30 秒：规则与模型会误报漏报，当前无正式认证、标定和法规审计，报告只能辅助分析与复核。
- 深挖：高风险用途需人类决策、可申诉、校准、合规和持续监控。
- 证据：README/reporting docs/报告内容。
- 边界：不能用演示输出直接处罚。

### Q124 [Security] permissive 模式什么时候可用

- 30 秒：仅可信本地开发/演示；一旦有网络暴露或多用户就必须禁用并接可信身份。
- 深挖：启动时检测环境，production profile 遇 permissive 应 fail-fast。
- 证据：`.env.example`、security helper。
- 边界：CORS 不能弥补无认证。

### Q125 [Observability] Request ID 应如何贯穿异步任务

- 30 秒：HTTP request ID 与 durable task/run correlation ID 分开保存，队列消息和日志都携带 trace context。
- 深挖：重试用同 task ID、新 attempt ID，避免日志混淆。
- 证据：当前 middleware/request ID 与 run/task IDs。
- 边界：当前没有异步 trace propagation。

### Q126 [Security] CORS 是认证吗

- 30 秒：不是；CORS 是浏览器同源读取策略，非浏览器客户端仍可调用，不能代替身份与授权。
- 深挖：严格 origin allowlist、credentials 和 CSRF 策略仍需配合认证。
- 证据：application CORS config。
- 边界：允许源配置不证明接口安全。

### Q127 [Security] RTSP 密钥如何管理

- 30 秒：不应把用户名密码写入普通 DB/日志/错误；使用 secret manager 引用、短期凭据、加密和轮换。
- 深挖：URL 展示要脱敏，worker 按权限解析 secret，审计访问而不记录值。
- 证据：当前错误关键词脱敏与 camera source fields。
- 边界：当前没有完整 secret storage。

### Q128 [Privacy] 视频和关键帧应保留多久

- 30 秒：由用途、法规和最小化原则决定，设置 source/derived artifacts 的独立 TTL、legal hold 和删除审计。
- 深挖：删除要覆盖 DB、对象、缓存、备份和导出，并处理关联 report。
- 证据：当前本地目录无自动 retention worker。
- 边界：具体法域策略 `【本人待补充】`，不能武断给天数。

### Q129 [CI] 仓库为什么没有 CI 是什么风险

- 30 秒：验证依赖人工，本地通过不能保证每个 commit/PR 都执行相同 gate，也无法防环境漂移。
- 深挖：先加 backend/frontend/build/compose/danger，后加 E2E/benchmark/nightly。
- 证据：无 tracked `.github`/其他 CI 配置。
- 边界：不要说 CI green。

### Q130 [Test] 临时 SQLite 测试隔离怎样工作

- 30 秒：autouse fixture 为每个测试创建 `tmp_path` DB、override `get_db`、create/drop schema 并清 engine cache。
- 深挖：隔离文件 I/O 目录和全局 service cache同样重要。
- 证据：`backend/tests/conftest.py`。
- 边界：SQLite 测试不能完全代表 PostgreSQL 语义。

### Q131 [Test] 4 条 deprecation warning 怎么处理

- 30 秒：来自 Starlette 的 `HTTP_422_UNPROCESSABLE_ENTITY` 常量弃用，应定位项目/依赖调用并迁移到新常量，避免未来升级失败。
- 深挖：把 warning baseline 纳入 CI，新增 warning fail 或分阶段清零。
- 证据：本次 487 tests 输出。
- 边界：warning 不影响本次 pass，但属于兼容债。

### Q132 [Test] 最应该补的三类测试是什么

- 30 秒：真实模型固定集回归、Playwright 浏览器 E2E、异步/实时/故障恢复与性能测试。
- 深挖：按风险再补上传安全、DB迁移和多 worker 去重。
- 证据：当前测试清单与缺失依赖。
- 边界：测试数量不是目标，风险覆盖才是。

### Q133 [Observability] 生产应监控哪些指标

- 30 秒：队列深度/等待、stage latency、FPS、decode/model errors、GPU/CPU/内存、event/alert rate、review FP/FN、artifact/DB mismatch。
- 深挖：用 SLO 将技术指标与 run success/freshness 绑定。
- 证据：当前只有 request ID/readiness/日志基础。
- 边界：仓库无 metrics endpoint/OTel。

### Q134 [Ops] readiness 的 `SELECT 1` 足够吗

- 30 秒：只证明 DB 基本可连接；不证明模型可加载、目录可写、磁盘充足、队列/对象存储或依赖健康。
- 深挖：区分 liveness/readiness/startup，按 service role 设计依赖检查并避免重检查放大故障。
- 证据：health API。
- 边界：当前本地两服务场景较简单。

### Q135 [Ops] SQLite 和 artifacts 如何备份恢复

- 30 秒：需一致快照、artifact checksums、run manifest 和恢复演练；简单复制活动 SQLite 与目录可能时间点不一致。
- 深挖：停写/online backup API、版本化对象存储、restore validation 与 RPO/RTO。
- 证据：当前本地 DB/files 架构。
- 边界：仓库无备份自动化或灾备演练。

### Q136 [压力] 这不就是一个包装得很漂亮的 YOLO Demo 吗

- 30 秒：如果只看默认 dry-run，算法效果确实不能高估；但仓库真实增加了 run provenance、轨迹规则、event/evidence/execution、告警复核、Bad Case、六类评测和报告闭环。准确定位是端到端验证平台，而不是生产模型系统。
- 深挖：现场从 process 入口讲到 review/evaluation 输出和测试，不用页面数量辩护。
- 证据：八条调用链与功能—证据矩阵。
- 边界：承认真实模型 benchmark 缺失。

### Q137 [压力] 487 个测试大部分都是 mock，有什么意义

- 30 秒：它们证明契约、规则、几何、事务和错误处理可重复，不证明模型泛化。mock 的价值和限制都明确，下一层必须补真实模型固定集和 E2E。
- 深挖：按测试层级给出信号、成本和 gate，不拿数量压人。
- 证据：test names、fixtures、验证输出。
- 边界：没有 CI 与真实依赖 acceptance。

### Q138 [压力] 本机评测是 1.0，你是不是做了数据泄漏

- 30 秒：我不会把本机 ignored 结果当正式结论；tracked expected 里有 toy/specific demo 标签，1.0 可能只说明样例与输出匹配。没有 dataset split、正式结果和独立 benchmark，就不能推断泛化或排除泄漏。
- 深挖：建立 immutable train/val/test、盲测、dataset hash 和标准工具。
- 证据：`evals/expected/` 与 ignored `evals/results/` 边界。
- 边界：不引用未审计本机分数作简历指标。

### Q139 [压力] 类名叫 DeepSortTracker 却默认不是 DeepSORT，是否误导

- 30 秒：命名确实可能误导，这是我会明确披露并改进的地方。当前 adapter contract 支持真实库，但默认可复现路径是 fallback；生产应重命名/显式 backend 字段并在缺依赖时 fail-fast。
- 深挖：展示 requirements 与 import fallback，而不是回避。
- 证据：tracker source、requirements。
- 边界：不认领未运行算法效果。

### Q140 [压力] RTSP 页面是假功能吗

- 30 秒：它是契约/UI preview，不是实时流功能；如果页面文案暗示已连接，应修正文案和状态。保留它的价值是先验证 camera lifecycle，但不能作为实时能力交付。
- 深挖：给出单路 RTSP 最小真实验收清单。
- 证据：realtime worker/tests。
- 边界：明确 Not Implemented 的部分。

### Q141 [压力] 把视频推理放 HTTP 请求里是不是很业余

- 30 秒：对生产确实不合适；对本地 MVP它降低了队列和一致性复杂度，使功能闭环先可验证。关键是明确退出条件，并按任务可恢复、幂等和资源隔离迁移。
- 深挖：画出 worker/outbox/heartbeat/cancel 设计和风险排序。
- 证据：process route 当前调用链。
- 边界：不声称能撑生产并发。

### Q142 [压力] DB 和文件双写不是架构混乱吗

- 30 秒：它是从 artifact-first 演进到 DB-first 的兼容债，收益是旧 run 可读，代价是双源一致性。现状有 fallback/导入/manifest，但生产应设迁移结束条件并选择唯一权威源。
- 深挖：提出 reconciliation、checksum 和 atomic publish。
- 证据：compatibility service/tests。
- 边界：承认当前非强一致。

### Q143 [压力] 没有认证还谈什么平台

- 30 秒：它只能叫可信本地环境下的验证平台，不能暴露给不可信网络。权限头是接口预览，不是安全交付；生产化的第一 gate 就是可信身份与对象级授权。
- 深挖：给出 OIDC/JWT、RBAC、tenant、audit、secret 路线。
- 证据：security helper/env。
- 边界：不拿 CORS/strict 模式搪塞。

### Q144 [压力] 为什么自己写 AP/MOTA，不用标准库

- 30 秒：轻量实现能在无额外依赖的 MVP 验证数据链路和失败样本，但不能替代标准 benchmark。正式发布应适配 pycocotools/TrackEval，并用当前实现做快速 smoke。
- 深挖：比较两层评测的速度、协议和权威性。
- 证据：requirements、evaluation metrics/tests。
- 边界：指标名不等于标准实现。

### Q145 [压力] 这个项目最大的失败是什么，为什么还值得讲

- 30 秒：最大缺口是页面和契约完整度高于真实模型/实时/生产验证；如果不说明会造成能力错觉。它仍值得讲，因为 run 可追溯、规则解释和质量闭环是可验证工程资产，同时缺口能展示风险判断与演进能力。
- 深挖：选择本人真实复盘案例 `【本人待补充】`，给出已做/未做分界。
- 证据：能力成熟度矩阵。
- 边界：不把“未来会做”算当前成果。

### Q146 [行为] 你与团队对架构意见不一致怎么办

- 30 秒：`【本人待补充】`；用具体约束、可逆性、数据和小实验比较，不把技术偏好当结论。
- 深挖：按 STAR 讲分歧、本人行动、决策记录、结果和关系维护。
- 证据：真实 ADR/PR/会议记录 `【本人待补充】`。
- 边界：不要虚构冲突或把同事写成反派。

### Q147 [行为] 讲一次你引入的缺陷

- 30 秒：`【本人待补充】`；主动说明影响、发现方式、止损、根因、测试和流程改进。
- 深挖：区分个人责任与系统原因，给可验证修复。
- 证据：真实 commit/test/incident `【本人待补充】`。
- 边界：不要用无关小错误逃避。

### Q148 [行为] 时间不足时你如何砍范围

- 30 秒：按用户主路径、安全/数据损失风险和可验证 acceptance 排序；SmartTraffic 会保留离线单视频闭环，明确砍掉伪实时、HA 和非关键导出。
- 深挖：说明怎样与 stakeholder 对齐“不做清单”。
- 证据：真实项目计划 `【本人待补充】`。
- 边界：不能为赶时间砍安全与事实边界。

### Q149 [行为] 你如何快速学会陌生模块或使用 AI

- 30 秒：`【本人待补充】`；先画入口—核心—输出—调用方—测试，AI 只做检索/草案，结论回到代码和运行验证。
- 深挖：讲一次 AI/资料给出错误答案后如何纠正。
- 证据：真实工作记录 `【本人待补充】`。
- 边界：不隐藏 AI，也不转移最终责任。

### Q150 [行为] 你如何定义这个项目成功

- 30 秒：仓库层成功是主链可运行、结果可追溯、规则可解释、质量问题可闭环且验证通过；业务层成功指标必须由真实用户/SLO/数据集定义：`【本人待补充】`。
- 深挖：区分 delivery、quality、adoption、operation 四类指标及反指标。
- 证据：当前 tests/artifacts；外部指标 `【本人待补充】`。
- 边界：不拿代码量、页面数或 toy F1 代替业务成功。

## 第四部分：四轮模拟面试

### 模拟面试 A：全栈项目面（45 分钟）

| 项目 | 内容 |
|---|---|
| 流程 | 5 分钟介绍 → 15 分钟主调用链 → 10 分钟数据/前端 → 10 分钟可靠性 → 5 分钟反问 |
| 提问顺序 | Q001 → Q004 → Q007 → Q008 → Q027 → Q028 → Q102 → Q043 → Q044 |
| 重点追问 | task 是否异步；DB/文件冲突；GET 副作用；前端 runtime type；失败恢复 |
| 必须说 | run、三种 mode、同步执行、DB-first/fallback、十页面、测试边界 |
| 不能说 | React Router、Celery、强一致、E2E 已覆盖、生产上线 |
| 评分 | 定位 15；调用链 25；事实证据 20；取舍 20；边界与表达 20；低于 70 需重练 Q001/Q004/Q028 |

### 模拟面试 B：CV/算法工程面（50 分钟）

| 项目 | 内容 |
|---|---|
| 流程 | 5 分钟 pipeline → 15 分钟 detection/tracking → 15 分钟 trajectory/events → 10 分钟 evaluation → 5 分钟改进 |
| 提问顺序 | Q010 → Q012 → Q013 → Q015 → Q016 → Q019 → Q023 → Q024 → Q033 → Q034 |
| 重点追问 | NMS 责任；fallback 是否 DeepSORT；px/s；曲线逆行；滑窗；AP/HOTA 标准 |
| 必须说 | Ultralytics 负责前后处理；fallback 无 ReID/Kalman/Hungarian；六类规则；指标为 MVP |
| 不能说 | 自研 YOLO、ByteTrack、km/h、COCO mAP、官方 TrackEval、真实 benchmark 1.0 |
| 评分 | 算法原理 25；代码对应 25；误差分析 20；评测严谨 20；诚信 10 |

### 模拟面试 C：后端/系统设计面（55 分钟）

| 项目 | 内容 |
|---|---|
| 流程 | 8 分钟现状架构 → 12 分钟任务系统 → 12 分钟存储一致性 → 10 分钟安全/观测 → 8 分钟迁移 → 5 分钟反问 |
| 提问顺序 | Q003 → Q006 → Q047 → Q055 → Q028 → Q046 → Q093 → Q124 → Q133 → Q044 |
| 重点追问 | at-least-once；幂等键；outbox；状态机；迁移回滚；OIDC；SLO |
| 必须说 | 当前同步/SQLite/本地文件；文件不在 DB 事务；无 CI/queue/auth；按风险演进 |
| 不能说 | exactly-once 已实现、Alembic 安全、strict auth 可信、readiness 完整 |
| 评分 | 现状理解 20；系统设计 30；一致性 20；安全可靠性 20；落地顺序 10 |

### 模拟面试 D：压力与行为面（40 分钟）

| 项目 | 内容 |
|---|---|
| 流程 | 5 分钟电梯陈述 → 15 分钟连续质疑 → 15 分钟行为案例 → 5 分钟复盘 |
| 提问顺序 | Q136 → Q139 → Q140 → Q138 → Q143 → Q145 → Q041 → Q146 → Q147 → Q150 |
| 重点追问 | 为何不是包装；个人具体动作；失败证据；AI 使用；未完成能力如何表达 |
| 必须说 | 先承认有效质疑，再给代码证据、当前价值和演进 gate；个人内容只讲真实经历 |
| 不能说 | 防御性夸张、归咎他人、虚构数字、把规划算成果、用页面截图替代证据 |
| 评分 | 压力稳定 20；事实诚信 25；个人所有权 25；复盘 15；沟通 15；任何虚构项直接不通过 |

## 第五部分：知识点到题目映射

| 知识点 | 对应题目 | 知识点 | 对应题目 |
|---|---|---|---|
| K01 | Q001、Q002、Q136 | K37 | Q020、Q082 |
| K02 | Q001、Q040、Q138 | K38 | Q021、Q083 |
| K03 | Q005、Q052 | K39 | Q022、Q084 |
| K04 | Q007、Q037、Q140 | K40 | Q023、Q079、Q085 |
| K05 | Q003、Q004 | K41 | Q024、Q086 |
| K06 | Q006、Q141 | K42 | Q025、Q088、Q089 |
| K07 | Q007、Q100 | K43 | Q026、Q106 |
| K08 | Q008、Q103 | K44 | Q026、Q106、Q107 |
| K09 | Q050、Q063 | K45 | Q090 |
| K10 | Q005、Q010、Q063 | K46 | Q047、Q094 |
| K11 | Q011、Q137 | K47 | Q092 |
| K12 | Q049、Q125 | K48 | Q093 |
| K13 | Q009、Q056 | K49 | Q028、Q142 |
| K14 | Q057 | K50 | Q098 |
| K15 | Q058 | K51 | Q027、Q095、Q097 |
| K16 | Q090 | K52 | Q027、Q099、Q100 |
| K17 | Q010、Q059 | K53 | Q017、Q103 |
| K18 | Q010、Q062 | K54 | Q102、Q104 |
| K19 | Q010、Q144 | K55 | Q029、Q106、Q107 |
| K20 | Q063、Q064 | K56 | Q030 |
| K21 | Q012、Q065、Q139 | K57 | Q031、Q109、Q110 |
| K22 | Q013、Q069 | K58 | Q035、Q110 |
| K23 | Q013、Q066、Q067 | K59 | Q032、Q113、Q114 |
| K24 | Q014、Q069 | K60 | Q115 |
| K25 | Q017、Q071 | K61 | Q033、Q116、Q144 |
| K26 | Q015、Q058 | K62 | Q034、Q117、Q144 |
| K27 | Q016、Q075 | K63 | Q035、Q118 |
| K28 | Q020、Q074 | K64 | Q036、Q119 |
| K29 | Q017、Q072、Q076 | K65 | Q036、Q105、Q120–Q122 |
| K30 | Q024、Q073、Q086 | K66 | Q119 |
| K31 | Q017、Q076 | K67 | Q037、Q140 |
| K32 | Q077、Q083 | K68 | Q039 |
| K33 | Q018、Q078、Q079 | K69 | Q040、Q129–Q132、Q137 |
| K34 | Q024、Q080 | K70 | Q038、Q124、Q126–Q128、Q143 |
| K35 | Q018、Q079、Q087 | K71 | Q006、Q059、Q064、Q099、Q133、Q141 |
| K36 | Q019、Q081 | K72 | Q044、Q045、Q136、Q145–Q150 |

## 第六部分：覆盖与自检

- 题目总数：150，连续编号 Q001–Q150。
- 完整模板：Q001–Q045，共 45 题；均包含类别、问题、考察点、30 秒、90 秒、深挖、追问、证据、易错点、事实边界。
- 紧凑深挖：Q046–Q150，共 105 题；均包含短答、深挖、证据和边界。
- 压力题：Q136–Q145 共 10 题；此外 Q023、Q028、Q033、Q034、Q037、Q038 也可作压力追问。
- 行为/个人题：Q041、Q042、Q045、Q146–Q150；所有不可由仓库证明的内容均使用 `【本人待补充】`。
- 模拟面试：全栈、CV、后端系统设计、压力行为共 4 轮，均含流程、顺序、追问、必说、禁说和评分。
- 知识映射：K01–K72 每项至少对应一道题，无孤立知识点。
- 功能覆盖：视频、检测、跟踪、轨迹、Zone/Rule、六类事件、告警、Analysis、Review、Bad Case、Evaluation、Report、Realtime、Docker、安全、测试与生产化均有独立题目。
- 术语边界：始终使用“YOLO adapter”“DeepSortTracker adapter / deterministic fallback”“像素速度”“连续帧拥堵 MVP”“realtime contract preview”“轻量评测”，不替换为未经证实的更强能力。
