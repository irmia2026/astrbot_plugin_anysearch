# AnySearch 插件迭代笔记

TASK-20260603-002 · 迭代已完成的 astrbot_plugin_anysearch

---

## 已修改

### 第一轮（LLM 视角审视）

- **工具描述重写** — 初版"全文摘要"措辞模糊（全文和摘要互斥），改为"返回网页全文内容（非简短摘要）"。新增与 Tavily 的分工说明。（第二轮用户要求移除 Tavily 引用，因为定位是独立工具。）
- **新增 freshness 参数** — API 支持 `constraint.freshness`（day/week/month/year）但初版未暴露。这对 LLM 是高频需求（"搜最近一周的某某"），增加后 LLM 无需人工拼接时间约束到 query 中。
- **max_results 上限补全** — 初版只做了下限 clamp（≥1），未做上限 clamp。现加上 `min(n, 100)`。
- **返回字段优化** — 移除 `search_time_ms`（LLM 不需要，纯噪音）；新增 `query` 回显（方便 LLM 多轮调用追踪）；每条结果新增 `index` 字段（1-based），方便 LLM 引用；新增 `content_truncated` 布尔标记。
- **内容智能截断** — 初版硬截断到 2000 字符可能断在词中。现查找最后一个句末标点（。！？.!?\n）在 max_len-120~max_len 范围内截断，找不到才硬截。
- **空结果表达** — 新增 `note: "未找到相关结果"`，避免 LLM 对着空 results 数组困惑。
- **content 字段不再回退到 description** — 初版 `content or description or ""` 混淆了两个字段语义。现 content 为空就为空，description 始终独立保留。
- **429 错误消息健壮化** — Retry-After 标头缺失或非数字时不再显示"未知秒后重试"，改为"请稍后重试"。

### 第二轮（对标 irmia_devkit_open）

- **响应格式对齐 devkit 协议** — 初版成功返回 `{"ok": true, "results": [...], "query": "..."}` 直接平铺。现改为 `{"ok": true, "data": {"query": "...", "results": [...], ...}}`，与 devkit 的 `_unwrap` → `{"ok": true, "data": result}` 模式一致。
- **移除 retryable 字段** — devkit 的 `_unwrap` 不保留额外字段于错误响应体中，retryable 是对协议的偏离。LLM 可从错误消息内容推断是否可重试。
- **新增 _err / _ok 辅助函数** — 对应 devkit 的 `err_json()` 和 `unwrap()`，保证所有响应形状一致，避免手拼 JSON 遗漏 `ensure_ascii=False` 或格式偏差。
- **async handler 增加 try/except** — 对齐 devkit 的 `call()` 方法中 `except Exception → _err(f"tool_name 失败: {e}")` 模式，确保任意 Python 异常都被捕获并返回结构化错误，不会裸奔到 AstrBot 框架层。
- **工具描述浓缩为 devkit 风格** — 采用 `【互联网深度搜索】` 前缀（对标 `【HTTP GET 唯一选择】`），移除行内参数列举（参数语义由 schema 定义，devkit 描述也不列举参数），聚焦"做什么、何时用、有何限制"。
- **错误消息精简** — 去掉多余前缀和冗余表述，对齐 devkit 简洁中文错误风格。

### 第三轮（用户反馈）

- **移除 Tavily 引用** — 工具描述中的 Tavily 分工说明和 402 错误中的"可改用 Tavily"提示均已移除。此插件定位为独立工具，不应假设其他工具存在。

## 审视但未改

- **domains 参数保持 string（逗号分隔）而非 enum** — 22 个领域在参数描述中枚举已足够 LLM 正确传递，转成 enum 增加 JSON 体积且限制 API 扩展。
- **description 字段保留不删** — 体积小（几十字），删除节省 token 有限，摘要级速览仍有 LLM 推理价值。
- **不增加 language 参数** — zone: cn 已暗含中文偏好，再加 language 造成参数冗余和 LLM 选择困难。
- **不增加 constraint.freshness 以外的 constraint 字段** — API 完全体 constraint 子字段未文档化，过度暴露增加 LLM 出错概率。
- **不做 domains 客户端校验** — 无效 domain 被 API 4xx 拒绝，客户端枚举列表引入维护负担。
- **工具名 anysearch_search 不变** — 遵循 `<服务名>_<动词>` 模式，与现有 `task_list`、`task_archive` 风格一致。
- **不使用 @dataclass + call() 模式** — devkit 全部工具使用此模式，但 handler-based 方式更简洁且同样满足需求。如需访问 context 或添加 tool_stats，切换成本很低。

## 如果重来一次（TASK-001 设计阶段反思）

- **先读 devkit 架构，再设计** — 应该先读完 ARCHITECTURE.md 理解响应协议三形态，再动手写代码。初版返回格式与 devkit 不一致是本迭代最大的教训——如果设计阶段就对齐，少改一轮。
- **描述优先于实现** — 应该先把工具描述当作设计文档写清楚（聚焦"做什么、何时用"），再实现代码。
- **返回字段设计应区分"给 LLM 的数据"和"给调试的元数据"** — search_time_ms 属于后者，初版不该混入返回体。
- **截断策略应早于实现想清楚** — 2000 字符硬截断"看起来合理"，但对 LLM 而言，一个未完成的句子比没有该句子更糟。

### 第四轮（运行时调试 — 弥亚）

- **handler 签名修正** — 初版签名 `async def anysearch_search(query, ...)` 在 AstrBot 框架中始终报 `TypeError: got multiple values for argument 'query'`。根因：`star_manager.py` 对所有 `FunctionTool(handler=...)` 的 handler 做了 `functools.partial(handler, star_cls_instance)`，将 Star 实例预绑定为第一个位置参数。AstrBot 调用链为 `partial(原函数, star)(event, **tool_args)` → `原函数(star, event, **tool_args)`。正确签名为 `async def anysearch_search(self, event, **kwargs)`。此行为未在 AstrBot 文档中明确说明，仅能从源码 `star_manager.py:1065` 推断。教训：裸函数 handler 的签名必须包含 `self`（Star 实例）+ `event`（AstrMessageEvent），否则框架级 `functools.partial` 注入会导致参数偏移。

- **AnySearch 响应格式与文档不一致** — 官方文档描述返回 `{"results": [...], "metadata": {...}}`，但实际匿名端点返回 `{"code": 0, "message": "success", "data": {"results": [...]}}`，结果多了一层 `data` 包裹。初版代码按文档在顶层取 `data.get("results")` → 永远是空数组。修复为 `data.get("data", data).get("results")`，同时兼容文档格式和实际格式。教训：第三方 API 的文档不一定和实际行为一致，上线前务必裸调一次 API 验证响应结构。
