# -*- coding: utf-8 -*-
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content

class CCTVcrawler(BaseCrawler):
    def __init__(self):
        super().__init__(name="cctv")
        self.base_url = "https://news.cctv.com/"

    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        news_list = []
        html = fetch_html(self.base_url, self.logger)
        if not html: return news_list
        try:
            soup = BeautifulSoup(html, 'lxml')
            all_links = soup.find_all('a', href=True)
            seen_urls = set()
            for a in all_links:
                if len(news_list) >= max_count: break
                url, title = a['href'], a.get_text(strip=True)
                if not re.search(r'/202\d/', url) or '.shtml' not in url: continue
                if len(title) < 10 or url in seen_urls: continue
                seen_urls.add(url)
                if url.startswith('//'): url = 'https:' + url
                content = ""
                detail_html = fetch_html(url, self.logger)
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, 'lxml')
                    meta_desc = detail_soup.find('meta', attrs={'name': 'description'})
                    summary_text = meta_desc['content'] if meta_desc else ""
                    target = (detail_soup.select_one('#content_area') or detail_soup.select_one('#text_area') or detail_soup.select_one('.cnt_bd'))
                    if target:
                        for junk in target.select('.ebm, .function, .share, .p-copyright, .shouquan'): junk.decompose()
                        content = target.get_text(separator="\n", strip=True)
                    if len(content) < 50:
                        p_texts = [p.get_text(strip=True) for p in detail_soup.find_all('p') if len(p.get_text(strip=True)) > 15 and "版权所有" not in p.get_text()]
                        content = "\n".join(p_texts) if p_texts else summary_text
                if not content or len(content) < 20: content = f"（同步央视新闻：{title}）请点击链接查看详情。"
                news_list.append(NewsItem(title=title, url=url, source="cctv", content=content.strip(), publish_time=datetime.now()))
        except Exception as e: self.logger.error(f"CCTV Error: {e}")
        return news_list