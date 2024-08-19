// Render responses
const response_gpt_text = document.querySelector(".response-gpt-text");
const response_gemini_text = document.querySelector(".response-gemini-text");
const response_claude_text = document.querySelector(".response-claude-text");
// Get conversation_id from the URL or initialize it as null
let conversation_id = window.location.pathname.split('/').pop();

document.addEventListener("DOMContentLoaded", function() {
    // Get current user
    const token = localStorage.getItem('token');

    // get chat history
    function loadConversations() {
        fetch(`/api/conversation`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            const conversationList = document.getElementById("conversation-list");
            conversationList.textContent = '';

            data.data.slice().reverse().forEach(item => {
                const li = document.createElement('li');
                
                const conversation_id_item=item[0];
                const conversationLink = document.createElement('a');
                conversationLink.href = `/conversation/${conversation_id_item}`;
                conversationLink.textContent = item[1];
                conversationLink.className="con_link";

                if(conversation_id_item===conversation_id){
                    li.style.backgroundColor='#FFFEFA';
                    // li.style.fontWeight=900;
                }

                li.appendChild(conversationLink);
                conversationList.appendChild(li);
            });
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    loadConversations();

    async function render_response(response, responseContainer, responseClass) {
        const data = response.data;
        responseContainer.textContent = '';

        data.forEach(item => {
            const newrequest = document.createElement('div');
            newrequest.className = 'request-text';
            newrequest.textContent = item[0];

            const newresponse = document.createElement('div');
            newresponse.className = responseClass;
            // Convert Markdown to HTML
            newresponse.textContent = item[1];
            // hljs.highlightBlock(newresponse);

            responseContainer.appendChild(newrequest);
            responseContainer.appendChild(newresponse);
        });
    }

    function getresponse_openai(conversation_id) {
        fetch(`/api/openai/${conversation_id}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            render_response(data, response_gpt_text, 'response-text-openai');
            response_gpt_text.scrollTop = response_gpt_text.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    getresponse_openai(conversation_id);

    function getresponse_gemini(conversation_id) {
        fetch(`/api/gemini/${conversation_id}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            render_response(data, response_gemini_text, 'response-text-gemini');
            response_gemini_text.scrollTop = response_gemini_text.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    getresponse_gemini(conversation_id);

    function getresponse_claude(conversation_id) {
        fetch(`/api/claude/${conversation_id}`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => response.json())
        .then(data => {
            render_response(data, response_claude_text, 'response-text-claude');
            response_claude_text.scrollTop = response_claude_text.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    getresponse_claude(conversation_id);

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }


    // Fetch API calls
    const requestInput = document.getElementById("request");

    async function handleSubmit() {
        const requestText = requestInput.value.trim();

        if (requestText !== "") {
            const request_id=generateUUID();
            // console.log(request_id);

            let conversation_id_ini=conversation_id;
            // console.log("initial:"+conversation_id);
            if(conversation_id_ini===''){
                conversation_id=generateUUID();
            }
            // console.log("random conversation id:"+conversation_id);

            try {
                // Create conversation_id and new request
                await fetch(`/api/conversation/${conversation_id}`, {
                    method: 'POST',
                    headers: {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({
                        request_text: requestText,
                        request_id: request_id
                    })
                });
 
                // POST request to OpenAI, Gemini, Claude and then GET their responses

    
                if (conversation_id_ini === "") {
                    sendApiRequest('/api/openai', requestText, request_id, );
                    sendApiRequest('/api/gemini', requestText, request_id, );
                    sendApiRequest('/api/claude', requestText, request_id, );
                    window.location.href = `/conversation/${conversation_id}`;
                }else{
                    sendApiRequest('/api/openai', requestText, request_id, () => getresponse_openai(conversation_id));
                    sendApiRequest('/api/gemini', requestText, request_id, () => getresponse_gemini(conversation_id));
                    sendApiRequest('/api/claude', requestText, request_id, () => getresponse_claude(conversation_id));
                }
                
                // Clear the input after submission
                requestInput.value = "";
            } catch (error) {
                console.error('Error with add new conversation_id:', error);
            }
        }
    }

    async function sendApiRequest(apiUrl, requestText, requestId, callback) {
        try {
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token
                },
                body: JSON.stringify({
                    request_text: requestText,
                    request_id: requestId
                })
            });
    
            const data = await response.json();
            callback(data);
        } catch (error) {
            console.error(`Error with ${apiUrl} request:`, error);
        }
    }

    // Event listener for the "Enter" key
    // requestInput.addEventListener("keydown", function(event) {
    //     if (event.key === "Enter") {
    //         event.preventDefault(); // Prevents the default form submission
    //         handleSubmit();
    //     }
    // });

    // Event listener for the button click
    const requestSubmit = document.getElementById("request-submit");
    requestSubmit.addEventListener("click", function(event) {
        event.preventDefault(); // Prevents the default form submission
        handleSubmit();
    });

    // Event listener for the button click
    const newconSubmit = document.getElementById("new-conversation");
    newconSubmit.addEventListener("click", function(event) {
        event.preventDefault();
        window.location.href = '/';
    });

    // Event listener for the button click
    const logo = document.querySelector(".logo");
    logo.addEventListener("click", function(event) {
        event.preventDefault();
        window.location.href = '/';
    });
});
