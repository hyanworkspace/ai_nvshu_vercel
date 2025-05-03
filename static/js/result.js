document.getElementById('save-btn').addEventListener('click', async () => {
    const userName = document.getElementById('user-name').value.trim();

    if (!userName) {
        alert('Please enter your name');
        return;
    }

    try {
        // 保存用户名到session
        const response = await fetch('/save_user_name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user_name: userName })
        });

        if (response.ok) {
            // 跳转到frame_11页面
            window.location.href = '/frame_11';
        } else {
            alert('Failed to save your name');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred');
    }
});
