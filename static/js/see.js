// DOM元素
const recordOption = document.getElementById('recordOption');
const uploadOption = document.getElementById('uploadOption');
const fileInput = document.getElementById('fileInput');
const videoRecorder = document.getElementById('videoRecorder');
const videoPreview = document.getElementById('videoPreview');
const confirmationPage = document.getElementById('confirmationPage');
const reUploadBtn = document.getElementById('reUploadBtn');
const confirmBtn = document.getElementById('confirmBtn');
const privacyPolicy = document.getElementById('privacyPolicy');
const agreeBtn = document.getElementById('agreeBtn');
const previewContainer = document.getElementById('previewContainer');
const recordPreview = document.getElementById('recordPreview'); // （预览画布）上应用特效
const startRecordBtn = document.getElementById('startRecordBtn');
const stopRecordBtn = document.getElementById('stopRecordBtn');
const recordControls = document.querySelector('.record-controls');
const mainContent = document.querySelector('.main-content');

// 录制相关变量
let videoStream = null;
let mediaRecorder = null;
let originalMediaRecorder = null; // 新增：用于原始视频的录制器
let recordedChunks = [];
let originalRecordedChunks = []; // 新增：用于存储原始视频数据
let uploadedFile = null;
let currentMode = null;
let recordedVideo = null;
let originalRecordedVideo = null; // 新增：存储原始视频的Blob
let animationFrameId;
let video_url;
let original_video_url; // 新增：原始视频的URL

const constraints = {
    audio: true,
    video: {
        width: { ideal: 640 },  // 设置理想的宽度
        height: { ideal: 640 }, // 设置理想的高度，保持1:1的比例
        aspectRatio: 1.0       // 强制使用1:1的宽高比
    }
};

// 录制选项点击事件
recordOption.addEventListener('click', async () => {
    if (!videoStream) {
        try {
            // 请求摄像头权限
            videoStream = await navigator.mediaDevices.getUserMedia(constraints);
            if (videoStream) {
                recordPreview.srcObject = videoStream;
                recordPreview.classList.remove('hidden');
                recordControls.classList.remove('hidden');
                
                // 设置录制控制
                setupRecordingControls();
            }
        } catch (err) {
            console.error('无法访问摄像头:', err);
            alert('无法访问摄像头，请确保已授予摄像头权限，并且摄像头未被其他应用程序占用。');
        }
    }
});

