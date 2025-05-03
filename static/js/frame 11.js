// 保存图片功能 
document.getElementById('save-image-btn').addEventListener('click', function () { 
    html2canvas(document.querySelector(".container")).then(canvas => { 
        const link = document.createElement('a'); 
        link.download = 'nushu-character.png'; 
        link.href = canvas.toDataURL('image/png'); 
        link.click(); 
    }); 
}); 

// 跳转到字典页面 
document.getElementById('go-to-dictionary-btn').addEventListener('click', function () { 
    const button = this; // Reference the button itself
    const dictionaryUrl = button.dataset.dictionaryUrl; // Get URL from data attribute
    if (dictionaryUrl) {
        window.location.href = dictionaryUrl; 
    } else {
        console.error('Dictionary URL not found on the button.');
    }
}); 

// 分享功能 
function shareToWeChat() { 
    alert('WeChat sharing would be implemented here'); 
    // 实际实现需要使用微信JS-SDK 
} 

function shareToInstagram() { 
    // 创建一个临时图片用于分享 
    html2canvas(document.querySelector(".container")).then(canvas => { 
        const image = canvas.toDataURL('image/png'); 
        // Instagram不支持直接分享，这里只是模拟 
        window.open(`https://www.instagram.com/create/story?backgroundImage=${encodeURIComponent(image)}`, '_blank'); 
    }); 
} 

function copyShareLink() { 
    const shareLink = window.location.href; 
    navigator.clipboard.writeText(shareLink).then(() => { 
        alert('Link copied to clipboard!'); 
    }).catch(err => { 
        console.error('Failed to copy: ', err); 
    }); 
} 

// 保存用户选择到session 
document.querySelectorAll('input[name="storage"]').forEach(radio => { 
    radio.addEventListener('change', async function () { 
        try { 
            // 保存用户选择
            const response = await fetch('/save_storage_preference', { 
                method: 'POST', 
                headers: { 
                    'Content-Type': 'application/json', 
                }, 
                body: JSON.stringify({ storage_preference: this.value }) 
            });

            // 如果用户选择 Yes，调用 add_to_dictionary
            if (this.value === 'yes') {
                await fetch('/add_to_dictionary', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
            }
        } catch (error) { 
            console.error('Error:', error); 
        } 
    }); 
}); 
