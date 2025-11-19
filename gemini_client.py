import google.generativeai as genai
import time
import os
from main import cm

class GeminiHandler:
    def __init__(self):
        api_key = cm.get("GEMINI_API_KEY")
        # 默认改用 flash，兼容性更好
        self.model_name = cm.get("GEMINI_MODEL", "gemini-2.5-pro-preview-03-25")
        self.is_ready = False
        
        if api_key:
            genai.configure(api_key=api_key)
            self.is_ready = True
        
        self.chat_session = None
        self.uploaded_file = None

    def list_available_models(self):
        """列出当前 Key 可用的模型，用于调试"""
        if not self.is_ready: return []
        try:
            return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        except Exception as e:
            print(f"List Models Error: {e}")
            return []

    def upload_file(self, file_path: str, progress_callback=None):
        """上传 PDF 文件到 Google 服务器 (带进度回调)"""
        if not self.is_ready: 
            print("❌ Gemini API Key not configured.")
            return False
        
        try:
            if progress_callback: progress_callback(10, "正在上传文件到 Google Cloud...")
            print(f"📤 Uploading to Gemini: {file_path}")
            
            sample_file = genai.upload_file(path=file_path, display_name="Research Paper")
            
            # 等待文件处理完成
            if progress_callback: progress_callback(40, "等待 Google 处理文件 (OCR/解析)...")
            
            wait_count = 0
            while sample_file.state.name == "PROCESSING":
                time.sleep(2)
                sample_file = genai.get_file(sample_file.name)
                wait_count += 1
                if progress_callback: 
                    progress = min(40 + wait_count * 5, 90)
                    progress_callback(progress, f"文件处理中 ({sample_file.state.name})...")
            
            if sample_file.state.name == "FAILED":
                raise ValueError(f"File processing failed: {sample_file.state.name}")
                
            print(f"✅ File Ready: {sample_file.uri}")
            self.uploaded_file = sample_file
            
            if progress_callback: progress_callback(100, "处理完成！")
            return True
        except Exception as e:
            print(f"❌ Gemini Upload Error: {e}")
            return False

    def start_chat(self):
        """开启一个新的带文件上下文的对话"""
        # 核心修复：参数名修正为 model_name
        try:
            if not self.uploaded_file:
                print("⚠️ No file uploaded, starting text-only chat.")
                model = genai.GenerativeModel(model_name=self.model_name)
                history = []
            else:
                sys_prompt = """
                你是一位精通计算机科学的科研专家。用户上传了一篇论文 PDF。
                你的任务是帮助用户深入理解这篇论文。
                
                要求：
                1. 回答必须基于 PDF 原文，不要编造。
                2. 如果涉及数学公式，请使用 LaTeX 格式包裹（例如 $E=mc^2$）。
                3. 如果用户询问细节（如“公式3怎么推导的？”），请结合上下文详细解释。
                """
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=sys_prompt
                )
                history = [{"role": "user", "parts": [self.uploaded_file]}]

            self.chat_session = model.start_chat(history=history)
            return True
        except Exception as e:
            print(f"Start Chat Error: {e}")
            return False

    def send_message(self, message: str):
        """发送消息"""
        if not self.chat_session:
            # 尝试重新初始化
            if not self.start_chat():
                return "错误：无法启动对话会话，请检查模型名称是否正确 (例如 gemini-2.5-pro-preview-03-25)。"
        
        try:
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            return f"Gemini Error: {str(e)}"