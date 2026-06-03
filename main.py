import json

import requests

from astrbot.api import FunctionTool, logger, star

ENDPOINT = "https://api.anysearch.com/v1/search"
CONTENT_MAX = 2000

_TOOL_DESC = (
    "【互联网深度搜索】返回网页全文内容，非简短摘要。"
    "适合技术文档、学术论文、安全分析、事实核查等需要原文细节的场景。"
    "匿名访问，每天1000次免费配额。15s超时，content超2000字符在句末截断。"
)

_TOOL_PARAMS = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "搜索关键词，支持自然语言"},
        "max_results": {"type": "integer", "description": "返回条数，1-100，默认 5"},
        "domains": {"type": "string", "description": "领域过滤，逗号分隔，如 tech,academic,security"},
        "zone": {"type": "string", "enum": ["cn", "intl"], "description": "搜索区域：cn 侧重中文结果，intl 全球"},
        "freshness": {"type": "string", "enum": ["day", "week", "month", "year"], "description": "时效过滤，仅返回指定时间范围内的结果"},
    },
    "required": ["query"],
}

_SENTENCE_END = {"。", "！", "？", ".", "!", "?", "\n"}


def _err(error: str) -> str:
    return json.dumps({"ok": False, "error": error}, ensure_ascii=False)


def _ok(data: dict) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _smart_truncate(text: str, max_len: int) -> tuple[str, bool]:
    if len(text) <= max_len:
        return text, False
    for i in range(max_len - 1, max(0, max_len - 120), -1):
        if text[i] in _SENTENCE_END:
            return text[:i + 1], True
    return text[:max_len], True


def _build_body(query: str, max_results: int, domains: str, zone: str, freshness: str) -> dict:
    n = max(1, min(int(max_results) if max_results else 5, 100))
    body = {"query": query, "max_results": n}
    if domains:
        body["domains"] = [d.strip() for d in domains.split(",") if d.strip()]
    if zone and zone in ("cn", "intl"):
        body["zone"] = zone
    if freshness and freshness in ("day", "week", "month", "year"):
        body["constraint"] = {"freshness": freshness}
    return body


def _search(query: str, max_results: int = 5, domains: str = "", zone: str = "", freshness: str = "") -> str:
    body = _build_body(query, max_results, domains, zone, freshness)

    try:
        resp = requests.post(ENDPOINT, json=body, timeout=15)
    except requests.exceptions.Timeout:
        return _err("AnySearch 请求超时，请稍后重试")
    except requests.exceptions.ConnectionError:
        return _err("AnySearch 服务暂不可用")
    except Exception as e:
        logger.warning(f"[AnySearch] 请求异常: {e}")
        return _err(f"AnySearch 请求失败: {e}")

    if resp.status_code == 402:
        return _err("免费配额已用完，明天自动恢复")
    if resp.status_code == 429:
        rh = resp.headers.get("Retry-After", "")
        wait = f"请 {rh}s 后重试" if rh and rh.isdigit() else "请稍后重试"
        return _err(f"请求过于频繁，{wait}")
    if resp.status_code >= 500:
        return _err("AnySearch 服务暂不可用")
    if resp.status_code != 200:
        return _err(f"AnySearch 返回异常状态码: {resp.status_code}")

    try:
        data = resp.json()
    except Exception:
        return _err("AnySearch 返回数据解析失败")

    # AnySearch 实际响应: {"code": 0, "message": "success", "data": {"results": [...]}}
    # 文档写的是 {"results": [...]}，但实际多了一层 data 包裹
    raw_results = data.get("data", data).get("results", [])
    if not raw_results:
        return _ok({"query": query, "results": [], "total_results": 0, "note": "未找到相关结果"})

    results = []
    for i, r in enumerate(raw_results):
        raw_content = r.get("content") or ""
        content, truncated = _smart_truncate(raw_content, CONTENT_MAX)
        results.append({
            "index": i + 1,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "description": r.get("description", ""),
            "content": content,
            "content_truncated": truncated,
            "quality_score": r.get("quality_score", 0),
            "published_at": r.get("published_at", ""),
        })

    return _ok({"query": query, "results": results, "total_results": len(results)})


async def anysearch_search(self, event, **kwargs) -> str:
    try:
        query = kwargs.get("query", "")
        max_results = int(kwargs.get("max_results", 5))
        domains = kwargs.get("domains", "") or ""
        zone = kwargs.get("zone", "") or ""
        freshness = kwargs.get("freshness", "") or ""
        return _search(query, max_results, domains, zone, freshness)
    except Exception as e:
        logger.error(f"[AnySearch] 工具调用异常: {e}")
        return _err(f"anysearch_search 失败: {e}")


class Main(star.Star):
    def __init__(self, context, config=None):
        super().__init__(context)
        tool = FunctionTool(
            name="anysearch_search",
            description=_TOOL_DESC,
            parameters=_TOOL_PARAMS,
            handler=anysearch_search,
        )
        context.add_llm_tools(tool)
        logger.info("astrbot_plugin_anysearch 已就绪 — anysearch_search 单工具 / 匿名 / 1000 次/天")
