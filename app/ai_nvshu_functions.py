# from gradio_client import Client, handle_file
from googletrans import Translator
from transformers import BertTokenizer, BertModel
import torch
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from utils import *
from dict_io import *
from config import Config
from dotenv import load_dotenv
import os
from PIL import Image
import time
# from langchain_google_genai import ChatGoogleGenerativeAI
from huggingface_hub import InferenceClient
HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

# variables --------------------
load_dotenv()  # 加载 .env 文件中的环境变量
nvshu_ai = InferenceClient(
    provider="sambanova",
    api_key=HF_TOKEN,
)

# 加载预训练的 BERT 模型和分词器
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')

simple_el_dict = load_dict_from_file('knowledge_tmp/simple.pkl')

# functions --------------------
def translate_text(text, src_language='en', target_language="zh-cn"):
    translator = Translator()
    result = translator.translate(text, src=src_language, dest=target_language)
    return result.text

# 定义向量化函数
def vectorize_texts(texts):
    embeddings = []
    for text in texts:
        # 对文本进行分词
        inputs = tokenizer(text, return_tensors='pt', padding=True, truncation=True, max_length=512)
        # 获取BERT模型输出
        with torch.no_grad():
            outputs = model(**inputs)
        # 提取最后一层的隐藏状态的第一个 token 的向量表示（[CLS] token）
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        embeddings.append(cls_embedding.numpy())
    # 将嵌入列表转换为 NumPy 数组
    return np.vstack(embeddings)


def find_most_similar_texts(input_embedding, text_embeddings, texts, n=5):
    # 计算相似度
    similarity_matrix = cosine_similarity(input_embedding, text_embeddings)

    # 找到最相似的文本的索引
    most_similar_indices = np.argsort(similarity_matrix[0, 1:])[-n:][::-1] + 1

    # 获取最相似的文本并去掉换行符
    most_similar_texts = [texts[i].replace('\n', '') for i in most_similar_indices]

    return most_similar_texts, most_similar_indices


# 最主要的函数 --------------------
# 视频/图像识别 + 找到最相近的三句诗，返回
def recognize_and_translate(filename, session_id):
    try:
        print(f"调用 filename: {filename}")
        # Ensure filename is a string (in case it's passed as a tuple)
        if isinstance(filename, tuple):
            filename = filename[0]  # Take the first element if it's a tuple
            
        video_path = os.path.join(Config.UPLOAD_FOLDER, os.path.basename(filename))
        print(f"调用 video_path: {video_path}")
        
        # Verify the path exists
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        # 识别图片内容
        from video_analysis import VideoAnalyzer
        analyzer = VideoAnalyzer(Config.VISION_MODEL, session_id)
        result = analyzer.analyze_video(video_path)
        # 翻译为中文
        return translate_text(result), result
    except Exception as e:
        print(f"调用video recg API时出错: {str(e)}")

# 怀旧打字机，纸上诉真情。
def find_similar(translated_result, n=3):
    # 读中英文版的
    poems = list()
    poems_eng = list()
    with open('knowledge_base/nvshu_origin_with_eng.txt', 'r', encoding='utf-8') as file:
        for index, line in enumerate(file):
            # Check if the line index is even or odd
            if index % 2 == 0:
                poems.append(line.rstrip())
            else:
                poems_eng.append(line.rstrip())
    poem_embeddings = load_dict_from_file("knowledge_base/poem_embeddings")
    try:
        # 找到最相似的诗句
        input_embedding = vectorize_texts([translated_result])
        most_similar_texts, idx = find_most_similar_texts(input_embedding, poem_embeddings, poems, n)
        most_similar_texts_eng = [poems_eng[i] for i in idx]

        # # 将数组转换为带换行符的字符串
        # most_similar_texts_str = '。  \n'.join(most_similar_texts)
        # most_similar_texts_eng_str = '  \n'.join(most_similar_texts_eng)
        # return most_similar_texts_str, most_similar_texts_eng_str
        return most_similar_texts, most_similar_texts_eng
    except Exception as e:
        print(f"find_similar()函数出错: {str(e)}")

def validate_poem_format(poem):
    """检查是否为五言诗（两句，每句五个字）"""
    normalized_poem = poem.replace(",", "，")
    parts = [part.strip() for part in normalized_poem.split("，") if part.strip()]
    return len(parts) == 2 and all(len(part.strip()) == 5 for part in parts)


