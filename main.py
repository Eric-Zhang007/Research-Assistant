import os
import yaml
import arxiv
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List

# --- 配置管理 ---
class ConfigManager:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        config = {
            "ARXIV_CATEGORIES": ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO"], # 增加 Robotics
            "ZOTERO_LIB_ID": os.getenv("ZOTERO_LIB_ID", ""),
            "ZOTERO_API_KEY": os.getenv("ZOTERO_API_KEY", ""),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
            "OPENAI_BASE_URL": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "OPENAI_MODEL": os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
            "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            "S2_API_KEY": os.getenv("S2_API_KEY", ""),
            "PDF_CACHE_DIR": "./pdf_cache"
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    yaml_config = yaml.safe_load(f) or {}
                    for k, v in yaml_config.items():
                        if k in config: config[k] = v
            except: pass
        
        if not os.path.exists(config["PDF_CACHE_DIR"]):
            os.makedirs(config["PDF_CACHE_DIR"])
        return config

    def save_config(self, new_config: Dict):
        self.config.update(new_config)
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True)
            return True
        except: return False

    def get(self, key, default=None):
        return self.config.get(key, default)

cm = ConfigManager()

# --- 真实 ArXiv 雷达逻辑 ---
class ArxivRadar:
    def __init__(self):
        self.categories = cm.get("ARXIV_CATEGORIES")

    def _extract_keywords(self, zotero_items, top_n=5):
        """从用户文献库中提取高频关键词"""
        if not zotero_items: return ["World Model", "Autonomous Driving"]
        
        text_pool = []
        for item in zotero_items:
            title = item.get('data', {}).get('title', '')
            text_pool.append(title.lower())
            
        full_text = " ".join(text_pool)
        # 简单的正则分词
        words = re.findall(r'\b[a-z-]{4,}\b', full_text)
        
        # 停用词表 (过滤掉无意义的通用学术词汇)
        stopwords = set([
            'with', 'using', 'from', 'based', 'that', 'this', 'approach', 'method',
            'learning', 'model', 'deep', 'neural', 'network', 'paper', 'proposed',
            'analysis', 'study', 'system', 'data', 'via', 'improving', 'towards',
            'evaluation', 'survey', 'review', 'application', 'performance'
        ])
        
        filtered_words = [w for w in words if w not in stopwords]
        counter = Counter(filtered_words)
        
        # 返回频率最高的 N 个词
        common = [pair[0] for pair in counter.most_common(top_n)]
        print(f"🔍 Extracted User Interests: {common}")
        return common

    def recommend_papers(self, zotero_items, max_results=10):
        """
        1. 分析 Zotero 偏好
        2. 搜索 ArXiv (限制在最近 2 天)
        """
        keywords = self._extract_keywords(zotero_items)
        
        # 构建 ArXiv 查询: (cat:cs.AI OR ...) AND (all:kw1 OR all:kw2)
        cat_query = " OR ".join([f"cat:{c}" for c in self.categories])
        # ArXiv query 长度限制严格，只取前 3 个关键词
        kw_query = " OR ".join([f'all:"{k}"' for k in keywords[:3]])
        
        search_query = f"({cat_query}) AND ({kw_query})"
        print(f"📡 ArXiv Query: {search_query}")
        
        try:
            client = arxiv.Client()
            search = arxiv.Search(
                query=search_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate
            )
            
            results = []
            for r in client.results(search):
                # 简单过滤：只看最近 7 天的 (Arxiv API 返回的可能有些旧)
                # if (datetime.now(r.published.tzinfo) - r.published).days > 7:
                #    continue
                
                results.append({
                    "title": r.title,
                    "summary": r.summary.replace("\n", " "),
                    "published": r.published.strftime("%Y-%m-%d"),
                    "authors": [a.name for a in r.authors],
                    "url": r.entry_id,
                    "arxiv_id": r.entry_id.split('/')[-1].split('v')[0]
                })
            return results
        except Exception as e:
            print(f"ArXiv Error: {e}")
            return []