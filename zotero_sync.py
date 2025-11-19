import json
import os
import time
import requests
from pyzotero import zotero
from main import cm

class ZoteroSync:
    def __init__(self):
        self.lib_id = cm.get("ZOTERO_LIB_ID")
        self.api_key = cm.get("ZOTERO_API_KEY")
        self.lib_type = 'user'
        self.cache_file = "zotero_cache.json"
        self.zot = None
        
        # 定义允许的论文类型白名单
        # 注意：如果你希望包含 ArXiv 预印本，请保留 'preprint'
        # 如果你只想要正式发表的，可以删掉 'preprint'
        self.ALLOWED_TYPES = {
            'journalArticle', 
            'conferencePaper', 
            'thesis', 
            'report',
            'preprint' # 通常 ArXiv 论文会被识别为这个，建议保留，否则会漏掉很多新文章
        }
        
        if self.lib_id and self.api_key:
            try:
                self.zot = zotero.Zotero(self.lib_id, self.lib_type, self.api_key)
                print(f"🔌 Zotero client initialized (ID: {self.lib_id})")
            except Exception as e:
                print(f"❌ Zotero Init Error: {e}")

    def _get_items_robust(self, limit, start, retries=3):
        for i in range(retries):
            try:
                # 尝试获取数据
                items = self.zot.items(limit=limit, start=start)
                return items
            except Exception as e:
                error_str = str(e)
                print(f"⚠️ Network error (Attempt {i+1}/{retries}): {error_str[:100]}...")
                if "ProxyError" in error_str or "SSLError" in error_str:
                    if hasattr(self.zot, 'session'):
                        self.zot.session.trust_env = False
                time.sleep(2)
        return None

    def _is_valid_paper(self, item):
        """过滤逻辑：排除快照、附件、网页和笔记"""
        data = item.get('data', {})
        item_type = data.get('itemType')
        
        # 1. 类型白名单检查
        if item_type not in self.ALLOWED_TYPES:
            return False
            
        # 2. 标题检查 (排除 Untitled 或空标题)
        title = data.get('title', '').strip()
        if not title:
            return False
            
        # 3. 排除 snapshot (虽然 attachment 类型已经被过滤，但双重保险)
        if 'snapshot' in title.lower() or 'snapshot' in item.get('links', {}).get('alternative', {}).get('href', ''):
            return False

        return True

    def fetch_all(self, force_refresh=False):
        if not self.zot: 
            print("⚠️ Zotero client not initialized.")
            return []

        if not force_refresh and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                    if cached:
                        print(f"📖 Loaded {len(cached)} items from cache.")
                        return cached
            except:
                pass

        print("🔄 Syncing items from Zotero...")
        all_items = []
        start = 0
        limit = 100
        
        try:
            while True:
                print(f"   Fetching items {start} - {start+limit}...")
                items = self._get_items_robust(limit, start)
                
                if items is None: break
                if not items: break
                
                # --- 核心修改：应用过滤器 ---
                valid_items = [i for i in items if self._is_valid_paper(i)]
                all_items.extend(valid_items)
                
                # 统计过滤掉的数量
                filtered_count = len(items) - len(valid_items)
                print(f"   + Retrieved {len(valid_items)} valid papers (Filtered {filtered_count} junk items)")
                
                if len(items) < limit: break
                start += limit
                time.sleep(0.5) 
            
            if all_items:
                print(f"💾 Saving {len(all_items)} valid items to cache...")
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(all_items, f, ensure_ascii=False)
                
            return all_items
        except Exception as e:
            print(f"❌ Zotero Sync Error: {e}")
            return all_items if all_items else []

    def add_paper(self, title, authors, summary, url, tags=["RA-Pushed"]):
        if not self.zot: return False
        try:
            template = self.zot.item_template('conferencePaper')
            template['title'] = title
            template['creators'] = [{'creatorType': 'author', 'lastName': name} for name in authors]
            template['abstractNote'] = summary
            template['url'] = url
            template['tags'] = [{'tag': t} for t in tags]
            return self.zot.create_items([template])
        except Exception as e:
            print(f"Add Paper Error: {e}")
            return False