import random
import pickle
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import logging
from sklearn.metrics.pairwise import cosine_similarity
from word_vector_manager import *


# 保存向量关系
def save_dict_to_file(dictionary, filename):
    with open(filename, 'wb') as f:
        pickle.dump(dictionary, f)

def load_dict_from_file(filename):
    with open(filename, 'rb') as f:
        dictionary = pickle.load(f)
    return dictionary

class SharedKnowledge:
    def __init__(self):
        self.known_mappings = {}  # 已知的原始字符和EL字向量的映射关系
        self.pending_mappings = []  # 待加入的EL字符
        self.simple_el_dict = {}  # 简单的EL字典，存储降维后的向量



class Machine:
    def __init__(self, name, knowledge, n, pca):
        self.name = name
        self.knowledge = knowledge
        self.masked_num = n
        self.replaced_indices = []  # 存储被替换的位置
        self.pca = pca  # PCA模型

        # 初始化 known_mappings
        self.knowledge.known_mappings.update({punctuation: punctuation for punctuation in ['，', '。', '！', '？']})
        self.word_clusters = self.cluster_word_vectors(word_vectors.vectors)

    def delete_from_simple_el_dict(self, original_char):
        if original_char in self.knowledge.simple_el_dict:
            del self.knowledge.simple_el_dict[original_char]

    def add_to_simple_el_dict(self, original_char, vector):
        #print(f"=====start add_to_simple_el_dict=======")
        # 使用PCA模型将向量降维
        transformed_vector = self.transform_with_pca(vector)

        # 检查这个向量是否已经在simple_el_dict字典中
        max_attempts = 20  # 设定最大尝试次数
        attempts = 0  # 初始化尝试次数计数器
        while any([np.array_equal(transformed_vector, existing_vector)
            for existing_vector in self.knowledge.simple_el_dict.values()]) and attempts < max_attempts:
                # 如果已经在字典中，直接随机生成一个新的三维向量（每个元素在0-23之间 包括23）
                transformed_vector = [random.randint(0, 23) for _ in range(3)]
                attempts += 1

        # 将降维后的向量添加到simple_el_dict字典中
        #print(f"=====end add_to_simple_el_dict=======")
        self.knowledge.simple_el_dict[original_char] = transformed_vector


    def transform_with_pca(self, vector):
        # 使用PCA模型将向量降维
        transformed_vector = self.pca.transform([vector])[0]

        # 将PCA的输出归一化到0.1-0.9范围，然后乘以23并取整数
        # 避免产生0和23的数值
        min_val = np.min(transformed_vector)
        max_val = np.max(transformed_vector)
        # 使用这个增加随机噪声的归一化公式
        normalized_vector = 0.1 + 0.8 * (transformed_vector - min_val) / (max_val - min_val)
        # 添加噪声
        noise = np.random.uniform(-0.3, 0.3, size=normalized_vector.shape)
        normalized_vector += noise
        # 限制数值范围
        np.clip(normalized_vector, 0, 1, out=normalized_vector)
        integer_vector = np.round(normalized_vector * 23).astype(int)

        return integer_vector.tolist()

    def cluster_word_vectors(self, word_vectors):
        # 将字典形式的词向量转换为矩阵形式
        vectors_matrix = np.array([vectors for word, vectors in word_vectors.items()])

        # Agglomerative Clustering Cluster BERT 的词向量
        agglomerative_clustering_model = AgglomerativeClustering(
            n_clusters=None,
            # affinity='cosine',
            linkage='average',
            distance_threshold=0.2  # 用于根据距离控制簇的数量
        )
        labels = agglomerative_clustering_model.fit_predict(vectors_matrix)

        # 创建一个映射关系，关联字符与对应的聚类标签
        word_clusters = {word: label for (word, _), label in zip(word_vectors.items(), labels)}

        return word_clusters

    def send_message(self, message):
        # 将一条消息中的一些原始字符替换为EL字符，然后发送这条消息
        el_message, replaced_indices = self.replace_with_el(message)

        # 记录替换的位置
        self.replaced_indices = replaced_indices

        # 用特殊标记[*]表示被替换的字符，移除随机新增的EL字符
        marked_message = ''.join(['*' if i in replaced_indices else c for i, c in enumerate(el_message)])

        # 创建一个新列表，存储字符的EL表示（向量）
        el_message_vectors = []
        for i, c in enumerate(message):
            if c in self.knowledge.known_mappings and i in replaced_indices:
                el_message_vectors.append(self.knowledge.known_mappings[c])
            elif c in [mapping[0] for mapping in self.knowledge.pending_mappings] and i in replaced_indices:
                el_char = [mapping[1] for mapping in self.knowledge.pending_mappings if mapping[0] == c][0]
                el_message_vectors.append(el_char)
            else:
                el_message_vectors.append(word_vectors.get_vector(c))  # 变更: 设置未被替换的原汉字向量

        return marked_message, el_message_vectors


    def receive_message(self, message, el_message_vectors):
        #print(f"receive_message start")

        # 加入已知EL到原始字符的转换
        for idx, el_char in enumerate(el_message_vectors):
            # 5/0
            if any([np.array_equal(el_char, v) for v in self.knowledge.known_mappings.values()]):
                original_char = [mapping[0] for mapping in self.knowledge.known_mappings.items() if np.array_equal(mapping[1], el_char)][0]
                message = message[:idx] + original_char + message[idx+1:]

        guess_message = self.guess_el(message, el_message_vectors)

        # 更新已知映射
        for mapping in self.knowledge.pending_mappings:
            if mapping[0] in guess_message and mapping not in self.knowledge.known_mappings.items():
                self.knowledge.known_mappings[mapping[0]] = mapping[1]

        #print(f"receive_message end")
        return guess_message


    def replace_with_el(self, message):
        #print(f"———— Enter replace_with_el ————")
        el_message = list(message)
        replaced_indices = []

        # 先检查消息中的字符是否所有都在EL字典中
        all_in_el = all([char in self.knowledge.known_mappings for char in message if char not in ['，', '。', '！', '？']])
        # 只有在不满足这个条件时，才去循环替换字符
        if not all_in_el:
            possible_choices = [char for char in message if (char not in ['，', '。', '！', '？']) and (not char in self.knowledge.known_mappings)]
            while len(replaced_indices) < self.masked_num:
                i = random.randrange(len(possible_choices))
                char = possible_choices[i]
                i = message.index(char)
                if i not in replaced_indices and char not in ['，', '。', '！', '？'] and char not in self.knowledge.known_mappings:
                    if char not in self.knowledge.known_mappings:
                        # print(f"creating new EL")
                        el_char = self.create_el_char(char)
                        el_message[i] = "*"
                    else:
                        el_message[i] = "*"
                        replaced_indices.append(i)

                    replaced_indices.append(i)

        else:  # 如果所有的字符都在EL字典中，返回"skip_flag"
            return "skip_flag", []

        #print(f"——————— Finish replace_with_el ———————")
        return ''.join(el_message), replaced_indices

    def create_el_char(self, original_char):
        #print(f"~~~~~~~~~~~~~~ Start create_el_char ~~~~~~~~~~~~~~~")
        # 使用聚类方法选择与 original_char 语义相似的潜在向量
        word_clusters = self.word_clusters
        if original_char in word_clusters.keys():
            # 确保选择到的词不在同一个簇
            source_cluster = word_clusters[original_char]
            candidate_words = [word for word, cluster in word_clusters.items() if cluster != source_cluster]
        else:
            candidate_words = chinese_list
        
        if not candidate_words:
            candidate_words = chinese_list

        max_attempts = 1000  # 设定最大尝试次数
        attempts = 0         # 初始化尝试次数计数器
        # 选择与原始字符具有某种相似性但与原始字符不在同一簇的其他词向量
        el_vector = None
        while attempts < max_attempts:
            #print(f"EL create attemp: {attempts}")
            # 调用 select_cluster 函数
            candidate_word = self.select_cluster(original_char)

            # Edit: randomize
            noise = random.uniform(0, 1)
            el_vector = (1 - noise) * word_vectors.get_vector(original_char) + noise * word_vectors.get_vector(candidate_word)

            # 确保所选字不在已经在已知映射 known_mappings 列表中
            if candidate_word not in self.knowledge.known_mappings.keys():
                break
            attempts += 1

        #print(f"sync knowledge...")
        self.knowledge.pending_mappings.append((original_char, el_vector))
        #print(f"sync knowledge finished, 降维准备...")
        # 将EL字的向量降维，并添加到simple_el_dict字典中
        #print(f"降维完毕...")
        self.add_to_simple_el_dict(original_char, el_vector)
        logging.info(f"EL：{original_char}，降维后：{self.knowledge.simple_el_dict[original_char]}")
        #print(f"~~~~~~~~~~~~ End create_el_char ~~~~~~~~~~~~~~~~~~")
        return el_vector

    def choose_similar_char(self, original_char):
        return random.choice(chinese_list)

    def check_guess(self, guess_message, el_message_vectors, the_other_machine):
        is_correct = True

        for idx in range(len(guess_message)):
            el_char = el_message_vectors[idx]
            original_char = [mapping[0] for mapping in self.knowledge.pending_mappings if np.array_equal(mapping[1], el_char)]

            # 如果original_char列表非空且猜测不正确
            if original_char and original_char[0] != guess_message[idx]:
                is_correct = False
                break

        # 使用 self.replaced_positions 选择待告知的加密字符
        if not is_correct:
            valid_indices = [idx for idx in self.replaced_indices if idx < len(self.knowledge.pending_mappings)]
            if valid_indices:
                mapping_index = random.choice(valid_indices)
                feedback = self.knowledge.pending_mappings[mapping_index]
            else:
                # 当 valid_indices 为空时选择一个可用的映射
                available_mappings = [mapping for mapping in self.knowledge.pending_mappings if mapping[0] not in the_other_machine.knowledge.known_mappings]
                feedback = random.choice(available_mappings) if available_mappings else None
                # print(len(self.knowledge.pending_mappings))
        else:
        # 从pending_mappings中获取正确映射
            correct_char = guess_message[self.replaced_indices[0]]
            feedback = (correct_char, [mapping[1] for mapping in self.knowledge.pending_mappings if mapping[0] == correct_char][0])
        return is_correct, feedback  # 依然返回 is_correct 变量的结果及 feedback

    def guess_el(self, message, el_message_vectors):
        # 修改猜测过程，只猜未知原文字符（标记为*的字符）
        unknown_indices = [i for i, char in enumerate(message) if char == "*"]

        guess_message = list(message)
        for idx in unknown_indices:
            guess_char = self.guess_char(el_message_vectors[idx])
            guess_message[idx] = guess_char

        #print(f"guess_el end")
        return ''.join(guess_message)


    def select_cluster(self, original_char):
        # #print(f"===========Enter select cluster!======")
        # # 使用linkage方法和fcluster方法进行agglomerative clustering
        # vectors_matrix = np.array([word_vectors[word] for word in chinese_list])
        # Z = linkage(vectors_matrix, method='average', metric='cosine')
        # clusters = fcluster(Z, t=0.1, criterion='distance')
        # 这段代码没有用
        if original_char in self.word_clusters.keys():
            cluster_label = self.word_clusters[original_char]  # 获取 original_char 的聚类标签
            # 过滤与 original_char 在同一聚类的词
            candidate_words = {word for word, label in self.word_clusters.items() if label != cluster_label}
        else:
            candidate_words = {word for word in chinese_list}

        # 确保不重复选择已知映射和待定映射中的字符
        known_mappings_values_set = {tuple(v) for v in self.knowledge.known_mappings.values() if isinstance(v, np.ndarray)} # 将已知映射的值转换为元组并存储在集合中
        candidate_words -= set(self.knowledge.known_mappings.keys())  # 从键中删除已知映射
        candidate_words -= set(mapping[1] for mapping in self.knowledge.pending_mappings if isinstance(mapping[1], str))  # 修改
        candidate_words -= {tuple(mapping[1]) for mapping in self.knowledge.pending_mappings if isinstance(mapping[1], np.ndarray)}  # 修改

        #print(f"===========End select cluster!========")
        return random.choice(list(candidate_words))

    def guess_char(self, el_char):
        # 猜测一个EL字符代表的原始字符
        possibly_correct_char = random.choice(chinese_list)
        # 确保每次猜测的字符不重复
        if list(el_char) != list(word_vectors.get_vector(possibly_correct_char)):
            return possibly_correct_char
        else:
            return random.choice([char for char in chinese_list if char != el_char])