// 设置录制控制
function setupRecordingControls() {
    currentMode = 'record';
    
    startRecordBtn.addEventListener('click', () => {
        // 开始录制
        recordedChunks = [];
        originalRecordedChunks = []; // 重置原始视频数据
        
        // 为带特效的视频创建canvas
        const recordingCanvas = document.createElement('canvas');
        recordingCanvas.width = 370;
        recordingCanvas.height = 370;
        const recordingCtx = recordingCanvas.getContext('2d');
        const recordedStream = recordingCanvas.captureStream(30); // 用于带特效的视频
        
        const options = { mimeType: 'video/webm' };
        
        try {
            // 设置带特效的视频录制器
            mediaRecorder = new MediaRecorder(recordedStream, options);
            
            // 设置原始视频录制器 - 直接使用原始videoStream
            originalMediaRecorder = new MediaRecorder(videoStream, options);
        } catch (e) {
            console.error('创建 MediaRecorder 失败:', e);
            alert('您的浏览器可能不支持视频录制功能，请尝试使用最新版本的 Chrome 或 Firefox。');
            return;
        }
            
        // 处理带特效的视频数据
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordedChunks.push(event.data);
            }
        };
        
        // 处理原始视频数据
        originalMediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                originalRecordedChunks.push(event.data);
            }
        };
        
        // 当带特效的视频停止录制时
        mediaRecorder.onstop = () => {
            const recordedBlob = new Blob(recordedChunks, { type: 'video/webm' });
            recordedVideo = recordedBlob;
            const url = URL.createObjectURL(recordedBlob);
            console.log('生成的特效视频 URL:', url);
            
            // 确保原始视频也已经停止录制
            if (originalMediaRecorder && originalMediaRecorder.state !== 'inactive') {
                originalMediaRecorder.stop();
            }
        };
        
        // 当原始视频停止录制时
        originalMediaRecorder.onstop = () => {
            const originalBlob = new Blob(originalRecordedChunks, { type: 'video/webm' });
            originalRecordedVideo = originalBlob;
            const originalUrl = URL.createObjectURL(originalBlob);
            console.log('生成的原始视频 URL:', originalUrl);
            
            // 在原始视频录制完成后显示确认页面
            showConfirmationPageFromRecord(recordedVideo, originalRecordedVideo);
        };
        
        // 启动两个录制器
        mediaRecorder.start();
        originalMediaRecorder.start();
        
        function processRecordingFrame() {
            if (!videoStream || mediaRecorder.state !== 'recording') return;

            // 1. 绘制原始视频到canvas
            recordingCtx.drawImage(recordPreview, 0, 0, recordingCanvas.width, recordingCanvas.height);
            
            // 2. 获取图像数据
            const imageData = recordingCtx.getImageData(0, 0, recordingCanvas.width, recordingCanvas.height);
            const data = imageData.data;
            
            // 3. 应用像素化效果
            const pixelSize = 5; // 调整像素块大小
            for (let y = 0; y < recordingCanvas.height; y += pixelSize) {
                for (let x = 0; x < recordingCanvas.width; x += pixelSize) {
                    // 计算当前块的平均颜色
                    let r = 0, g = 0, b = 0, count = 0;
                    
                    for (let dy = 0; dy < pixelSize && y + dy < recordingCanvas.height; dy++) {
                        for (let dx = 0; dx < pixelSize && x + dx < recordingCanvas.width; dx++) {
                            const idx = ((y + dy) * recordingCanvas.width + (x + dx)) * 4;
                            r += data[idx];
                            g += data[idx + 1];
                            b += data[idx + 2];
                            count++;
                        }
                    }
                    
                    r = Math.round(r / count);
                    g = Math.round(g / count);
                    b = Math.round(b / count);
                    
                    // 应用平均颜色到整个块
                    for (let dy = 0; dy < pixelSize && y + dy < recordingCanvas.height; dy++) {
                        for (let dx = 0; dx < pixelSize && x + dx < recordingCanvas.width; dx++) {
                            const idx = ((y + dy) * recordingCanvas.width + (x + dx)) * 4;
                            data[idx] = r;
                            data[idx + 1] = g;
                            data[idx + 2] = b;
                        }
                    }
                }
            }

            // 4.2. 应用阈值（Threshold）效果
            const threshold = 128; // 可以调整阈值（0-255之间）
            for (let i = 0; i < data.length; i += 4) {
                // 计算灰度值 (使用加权平均法)
                const gray = Math.round(0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]);
                // 根据阈值转换为纯黑或纯白
                const value = gray > threshold ? 255 : 0;
                // 设置相同的值到RGB通道
                data[i] = value;     // R
                data[i + 1] = value; // G
                data[i + 2] = value; // B
                // Alpha通道保持不变
            }
            
            // 5. 放回处理后的图像数据
            recordingCtx.putImageData(imageData, 0, 0);
            
            animationFrameId = requestAnimationFrame(processRecordingFrame);
        }
        
        processRecordingFrame();
        startRecordBtn.classList.add('hidden');
        stopRecordBtn.classList.remove('hidden');
    });
    
    stopRecordBtn.addEventListener('click', () => {
        // 停止两个录制器
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        
        if (originalMediaRecorder && originalMediaRecorder.state !== 'inactive') {
            originalMediaRecorder.stop();
        }
        
        stopRecordBtn.classList.add('hidden');
        startRecordBtn.classList.remove('hidden');
        
        if (videoStream) {
            videoStream.getTracks().forEach(track => track.stop());
            videoStream = null;
        }
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
        }
        recordPreview.classList.add('hidden');
        recordControls.classList.add('hidden');
    });
}


