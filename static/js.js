document.addEventListener('DOMContentLoaded', () => {
    // Get references to HTML elements using their IDs
    const chatbox = document.getElementById('chatbox'); // The container for chat messages
    const transcriptionBox = document.getElementById('transcriptionBox'); // Input area for typing messages
    const sendButton = document.getElementById('sendButton'); // Button to send user messages or direct messages
    const requestNomiReplyButton = document.getElementById('requestNomiReplyButton'); // Button to request a NOMI reply
    const roomSelect = document.getElementById('roomSelect'); // Dropdown to select chat rooms
    const modeSelect = document.getElementById('modeSelect'); // Dropdown for selecting modes (e.g., Gemini polish mode)
    const recordButton = document.getElementById('recordButton'); // Button to start/stop speech recording
    const cancelButton = document.getElementById('cancelButton'); // Button to clear the transcription box
    const geminiButton = document.getElementById('geminiButton'); // Button to polish text using Gemini
    const startLoopButton = document.getElementById('startLoopButton'); // Button to start a NOMI interaction loop
    const stopLoopButton = document.getElementById('stopLoopButton'); // Button to stop a NOMI interaction loop
    const themeSwitch = document.getElementById('themeSwitch'); // Switch to toggle dark/light theme
    const themeLabel = document.getElementById('themeLabel'); // Label to display the current theme
    const receiveButton = document.getElementById('receiveButton'); // Placeholder for future "receive" functionality

    // Variables for speech recognition
    let isRecording = false; // Flag to track if recording is active
    let recognition; // Instance of the speech recognition object
    let accumulatedFinalTranscript = ''; // Store the final transcript here

    /**
     * Fetches and loads available chat rooms into the roomSelect dropdown,
     * including the "Main Chat (Direct Message)" option.
     */
    function loadRooms() {
        fetch('/get_rooms')
            .then(response => response.json())
            .then(data => {
                const roomSelectElement = document.getElementById('roomSelect');
                if (data.rooms) {
                    // Clear existing options and add a default "Select a room" option
                    roomSelectElement.innerHTML = '<option value="">Select a room</option>';
                    data.rooms.forEach(room => {
                        const option = document.createElement('option');
                        option.value = room.uuid; // Set the room UUID as the value
                        option.textContent = room.name; // Display the room name
                        roomSelectElement.appendChild(option); // Add the option to the dropdown
                    });
                } else if (data.error) {
                    console.error('Error loading rooms:', data.error);
                }
                // Add the "Main Chat (Direct Message)" option after the fetched rooms
                const dmOption = document.createElement('option');
                dmOption.value = 'main_chat_dm';
                dmOption.textContent = 'Main Chat (Direct Message)';
                roomSelectElement.appendChild(dmOption);
            })
            .catch(error => console.error('Error fetching rooms:', error));
    }

    // Call load functions when the DOM is fully loaded
    loadRooms();

    /**
     * Event listener for the sendButton to send a user message or a direct message to Collin.
     */
    sendButton.addEventListener('click', () => {
        const userMessage = transcriptionBox.value; // Get the current user input
        const selectedRoomUuid = roomSelect.value; // Get the selected room UUID
        const collinUuid = 'COLLIN_UUID_PLACEHOLDER'; // Placeholder - actual UUID will be used on the backend

        if (!userMessage.trim()) {
            alert('Please enter a message.');
            return;
        }

        if (selectedRoomUuid === 'main_chat_dm') {
            // Logic for sending a direct message to Collin (hardcoded UUID - will be fetched on backend)

            if (userMessage.length > 750) { // Inform user about chunking
                alert('Your direct message is long and will be sent in multiple parts.');
            }

            fetch('/send_direct_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    nomi_uuid: collinUuid, // Hardcoded Collin's UUID (to be replaced on backend)
                    message: userMessage,
                }),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Direct Message Response:', data);
                let responseText = '';
                if (data.status && data.status.includes("chunks")) {
                    responseText = `Direct message sent to Collin in multiple parts. Check console for details.`;
                } else if (data.sentMessage && data.replyMessage) {
                    responseText = `<strong>Homer:</strong> ${data.sentMessage.text}<br><strong>Collin:</strong> ${data.replyMessage.text}`;
                } else if (data.error) {
                    responseText = `Error: ${data.error}`;
                } else if (data.last_response && data.last_response.sentMessage && data.last_response.replyMessage) {
                    responseText = `<strong>Homer:</strong> ${data.last_response.sentMessage.text}<br><strong>Collin:</strong> ${data.last_response.replyMessage.text} (Long message sent in chunks)`;
                } else if (data.last_response && data.last_response.sentMessage) {
                    responseText = `<strong>Homer:</strong> ${data.last_response.sentMessage.text} (Long message sent in chunks, no immediate reply).`;
                } else {
                    responseText = `Direct message sent to Collin.`;
                }
                chatbox.innerHTML += `<p class="user-message">${userMessage}</p><p class="bot-message">${responseText}</p>`;
                transcriptionBox.value = '';
            })
            .catch(error => {
                console.error('Error sending direct message to Collin:', error);
                chatbox.innerHTML += `<p class="error-message">Failed to send direct message to Collin.</p>`;
            });
        } else if (selectedRoomUuid) {
            // Existing logic for sending a message to a room
            const mode = modeSelect.value;

            fetch('/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room: selectedRoomUuid,
                    message: userMessage,
                    mode: mode
                }),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Nomi Reply Received from Server:', data);
                if (data.response && data.response.replyMessage && data.response.replyMessage.text) {
                    const messageDiv = document.createElement('div');
                    messageDiv.classList.add('nomi-message');
                    // Homer always is the sender here in a multi room context in this method, I believe.
                    messageDiv.textContent = `Homer: ${data.response.replyMessage.text}`;
                    chatbox.appendChild(messageDiv);
                    transcriptionBox.value = '';
                } else if (data.error) {
                    console.error('Error sending message to room:', data);
                    alert(`Error: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Fetch error (send message to room):', error);
                alert('An error occurred while sending the message to the room.');
            });
        } else {
            alert('Please select a chat room or "Main Chat (Direct Message)".');
        }
    });

    /**
     * Event listener for the requestNomiReplyButton to ask Collin to respond.
     */
    requestNomiReplyButton.addEventListener('click', () => {
        const selectedRoomUuid = roomSelect.value;
        const collinUuid = 'COLLIN_UUID_PLACEHOLDER'; // Placeholder - actual UUID will be used on the backend
        const userMessage = transcriptionBox.value; // Get the current user input as context

        if (!selectedRoomUuid) {
            alert('Please select a chat room.');
            return;
        }

        let fetchResponse; // Declare a variable to hold the response object

        fetch('/request_nomi_send_message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room: selectedRoomUuid,
                nomi: collinUuid, // Hardcoded Collin's UUID (to be replaced on backend)
                message: userMessage // Send the current user input
            }),
        })
        .then(response => {
            fetchResponse = response; // Capture the response object
            return response.json();
        })
        .then(data => {
            if (fetchResponse.ok) {
                console.log('Collin Reply Received from Server:', data);
                if (data.replyMessage && data.replyMessage.text) {
                    const messageDiv = document.createElement('div');
                    messageDiv.classList.add('nomi-message');
                    messageDiv.textContent = `Collin: ${data.replyMessage.text}`;
                    chatbox.appendChild(messageDiv);
                    // Optionally clear the input box after NOMI reply
                    // transcriptionBox.value = '';
                } else {
                    console.warn('Collin reply requested successfully, but no reply message found in the server response.');
                }
            } else {
                console.error('Error requesting Collin reply from server:', data);
                alert(`Error: ${data.error || fetchResponse.statusText}`); // Use fetchResponse here
            }
        })
        .catch(error => {
            console.error('Fetch error (request Collin reply from server):', error);
            alert('An error occurred while requesting Collin\'s reply from the server.');
        });
    });

    /**
     * Event listener for the cancelButton to clear the transcription box.
     */
    cancelButton.addEventListener('click', () => {
        transcriptionBox.value = ''; // Clear the text in the input area
    });

    /**
     * Event listener for the geminiButton to polish text using the Gemini API.
     */
    geminiButton.addEventListener('click', () => {
        const message = transcriptionBox.value; // Get the text to polish
        const mode = modeSelect.value; // Get the selected polish mode
        // Check if there is text to polish
        if (message.trim()) {
            fetch('/gemini_polish', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message, mode: mode }),
            })
                .then(response => {
                    return response.json().then(data => ({ ok: response.ok, data: data }));
                })
                .then(({ ok, data }) => {
                    // If the request is successful and the response contains polished text
                    if (ok && data.response) {
                        transcriptionBox.value = data.response;
                    } else {
                        console.error('Gemini Error:', data);
                        alert(`Gemini Error: ${data.error || (data && data.statusText) || 'Request failed'}`);
                    }
                })
                .catch(error => {
                    console.error('Fetch error (Gemini):', error);
                    alert('Error communicating with Gemini.');
                });
        } else {
            alert('Please enter text to polish with Gemini.');
        }
    });

    /**
     * Event listener for the startLoopButton to initiate a NOMI interaction loop with Collin.
     */
    startLoopButton.addEventListener('click', () => {
        const startPrompt = transcriptionBox.value; // Get the starting prompt for the loop
        const selectedRoomUuid = roomSelect.value; // Get the selected room UUID
        const collinUuid = 'COLLIN_UUID_PLACEHOLDER'; // Placeholder - actual UUID will be used on the backend
        const mode = modeSelect.value; // Get the selected interaction mode
        const duration = prompt('Enter loop duration in seconds:', 30); // Prompt the user for the loop duration

        // Check if required fields are filled
        if (!selectedRoomUuid || !startPrompt || !duration) {
            alert('Please select a room, enter a start prompt, and a duration.');
            return;
        }

        // Send a request to start the NOMI interaction loop with Collin
        fetch('/start_loop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room: selectedRoomUuid,
                nomi: collinUuid, // Hardcoded Collin's UUID (to be replaced on backend)
                start_prompt: startPrompt,
                duration: parseInt(duration, 10), // Parse duration as an integer
                mode: mode
            }),
        })
            .then(response => response.json())
            .then(data => {
                // If the request is successful and the response indicates success
                if (response.ok && data.status) {
                    alert(data.status); // Show the status message (e.g., "Loop started successfully.")
                } else {
                    console.error('Error starting loop with Collin:', data);
                    alert(`Error starting loop with Collin: ${data.error || response.statusText}`);
                }
            })
            .catch(error => {
                console.error('Fetch error (start loop with Collin):', error);
                alert('Error starting the loop with Collin.');
            });
    });

    /**
     * Event listener for the stopLoopButton to terminate a running NOMI interaction loop.
     */
    stopLoopButton.addEventListener('click', () => {
        const selectedRoomUuid = roomSelect.value; // Get the selected room UUID
        // Check if a room is selected
        if (!selectedRoomUuid) {
            alert('Please select a room to stop the loop in.');
            return;
        }
        // Send a request to stop the NOMI interaction loop
        fetch('/stop_loop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ room_uuid: selectedRoomUuid }),
        })
            .then(response => response.json())
            .then(data => {
                // If the request is successful and the response indicates success
                if (response.ok && data.status) {
                    alert(data.status); // Show the status message (e.g., "Loop stopped successfully.")
                } else {
                    console.error('Error stopping loop:', data);
                    alert(`Error stopping loop: ${data.error || response.statusText}`);
                }
            })
            .catch(error => {
                console.error('Fetch error (stop loop):', error);
                alert('Error stopping the loop.');
            });
    });

    // Speech recognition functionality (if supported by the browser)
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        let accumulatedFinalTranscript = '';

        recognition.onstart = () => {
            isRecording = true;
            recordButton.classList.add('recording');
        };

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let currentFinalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    currentFinalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            accumulatedFinalTranscript += currentFinalTranscript; // Append the new final transcript
            transcriptionBox.value = accumulatedFinalTranscript + interimTranscript; // Update the box
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isRecording = false;
            recordButton.classList.remove('recording');
        };

        recognition.onend = () => {
            isRecording = false;
            recordButton.classList.remove('recording');
        };

        recordButton.addEventListener('click', () => {
            if (isRecording) {
                recognition.stop();
            } else {
                // Clear the accumulated transcript when starting a new recording
                accumulatedFinalTranscript = '';
                transcriptionBox.value = '';
                recognition.start();
            }
        });
    } else {
        recordButton.disabled = true;
        recordButton.title = 'Speech recognition not supported in this browser.';
    }

    // Toggle dark/light theme
    themeSwitch.addEventListener('change', () => {
        document.body.classList.toggle('dark-mode');
        themeLabel.textContent = document.body.classList.contains('dark-mode') ? '🌑 Dark Mode' : '🌞 Light Mode';
    });

    // Placeholder for future receive button functionality
    receiveButton.addEventListener('click', () => {
        alert('Receive messages functionality will be implemented in the future.');
    });
});