# AnySearch 搜索插件

**匿名深度搜索工具**——返回网页全文内容，不是摘要片段。每天 1000 次免费配额，无需 API Key。

## 为什么用这个？

和 Tavily 的区别：Tavily 给的是 snippet（摘要），AnySearch 给的是全文 content。当你需要读原文细节（技术文档、安全分析、学术论文、法律条文）时，全文比摘要管用得多。

## 安装

丢到 AstrBot 的 `data/plugins/` 下，重载即可。

```bash
git clone https://github.com/irmia2026/astrbot_plugin_anysearch.git
```

不需要配置——匿名端点，即装即用。

## 工具

| 工具名 | 用途 |
|--------|------|
| `anysearch_search` | 互联网深度搜索，返回全文内容 |

参数：`query`（必填）、`max_results`（1-100，默认 5）、`domains`（22 个领域可选）、`zone`（cn/intl）、`freshness`（day/week/month/year）。

## 限制

- 匿名端点每天 1000 次，按 IP 限速
- content 超过 2000 字符会在句末截断
- `quality_score` 匿名端点一律为 0

## 作者

伊尔弥亚 — 弥亚庄园的祭司小姐，偶尔写代码。

[irmia2026](https://github.com/irmia2026)
