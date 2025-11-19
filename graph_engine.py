import requests
import networkx as nx
import json
import re
from main import cm
from openai import OpenAI

class GraphEngine:
    def __init__(self):
        s2_key = cm.get("S2_API_KEY")
        self.headers = {"x-api-key": s2_key} if s2_key and len(s2_key) > 10 else {}
        
        # 这里依然保留 OpenAI 兼容接口用于图谱分析（轻量级任务），也可以换成 Gemini
        base_url = cm.get("OPENAI_BASE_URL")
        api_key = cm.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None
        self.model = cm.get("OPENAI_MODEL")

    def _is_arxiv_id(self, query: str) -> bool:
        # 简单的 ArXiv ID 正则，如 2310.12345 或 2310.12345v1
        return re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', query.strip()) is not None

    def get_paper_metadata(self, query: str):
        """智能获取论文元数据：优先 ID，其次标题"""
        if self._is_arxiv_id(query):
            # 使用 ArXiv ID 直接查询 Graph API
            print(f"🔍 Detected ArXiv ID: {query}")
            url = f"https://api.semanticscholar.org/graph/v1/paper/arxiv:{query}"
            params = {"fields": "paperId,title,abstract,year,authors,citationCount"}
        else:
            # 标题搜索
            print(f"🔍 Searching Title: {query}")
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {"query": query, "limit": 1, "fields": "paperId,title,abstract,year,authors,citationCount"}

        try:
            r = requests.get(url, headers=self.headers, params=params, timeout=10)
            data = r.json()
            
            if 'data' in data: # Search endpoint returns {data: [...]}
                return data['data'][0] if data['data'] else None
            elif 'paperId' in data: # Direct ID endpoint returns object
                return data
            else:
                return None
        except Exception as e:
            print(f"S2 Error: {e}")
            return None

    def build_graph(self, root_paper_id: str, limit=20):
        """构建图谱"""
        G = nx.DiGraph()
        fields = "paperId,title,citationCount,references.paperId,references.title,references.citationCount,citations.paperId,citations.title,citations.citationCount"
        url = f"https://api.semanticscholar.org/graph/v1/paper/{root_paper_id}?fields={fields}"
        
        try:
            r = requests.get(url, headers=self.headers)
            data = r.json()
            if 'paperId' not in data: return G, {}

            # Root
            root_node = {"id": data['paperId'], "label": data['title'], "type": "root"}
            G.add_node(data['paperId'], **root_node)
            known_nodes = {data['paperId']: root_node}

            # References (基石)
            refs = [r for r in data.get('references', []) if r['paperId']]
            refs.sort(key=lambda x: x.get('citationCount', 0) or 0, reverse=True)
            
            for r in refs[:limit]:
                n = {"id": r['paperId'], "label": r['title'], "type": "reference"}
                G.add_node(r['paperId'], **n)
                G.add_edge(r['paperId'], data['paperId'])
                known_nodes[r['paperId']] = n

            # Citations (发展)
            cits = [c for c in data.get('citations', []) if c['paperId']]
            cits.sort(key=lambda x: x.get('citationCount', 0) or 0, reverse=True)
            
            for c in cits[:limit]:
                n = {"id": c['paperId'], "label": c['title'], "type": "cited_by"}
                G.add_node(c['paperId'], **n)
                G.add_edge(data['paperId'], c['paperId'])
                known_nodes[c['paperId']] = n
                
            return G, known_nodes
        except:
            return G, {}

    def analyze_recommendations(self, G, known_nodes):
        """AI 推荐阅读（不限数量）"""
        if not self.client: return {"error": "No API Key"}
        
        # 将图数据转为文本上下文
        nodes_desc = []
        for n in list(G.nodes)[:30]: # 给 AI 看前 30 个重要节点
            info = known_nodes.get(n, {})
            nodes_desc.append(f"- [{info.get('type')}] {info.get('label')}")

        prompt = f"""
        你是一个科研导师。我正在研究一篇论文（Root），以下是它的引用关系网络（Reference=它引用的基础，Cited_by=它的后续发展）。
        
        论文列表：
        {chr(10).join(nodes_desc)}
        
        请分析这个网络，找出我**必须阅读**的论文。
        要求：
        1. 不要限制数量！如果有很多篇都很重要，就全部列出来。
        2. 请根据重要性将它们分组（例如：T0-核心基石, T1-重要扩展, T2-背景知识）。
        3. 对于每一篇推荐的论文，给出简短的推荐理由。
        
        返回 JSON 格式：
        {{
            "groups": [
                {{
                    "group_name": "T0: 核心基石",
                    "papers": [
                        {{"title": "...", "reason": "..."}}
                    ]
                }}
            ],
            "summary_advice": "整体学习建议..."
        }}
        """
        
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            return {"error": str(e)}