def create_new_poem(video_description, similar_poems, max_retries=2):
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            # v2
            completion = nvshu_ai.chat.completions.create(
                model=Config.VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位旧时的女性诗人，必须严格按照五言诗格式（两句，每句五个字）生成诗歌。写一句五言诗，如 一齐花纸女，我来几俫欢 （五个字，五个字）来写。要求：上下两句，每句都是五个字，严禁不同字数，共十个中文字。直接给出诗句，中间用逗号分开，不要用特殊字符。",
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"{video_description}，基于这段文字内容，请你以旧时的女性的视角，结合这三句诗句：{similar_poems}创作一个新的五言诗。"
                            }
                        ]
                    }
                ],
                max_tokens=50,
            )
            new_poem = completion.choices[0].message.content.strip()

            # 检查诗歌格式（确保是五言诗）
            if not validate_poem_format(new_poem):
                print(new_poem)
                raise ValueError("Generated poem does not meet the required format")

            # 返回诗歌及其翻译
            return new_poem, translate_text(new_poem, 'zh-cn', 'en')
        except Exception as e:
            last_error = e
            print(f"Attempt {retry_count + 1} failed: {e}")
            retry_count += 1
            if retry_count <= max_retries:
                time.sleep(1)  # 稍作延迟再重试
    # 如果所有尝试都失败，返回默认值
    print(f"All retries failed. Last error: {last_error}")
    return "江永女书奇，闺中秘语稀。", translate_text("江永女书奇，闺中秘语稀。", 'zh-cn', 'en')


# create_nvshu_from_poem('江永女书奇，闺中秘语稀。')
# poem = '江永女书奇，闺中秘语稀。'
def create_nvshu_from_poem(poem):
    # A发送诗句给B
    EL_mappings = load_dict_from_file('knowledge_tmp/EL_vectors.pkl')
    
    with open('knowledge_base/pca.pkl', 'rb') as f:
        pca = pickle.load(f)

    current_knowledge = SharedKnowledge()
    current_knowledge.known_mappings = EL_mappings
    current_knowledge.simple_el_dict = simple_el_dict

    # 创建两个Machine对象
    machine_A = Machine('A', current_knowledge, n=1, pca=pca)
    machine_B = Machine('B', current_knowledge, n=1, pca=pca)

    try:
        # print(f"尝试读取诗句……")
        marked_message, el_message_vectors = machine_A.send_message(poem)
        if marked_message == "skip_flag":   # 检查标记，并跳过当前句子
            print(f"已全包含，报错")
    except KeyError:
        print('error generating the character with agents')
    

    # B接收诗句并猜测EL字符
    max_tries = 5
    list_to_guess = list()
    word_idx = 0
    list_of_guess = []
    for j in range(max_tries):
        
        guess = machine_B.receive_message(marked_message, el_message_vectors)

        if j == 0:
            word_idx = get_differing_indices(guess, poem)[0]
            random_number = random.randint(1000, 4000)
            list_to_guess = get_transition_keys(word_vectors, guess[word_idx], poem[word_idx])
            list_to_guess = sample_transition_keys(list_to_guess, random_number)
            # print(list_to_guess)
        else:
            if len(list_to_guess) > 0:
                guess = replace_string_element(guess, word_idx, list_to_guess[0])
                list_to_guess = list_to_guess[1:]
                
        # print(f"Guess result {j}: {guess}")
        list_of_guess.append(guess[machine_A.replaced_indices[0]])
        is_correct, feedback = machine_A.check_guess(guess, el_message_vectors, machine_B)

        if is_correct:
            # print(f"B的猜测在第{j+1}次就完全正确！")
            machine_A.knowledge.known_mappings[feedback[0]] = feedback[1]
            machine_B.knowledge.known_mappings[feedback[0]] = feedback[1]
            break

        elif j == max_tries -  1:
            if feedback is not None: # 确认feedback非空
                # print(f"在{j+1}次尝试后，A告诉B正确答案")
                # 更新 A 和 B 的 known_mappings
                machine_A.knowledge.known_mappings[feedback[0]] = feedback[1]
                machine_B.knowledge.known_mappings[feedback[0]] = feedback[1]

                # 改动这两句代码，B在知道答案后将其加入知识库,然后再返回
                updated_guess = machine_B.receive_message(marked_message, el_message_vectors)
                # print(f"获得答案后，B答对了，猜测结果为：{updated_guess}")
                guess = updated_guess
        
    # 中文字, 中文字位置, 女书字（3-dim），768-dim vect, list of guess
    return feedback[0], poem.index(feedback[0]), machine_A.knowledge.simple_el_dict[feedback[0]], list(feedback[1].astype('float')), list_of_guess #'\n'.join(list_of_guess)

def get_char_translate(char_cn, poem, poem_eng):
    completion = nvshu_ai.chat.completions.create(
        model=Config.VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"这句五言诗{poem}的翻译是{poem_eng}，请返回对应{char_cn}这个字的英语单词。要求只要输出一个单词。"
                    }
                ]
            }
        ],
        max_tokens=50,
    )
    return completion.choices[0].message['content']
    
def find_content_boundaries(img_array, background_value=16, tolerance=2):
    """找到字的实际内容边界，返回上下实际内容的位置"""
    mask = np.abs(img_array - background_value) > tolerance
    rows = np.any(mask, axis=1)
    if not np.any(rows):
        return None, None
    
    # 找到实际内容的上下边界
    content_top = np.where(rows)[0][0]
    content_bottom = np.where(rows)[0][-1]
    
    return content_top, content_bottom

