import streamlit as st
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import os
import time
import json
from main import cm, ArxivRadar
from graph_engine import GraphEngine
from zotero_sync import ZoteroSync
from pdf_manager import PDFManager
from gemini_client import GeminiHandler

# --- Page Config ---
st.set_page_config(page_title="AI Research Assistant Pro", layout="wide", page_icon="🧬")
st.markdown("""
<style>
    .stButton>button { border-radius: 6px; }
    .stChatMessage { padding: 1rem; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 0.5rem; }
    @media (prefers-color-scheme: dark) {
        .stChatMessage { background-color: #262730; }
    }
</style>
""", unsafe_allow_html=True)

# --- Init Engines (Singleton) ---
if 'engines' not in st.session_state:
    st.session_state.engines = {
        'graph': GraphEngine(),
        'zotero': ZoteroSync(),
        'pdf': PDFManager(),
        'gemini': GeminiHandler(),
        'radar': ArxivRadar()
    }

engines = st.session_state.engines

# --- Auto-Run Logic ---
if 'zotero_items' not in st.session_state:
    items = engines['zotero'].fetch_all(force_refresh=False)
    st.session_state.zotero_items = items
    if items and 'arxiv_recs' not in st.session_state:
        recs = engines['radar'].recommend_papers(items, max_results=10)
        st.session_state.arxiv_recs = recs

# --- View State ---
if 'view' not in st.session_state: st.session_state.view = 'home'
if 'selected_paper' not in st.session_state: st.session_state.selected_paper = None
if 'chat_history' not in st.session_state: st.session_state.chat_history = []
if 'gemini_ready' not in st.session_state: st.session_state.gemini_ready = False

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ 控制台")
    
    with st.expander("✨ Gemini (全文研读)", expanded=True):
        g_key = st.text_input("Gemini Key", value=cm.get("GEMINI_API_KEY"), type="password")
        g_model = st.text_input("Model", value=cm.get("GEMINI_MODEL", "gemini-2.5-pro-preview-03-25"), help="我也不知道哪个能用")
        
        if st.button("检查可用模型"):
            # 重新初始化以应用 Key
            cm.save_config({"GEMINI_API_KEY": g_key})
            eng_gemini = GeminiHandler()
            models = eng_gemini.list_available_models()
            if models:
                st.success(f"可用模型: {', '.join(models)}")
            else:
                st.error("无法列出模型，请检查 Key 或网络。")

        if g_key and g_key != cm.get("GEMINI_API_KEY"):
            cm.save_config({"GEMINI_API_KEY": g_key, "GEMINI_MODEL": g_model})
            engines['gemini'] = GeminiHandler()
            st.toast("Gemini Config Updated!")

    with st.expander("🤖 基础配置"):
        o_key = st.text_input("OpenAI Key", value=cm.get("OPENAI_API_KEY"), type="password")
        s2_key = st.text_input("S2 Key", value=cm.get("S2_API_KEY"), type="password")
        
    with st.expander("📚 Zotero 配置"):
        z_id = st.text_input("User ID", value=cm.get("ZOTERO_LIB_ID"))
        z_key = st.text_input("API Key", value=cm.get("ZOTERO_API_KEY"), type="password")
        if st.button("保存并重新同步"):
            cm.save_config({"ZOTERO_LIB_ID": z_id, "ZOTERO_API_KEY": z_key})
            st.session_state.zotero_items = engines['zotero'].fetch_all(force_refresh=True)
            st.rerun()

