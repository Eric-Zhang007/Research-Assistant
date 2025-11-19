import os
import requests
import time
from main import cm

class PDFManager:
    def __init__(self):
        self.cache_dir = cm.get("PDF_CACHE_DIR", "./pdf_cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_pdf_path(self, arxiv_id: str) -> str:
        """获取本地 PDF 路径，如果不存在则下载"""
        # 清洗 ID (处理版本号如 v1)
        clean_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id
        filename = f"{clean_id}.pdf"
        file_path = os.path.join(self.cache_dir, filename)

        if os.path.exists(file_path):
            return file_path
        
        return self._download_from_arxiv(clean_id, file_path)

    def _download_from_arxiv(self, arxiv_id: str, save_path: str) -> str:
        """从 ArXiv 下载 PDF"""
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        print(f"⬇️ Downloading PDF: {url}")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ResearchAssistant/1.0"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ PDF Saved: {save_path}")
                return save_path
            else:
                print(f"❌ Download failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Network error during download: {e}")
            return None