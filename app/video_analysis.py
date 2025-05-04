import json
import cv2
import os
import base64
import requests
from PIL import Image
from io import BytesIO
from config import Config
from process_video import convert_webm_to_mp4
from huggingface_hub import InferenceClient

# HF_TOKEN = os.getenv('HF_TOKEN')
HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

nvshu_ai = InferenceClient(
    provider="sambanova",
    api_key=HF_TOKEN,
)

class VideoAnalyzer:
    def __init__(self, model, session_id):
        self.output_dir = Config.OUTPUT_DIR+f'/{session_id}'
        self.model = model
        os.makedirs(self.output_dir, exist_ok=True)
        
    def extract_key_frames(self, video_path):
        """
        从视频中抽取关键帧，最多抽取MAX_FRAMES帧
        :param video_path: 视频文件路径
        :return: 提取的帧列表(PIL图像)
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frames = []
        
        # 计算采样间隔，确保最多取MAX_FRAMES帧
        sample_interval = max(1, total_frames // int(Config.MAX_FRAMES))
        
        for frame_count in range(0, total_frames, sample_interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
            ret, frame = cap.read()
            if not ret:
                continue
            if len(frames) >= Config.MAX_FRAMES:
                break
                
            # 转换颜色空间从BGR到RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            frames.append(pil_image)
            
            # 保存帧供调试使用
            frame_path = os.path.join(self.output_dir, f"frame_{frame_count}.jpg")
            pil_image.save(frame_path)
            
        cap.release()
        return frames
    
    def encode_image_to_base64(self, image):
        """
        将PIL图像编码为base64字符串
        """
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    def analyze_frame(self, image):
        max_retries = 2
        retry_count = 0
        base64_image = self.encode_image_to_base64(image)
        while retry_count <= max_retries:
            try:
                completion = nvshu_ai.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": Config.PROMPT,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=512,
                )

                return completion.choices[0].message['content']
            except Exception as e:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"API调用出错: {e}")
                    continue
                else:
                    print(f"API调用最终失败: {str(e)}")
                    raise
            
    
    def analyze_video(self, video_path):
        """
        分析整个视频内容
        """
        try:
            # 确保路径使用正确的分隔符
            video_path = os.path.normpath(video_path)
            print(f"处理视频路径: {video_path}")
            
            # 1. webm to mp4
            if video_path.lower().endswith('.webm'):
                # 如果是 webm 格式，先转换为 mp4
                mp4_path = convert_webm_to_mp4(video_path)
                if mp4_path is None:
                    raise Exception("WebM 转 MP4 失败")
                video_path = mp4_path
                print(f"转换后的视频路径: {video_path}")
            
            # 2. 抽取关键帧
            frames = self.extract_key_frames(video_path)
            if not frames:
                raise Exception("无法从视频中抽取关键帧")
            
            # 3. 分析每一帧
            for i, frame in enumerate(frames):
                if i == int(Config.MAX_FRAMES) // 2:
                    analysis = self.analyze_frame(frame)
                    return analysis
        except Exception as e:
            print(f"视频分析出错: {str(e)}")
            raise
    
    def read_jpeg_to_pil(self, jpeg_path):
        """
        从 JPEG 文件读取并转换为 PIL Image 对象
        :param jpeg_path: JPEG 文件路径
        :return: PIL Image 对象
        """
        try:
            # 直接使用 PIL 打开 JPEG 文件
            pil_image = Image.open(jpeg_path)
            # 确保图像是 RGB 模式
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            return pil_image
        except Exception as e:
            print(f"读取 JPEG 文件时出错: {str(e)}")
            return None

    def read_jpeg_to_frames(self, jpeg_path):
        """
        从 JPEG 文件读取并返回与 extract_key_frames 相同格式的帧列表
        :param jpeg_path: JPEG 文件路径
        :return: 包含单个 PIL Image 对象的列表
        """
        pil_image = self.read_jpeg_to_pil(jpeg_path)
        if pil_image:
            return [pil_image]
        return []
    
    # def summarize_analyses(self, frame_analyses):
    #     """
    #     使用LLM汇总所有帧的分析结果
    #     """
    #     if not frame_analyses:
    #         return "未能获取视频内容分析"
        
    #     # 将所有帧分析结果合并为一个文本
    #     combined_analyses = "\n\n".join(
    #         [f"帧 {i+1} 分析:\n{analysis}" for i, analysis in enumerate(frame_analyses)]
    #     )
    #     headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Bearer {self.api_key}"
    #     }
        
    #     payload = {
    #         "model": "gpt-4",
    #         "messages": [
    #             {
    #                 "role": "system",
    #                 "content": Config.SUMMARY_PROMPT
    #             },
    #             {
    #                 "role": "user",
    #                 "content": f"请根据以下各帧的分析结果，总结视频的主要内容:\n\n{combined_analyses}"
    #             }
    #         ],
    #         "max_tokens": 2000
    #     }
        
    #     try:
    #         response = requests.post(
    #             "https://api.openai.com/v1/chat/completions",
    #             headers=headers,
    #             json=payload
    #         )
    #         response.raise_for_status()
    #         return response.json()["choices"][0]["message"]["content"]
    #     except Exception as e:
    #         print(f"总结API调用出错: {e}")
    #         return combined_analyses  # 如果总结失败，返回原始分析