def get_sublist_keys(dictionary, start_key, end_key):
    # Convert dictionary keys to a list
    keys_list = list(dictionary.keys())

    # Find the indices of the start and end keys
    start_index = keys_list.index(start_key)
    end_index = keys_list.index(end_key)
    
    # Check if start index is actually before end index
    if start_index > end_index:
        start_index, end_index = end_index, start_index

    # Generate a random length for the sublist between start and end indices (inclusive)
    length = random.randint(1, end_index - start_index + 1)
    # length = random.randint(1, 30)

    # Retrieve the sublist of keys of the given length
    sublist_keys = keys_list[start_index:start_index + length]
    
    return sublist_keys


def get_differing_indices(list1, list2):
    # Ensure both lists are of the same length
    if len(list1) != len(list2):
        raise ValueError("Both lists must be of the same length")

    # Use a list comprehension to get the differing indices
    differing_indices = [i for i, (a, b) in enumerate(zip(list1, list2)) if a != b]

    return differing_indices

def replace_string_element(s, index, replacement):
    # Convert string to list
    s_list = list(s)
    
    # Replace the element at the given index
    s_list[index] = replacement
    
    # Convert list back to string
    return ''.join(s_list)


def euclidean_distance(v1, v2):
    """Compute the Euclidean distance between two vectors."""
    v1 = np.array(v1)
    v2 = np.array(v2)
    return np.linalg.norm(v1 - v2)

