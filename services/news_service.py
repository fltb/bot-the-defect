import asyncio
import httpx
import feedparser
import logging
import re

from datetime import datetime, timedelta
from typing import List, Dict, Any, Protocol
from dataclasses import dataclass, field

from config import settings

# 定义一个简单的数据结构来存储标准化的新闻条目
@dataclass
class NewsItem:
    source: str
    title: str
    link: str
    published_date: datetime
    summary: str

class ReportRenderer(Protocol):
    def render(self, items: List[NewsItem]) -> str: ...

class TextRenderer:
    def render(self, items: List[NewsItem]) -> str:
        lines = [f"{len(items)} 条新闻汇总：\n"]
        for i, it in enumerate(items, 1):
            lines.append(f"{i}. [{it.source}] {it.title}")
            if it.summary:
                lines.append(f"   摘要: {it.summary}")
            lines.append(f"   链接: {it.link}\n")
        return "\n".join(lines)

class MarkdownRenderer:
    def render(self, items: List[NewsItem]) -> str:
        lines = [f"# 新闻汇总 ({len(items)})\n"]
        for i, it in enumerate(items, 1):
            lines.append(f"## {i}. [{it.source}] {it.title}")
            if it.summary:
                lines.append(f"> {it.summary}")
            lines.append(f"[阅读原文]({it.link})\n")
        return "\n".join(lines)


class HTMLRenderer:
    def render(self, items: List[NewsItem]) -> str:
        html = ['<html><body>']
        html.append(f'<h1>新闻汇总 ({len(items)})</h1>')
        for it in items:
            html.append(f'<h2>[{it.source}] <a href="{it.link}">{it.title}</a></h2>')
            if it.summary:
                html.append(f'<p>{it.summary}</p>')
        html.append('</body></html>')
        return ''.join(html)


class NewsService:
    def __init__(self):
        self.feeds = settings.RSS_FEEDS
        self.timeout = 10
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """去除 HTML 标签"""
        return re.sub(r'<[^>]+>', '', text)

    async def _fetch_feed(self, name: str, url: str) -> List[NewsItem]:
        items: List[NewsItem] = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=self.timeout)
                resp.raise_for_status()
            parsed = feedparser.parse(resp.text)
            for entry in parsed.entries:
                pub_struct = entry.get('published_parsed') or entry.get('updated_parsed')
                if pub_struct:
                    pub_dt = datetime(*pub_struct[:6])
                else:
                    # 有时 entry.published 是字符串，尝试解析常见格式
                    raw = entry.get('published') or entry.get('updated') or ''
                    try:
                        pub_dt = datetime.fromisoformat(raw)
                    except Exception:
                        pub_dt = datetime.utcnow()
                summary = entry.get('summary', entry.get('title', ''))
                clean_summary = self._clean_html(summary)
                if len(clean_summary) > 64:
                    clean_summary = clean_summary[:61] + '...'

                items.append(NewsItem(
                    source=name,
                    title=entry.get('title', 'N/A'),
                    link=entry.get('link', '#'),
                    published_date=pub_dt,
                    summary=clean_summary
                ))

        except Exception as e:
            logging.error(f"[{name}] 获取失败: {e}")
        return items

    def _filter_items(self, items: List[NewsItem]) -> List[NewsItem]:
        logging.debug(f"Filtering items by keywords and sources: start with {len(items)} items")
        filtered = []
        for it in items:
            if settings.INCLUDE_KEYWORDS and not any(kw in it.title for kw in settings.INCLUDE_KEYWORDS):
                continue
            if it.source in getattr(settings, 'EXCLUDE_SOURCES', []):
                continue
            filtered.append(it)
        logging.debug(f"After _filter_items: {len(filtered)} items remain")
        return filtered

    def _filter_last_24h(self, items: List[NewsItem]) -> List[NewsItem]:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        logging.debug(f"Filtering last 24h: cutoff is {cutoff.isoformat()}, start with {len(items)} items")
        recent = [it for it in items if it.published_date >= cutoff]
        logging.debug(f"After _filter_last_24h: {len(recent)} items remain")
        return recent

    def _select_renderer(self) -> ReportRenderer:
        fmt = settings.REPORT_FORMAT.lower()
        if fmt == 'html': return HTMLRenderer()
        if fmt == 'text': return TextRenderer()
        return MarkdownRenderer()

    def _format_report(self, items: List[NewsItem]) -> str:
        logging.debug(f"Formatting report with {len(items)} items")
        renderer = self._select_renderer()
        report = renderer.render(items)
        logging.debug("Report formatting complete")
        return report

    async def get_report(self) -> str:
        logging.info("Starting report generation")
        # 并发抓取
        tasks = [self._fetch_feed(name, url) for name, url in self.feeds.items()]
        lists = await asyncio.gather(*tasks)
        # 单源限额 & 合并
        all_items = []
        for lst in lists:
            lst.sort(key=lambda x: x.published_date, reverse=True)
            all_items.extend(lst[:settings.MAX_ITEMS_PER_FEED])
        logging.debug(f"After merging feeds: {len(all_items)} items")
        # 关键词/源过滤
        all_items = self._filter_items(all_items)
        # 24h 内过滤
        all_items = self._filter_last_24h(all_items)
        # 全局去重 & 总数限额
        unique, seen = [], set()
        for it in all_items:
            if it.link not in seen:
                seen.add(it.link)
                unique.append(it)
            if len(unique) >= settings.MAX_TOTAL_ITEMS:
                break
        logging.debug(f"After deduplication & limit: {len(unique)} items")
        # 渲染并返回
        report = self._format_report(unique)
        logging.info("Report generation finished")
        return report
