// Minimum display time for each step (in milliseconds)
// const MIN_DISPLAY_TIME = 10000; // 10 seconds
const MIN_DISPLAY_TIME = 5000;
let lastStepTime = 0;

document.addEventListener('DOMContentLoaded', function() {
        // // Check if the user has agreed to privacy
        // if (sessionStorage.getItem('agreedToPrivacy') === 'true') {
        //     document.body.classList.add('agreed-style');
        // }
    
    
    const urlParams = new URLSearchParams(window.location.search);
    const videoUrl = urlParams.get('video_url');
    const origVideoUrl = urlParams.get('original_video_url');
    
    if (!videoUrl) {
        alert('No video URL provided');
        return;
    }

    // Initialize left panel with video
    const leftContent = document.getElementById('left-content');
    const videoElement = document.createElement('video');
    videoElement.src = videoUrl;
    videoElement.controls = true;
    videoElement.autoplay = true;
    videoElement.loop = true;
    leftContent.appendChild(videoElement);

    // Start the process
    describeVideo(origVideoUrl);
});

// // 打字机效果函数
// async function typeWriter(element, text) {
//     element.innerHTML = ''; // Clear existing content
//     // 确保 text 是字符串类型
//     text = String(text || '');
//     let currentIndex = 0;
//     return new Promise((resolve) => {
//         function type() {
//             if (currentIndex < text.length) {
//                 element.innerHTML += text.charAt(currentIndex);
//                 currentIndex++;
//                 setTimeout(type, 50); // 每个字符的显示间隔为 50ms
//             } else {
//                 resolve(); // 打字效果完成后 resolve
//             }
//         }
//         type();
//     });
// }
async function typeWriter(element, texts) {
    element.innerHTML = ''; // 清空现有内容
    
    // 确保 texts 是数组（如果是字符串，转为单元素数组）
    const lines = Array.isArray(texts) ? texts : [String(texts || '')];
    
    // 逐行处理
    for (const line of lines) {
        const lineElement = document.createElement('div'); // 每行用 div 包裹
        element.appendChild(lineElement);
        
        // 当前行的打字机效果
        await new Promise((resolve) => {
            let currentIndex = 0;
            function type() {
                if (currentIndex < line.length) {
                    lineElement.innerHTML += line.charAt(currentIndex);
                    currentIndex++;
                    setTimeout(type, 50); // 每个字符间隔 50ms
                } else {
                    resolve(); // 当前行完成
                }
            }
            type();
        });
    }
}

function addStatusItem(text, isActive = false, isCompleted = false, toggleContent = null) {
    const rightContent = document.getElementById('right-content');
    const statusItem = document.createElement('div');
    statusItem.className = `status-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : 'pending'}`;
    
    statusItem.innerHTML = `
        <div class="status-icon">${isCompleted ? '✓' : '•'}</div>
        <div class="status-text">${text}</div>
    `;
    
    // if (toggleContent) {
    //     const toggleId = 'toggle-' + Date.now();
    //     statusItem.innerHTML += `
    //         <button class="toggle-button" onclick="document.getElementById('${toggleId}').style.display = 
    //             document.getElementById('${toggleId}').style.display === 'none' ? 'none' : 'block'">
    //             Show details
    //         </button>
    //         <div id="${toggleId}" class="toggle-content">
    //             ${toggleContent}
    //         </div>
    //     `;
    // }
    if (toggleContent) {
        const toggleId = 'toggle-' + Date.now();
        statusItem.innerHTML += `
            <button class="toggle-button" onclick="toggleDetails('${toggleId}', this)">
                Show details
            </button>
            <div id="${toggleId}" class="toggle-content" style="display: none;">
                ${toggleContent}
            </div>
        `;
    }
    
    rightContent.appendChild(statusItem);
    return statusItem;
}

function toggleDetails(contentId, button) {
    const content = document.getElementById(contentId);
    if (content.style.display === 'none') {
        content.style.display = 'block';
        button.textContent = 'Hide details';
    } else {
        content.style.display = 'none';
        button.textContent = 'Show details';
    }
}

