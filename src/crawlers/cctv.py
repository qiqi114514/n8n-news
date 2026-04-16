# -*- coding: utf-8 -*-
"""央视网爬虫"""
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawlers.base import BaseCrawler, NewsItem
from utils import fetch_html, fetch_article_content


class CCTVcrawler(BaseCrawler):
    """央视网新闻爬虫"""
    
    def __init__(self):
        super().__init__(name="cctv")
        self.base_url = "https://news.cctv.com/"
    
    def fetch_news_list(self, max_count: int = 10) -> List[NewsItem]:
        """抓取央视网新闻列表"""
        news_list = []
        html = fetch_html(self.base_url, self._get_logger())
        if not html:
            return news_list
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            all_links = soup.find_all('a', href=True)
            seen_urls = set()
            
            for a in all_links:
                if len(news_list) >= max_count:
                    break
                
                url = a['href']
                title = a.get_text(strip=True)
                
                # 过滤无效链接
                if not re.search(r'/202\d/', url) or '.shtml' not in url:
                    continue
                if len(title) < 10 or url in seen_urls:
                    continue
                seen_urls.add(url)
                
                # 处理协议相对 URL
                if url.startswith('//'):
                    url = 'https:' + url
                
                # 抓取正文内容
                content = ""
                detail_html = fetch_html(url, self._get_logger())
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, 'lxml')
                    
                    # 尝试获取描述
                    meta_desc = detail_soup.find('meta', attrs={'name': 'description'})
                    summary_text = meta_desc['content'] if meta_desc else ""
                    
                    # 查找主要内容区域
                    target = (
                        detail_soup.select_one('#content_area') or
                        detail_soup.select_one('#text_area') or
                        detail_soup.select_one('.cnt_bd')
                    )
                    
                    if target:
                        # 移除无关元素
                        for junk in target.select('.ebm, .function, .share, .p-copyright, .shouquan'):
                            junk.decompose()
                        content = target.get_text(separator="\n", strip=True)
                    
                    # 如果内容太少，尝试从段落提取
                    if len(content) < 50:
                        p_texts = [
                            p.get_text(strip=True) 
                            for p in detail_soup.find_all('p') 
                            if len(p.get_text(strip=True)) > 15 and "版权所有" not in p.get_text()
                        ]
                        content = "\n".join(p_texts) if p_texts else summary_text
                
                # 确保有内容
                if not content or len(content) < 20:
                    content = f"（同步央视新闻：{title}）请点击链接查看详情。"
                
                news_list.append(NewsItem(
                    title=title,
                    url=url,
                    source="cctv",
                    content=content.strip(),
                    publish_time=datetime.now()
                ))
        
        except Exception as e:
            self._get_logger().error(f"CCTV Error: {e}")
        
        return news_list