def get_random_sublist_keys(dictionary, start_key, end_key, length):
    # Convert dictionary keys to a list
    keys_list = list(dictionary.keys())

    # Get the indices of the start and end keys
    start_index = keys_list.index(start_key)
    end_index = keys_list.index(end_key)

    # Check if start index is before end index, if not swap them
    if start_index > end_index:
        start_index, end_index = end_index, start_index

    # Ensure the selected sublist length includes the start and end keys
    if length < 2:
        raise ValueError("Length should be at least 2 to include both start and end keys")

    # Determine potential length of the sublist between start and end indices (excluding start and end keys)
    potential_length = end_index - start_index - 1

    # Check if the required length minus 2 (for start and end keys) is feasible
    if length - 2 > potential_length:
        length = potential_length - 2
        # raise ValueError("Requested sublist length minus 2 exceeds the number of available keys between start and end keys")

    # Randomly select keys within the span based on the given length minus 2 (for start and end keys)
    selected_keys = sorted(random.sample(keys_list[start_index+1:end_index], length-2))

    # Sort the selected keys based on the Euclidean distance of their values to the end key's value
    sorted_keys = sorted(selected_keys, key=lambda k: euclidean_distance(dictionary[k], dictionary[end_key]))

    # Add start and end keys to the beginning and end of the list, respectively
    final_list = [start_key] + sorted_keys + [end_key]
    
    return final_list