// 录制后显示确认页面 - 修改为接受两个参数
function showConfirmationPageFromRecord(blob, originalBlob) {
    recordedVideo = blob;
    originalRecordedVideo = originalBlob; // 保存原始视频
    const videoUrl = URL.createObjectURL(blob);
    videoPreview.src = videoUrl;
    hideMainContent();
    confirmationPage.classList.remove('hidden');
    confirmationPage.style.display = 'flex';
}

// 上传选项点击事件
uploadOption.addEventListener('click', () => {
    currentMode = 'upload';
    fileInput.click();
});

// 文件选择事件
fileInput.addEventListener('change', async (e) => {
    if (e.target.files.length > 0) {
        uploadedFile = e.target.files[0];
        
        if (uploadedFile.size > 5 * 1024 * 1024) {
            alert("File size exceeds 5MB limit. Please choose a smaller file.");
            return;
        }
        
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('session_id', document.cookie.match(/session_id=([^;]+)/)?.[1] || '');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                alert('上传成功');
                fileInput.value = '';
                video_url = result.file_url
                // alert(video_url) // 调试信息
                showConfirmationPageFromUpload(result.file_url);

            } else {
                alert('上传失败: ' + result.error);
            }
        } catch (err) {
            console.error('上传错误:', err);
            alert('上传失败: ' + err.message);
        }
    }
});

// 上传后显示确认页面
function showConfirmationPageFromUpload(url) {
    video_url = url;
    videoPreview.src = url;
    hideMainContent();
    confirmationPage.classList.remove('hidden');
    confirmationPage.style.display = 'flex';
}

// 按钮事件处理
confirmBtn.addEventListener('click', () => {
    showPrivacyPolicy();
});

function showPrivacyPolicy() {
    privacyPolicy.classList.remove('hidden');
    privacyPolicy.style.display = 'flex';
    // 添加动画效果
    privacyPolicy.style.opacity = '0';
    setTimeout(() => {
        privacyPolicy.style.opacity = '1';
        privacyPolicy.style.transition = 'opacity 0.3s ease-in-out';
    }, 10);
}

agreeBtn.addEventListener('click', () => {
    // 添加淡出动画
    privacyPolicy.style.opacity = '0';
    privacyPolicy.style.transition = 'opacity 0.3s ease-in-out';
    
    setTimeout(() => {
        privacyPolicy.classList.add('hidden');
        privacyPolicy.style.display = 'none';

        // Set flag in sessionStorage
        sessionStorage.setItem('agreedToPrivacy', 'true');
        
        if (currentMode === 'record') {
            // 上传两个视频
            uploadRecordedVideos(recordedVideo, originalRecordedVideo);
        } else if (currentMode === 'upload' && video_url) {
            confirm_video(video_url);
        } else {
            console.error('No video URL available');
            alert('Error: No video URL available');
        }
    }, 300);
});

