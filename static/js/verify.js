// verify.js
document.addEventListener('DOMContentLoaded', function() {
    const verifyForm = document.querySelector('form');
    const successPopup = document.getElementById('successPopup');

    verifyForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        try {
            const response = await fetch('/register', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                successPopup.style.display = 'block';
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
});