def find_closest_key_to_midpoint(dictionary, key1, key2):
    # Get vectors corresponding to the two keys
    v1 = np.array(dictionary[key1])
    v2 = np.array(dictionary[key2])

    # Calculate the midpoint
    midpoint = (v1 + v2) / 2

    # Find the key with the vector that has the smallest distance to the midpoint
    # Exclude the two provided keys from consideration
    closest_key = min(
        [k for k in dictionary.keys() if k not in [key1, key2]], 
        key=lambda k: euclidean_distance(dictionary[k], midpoint)
    )

    return closest_key

def magnitude(v):
    return np.linalg.norm(v)



def select_keys_from_span(dictionary, start_key, end_key, num_keys_to_select):
    # Extract keys between start and end (inclusive)
    keys = list(dictionary.keys())
    start_idx = keys.index(start_key)
    end_idx = keys.index(end_key)
    
    span_keys = keys[start_idx:end_idx + 1]
    
    # If we have fewer keys in the span than the required selection, just return them
    if len(span_keys) <= num_keys_to_select:
        return span_keys
    
    # Compute weights for selection; middle keys are weighted higher
    middle_idx = len(span_keys) // 2
    weights = [1 + abs(i - middle_idx) for i in range(len(span_keys))]
    
    # Normalize the weights to make it a probability distribution
    weights = [w / sum(weights) for w in weights]
    
    # Randomly select keys based on the weighted probability without replacement
    selected_keys = np.random.choice(span_keys, size=num_keys_to_select, replace=False, p=weights)
    
    # Sort the selected keys based on their similarity to the end key's value
    end_vector = dictionary[end_key].reshape(1, -1)
    similarities = [cosine_similarity(dictionary[key].reshape(1, -1), end_vector)[0][0] for key in selected_keys]
    
    sorted_keys = [k for _, k in sorted(zip(similarities, selected_keys), key=lambda pair: -pair[0])]

    sorted_keys = [start_key] + sorted_keys + [end_key]
    
    return sorted_keys


    # sorted_dict = dict(sorted(word_vectors.items(), key=lambda item: magnitude(item[1])))

