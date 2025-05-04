// Get the poem from URL parameters
const urlParams = new URLSearchParams(window.location.search);
const poem = urlParams.get('poem');

// Global variables
let charData = null;
let replaceData = null;
let guessInterval = null;

// 新增函数：处理自定义格式的字符串
function parseCustomFormat(str) {
    // 这里需要根据你的实际字符串格式来编写解析逻辑
    // 示例：假设格式是 "江永[14,0,16]书奇"
    const result = [];
    let currentPart = '';
    let inArray = false;
    let arrayContent = '';
    
    for (const char of str) {
        if (char === '[') {
            if (currentPart) {
                result.push(currentPart);
                currentPart = '';
            }
            inArray = true;
            arrayContent = '';
        } else if (char === ']') {
            inArray = false;
            try {
                const arrayData = JSON.parse(`[${arrayContent}]`);
                result.push(arrayData);
            } catch (e) {
                console.error('解析数组内容失败:', arrayContent);
            }
        } else if (inArray) {
            arrayContent += char;
        } else {
            currentPart += char;
        }
    }
    
    if (currentPart) {
        result.push(currentPart);
    }
    
    return result;
}

// 修改后的renderMixedContent函数
function renderMixedContent(data) {
    // 如果数据是字符串，先尝试解析
    if (typeof data === 'string') {
        try {
            data = JSON.parse(data);
        } catch (e) {
            data = parseCustomFormat(data);
        }
    }
    
    // 确保是数组
    if (!Array.isArray(data)) {
        console.error('最终数据不是数组:', data);
        return '';
    }
    
    return data.map(item => {
        try {
            if (Array.isArray(item)) {
                const imgName = `combined_${item.join('-')}_vertical.png`;
                return `<img src="/static/nvshu_images/${imgName}" alt="" class="inline-block h-[1em] align-middle">`;
            }
            // 处理字符串可能包含多个字符的情况
            if (typeof item === 'string' && item.length > 1) {
                return item.split('').join('');
            }
            return item;
        } catch (e) {
            console.error('处理项目失败:', item);
            return '';
        }
    }).join('');
}

// Initialize the page
document.addEventListener('DOMContentLoaded', async () => {
    if (!poem) {
        alert('No poem provided');
        return;
    }
    
    // Display the original poem
    document.getElementById('original-text').textContent = poem;
    
    try {
        // Get the simple_el version of the poem
        const replaceResponse = await fetch('/replace_with_created_char', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ poem: poem })
        });
        
        replaceData = await replaceResponse.json();
        
        if (replaceData.poem_in_simple_el) {
            // 调试输出
            console.log('原始 poem_in_simple_el:', replaceData.poem_in_simple_el);
            console.log('类型:', typeof replaceData.poem_in_simple_el);
            // 解析字符串为数组
            let parsedData;
            try {
                // 尝试解析JSON字符串（如果格式是 "['江', '永', [14,0,16], ...]"）
                parsedData = JSON.parse(replaceData.poem_in_simple_el);
                
                // 如果是字符串但不符合JSON格式（如 "江永[14,0,16]书奇"），按字符处理
                if (typeof parsedData === 'string') {
                    parsedData = parseCustomFormat(replaceData.poem_in_simple_el);
                }
            } catch (e) {
                // 如果JSON解析失败，尝试自定义解析
                parsedData = parseCustomFormat(replaceData.poem_in_simple_el);
            }
            
            console.log('解析后数据:', parsedData);
            document.getElementById('revealing-text').innerHTML = renderMixedContent(parsedData);

            
            // Get character data
            const charResponse = await fetch('/generate_char', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ poem: poem })
            });
            
            charData = await charResponse.json();
            
            if (charData.char_pos && charData.guess_char.length > 0) {
                // Start the automatic revelation process
                startAutomaticRevelation();
            }
        }
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('loading').textContent = 'Failed to process the poem';
    }
});

// // Start the automatic character revelation
// function startAutomaticRevelation() {
//     const pos = charData.char_pos;
//     console.info('pos:', pos);

//     // 1. Highlight the character in the original poem
//     highlightCharacter(pos);
    
//     const guessChars = charData.guess_char;
//     console.info('guessChars:', guessChars);

//     const poem_simple_el_in_list = replaceData.poem_in_list;

//     const simpleEl = charData.simple_el;
//     console.info('simpleEl:', simpleEl);
    
//     // 2. Animate the guessing process for this character
//     let currentGuessIndex = 0;
//     const revealingText = document.getElementById('revealing-text');
    
//     // Start the guessing animation
//     guessInterval = setInterval(() => {
//         // Create a copy of the original characters
//         const displayChars = [...poem_simple_el_in_list];
        
