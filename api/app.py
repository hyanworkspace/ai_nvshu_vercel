from flask import Flask, render_template, request, jsonify, session, send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
from config import Config
from ai_nvshu_functions import find_similar, recognize_and_translate, create_new_poem, create_nvshu_from_poem, create_combined_nvshu_image, replace_with_simple_el, get_char_translate
from utils import load_dict_from_file
from process_video import pixelate
# from huggingface_hub import login
# import logging

# 设置日志配置
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.secret_key = 'a-secret-key'
# app.secret_key = os.environ.get('SECRET_KEY', 'a-secret-key')  # 使用环境变量中的密钥
# # 登录 Hugging Face
# huggingface_token = os.environ.get('HUGGINGFACE_TOKEN')
# if huggingface_token:
#     login(token=huggingface_token)

# 使用 Config 类中的配置
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.config['DICTIONARY_PATH'] = Config.DICTIONARY_PATH


# 确保上传目录存在
if not os.path.exists(Config.UPLOAD_FOLDER):
    os.makedirs(Config.UPLOAD_FOLDER) 


# 允许的文件类型
ALLOWED_EXTENSIONS = Config.ALLOWED_EXTENSIONS

def allowed_file(filename):
    # return True/False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def before_request():
    # 如果用户没有session_id，创建一个新的
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

@app.route('/')
def index():
    return render_template('see.html')

@app.route('/see')
def see():
    return render_template('see.html')

# @app.route('/upload', methods=['POST'])
# def upload_file():
#     if 'file' not in request.files:
#         return jsonify({'error': '没有文件'}), 400
    
#     file = request.files['file']
#     if file.filename == '':
#         return jsonify({'error': '没有选择文件'}), 400
    
#     if file and allowed_file(file.filename):
#         # 生成唯一的文件名
#         original_filename = secure_filename(file.filename)
#         file_extension = original_filename.rsplit('.', 1)[1].lower()
#         unique_filename = f"{str(uuid.uuid4())}.{file_extension}"
        
#         # 保存文件
#         file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
#         file.save(file_path)
        
#         # 生成文件URL
#         file_url = f'/uploads/{unique_filename}'
#         session['video_url'] = file_url

#         return jsonify({
#             'message': '文件上传成功',
#             'file_url': file_url
#         })
    