def trim_whitespace(image, padding = 0):
    """裁剪图片周围的空白区域（针对灰度图像）"""
    # 转换为numpy数组
    img_array = np.array(image)
    
    # 对于灰度图像，判断非背景像素
    # 假设背景色为16（根据你的图片情况）
    mask = img_array != 16
    
    # 找到非空白区域的边界
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not np.any(rows) or not np.any(cols):
        return image
    
    # 获取非空白区域的边界索引
    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]
    
    # 添加小边距
    y_min = max(0, y_min - padding)
    y_max = min(img_array.shape[0], y_max + padding)
    x_min = max(0, x_min - padding)
    x_max = min(img_array.shape[1], x_max + padding)
    
    # 裁剪图片
    return image.crop((x_min, y_min, x_max, y_max))


def replace_with_simple_el(message):
    el_message = [char for char in message]
    replaced_indices = []

    # 先检查消息中的字符是否所有都在EL字典中
    known_chinese = list(simple_el_dict.keys()) + ['，', '。', '！', '？', '\n']
    check_in_el = [char in known_chinese for char in message]
    
    # 找出 True 值的位置
    true_indices = [i for i, value in enumerate(check_in_el) if value]
    for i in true_indices:
        # print(i)
        if message[i] not in ['，', '。', '！', '？', '\n']:
            el_message[i] = simple_el_dict[message[i]]
            replaced_indices.append(i)

    return el_message, ''.join([str(char) for char in el_message]), replaced_indices



def init_marked_message(message):
    # A发送诗句给B
    known_chinese = list(simple_el_dict.keys())
    possible_choices = [char for char in message if (char not in ['，', '。', '！', '？']) and (not char in known_chinese)]
    i = random.randrange(len(possible_choices))
    char = possible_choices[i]
    pos = message.index(char)
    marked_message = ''.join(['*' if i in [pos] else c for i, c in enumerate(message)])

    return pos, char, marked_message

def print_nvshu_list(nvshu_list):
    """
    打印女书字符列表，使其更易读
    参数:
        nvshu_list: 包含中文字符和三维向量的列表
    """
    print("\n女书字符列表:")
    print("-" * 50)
    for i, item in enumerate(nvshu_list):
        if isinstance(item, str):
            print(f"位置 {i}: 中文字符 '{item}'")
        elif isinstance(item, list) and len(item) == 3:
            print(f"位置 {i}: 三维向量 {item}")
    print("-" * 50)


def create_combined_nvshu_image(repr_3dim):
    """将3个女书字符图片拼接成一个大图"""
    # 假设所有图片都是相同尺寸
    image_dir = 'knowledge_base/nvshu_comp'  # 存放女书字符图片的目录
    images = []
    trimmed_images = []
    content_boundaries = []
    
    # 加载每个数字对应的图片
    for num in repr_3dim:
        image_path = os.path.join(image_dir, f'{int(num)}.png')
        if os.path.exists(image_path):
            img = Image.open(image_path)
            images.append(img)
            trimmed_img = trim_whitespace(img)
            trimmed_images.append(trimmed_img)
            # 获取每个字的实际内容边界
            img_array = np.array(trimmed_img)
            top, bottom = find_content_boundaries(img_array)
            if top is not None and bottom is not None:
                content_boundaries.append((top, bottom))
    
    if not trimmed_images:
        return None
    
    # 获取单个图片的尺寸
    width, height = images[0].size
    
    # 创建新图片（水平排列）
    combined_width = width * len(images)
    combined_height = height
    combined_image = Image.new('RGBA', (combined_width, combined_height))
    # 拼接图片
    for i, img in enumerate(images):
        combined_image.paste(img, (i * width, 0))
    # 保存临时文件
    output_path = os.path.join('static/nvshu_images', f'combined_{"-".join(map(str, repr_3dim))}.png')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined_image.save(output_path)
    
    # 创建新图片（竖直排列）
    # 找到最大宽度
    max_width = max(img.size[0] for img in trimmed_images)
    # 计算总高度（加上字符间距）
    spacing = 20  # 字符间距，可以调整
    total_height = sum(img.size[1] for img in trimmed_images) + spacing * (len(trimmed_images) - 1)
    
    # 创建新图片
    combined_image = Image.new('RGBA', (max_width, total_height), (0, 0, 0, 0))
    
    # 拼接图片
    current_y = 0
    for img in trimmed_images:
        # 计算水平居中位置
        x_offset = (max_width - img.size[0]) // 2
        combined_image.paste(img, (x_offset, current_y))
        current_y += img.size[1] + spacing
    # 保存临时文件
    output_path = os.path.join('static/nvshu_images', f'combined_{"-".join(map(str, repr_3dim))}_vertical.png')
    combined_image.save(output_path)
    
    # 返回相对路径
    return output_path
