# 视频的处理：转换和截取
import os
#设置最终保存的临时文件数量最大为100
import time  # 需要在文件开始或者这个代码块的开始导入time模块
from moviepy.editor import VideoFileClip
import subprocess
from PIL import Image
import numpy as np

def convert_webm_to_mp4(input_path):
    """将 WebM 转换为 MP4 格式"""
    output_path = input_path.rsplit('.', 1)[0] + '.mp4'
    if not os.path.exists(output_path):  # 如果转换后的文件不存在才进行转换
        try:
            # 确保路径使用正确的分隔符
            input_path = os.path.normpath(input_path)
            output_path = os.path.normpath(output_path)
            
            # Windows 系统下可能需要指定 ffmpeg 的完整路径
            ffmpeg_cmd = 'ffmpeg'
            if os.name == 'nt':  # Windows 系统
                # 尝试在系统 PATH 中查找 ffmpeg
                import shutil
                ffmpeg_path = shutil.which('ffmpeg')
                if ffmpeg_path:
                    ffmpeg_cmd = ffmpeg_path
                else:
                    # 如果找不到 ffmpeg，尝试使用相对路径
                    ffmpeg_cmd = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg', 'bin', 'ffmpeg.exe')
            
            command = [
                ffmpeg_cmd,
                '-i', input_path,  # 输入文件
                '-c:v', 'libx264',  # 视频编码器
                '-c:a', 'aac',      # 音频编码器
                '-strict', 'experimental',
                '-b:a', '192k',     # 音频比特率
                output_path
            ]
            
            print(f"执行命令: {' '.join(command)}")
            subprocess.run(command, check=True)
            print(f"转换成功: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"转换失败: {str(e)}")
            return None
        except Exception as e:
            print(f"发生错误: {str(e)}")
            return None
    return output_path




# 截取视频的一部分
def trim_video(input_path, output_path, duration=5):
    """
    从视频开始处截取指定时长的片段
    
    参数:
    input_path (str): 输入视频的路径
    output_path (str): 输出视频的保存路径
    duration (int): 需要截取的时长(秒)，默认为5秒
    
    返回:
    bool: 操作是否成功
    str: 成功或错误信息
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_path):
            return False, f"输入文件不存在: {input_path}"
            
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 加载视频
        video = VideoFileClip(input_path)
        
        # 检查视频时长
        if video.duration < duration:
            video.close()
            return False, f"视频总时长({video.duration}秒)小于要截取的时长({duration}秒)"
        
        # 截取视频
        trimmed_video = video.subclip(0, duration)
        
        # 导出视频
        trimmed_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac'  # 保持音频编码为 AAC
        )
        
        # 清理资源
        trimmed_video.close()
        video.close()
        return True, f"成功截取视频前{duration}秒并保存到: {output_path}"
    except Exception as e:
        return False, f"处理视频时出错: {str(e)}"

def pixelate(image_path, pixel_size=20):
    
    # 拆分目录和文件名
    dir_name = os.path.dirname(image_path)  # 获取目录部分
    file_name = os.path.basename(image_path)  # 获取文件名部分

    # 添加前缀
    output_path = os.path.join(dir_name, f"pixelated_{file_name}")
    # 打开图像（保留RGBA通道）
    image = Image.open(image_path)
    
    # 计算缩小后的尺寸
    small_size = (image.width // pixel_size, image.height // pixel_size)
    
    # 缩小图像
    small_image = image.resize(small_size, Image.NEAREST)
    
    # 再放大回原始尺寸
    pixelated_image = small_image.resize(image.size, Image.NEAREST)
    
    # 保存为PNG格式（支持透明度）
    pixelated_image.save(output_path, format='PNG')

    return output_path
    
# # 使用示例
# pixelate('/Users/hyan/Devoff/artworks/nvshu/ai_nvshu/static/nvshu_images/combined_10-0-23_vertical.png', '/Users/hyan/Devoff/artworks/nvshu/ai_nvshu/static/nvshu_images/pixelated_hieroglyph_np.jpg', 20)


# # 使用示例
# if __name__ == "__main__":
#     input_file = "input.mp4"
#     output_file = "output_5sec.mp4"
    
#     success, message = trim_video(input_file, output_file)
#     print(message)