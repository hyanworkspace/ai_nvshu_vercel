# 这个代码需要在真正上线（每一版）之前运行一次
# 目的是为了建立一个最初的 knowledge_base
# 当然这个也可以是空的，这样就knowledge_base 就是空的
# 代表着这个AI女书没有任何初始的知识

import random
import torch
from transformers import BertModel, BertTokenizer
from sklearn.decomposition import PCA
from scipy.cluster.hierarchy import linkage, fcluster
import numpy as np
import pickle
from ai_nvshu_functions import create_combined_nvshu_image


import sys
sys.path.append('.')
from utils import *


tmp_dir = '/Users/hyan/Devoff/artworks/nvshu/flask_app_dev/knowledge_tmp'
consolidated_dir = '/Users/hyan/Devoff/artworks/nvshu/flask_app_dev/knowledge_base'
init_word_num = 20

# -----------------------------------------------------------------------
# main的第一部分，准备工作 
# -----------------------------------------------------------------------

# 加载预训练模型
model = BertModel.from_pretrained('bert-base-chinese')
tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
# 检查是否有可用的GPU
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)

# 读取chinese_list.txt
with open(f'{consolidated_dir}/chinese_list.txt', 'r', encoding='utf-8') as f:
    chinese_list = list(f.read()) + ['，', '。', '！', '？']


# 读取nvshu_final_poems.txt
with open(f'{consolidated_dir}/nvshu_final_poems.txt', 'r', encoding='utf-8') as f:
    poems = f.read().splitlines()



# # 为每个汉字创建一个向量表示
# word_vectors = {}
# for word in chinese_list:
#     inputs = tokenizer(word, return_tensors='pt').to(device)
#     outputs = model(**inputs)
#     word_vectors[word] = outputs.last_hidden_state[0].mean(0).detach().cpu().numpy()

# with open(f'{tmp_dir}/word_vectors.pkl', 'wb') as f:
#     pickle.dump(word_vectors, f)

# # -----------------------------------------------------------------------
# # PCA 
# # -----------------------------------------------------------------------

# # 高级版
# from sklearn.preprocessing import MinMaxScaler

# # 创建归一化对象
# scaler = MinMaxScaler()

# # 使用中文字典训练归一化模型，并对数据进行归一化
# word_vectors_values = list(word_vectors.values())
# word_vectors_values_normalized = scaler.fit_transform(word_vectors_values)

# # 创建PCA对象
# pca = PCA(n_components=3)

# # 使用归一化后的数据训练PCA模型
# pca.fit(word_vectors_values_normalized)

# with open(f'{tmp_dir}/scaler.pkl', 'wb') as f:
#     pickle.dump(scaler, f)

# with open(f'{tmp_dir}/pca.pkl', 'wb') as f:
#     pickle.dump(pca, f)


with open(f'{consolidated_dir}/pca.pkl', 'rb') as f:
    pca = pickle.load(f)


# -----------------------------------------------------------------------
# main的第二部分，也是主要部分，造字过程
# -----------------------------------------------------------------------
# 创建两个Machine对象
machine_A = Machine('A', SharedKnowledge(), n=1, pca=pca)
machine_B = Machine('B', SharedKnowledge(), n=1, pca=pca)

# 训练循环
i = 0

# while i < len(poems):
while i < init_word_num:
    print(f"iter:{i}")
    # 打印字典
    print_known_mappings(machine_A.knowledge.known_mappings)
    print(f"降维EL字典：{machine_A.knowledge.simple_el_dict}")

    # A发送诗句给B
    skip_flag = False
    try:
        print(f"尝试读取诗句……")
        marked_message, el_message_vectors = machine_A.send_message(poems[i])
        if marked_message == "skip_flag":   # 检查标记，并跳过当前句子
            print(f"已全包含，跳过")
            i += 1
            continue
    except KeyError:
        skip_flag = True

    if skip_flag:
        print(f"本轮无效，跳过")
        # 对于无效句子。删除生成的EL字符
        for original_char, _ in machine_A.knowledge.pending_mappings:
            machine_A.delete_from_simple_el_dict(original_char)
        print(f"删除了")
        machine_A.knowledge.pending_mappings = []  # 清空未完成训练的映射
        i += 1  # 分配新的诗句
        continue

    print(f"原始诗句: {poems[i]}")
    print(f"加密诗句: {marked_message}")

    # B接收诗句并猜测EL字符
    max_tries = 150

    list_to_guess = list()
    word_idx = 0
    
    for j in range(max_tries):
        #print(f"Guess {j}")
        guess = machine_B.receive_message(marked_message, el_message_vectors)


        if j == 0:
            word_idx = get_differing_indices(guess, poems[i])[0]
            random_number = random.randint(1000, 4000)
            list_to_guess = get_transition_keys(word_vectors, guess[word_idx], poems[i][word_idx])
            list_to_guess = sample_transition_keys(list_to_guess, random_number)
            print(list_to_guess)
        else:
            if len(list_to_guess) > 0:
                guess = replace_string_element(guess, word_idx, list_to_guess[0])
                list_to_guess = list_to_guess[1:]
                
        print(f"Guess result {j}: {guess}")

        is_correct, feedback = machine_A.check_guess(guess, el_message_vectors, machine_B)


        if is_correct:
            print(f"B的猜测在第{j+1}次就完全正确！")
            machine_A.knowledge.known_mappings[feedback[0]] = feedback[1]
            machine_B.knowledge.known_mappings[feedback[0]] = feedback[1]
            break

        elif j == max_tries -  1:
            if feedback is not None: # 确认feedback非空
                print(f"在{j}次尝试后，A告诉B正确答案")
                # 更新 A 和 B 的 known_mappings
                machine_A.knowledge.known_mappings[feedback[0]] = feedback[1]
                machine_B.knowledge.known_mappings[feedback[0]] = feedback[1]

                # 改动这两句代码，B在知道答案后将其加入知识库,然后再返回
                updated_guess = machine_B.receive_message(marked_message, el_message_vectors)
                print(f"获得答案后，B答对了，猜测结果为：{updated_guess}")
                guess = updated_guess
        

    # 清空 pending_mappings，以免传递到下一轮
    machine_A.knowledge.pending_mappings = []

    # 在循环的最后
    i += 1



#计算同一字的相似度关系
EL_mappings=machine_A.knowledge.known_mappings
punctuations=['，', '。', '！', '？']

# 遍历字典的键
for key in list(EL_mappings.keys()):  # 使用 list() 创建键的副本，因为我们不能在遍历字典时修改字典
    # 如果键是标点符号，就从字典中删除这个键值对
    if key in punctuations:
        del EL_mappings[key]

save_dict_to_file(EL_mappings, f'{tmp_dir}/EL_vectors.pkl')
save_dict_to_file(word_vectors, f'{tmp_dir}/word_vectors.pkl')
save_dict_to_file(machine_A.knowledge.simple_el_dict, f'{tmp_dir}/simple.pkl')


# EL_mappings_ = load_dict_from_file(f'{consolidated_dir}/EL_vectors.pkl')
# word_vectors_ = load_dict_from_file(f'{consolidated_dir}/word_vectors.pkl')
# simple_el_dict_ = load_dict_from_file(f'{tmp_dir}/simple.pkl')

# # 顺便 init 一下 dictionary，
# # 其实不用
# dict = {}
# for char in list(simple_el_dict_.keys()):
#     dict[char] = {
#         '3dim': simple_el_dict_[char],
#         'img_path': create_combined_nvshu_image(simple_el_dict_[char])
#     }
# dict[char]
# import pandas as pd
# pd.DataFrame(dict).T