// 修改上传函数以处理两个视频
async function uploadRecordedVideos(effectBlob, originalBlob) {
    if (!effectBlob || !originalBlob) {
        alert('没有可上传的视频');
        return;
    }

    // 先上传带特效的视频
    const effectFormData = new FormData();
    effectFormData.append('file', effectBlob, 'effect-video.webm');
    effectFormData.append('session_id', document.cookie.match(/session_id=([^;]+)/)?.[1] || '');

    try {
        // 上传带特效的视频
        const effectResponse = await fetch('/upload', {
            method: 'POST',
            body: effectFormData
        });

        const effectResult = await effectResponse.json();
        if (effectResponse.ok) {
            video_url = effectResult.file_url;
            
            // 然后上传原始视频
            const originalFormData = new FormData();
            originalFormData.append('file', originalBlob, 'original-video.webm');
            originalFormData.append('session_id', document.cookie.match(/session_id=([^;]+)/)?.[1] || '');
            
            const originalResponse = await fetch('/upload', {
                method: 'POST',
                body: originalFormData
            });
            
            const originalResult = await originalResponse.json();
            if (originalResponse.ok) {
                original_video_url = originalResult.file_url;
                alert('两个视频上传成功');
                
                // 将两个URL都传递给confirm_video函数
                confirm_video(video_url, original_video_url);
            } else {
                alert('原始视频上传失败: ' + originalResult.error);
            }
        } else {
            alert('带特效视频上传失败: ' + effectResult.error);
        }
    } catch (err) {
        console.error('上传错误:', err);
        alert('上传失败: ' + err.message);
    }
}

reUploadBtn.addEventListener('click', () => {
    // 停止所有视频流
    if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
    }
    
    // 隐藏确认页面
    confirmationPage.classList.add('hidden');
    confirmationPage.style.display = 'none';
    
    // 隐藏隐私政策
    privacyPolicy.classList.add('hidden');
    privacyPolicy.style.display = 'none';
    
    // 显示主内容
    const mainContainer = document.querySelector('.flex.flex-row.items-center.justify-center');
    if (mainContainer) {
        mainContainer.style.display = 'flex';
    }
    
    // 重置视频预览
    videoPreview.src = '';
    recordPreview.srcObject = null;
    recordPreview.classList.add('hidden');
    recordControls.classList.add('hidden');
    
    // 重置文件输入
    fileInput.value = '';
    
    // 重置所有状态
    recordedChunks = [];
    originalRecordedChunks = []; // 重置原始视频数据
    uploadedFile = null;
    currentMode = null;
    recordedVideo = null;
    originalRecordedVideo = null; // 重置原始视频
    video_url = null;
    original_video_url = null; // 重置原始视频URL
    
    // 取消任何运行中的动画
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }
});

// 拖放处理
document.addEventListener('DOMContentLoaded', () => {
    const uploadCircle = document.getElementById('uploadOption');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadCircle.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadCircle.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadCircle.addEventListener(eventName, unhighlight, false);
    });
    
    uploadCircle.addEventListener('drop', handleDrop, false);
});

// 辅助函数
function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function highlight() {
    uploadCircle.style.backgroundColor = '#f8f5e6';
    uploadCircle.style.transform = 'scale(1.05)';
}

function unhighlight() {
    uploadCircle.style.backgroundColor = '#F5F0DF';
    uploadCircle.style.transform = 'scale(1)';
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        currentMode = 'upload';
        uploadedFile = files[0];
        
        if (uploadedFile.size > 5 * 1024 * 1024) {
            alert("File size exceeds 5MB limit. Please choose a smaller file.");
            return;
        }
        
        if (!uploadedFile.type.match('video.*|image.*')) {
            alert("Please upload a video or image file (MP4, PNG, JPG).");
            return;
        }
    }
}

// 修改确认视频的函数 - 现在接受两个参数
function confirm_video(url_, original_url = null) {
    if (!url_) {
        console.error('No URL provided to confirm_video');
        alert('Error: No video URL available');
        return;
    }
    
    let redirectUrl = `/think?video_url=${encodeURIComponent(url_)}`;
    
    // 如果有原始视频URL，添加到重定向链接
    if (original_url) {
        redirectUrl += `&original_video_url=${encodeURIComponent(original_url)}`;
    }
    
    console.log('Redirecting to:', redirectUrl);
    window.location.href = redirectUrl;
}

// 隐藏主页面内容
function hideMainContent() {
    const mainContainer = document.querySelector('.flex.flex-row.items-center.justify-center');
    if (mainContainer) {
        mainContainer.style.display = 'none';
    }
}