#     return jsonify({'error': '不允许的文件类型'}), 400

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    if file and allowed_file(file.filename):
        # 生成唯一的文件名
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{str(uuid.uuid4())}.{file_extension}"
        
        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # 生成文件URL
        file_url = f'/uploads/{unique_filename}'
        
        # 同时设置 video_url 和 original_video_url
        session['video_url'] = file_url
        session['original_video_url'] = file_url

        return jsonify({
            'message': '文件上传成功',
            'file_url': file_url
        })
    
    return jsonify({'error': '不允许的文件类型'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/<path:filename>')
def serve_video(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    response = send_from_directory(file_path)
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Content-Type'] = 'video/mp4'
    return response

# 可以添加一个定期清理旧会话文件的任务
@app.cli.command('cleanup-uploads')
def cleanup_uploads():
    # 实现清理逻辑，例如删除24小时前的会话目录
    pass




# ----------------------------------------
# think 
# ----------------------------------------

@app.route('/think')
def think():
    if app.debug:
        video_url = '/uploads/output_5sec.mp4'
        original_video_url = '/uploads/output_5sec.mp4'
    else:
        video_url = request.args.get('video_url')
        original_video_url = request.args.get('original_video_url', video_url) 
    # 确保session中有正确的URL
    session['video_url'] = video_url
    session['original_video_url'] = original_video_url
    return render_template('think.html', video_url=video_url, original_video_url=original_video_url)

@app.route('/describe_video', methods=['POST'])
def describe_video():
    try:
        if app.debug:
            video_desc = '这里是ai叙述文字内容'
            video_desc_en = 'This is english translation of video description'
        else:
            
            video_url = session.get('original_video_url', session.get('video_url'))
            if not video_url:
                raise ValueError('No video URL provided for describe_video')
            
            data = request.get_json()
            if data and data.get('original_video_url'):
                video_url = data['original_video_url']
            
            # 从 URL 中提取文件名
            filename = os.path.basename(video_url.split('?')[0])
            # 构建完整的文件路径
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # 规范化路径
            video_path = os.path.abspath(os.path.normpath(video_path))
            
            print(f'处理的视频路径: {video_path}')
            
            # 验证文件是否存在
            if not os.path.isfile(video_path):
                raise FileNotFoundError(f'视频文件不存在: {video_path}')
            
            # 验证路径是否在允许的目录内
            if not video_path.startswith(os.path.abspath(app.config['UPLOAD_FOLDER'])):
                raise ValueError('无效的文件路径')
            
            video_desc, video_desc_en = recognize_and_translate(video_path, session['session_id'])

        return jsonify({
            "video_desc": video_desc,
            'video_desc_eng': video_desc_en
        })
    except Exception as e:
        print("Error:", str(e))  # 打印具体错误
        return jsonify({"error": str(e)}), 500

@app.route('/generate_poem', methods=['POST'])
def generate_poem():
    try:
        if app.debug:
            new_poem = '江永女书奇，闺中秘语稀。'
            new_poem_en = 'This is machine generated poem'
        else:
            data = request.get_json()
            new_poem, new_poem_en = create_new_poem(data.get('video_description'), data.get('similar_poems'))
            new_poem = new_poem.replace(',', '，')
            # print(new_poem)  # 打印诗句
        session['poem'] = new_poem
        session['poem_eng'] = new_poem_en
        return jsonify({
            "poem": new_poem,
            'poem_eng': new_poem_en
        })
    except Exception as e:
        print("Error:", str(e))  # 打印具体错误
        return jsonify({"error": str(e)}), 500


@app.route('/find_similar_poems', methods=['POST'])
def find_similar_poems():
    try:
        if app.debug:
            new_poem = ['最接近的女书诗句1', '\n最接近的女书诗句2', '\n最接近的女书诗句3']
            new_poem_en = ['This is machine generated poem1', '\nThis is machine generated poem2', '\nThis is machine generated poem3']
        else:
            data = request.get_json()
            new_poem, new_poem_en = find_similar(data.get('video_description'))
        session['similar_poems'] = new_poem
        return jsonify({
            "similar_poems": new_poem,
            'similar_poems_eng': new_poem_en
        })
    except Exception as e:
        print("Error:", str(e))  # 打印具体错误
        return jsonify({"error": str(e)}), 500



# ----------------------------------------
# guess 
# ----------------------------------------

@app.route('/replace_with_created_char', methods=['POST'])
def replace_with_created_char():
    try:
        data = request.get_json()
        poem = data.get('poem')
        if not poem:
            return jsonify({'error': 'No poem provided'}), 400
        
        poem_in_list, poem_replaced_with_simple_el, _ = replace_with_simple_el(data.get('poem'))
        return jsonify({
            'poem_orig': poem,
            "poem_in_list": poem_in_list,
            "poem_in_simple_el": poem_replaced_with_simple_el
        })
    except Exception as e:
        print("Error:", str(e))  # 打印具体错误
        return jsonify({"error": str(e)}), 500


@app.route('/generate_char', methods=['POST'])
def generate_char():
    try:
        if app.debug:
            char_pos, simple_el, repr_token, guess_char = load_dict_from_file('knowledge_tmp/tmp.pkl')
            char_translate = 'translateHere'
            char_cn = session['poem'][char_pos]
        else:
            data = request.get_json()
            char_cn, char_pos, simple_el, repr_token, guess_char = create_nvshu_from_poem(data.get('poem'))
            char_translate = get_char_translate(char_cn, data.get('poem'), data.get('poem_eng'))
        img_path = create_combined_nvshu_image(list(simple_el))
        img_path_pixelated = pixelate(img_path)
        session['char_img_path'] = img_path_pixelated
        session['char_translate'] = char_translate
        session['char_3dim'] = simple_el
        session['char'] = char_cn
        return jsonify({
            'char_translate':char_translate, # TODO 加到页面上
            "char_pos": char_pos,
            'simple_el': simple_el,
            'repr_token': repr_token,
            'char_img_path': img_path_pixelated, 
            'guess_char': guess_char
        })
    except Exception as e:
        print("Error:", str(e))  # 打印具体错误
        return jsonify({"error": str(e)}), 500


@app.route('/guess')
def guess():
    poem = request.args.get('poem', '')
    return render_template('guess.html', poem=poem)


@app.route('/get_result')
def get_result():
    return render_template('result.html', video_url=session['video_url'], char_translate=session['char_translate'], char_img_path=session['char_img_path'], char_3dim=session['char_3dim'])


@app.route('/save_user_name', methods=['POST'])
def save_user_name():
    data = request.get_json()
    session['user_name'] = data.get('user_name')
    return jsonify({'status': 'success'})

@app.route('/frame_11')
def frame_11():
    # 确保这里有你需要的模板和逻辑
    return render_template(
        'frame_11.html', 
        video_url=session['original_video_url'], char_img_path=session['char_img_path'], 
        char_3dim=session['char_3dim'], username=session['user_name'],  char_translate=session['char_translate'],
        poem=session['poem'], poem_eng=session['poem_eng'],  
        )

@app.route('/save_storage_preference', methods=['POST'])
def save_storage_preference():
    data = request.get_json()
    session['storage_preference'] = data.get('storage_preference')
    return jsonify({'status': 'success'})

@app.route('/dictionary')
def dictionary():
    return render_template('dictionary.html')

@app.route('/get_dictionary')
def get_dictionary():
    try:
        dictionary = load_dict_from_file(app.config['DICTIONARY_PATH'])
        return jsonify(dictionary)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_dictionary')
def search_dictionary():
    search_term = request.args.get('term', '').strip().lower()
    if not search_term:
        return jsonify({}), 400
    try:
        dictionary = load_dict_from_file(app.config['DICTIONARY_PATH'])
        # 简单搜索实现 - 匹配包含搜索词的中文字符
        results = {k: v for k, v in dictionary.items() if search_term in k.lower()}
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/add_to_dictionary', methods=['POST'])
def add_to_dictionary():
    try:
        from dict_io import add_to_dictionary
        char = session.get('char')
        char_3dim = session.get('char_3dim')
        
        if char and char_3dim:
            add_to_dictionary(char, char_3dim)
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': 'Missing character data'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(debug=False)