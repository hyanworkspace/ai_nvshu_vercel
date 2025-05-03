# Nvshu Web App repo

这个repo的大致结构：
```
root/
│
├── requirements.txt # repo 的依赖
├── app.py # python backend, 类似于后端服务器
├── config.py # 存一些参数
├── ai_nvshu_functions.py # 用来计算女书不同输出的函数，诗歌，字，etc。
├── process_video.py # 用于处理视频和图片的工具函数
├── templates/ # 这里放所有的 html 网页
│   └── base.html # 基础页面模板
│   └── index.html # 主页
│   └── see.html # 上传视频/录制的页面
│   └── think.html # 生成女书结果的页面
└── static/ 
│   └── css/ # 这里放一些网站美化相关的文件
│   │   └── style.css
│   │   └── think.css # 一些尝试，可以删除
│   └── js/ # javascript
│   └── nvshu_images/ # 暂存的用户生成的新女书字图片
└── knowledge_base/   # 一些运行需要的数据
```


配置环境tips
1. 安装Anaconda
* 如果你已经安装了Anaconda，可以跳过这一步  
* 如果还没安装，请访问Anaconda官网下载安装包并按照指示完成安装


克隆GitHub仓库

* 打开命令提示符(cmd)或PowerShell
* 导航到你想保存代码的目录：`cd path_to_target_folder`  
* 使用git命令克隆仓库：`git clone git@github.com:hyanworkspace/ai_nvshu.git`  
* 进入仓库目录：`cd ai_nvshu`


创建虚拟环境
* 打开Anaconda Prompt(在开始菜单中搜索)  
* 创建新的虚拟环境：`conda create -n 环境名称 python=3.x`（可以试一下 3.10，原始测试版本为 3.11.11），假设想要设置环境名称为nvshu，且运行环境为 python 3.10，则运行`conda create -n nvshu python=3.10`  
* 激活环境：`conda activate nvshu`


安装依赖项
* 确保你位于包含requirements.txt的目录中
* 安装所有依赖项：`pip install -r requirements.txt`
* 如果某些包安装失败，可以尝试：`conda install 包名称`


运行程序
* 运行`python app.py`
* 打开浏览器，浏览网址：http://127.0.0.1:5000/
