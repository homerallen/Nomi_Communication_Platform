document.addEventListener('DOMContentLoaded', async function () {
    const chatbox = document.getElementById('chatbox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const modeSelect = document.getElementById('modeSelect');
    const gemini_check_box = document.getElementById('gemini_check_box');
    const recordButton = document.getElementById('recordButton');
    const nomiSelect = document.getElementById('nomiSelect');

    let micOn = false;

    function displayMessage(message, sender, showButtons = false, existingMessageDiv = null) {
        let messageDiv;
        if (existingMessageDiv) {
            messageDiv = existingMessageDiv;
            messageDiv.querySelector('.message-content').innerHTML = message.replace(/\n/g, '<br>');
        } else {
            messageDiv = document.createElement('div');
            messageDiv.classList.add('message', sender);
            const messageContentDiv = document.createElement('div');
            messageContentDiv.classList.add('message-content');
            messageContentDiv.innerHTML = message.replace(/\n/g, '<br>');
            messageDiv.appendChild(messageContentDiv);

            if (showButtons) {
                const buttonContainer = document.createElement('div');
                buttonContainer.classList.add('approval-buttons');

                const approveButton = document.createElement('button');
                approveButton.textContent = "👍";
                approveButton.addEventListener('click', () => {
                    sendApprovedMessage(messageDiv, message);
                    discardReview(messageDiv);
                });

                const discardButton = document.createElement('button');
                discardButton.textContent = "👎";
                discardButton.addEventListener('click', () => discardReview(messageDiv));

                buttonContainer.appendChild(approveButton);
                buttonContainer.appendChild(discardButton);
                messageDiv.appendChild(buttonContainer);
            }
            chatbox.appendChild(messageDiv);
        }
        chatbox.scrollTop = chatbox.scrollHeight;
        return messageDiv;
    }

    async function getErrorMessage(response) {
        let errorMessage = `HTTP error ${response.status}: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorMessage += `: ${errorData.error || "Server Error"}`;
        } catch (jsonError) {
            errorMessage += ": Could not parse server error message.";
        }
        return errorMessage;
    }

    async function gemini_request(message = userInput.value.trim(), mode = modeSelect.value.trim()) {
        if (!message) return null;

        displayMessage(`Homer: ${message}`, 'user');
        userInput.value = '';
        userInput.focus();

        const sendingMessageDiv = displayMessage("Processing...", 'sending');

        try {
            const formData = new FormData();
            formData.append('message', message);
            formData.append('mode', mode);

            const response = await fetch('/gemini_request', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = await getErrorMessage(response);
                displayMessage(`Error: ${errorMessage}`, 'gemini', false, sendingMessageDiv);
                return null;
            }

            const data = await response.json();

            if (data?.gemini) {
                sendingMessageDiv.remove();
                return displayMessage(`${data.gemini}`, 'gemini-review', true);
            } else {
                let errorMessage = data?.error || "No Gemini response received from the server.";
                displayMessage(`Error: ${errorMessage}`, 'gemini', false, sendingMessageDiv);
                return null;
            }

        } catch (error) {
            console.error("Fetch error:", error);
            displayMessage(`Error: Network error or server unavailable.`, 'gemini', false, sendingMessageDiv);
            return null;
        }
    }

    async function nomi_request(message = userInput.value.trim(), agiready = false, nomi) {
        if (!message) return null;

        displayMessage(`Homer: ${message}`, 'user');
        userInput.value = '';
        userInput.focus();

        const sendingMessageDiv = displayMessage("Processing...", 'sending');

        try {
            const formData = new FormData();
            formData.append('message', message);
            formData.append('agiready', agiready);
            formData.append('nomi', nomi)

            const response = await fetch('/nomi_request', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = await getErrorMessage(response);
                displayMessage(`Error: ${errorMessage}`, 'nomi', false, sendingMessageDiv);
                return null;
            }

            const data = await response.json();

            if (data?.nomi && data["nomi"]["replyMessage"] && data["nomi"]["replyMessage"]["text"]) {
                sendingMessageDiv.remove();
                return displayMessage(`${nomiSelect.value}: ${data["nomi"]["replyMessage"]["text"]}`, 'nomi');
            } else {
                let errorMessage = data?.error || "No NOMI response received from the server or incorrect format.";
                displayMessage(`Error: ${errorMessage}`, 'nomi', false, sendingMessageDiv);
                return null;
            }

        } catch (error) {
            console.error("Fetch error:", error);
            displayMessage(`Error: Network error or server unavailable.`, 'nomi', false, sendingMessageDiv);
            return null;
        }
    }

    async function sendApprovedMessage(messageDiv, geminiText) {
        const sendingMessageDiv = displayMessage("Sending...", 'sending');

        try {
            const formData = new FormData();
            formData.append('message', geminiText);

            const response = await fetch('/process_nomi', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = await getErrorMessage(response);
                displayMessage(`Nomi Error: ${errorMessage}`, 'nomi', false, sendingMessageDiv);
                throw new Error(errorMessage);
            }

            const nomiData = await response.json();

            if (nomiData) {
                if (nomiData.error) {
                    displayMessage(`Nomi Error: ${nomiData.error}`, 'nomi', false, sendingMessageDiv);
                } else if (nomiData?.replyMessage?.text) {
                    sendingMessageDiv.remove();
                    displayMessage(`${nomiSelect.value}: ${nomiData.replyMessage.text}`, 'nomi');
                } else {
                    displayMessage("Nomi response format incorrect or missing content.", 'nomi', false, sendingMessageDiv);
                    console.error("Nomi Data:", nomiData);
                }
            } else {
                displayMessage("No Nomi data received.", 'nomi', false, sendingMessageDiv);
            }
        } catch (error) {
            console.error("Fetch error:", error);
            displayMessage(`Nomi Error: Network error or server unavailable.`, 'nomi', false, sendingMessageDiv);
        }
    }

    function discardReview(messageDiv) {
        messageDiv.remove();
    }

    async function process_mic() {
        micOn = !micOn;

        if (micOn) {
            fetch('/start_mic', {
                method: 'GET', // Use POST to send data, GET if not sending data
            })
                .then(response => response.json()) // Parse JSON response
                .then(data => {
                    console.log('Success:', data);
                    //responseDiv.textContent = data.message; // Display the message
                })
                .catch((error) => {
                    console.error('Error:', error);
                    //responseDiv.textContent = "Error calling Flask method.";
                });
        } else {
            fetch('/stop_mic', {
                method: 'GET', // Use POST to send data, GET if not sending data
            })
                .then(response => response.json()) // Parse JSON response
                .then(data => {
                    console.log('Success:', data);
                    userInput.value += data['voice_text']['text']
                })
                .catch((error) => {
                    console.error('Error:', error);

                });
        }
    }

    async function process_message() {
        let geminiMessageDiv = null;
        let nomiMessageDiv = null;

        try {
            if (gemini_check_box.checked) {
                geminiMessageDiv = await gemini_request();
                if (!geminiMessageDiv) {
                    console.error("Gemini request failed, stopping process");
                    return;
                }
            }

            const messageForNomi = gemini_check_box.checked ? geminiMessageDiv.querySelector('.message-content').textContent : undefined;
            nomiMessageDiv = await nomi_request(messageForNomi, gemini_check_box.checked, nomiSelect.value);

            if (!nomiMessageDiv) {
                console.error("Nomi request failed");
                return;
            }

            console.log("Both requests (if applicable) completed successfully.");
        } catch (error) {
            console.error("An error occurred:", error);
        }
    }

    sendButton.addEventListener('click', process_message);
    recordButton.addEventListener('click', process_mic);
});

