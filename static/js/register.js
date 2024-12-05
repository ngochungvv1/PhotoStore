// register.js
async function checkAvailability(field, value) {
    try {
        const response = await fetch('/check-availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ [field]: value })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data.available;
    } catch (error) {
        console.error('Error:', error);
        return true;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    const email = document.getElementById('email');
    const username = document.getElementById('username');
    const password = document.getElementById('password');
    const confirmPassword = document.getElementById('confirm_password');
    const submitButton = form.querySelector('button[type="submit"]');
    let isSubmitting = false;

    // Validation states
    let validationState = {
        email: false,
        username: false,
        password: false,
        confirmPassword: false
    };

    function updateSubmitButton() {
        const isValid = Object.values(validationState).every(Boolean);
        submitButton.disabled = !isValid;
        
        if (isValid) {
            submitButton.classList.remove('disabled');
            submitButton.style.backgroundColor = '#2196F3';
            submitButton.style.cursor = 'pointer';
        } else {
            submitButton.classList.add('disabled');
            submitButton.style.backgroundColor = '#cccccc';
            submitButton.style.cursor = 'not-allowed';
        }
    }

    // Email validation
    email.addEventListener('blur', async function() {
        if (!email.value) {
            validationState.email = false;
            updateSubmitButton();
            return;
        }
        
        const emailError = document.getElementById('emailError');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const isFormatValid = emailRegex.test(email.value);
        const isAvailable = await checkAvailability('email', email.value);
        
        validationState.email = isFormatValid && isAvailable;
        
        if (!isFormatValid) {
            emailError.textContent = 'Email không hợp lệ';
            email.classList.add('invalid');
        } else if (!isAvailable) {
            emailError.textContent = 'Email này đã được sử dụng';
            email.classList.add('invalid');
        } else {
            emailError.textContent = '';
            email.classList.remove('invalid');
        }
        updateSubmitButton();
    });

    // Username validation
    username.addEventListener('blur', async function() {
        if (!username.value) {
            validationState.username = false;
            updateSubmitButton();
            return;
        }
        
        const usernameError = document.getElementById('usernameError');
        const isAvailable = await checkAvailability('username', username.value);
        
        validationState.username = isAvailable;
        
        if (!isAvailable) {
            usernameError.textContent = 'Tên đăng nhập này đã tồn tại';
            username.classList.add('invalid');
        } else {
            usernameError.textContent = '';
            username.classList.remove('invalid');
        }
        updateSubmitButton();
    });

    // Password validation
    password.addEventListener('input', function() {
        const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d]{8,}$/;
        const passwordError = document.getElementById('passwordError');
        
        validationState.password = passwordRegex.test(password.value);
        
        if (!validationState.password) {
            passwordError.textContent = 'Mật khẩu phải có ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường và số';
            password.classList.add('invalid');
        } else {
            passwordError.textContent = '';
            password.classList.remove('invalid');
        }
        
        // Check confirm password when password changes
        if (confirmPassword.value) {
            validationState.confirmPassword = password.value === confirmPassword.value;
            const confirmPasswordError = document.getElementById('confirmPasswordError');
            if (!validationState.confirmPassword) {
                confirmPasswordError.textContent = 'Mật khẩu không khớp';
                confirmPassword.classList.add('invalid');
            } else {
                confirmPasswordError.textContent = '';
                confirmPassword.classList.remove('invalid');
            }
        }
        
        updateSubmitButton();
    });

    // Confirm password validation
    confirmPassword.addEventListener('input', function() {
        const confirmPasswordError = document.getElementById('confirmPasswordError');
        validationState.confirmPassword = password.value === confirmPassword.value;
        
        if (!validationState.confirmPassword) {
            confirmPasswordError.textContent = 'Mật khẩu không khớp';
            confirmPassword.classList.add('invalid');
        } else {
            confirmPasswordError.textContent = '';
            confirmPassword.classList.remove('invalid');
        }
        
        updateSubmitButton();
    });

    // Form submission with anti-spam
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        if (isSubmitting) {
            return;
        }
    
        isSubmitting = true;
        submitButton.disabled = true;
        submitButton.textContent = 'Đang xử lý...';
    
        try {
            const formData = new FormData(this);
            const response = await fetch('/register', {
                method: 'POST',
                body: formData
            });
    
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                // If response is HTML (verify page), handle it differently
                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
            } else {
                // Handle other responses
                if (response.ok) {
                    window.location.href = '/verify';
                } else {
                    throw new Error('Registration failed');
                }
            }
        } catch (error) {
            console.error('Error:', error);
        } finally {
            isSubmitting = false;
            submitButton.disabled = false;
            submitButton.textContent = 'Đăng ký';
        }
    });

    // Initial button state
    updateSubmitButton();
});