# --- Functions ---
def show_home():
    st.title("🧬 Deep Research Graph (Pro)")
    
    radar_title = "📡 ArXiv 雷达"
    if st.session_state.get('arxiv_recs'):
        radar_title += f" ({len(st.session_state.arxiv_recs)} New)"
        
    tabs = st.tabs(["🔍 搜论文", "📚 Zotero 知识库", radar_title])
    
    with tabs[0]:
        c1, c2 = st.columns([4, 1])
        query = c1.text_input("输入论文标题 或 ArXiv ID", placeholder="2310.12345 或 π0: a VLA...")
        if c2.button("🚀 分析", use_container_width=True) and query:
            with st.status("🔍 正在检索文献...", expanded=True):
                st.write("正在连接 Semantic Scholar...")
                meta = engines['graph'].get_paper_metadata(query)
                if meta:
                    st.write(f"✅ 找到: **{meta['title']}**")
                    st.session_state.selected_paper = meta
                    st.session_state.view = 'paper'
                    st.session_state.gemini_ready = False # 重置状态
                    st.session_state.chat_history = []
                    st.rerun()
                else:
                    st.error("未找到。请尝试使用 ArXiv ID。")

    # (Tab 2 & 3 省略代码，保持原样，此处仅展示修改部分)
    with tabs[1]:
        st.caption(f"共加载 {len(st.session_state.zotero_items)} 篇")
        # ... (Zotero List Logic - Same as before) ...
        # 仅为了完整性示意，实际运行时请保留之前的 Zotero 代码逻辑
        filtered = st.session_state.zotero_items[:10] 
        for item in filtered:
            d = item.get('data', {})
            with st.expander(f"📄 {d.get('title', 'No Title')}"):
                if st.button("深度研读", key=f"z_{item['key']}"):
                     # ... (Logic same as before)
                     st.session_state.selected_paper = {'title': d['title'], 'abstract': d.get('abstractNote', ''), 'arxivId': None} # Simplified
                     st.session_state.view = 'paper'
                     st.rerun()
    
    with tabs[2]:
        if st.session_state.get('arxiv_recs'):
             for p in st.session_state.arxiv_recs:
                 with st.container():
                     st.markdown(f"**{p['title']}**")
                     if st.button("研读", key=f"r_{p['arxiv_id']}"):
                         st.session_state.selected_paper = {'title': p['title'], 'abstract': p['summary'], 'arxivId': p['arxiv_id']}
                         st.session_state.view = 'paper'
                         st.rerun()


def show_paper_detail():
    p = st.session_state.selected_paper
    if st.button("← 返回首页"):
        st.session_state.view = 'home'
        st.rerun()

    st.title(p.get('title'))
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.info(p.get('abstract', '无摘要'))
        # ... (Graph Logic same as before) ...
        if p.get('paperId'):
             if st.button("生成引用图谱"):
                 with st.spinner("分析中..."):
                     G, known = engines['graph'].build_graph(p['paperId'])
                     st.success(f"节点: {len(G.nodes)}")

    with c2:
        st.subheader("🤖 Gemini 全文对话")
        aid = p.get('arxivId') or p.get('externalIds', {}).get('ArXiv')
        
        if not aid:
            st.warning("未检测到 ArXiv ID，无法启用全文模式。")
        else:
            # 如果还没准备好，显示吞噬按钮
            if not st.session_state.gemini_ready:
                if st.button("🚀 吞噬论文 (开启全文模式)"):
                    # 进度条 UI
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(percent, text):
                        progress_bar.progress(percent)
                        status_text.text(text)

                    # 1. Download
                    update_progress(10, "正在从 ArXiv 下载 PDF...")
                    path = engines['pdf'].get_pdf_path(aid)
                    
                    if path:
                        # 2. Upload & Process
                        success = engines['gemini'].upload_file(path, progress_callback=update_progress)
                        if success:
                            engines['gemini'].start_chat()
                            st.session_state.gemini_ready = True
                            st.success("论文已吞噬！开始提问吧。")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("上传失败，请检查 Key 或网络。")
                    else:
                        st.error("PDF 下载失败")
            else:
                st.success(f"✅ 已加载全文 (ID: {aid})")
                if st.button("重置/清除上下文"):
                    st.session_state.gemini_ready = False
                    st.session_state.chat_history = []
                    st.rerun()

        # Chat Interface
        chat_container = st.container(height=500)
        for msg in st.session_state.chat_history:
            with chat_container.chat_message(msg['role']):
                st.write(msg['content'])
        
        # Input locking
        input_disabled = not st.session_state.gemini_ready
        placeholder = "请先点击上方按钮加载论文..." if input_disabled else "问点什么 (e.g. '核心公式是什么？')..."
        
        if prompt := st.chat_input(placeholder, disabled=input_disabled):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.rerun()
            
        if st.session_state.chat_history and st.session_state.chat_history[-1]['role'] == 'user':
             with chat_container.chat_message("assistant"):
                 with st.spinner("Gemini 正在阅读原文并思考..."):
                     resp = engines['gemini'].send_message(st.session_state.chat_history[-1]['content'])
                     st.write(resp)
                     st.session_state.chat_history.append({"role": "assistant", "content": resp})

if st.session_state.view == 'home':
    show_home()
else:
    show_paper_detail()