function updateStatusItem(item, text, isCompleted = true, toggleContent = null) {
    item.className = `status-item ${isCompleted ? 'completed' : 'active'}`;
    item.innerHTML = `
        <div class="status-icon">${isCompleted ? '✓' : '•'}</div>
        <div class="status-text">${text}</div>
    `;
    
    if (toggleContent) {
        const toggleId = 'toggle-' + Date.now();
        item.innerHTML += `
            <button class="toggle-button" onclick="toggleDetails('${toggleId}', this)">
                Show details
            </button>
            <div id="${toggleId}" class="toggle-content" style="display: none;">
                ${toggleContent}
            </div>
        `;
    }
}

async function describeVideo(videoUrl) {
    const analyzingItem = addStatusItem("The agent is seeing...", true);
    lastStepTime = Date.now();

    try {
        const response = await fetch('/describe_video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video_url: videoUrl })
        });
        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        // Update the status item with toggleable content
        const toggleContent = `
            <div class="language-section">
                <div class="language-label" style="color: #777">${data.video_desc}</div>
            </div>
            <div class="language-section">
                <div class="language-label" style="color: #777">${data.video_desc_eng}</div>
            </div>
        `;
        updateStatusItem(analyzingItem, "Video analysis completed", true, toggleContent);
        
        // Display both Chinese and English descriptions with typewriter effect
        const leftContent = document.getElementById('left-content');
        leftContent.innerHTML = `
            <div class="language-section w-[300px] h-[300px] rounded-full radial-fade-small flex-col flex items-center justify-center p-4 text-center relative">
                <div class="text-black text-xl break-words">
                    <div id="chinese-desc" class="description"></div>
                </div>
                <div class="text-black opacity-50 text-sm break-words pt-8">
                    <div id="english-desc" class="description"></div>
                </div>
            </div>
        `;

        // Apply typewriter effect to both descriptions sequentially
        const chineseDesc = document.getElementById('chinese-desc');
        const englishDesc = document.getElementById('english-desc');
        
        await typeWriter(chineseDesc, data.video_desc);
        await typeWriter(englishDesc, data.video_desc_eng);

        // Calculate remaining time to reach MIN_DISPLAY_TIME
        const elapsed = Date.now() - lastStepTime;
        const remainingTime = Math.max(0, MIN_DISPLAY_TIME - elapsed);
        
        // After minimum display time, move to next step
        setTimeout(() => {
            findSimilarPoems(data.video_description || data.video_desc);
        }, remainingTime);
    } catch (error) {
        updateStatusItem(analyzingItem, `Error: ${error.message}`);
        console.error('Error:', error);
    }
}

async function findSimilarPoems(description) {
    const thinkingItem = addStatusItem("The agent is thinking...", true);
    lastStepTime = Date.now();

    try {
        const response = await fetch('/find_similar_poems', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video_description: description })
        });
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update the status item with toggleable content
        // ${data.similar_poems.map(poem => `<div>${poem}</div>`).join('')}
        const toggleContent = `
            <div class="language-section">
                <div class="poem" style="color: #777">${data.similar_poems.join('<br>')}</div>
            </div>
            <div class="language-section">
                <div class="poem" style="color: #777">${data.similar_poems_eng.join('<br>')}</div>
            </div>
        `;
        updateStatusItem(thinkingItem, "Found similar poems", true, toggleContent);
        
        // Display both Chinese and English poems with typewriter effect
        const leftContent = document.getElementById('left-content');
        leftContent.innerHTML = `
            <div class="language-section w-[300px] h-[300px] rounded-full radial-fade-small flex-col flex items-center justify-center p-4 text-center relative">
                <div class="text-black text-xl break-words">
                    <div id="chinese-poems" class="poem"></div>
                </div>
                <div class="text-black opacity-50 text-sm break-words pt-8">
                    <div id="english-poems" class="poem"></div>
                </div>
            </div>
        `;

        // Apply typewriter effect to both poems sequentially
        const chinesePoems = document.getElementById('chinese-poems');
        const englishPoems = document.getElementById('english-poems');
        
        await typeWriter(chinesePoems, data.similar_poems);
        await typeWriter(englishPoems, data.similar_poems_eng);

        // Calculate remaining time to reach MIN_DISPLAY_TIME
        const elapsed = Date.now() - lastStepTime;
        const remainingTime = Math.max(0, MIN_DISPLAY_TIME - elapsed);
        
        // After minimum display time, move to next step
        setTimeout(() => {
            generatePoem(description, data.similar_poems);
        }, remainingTime);
    } catch (error) {
        updateStatusItem(thinkingItem, `Error: ${error.message}`);
        console.error('Error:', error);
    }
}

