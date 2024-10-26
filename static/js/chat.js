const socket = io({
    transports: ['websocket', 'polling']  // Allow fallback to polling if WebSocket fails
});

const userName = "{{ current_user.FirstName|e }}";
const userRoom = "{{ room|e }}";

// Join the assigned room
socket.emit('join', { username: userName, room: userRoom });

// Function to send the message
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (message && userRoom) {
        socket.emit('message', { username: userName, message: message, room: userRoom });

        // Append the user's message to the chat box
        const chatBox = document.getElementById('chat-box');
        const userMessage = document.createElement('div');
        userMessage.classList.add('chat-message', 'text-end');
        userMessage.innerHTML = `<strong>${userName}:</strong> ${message}`;
        chatBox.appendChild(userMessage);
        input.value = '';  // Clear the input field
    }
}

// Send message when the Send button is clicked
document.getElementById('send-btn').addEventListener('click', sendMessage);

// Send message when Enter is pressed
document.getElementById('chat-input').addEventListener('keydown', function(event) {
    if (event.key === 'Enter' || event.keyCode === 13) {
        event.preventDefault();  // Prevent default Enter behavior
        sendMessage();
    }
});

// Receive messages from the server
socket.on('message', function(data) {
    console.log('Message received:', data);
    const chatBox = document.getElementById('chat-box');
    const message = document.createElement('div');
    message.classList.add('chat-message', 'text-start');
    message.innerHTML = data;
    chatBox.appendChild(message);
});