//         // Replace the current position with the current guess character
//         displayChars[pos] = guessChars[currentGuessIndex % guessChars.length];
        
//         // Update the display
//         revealingText.innerHTML = displayChars.join('');
        
//         // Move to next guess character
//         currentGuessIndex++;
        
//         // If we've gone through all guess characters, show the simple_el and stop
//         if (currentGuessIndex >= guessChars.length) {
//             clearInterval(guessInterval);
//             displayChars[pos] = simpleEl;
//             revealingText.innerHTML = displayChars.join('');
//             // Display the character image
//             displayCharacterImage();
//             // Hide the loading text only after character image is displayed
//             document.getElementById('loading').style.display = 'none';
//         }
//     }, 2000); // Change every 2 seconds
// }
function startAutomaticRevelation() {
    const pos = charData.char_pos;
    console.info('pos:', pos);

    highlightCharacter(pos);
    
    const guessChars = charData.guess_char;
    console.info('guessChars:', guessChars);

    const originalContent = [...replaceData.poem_in_simple_el]; // 确保这是数组
    
    let currentGuessIndex = 0;
    const revealingText = document.getElementById('revealing-text');
    
    guessInterval = setInterval(() => {
        // 创建副本时保留图片元素
        const displayChars = [...originalContent];
        
        // 只替换当前猜测位置的文本内容
        console.log('displayChars[pos]:', displayChars[pos]);
        console.log('类型:', typeof displayChars);
        if (typeof displayChars[pos] === 'string') {
            displayChars[pos] = guessChars[currentGuessIndex % guessChars.length];
        }
        
        revealingText.innerHTML = renderMixedContent(displayChars);
        
        currentGuessIndex++;
        
        if (currentGuessIndex >= guessChars.length) {
            clearInterval(guessInterval);
            if (typeof displayChars[pos] === 'string') {
                displayChars[pos] = charData.simple_el;
            }
            revealingText.innerHTML = renderMixedContent(displayChars);
            displayCharacterImage();
            document.getElementById('loading').style.display = 'none';
        }
    }, 2000);
}

// Highlight the character in the original poem
function highlightCharacter(pos) {
    const originalText = document.getElementById('original-text');
    const text = originalText.textContent;
    
    originalText.innerHTML = text.split('').map((char, index) => {
        return index === pos ? 
            `<span class="highlight">${char}</span>` : 
            char;
    }).join('');
}

// Display the character image
function displayCharacterImage() {
    const container = document.getElementById('char-image-container');
    container.innerHTML = '';
    
    if (charData.char_img_path) {
        // Hide the encoding and guessing text
        document.getElementById('encoding-text').style.display = 'none';
        document.getElementById('guessing-text').style.display = 'none';
        
        // Show the consensus title and change circle style
        document.getElementById('consensus-title').classList.remove('hidden');
        
        // Change the listener circle from animated to static style
        const listenerCircle = document.querySelector('.radial-fade-listener');
        if (listenerCircle) {
            listenerCircle.classList.remove('radial-fade-listener');
            listenerCircle.classList.add('radial-fade-small');
        }

        const img = document.createElement('img');
        img.src = charData.char_img_path;
        img.alt = 'Generated Nüshu character';
        img.className = 'char-image';
        container.appendChild(img);

        // 添加生成结果按钮
        const button = document.createElement('button');
        button.id = 'generate-result-btn';
        button.className = 'w-full max-w-[20vw] px-10 py-2 rounded-[30px] border-[2px] border-dashed border-[rgb(255,251,233)] bg-[rgba(255,251,233,0.4)] text-[rgb(255,251,233)] font-inknut mt-auto';
        button.style.padding = '0.1rem 1rem';
        button.textContent = 'Generate Result';
        button.addEventListener('click', () => {
            // 跳转到结果页面
            window.location.href = '/get_result';
        });
        
        // 将按钮添加到专门的按钮容器中
        const buttonContainer = document.getElementById('button-container');
        buttonContainer.appendChild(button);

    } else {
        console.error('No character image path available');
    }
}

function showConsensusReached() {
    const revealingText = document.getElementById('revealing-text');
    const circleContainer = revealingText.closest('.radial-fade-listener');
    
    // Change the animation class to static class
    if (circleContainer) {
        circleContainer.classList.remove('radial-fade-listener');
        circleContainer.classList.add('radial-fade-small');
    }
    
    revealingText.textContent = "Consensus Reached!";
    revealingText.style.display = 'block';
    
    // Add the button after a short delay
    setTimeout(() => {
        addGenerateResultButton();
    }, 1000);
}