def get_transition_keys(data, start_key, end_key):
    """Get keys that transition from start_key to end_key based on their vector values."""
    start_vec = data[start_key]
    end_vec = data[end_key]
    
    weights = {}
    
    for key, vec in data.items():
        distance_to_start = euclidean_distance(vec, start_vec)
        distance_to_end = euclidean_distance(vec, end_vec)
        
        # Avoid dividing by zero
        if distance_to_start + distance_to_end == 0:
            continue

        # Calculate weight based on distances to start and end vectors
        weight = distance_to_start / (distance_to_start + distance_to_end)
        weights[key] = weight

    # Sort keys based on weight
    sorted_keys = sorted(weights, key=weights.get)
    
    return sorted_keys


def sample_transition_keys(transition_keys, sample_length):
    # """Sample keys with more emphasis on the beginning."""
    # indices = np.linspace(0, len(transition_keys)-1, sample_length)
    # exponentiated_indices = np.power(indices, 1.5).astype(int)
    # print(exponentiated_indices)
    # exponentiated_indices = np.unique(np.clip(exponentiated_indices, 0, len(transition_keys)-1))
    # print(exponentiated_indices)
    # return [transition_keys[i] for i in exponentiated_indices]
    """Sample keys with more emphasis on the beginning and ensure continuous entries towards the end."""
    indices = np.linspace(0, len(transition_keys)-1, sample_length)
    exponentiated_indices = np.power(indices, 1.5).astype(int)
    exponentiated_indices = np.unique(np.clip(exponentiated_indices, 0, len(transition_keys)-1))
    
    # Ensure the last entries are continuous
    for i in range(len(exponentiated_indices) - 1, 0, -1):
        if exponentiated_indices[i] - exponentiated_indices[i-1] > 1:
            exponentiated_indices[i-1] = exponentiated_indices[i] - 1

    # print(exponentiated_indices)

    return [transition_keys[i] for i in exponentiated_indices]



def sample_keys_parabolically(keys, sample_length):
    # Generate a parabolic distribution
    x = np.linspace(-1, 1, len(keys))
    y = -x**2 + 1

    # Normalize the distribution
    probabilities = y / sum(y)

    sampled_keys = np.random.choice(keys, size=sample_length, replace=False, p=probabilities)
    
    return list(sampled_keys)

#简化向量打印
def print_known_mappings(known_mappings, n=2):
    pretty_mappings = {}
    for k, v in known_mappings.items():
        if isinstance(v, np.ndarray):
            pretty_values = list(v[:n])
            pretty_values.append("...")
            pretty_mappings[k] = f"array({pretty_values})"
        else:
            pretty_mappings[k] = v
    print("当前EL字典:", pretty_mappings)