async function generatePoem(description, poems) {
    const reflectingItem = addStatusItem("The agent is reflecting...", true);
    lastStepTime = Date.now();

    try {
        const response = await fetch('/generate_poem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ video_description: description, similar_poems: poems})
        });
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        // Update the status item with toggleable content
        const toggleContent = `
            <div class="language-section">
                <div class="poem" style="color: #777">${data.poem}</div>
            </div>
            <div class="language-section">
                <div class="poem" style="color: #777">${data.poem_eng}</div>
            </div>
        `;
        updateStatusItem(reflectingItem, "Generated new poem", true, toggleContent);
        
        // Display both Chinese and English poems with typewriter effect
        const leftContent = document.getElementById('left-content');
        leftContent.innerHTML = `
            <div class="language-section w-[300px] h-[300px] rounded-full radial-fade-small flex items-center justify-center p-4 text-center relative">
                <div class="text-black text-4xl vertical-text break-words">
                    <div id="chinese-poem" class="poem"></div>
                </div>
                <div class="absolute text-black opacity-50 text-sm break-words">
                    <div id="english-poem" class="poem"></div>
                </div>
            </div>
        `;

        // Apply typewriter effect to both poems sequentially
        const chinesePoem = document.getElementById('chinese-poem');
        const englishPoem = document.getElementById('english-poem');
        
        await typeWriter(chinesePoem, data.poem);
        await typeWriter(englishPoem, data.poem_eng);

        // Calculate remaining time to reach MIN_DISPLAY_TIME
        const elapsed = Date.now() - lastStepTime;
        const remainingTime = Math.max(0, MIN_DISPLAY_TIME - elapsed);
        
        // After minimum display time, mark as completed
        setTimeout(() => {
            // replaceWithSimpleEl(data.poem)
            window.location.href = `/guess?poem=${data.poem}`;
        }, remainingTime);
    } catch (error) {
        updateStatusItem(reflectingItem, `Error: ${error.message}`);
        console.error('Error:', error);
    }
}
// async function replaceWithSimpleEl(poem) {
//     const reflectingItem = addStatusItem("The agent is creating...", true);
//     lastStepTime = Date.now();
//     try {
        
//         const response = await fetch('/replace_with_created_char', {
//             method: 'POST',
//             headers: {
//                 'Content-Type': 'application/json',
//             },
//             body: JSON.stringify({ poem: poem })
//         });
//         const data = await response.json();

//         if (data.error) {
//             throw new Error(data.error);
//         }
        
//         // Display both Chinese and English poems with typewriter effect
//         const leftContent = document.getElementById('left-content');
//         leftContent.innerHTML = `
//             <div class="language-section">
//                 <div class="language-label">Chinese Poem:</div>
//                 <div id="chinese-poem" class="poem"></div>
//             </div>
//             <div class="language-section">
//                 <div class="language-label">Poem with Nvshu:</div>
//                 <div id="poem-el" class="poem"></div>
//             </div>
//         `;

//         // Apply typewriter effect to both poems sequentially
//         const chinesePoem = document.getElementById('chinese-poem');
//         const elPoem = document.getElementById('poem-el');
        
//         await typeWriter(chinesePoem, data.poem_orig);
//         await typeWriter(elPoem, data.poem_in_simple_el);

//         // Calculate remaining time to reach MIN_DISPLAY_TIME
//         const elapsed = Date.now() - lastStepTime;
//         const remainingTime = Math.max(0, MIN_DISPLAY_TIME - elapsed);
        
//         // After minimum display time, mark as completed
//         setTimeout(() => {
//             // 跳转到 guess.html 页面
//             window.location.href = `/guess?poem=${data.poem_orig}`;
//         }, remainingTime);
//     } catch (error) {
//         updateStatusItem(reflectingItem, `Error: ${error.message}`);
//         console.error('Error:', error);
//     }
// }
