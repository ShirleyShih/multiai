function open_signinup(){
    document.querySelector('.form-signinup').style.display = 'flex';
}

function close_signinup(){
    document.querySelector('.form-signinup').style.display = 'none';
}

document.addEventListener('DOMContentLoaded', async () => {
    await checkSignInStatus();
    document.querySelector('#signinup-form').addEventListener('submit', handleFormSubmit);
    document.querySelector('.redirect-signinup').addEventListener('click', redirectSigninup);
});

async function checkSignInStatus() {
    const token = localStorage.getItem('token');
    if (!token) {
        setSignInButton("會員註冊/登入<br>看聊天紀錄", open_signinup);
        return;
    }

    try {
        const response = await fetch('/api/user/auth', {
            headers: {
                'Authorization': 'Bearer ' + token // Add the Authorization header
            }
        });

        if (response.ok) {
            const data = await response.json();
            console.log("User is signed in");
            setSignInButton("Hi, "+data.data.name+"<br>我要登出", async () => {
                localStorage.removeItem('token');
                // location.reload();
                window.location.href = '/';
            });
        } else {
            throw new Error('Unauthorized');
        }
    } catch (error) {
        console.error("Error checking sign-in status:", error);
        setSignInButton("會員註冊/登入<br>看聊天紀錄", open_signinup);
    }
}

function setSignInButton(text, onClick) {
    const button_member = document.querySelector('.button_member');
    button_member.innerHTML = text;
    button_member.onclick = onClick;
}



async function handleFormSubmit(event) {
    event.preventDefault(); // Prevent default form submission

    const emailInput = document.querySelector('#email');
    const passwordInput = document.querySelector('#password');
    const signinup_message = document.querySelector('.signinup-message');

    if (document.querySelector('.signinup-title').textContent === "註冊會員帳號") {
        // Registration form submission
        const nameInput = document.querySelector('#name');
        if (!nameInput.value || !emailInput.value || !passwordInput.value) {
            signinup_message.textContent = "請填寫所有必填欄位";
            return; // Exit function early if any field is empty
        }

        try {
            const response = await fetch('/api/user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: nameInput.value,
                    email: emailInput.value,
                    password: passwordInput.value
                })
            });

            const data = await response.json();
            signinup_message.textContent = data.message;
        } catch (error) {
            signinup_message.textContent = "內部伺服器錯誤";
        }
    } else {
        // Login form submission logic
        try {
            const response = await fetch('/api/user/auth', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: emailInput.value,
                    password: passwordInput.value
                })
            });
            
            const data = await response.json();
            console.log(data.token);
            if (data.token) {
                localStorage.setItem('token', data.token);
                // location.reload();
                window.location.href = '/';
            } else {
                signinup_message.textContent = data.message;
            }
        } catch (error) {
            signinup_message.textContent = "內部伺服器錯誤";
        }
    }
}

function redirectSigninup(event) {
    event.preventDefault(); // Prevent default form submission

    const redirect = document.querySelector('.redirect-signinup');
    const signinup_title = document.querySelector('.signinup-title');
    const signinup_button = document.querySelector('button');
    const nameInput = document.querySelector('#name');

    if (redirect.textContent === "還沒有帳戶？點此註冊") {
        redirect.textContent = "已經有帳戶了？點此登入";
        signinup_title.textContent = "註冊會員帳號";
        signinup_button.textContent = "註冊新帳戶";
        nameInput.style.display = 'block';
        nameInput.setAttribute('required', '');
    } else {
        redirect.textContent = "還沒有帳戶？點此註冊";
        signinup_title.textContent = "登入會員帳號";
        signinup_button.textContent = "登入帳戶";
        nameInput.style.display = 'none';
        nameInput.removeAttribute('required');
    }
}