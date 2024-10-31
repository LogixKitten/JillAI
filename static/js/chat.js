const socket = io({
    transports: ['websocket', 'polling'],  // Allow fallback to polling if WebSocket fails
    pingInterval: 10000, // 10 seconds
    pingTimeout: 5000,   // 5 seconds
});

// Join the assigned room
socket.emit('join', { user: CurrentUser, room: userRoom });

let previousDate = null; // To keep track of the previous message date

///////////////-------- HANDLE CHAT HISTORY --------//////////////////////////
socket.on('load_chat_history', function(data) {
    console.log('Chat history received:', data);

    if (data.length === 0) {
        const currentDate = new Date().toISOString();
        const localTimeString = convertUTCToLocalDate(currentDate);
        const dateDiv = document.createElement('div');
        dateDiv.classList.add('date-divider');
        const dateP = document.createElement('p');
        dateP.textContent = localTimeString;
        dateP.style.textAlign = 'center';
        dateDiv.appendChild(dateP);
        chatBox.appendChild(dateDiv);
    }
    
    // Parse the JSON data to get the logs
    const chatLogs = JSON.parse(data);
    
    const chatBox = document.getElementById('chat-box');
    

    // Assuming chatLogs is an array of chat history objects
    chatLogs.forEach(log => {
        log.chat_history.forEach(entry => {
            const currentDate = convertUTCToLocalDate(entry.timestamp);

            // Check if the current message date is different from the previous message date
            if (previousDate !== currentDate) {
                const dateDiv = document.createElement('div');
                dateDiv.classList.add('date-divider');
                const dateP = document.createElement('p');
                dateP.textContent = currentDate;
                dateP.style.textAlign = 'center';
                dateDiv.appendChild(dateP);
                chatBox.appendChild(dateDiv);
                previousDate = currentDate; // Update the previous date
            }

            const message = document.createElement('div');   
            const messageContainer = document.createElement('div');
            const avatarContainer = document.createElement('div');
            const avatarImage = document.createElement('img');
            const avatarName = document.createElement('div');

            const persona = entry.sender_name.toLowerCase();

            // Styling the message based on the sender
            if (entry.sender === 'User' || entry.sender === 'Agent') {
                message.classList.add('chat-message', 
                    entry.sender === 'Agent' ? 'incoming-message' : 
                    'outgoing-message'                    
                );            
            } else if (entry.sender === 'System') {
                message.classList.add('server-message', 'text-start');
            }            

            // Styling the message container based on the sender
            if (entry.sender === 'User' || entry.sender === 'Agent') {
                messageContainer.classList.add('message-container', 
                    entry.sender === 'Agent' ? 'incoming-container' : 
                    'outgoing-container'
                );
            }

            // Add persona and avatar for agent messages
            if (entry.sender == 'Agent') {
                avatarContainer.classList.add('avatar-container');                
                avatarImage.classList.add('avatar-image');
                avatarImage.src = `/static/img/personas/${persona}.png`;

                // Add the persona name above the avatar                
                avatarName.classList.add('avatar-name');
                avatarName.textContent = entry.sender_name;

                avatarContainer.appendChild(avatarName); 
                avatarContainer.appendChild(avatarImage);
                
                const timestamp = document.createElement('div'); // Create a timestamp element

                const messageTime = new Date(Date.parse(entry.timestamp + 'Z'));
                const localTimeString = convertUTCToLocal(messageTime);
                timestamp.classList.add('timestamp');
                timestamp.textContent = localTimeString;

                // Add the message text
                message.classList.add('message-text');
                message.innerHTML = `${entry.message}`;

                // Append message text and avatar container
                messageContainer.appendChild(avatarContainer);
                messageContainer.appendChild(message);
                messageContainer.appendChild(timestamp);                
                chatBox.appendChild(messageContainer);
            }

            if (entry.sender == 'User') {                
                avatarContainer.classList.add('avatar-container');                
                avatarImage.classList.add('avatar-image');
                avatarImage.src = CurrentUser["Avatar"];

                avatarName.classList.add('avatar-name');
                avatarName.textContent = CurrentUser["FirstName"];

                // Append avatar and name to the avatar container                
                avatarContainer.appendChild(avatarName);
                avatarContainer.appendChild(avatarImage);

                const timestamp = document.createElement('div'); // Create a timestamp element

                const messageTime = new Date(Date.parse(entry.timestamp + 'Z'));
                const localTimeString = convertUTCToLocal(messageTime);
                timestamp.classList.add('timestamp');
                timestamp.textContent = localTimeString;

                // Add the message text
                message.classList.add('message-text');
                message.innerHTML = `${entry.message}`;

                // Append message text and avatar container
                messageContainer.appendChild(timestamp);
                messageContainer.appendChild(message);
                messageContainer.appendChild(avatarContainer);
                chatBox.appendChild(messageContainer);
            }

            if (entry.sender == 'System') {
                const serverMessageContainer = document.createElement('div');
                serverMessageContainer.classList.add('server-container');

                message.classList.add('message-text');

                const timestamp = document.createElement('div'); // Create a timestamp element

                const messageTime = new Date(Date.parse(entry.timestamp + 'Z'));
                const localTimeString = convertUTCToLocal(messageTime);
                timestamp.classList.add('timestamp');
                timestamp.textContent = localTimeString;

                message.innerHTML = `${entry.message}`;

                serverMessageContainer.appendChild(message);
                serverMessageContainer.appendChild(timestamp);
                chatBox.appendChild(serverMessageContainer);
            }            
        });
    });

    // Scroll to the bottom of the chat box to keep the latest message in view
    chatBox.scrollTop = chatBox.scrollHeight;
});


///////////////-------- HANDLE SERVER MESSAGES --------//////////////////////////
socket.on('message', function(data) {    
    const chatBox = document.getElementById('chat-box');

    const date = new Date().toISOString();
    const currentDate = convertUTCToLocalDate(date);

    // Check if the current message date is different from the previous message date
    if (previousDate !== currentDate) {
        const dateDiv = document.createElement('div');
        dateDiv.classList.add('date-divider');
        const dateP = document.createElement('p');
        dateP.textContent = currentDate;
        dateP.style.textAlign = 'center';
        dateDiv.appendChild(dateP);
        chatBox.appendChild(dateDiv);
        previousDate = currentDate; // Update the previous date
    }

    const serverMessageContainer = document.createElement('div');
    serverMessageContainer.classList.add('server-container');

    const message = document.createElement('div');

    message.classList.add('server-message', 'text-start');

    const timestamp = document.createElement('div'); // Create a timestamp element
    
    const currentTime = new Date().toISOString();
    const localTimeString = convertUTCToLocal(currentTime);
    timestamp.classList.add('timestamp');
    timestamp.textContent = localTimeString;

    message.innerHTML = data;

     // Append timestamp to message container
    serverMessageContainer.appendChild(message);
    serverMessageContainer.appendChild(timestamp);
    chatBox.appendChild(serverMessageContainer);

    // Scroll to the bottom of the chat box to keep the latest message in view
    chatBox.scrollTop = chatBox.scrollHeight;

    showTypingIndicator();
});


///////////////-------- HANDLE USER MESSAGES --------//////////////////////////
function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();

    if (message && userRoom) {
        socket.emit('message', { user: CurrentUser, message: message, room: userRoom });

        // Get the chat box container
        const chatBox = document.getElementById('chat-box');

        const date = new Date().toISOString();
        const currentDate = convertUTCToLocalDate(date);

        // Check if the current message date is different from the previous message date
        if (previousDate !== currentDate) {
            const dateDiv = document.createElement('div');
            dateDiv.classList.add('date-divider');
            const dateP = document.createElement('p');
            dateP.textContent = currentDate;
            dateP.style.textAlign = 'center';
            dateDiv.appendChild(dateP);
            chatBox.appendChild(dateDiv);
            previousDate = currentDate; // Update the previous date
        }

        // Create elements for the user message
        const userMessage = document.createElement('div');
        const messageContainer = document.createElement('div');
        const avatarContainer = document.createElement('div');
        const avatarImage = document.createElement('img');
        const avatarName = document.createElement('div');
        const timestamp = document.createElement('div'); // Create a timestamp element

        // Styling the user message on the right side
        userMessage.classList.add('chat-message', 'outgoing-message');        
        userMessage.innerHTML = `${message}`;

        // Styling the avatar on the right side
        avatarContainer.classList.add('avatar-container');
        avatarImage.classList.add('avatar-image');
        avatarName.classList.add('avatar-name');

        // Set the avatar image and name
        avatarImage.src = CurrentUser["Avatar"];
        avatarName.textContent = CurrentUser["FirstName"];

        // Append avatar and name
        avatarContainer.appendChild(avatarName);
        avatarContainer.appendChild(avatarImage);

        // Create a timestamp and style it
        const currentTime = new Date().toISOString();
        const localTimeString = convertUTCToLocal(currentTime);
        timestamp.classList.add('timestamp');
        timestamp.textContent = localTimeString;

        // Create a container for the whole message (message + avatar)
        messageContainer.classList.add('message-container', 'outgoing-container');
        messageContainer.appendChild(timestamp); // Append timestamp to message container
        messageContainer.appendChild(userMessage);
        messageContainer.appendChild(avatarContainer);
        

        // Append the message container to the chat box
        chatBox.appendChild(messageContainer);

        input.value = ''; // Clear the input field

        // Scroll to the bottom of the chat box to keep the latest message in view
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// Send message when the Send button is clicked
document.getElementById('send-btn').addEventListener('click', function() {
    showTypingIndicator();
    sendMessage();    
});

// Send message when Enter is pressed
document.getElementById('chat-input').addEventListener('keydown', function(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault(); // Prevent the default behavior
        showTypingIndicator();
        sendMessage();
    }
});


// Function to create and show the typing indicator
function showTypingIndicator() {
    const chatBox = document.getElementById("chat-box");
    // Check if the indicator already exists to avoid duplicates
    if (!document.getElementById("typingNoticeContainer")) {
        const typingNoticeContainer = document.createElement("div");
        typingNoticeContainer.id = "typingNoticeContainer";
        typingNoticeContainer.classList.add("typing-notice"); // Add a class for styling

        const personaName = CurrentUser["CurrentPersona"];
        const capitalizedPersonaName = personaName.charAt(0).toUpperCase() + personaName.slice(1);
        
        // Set up the inner HTML with the typing message
        typingNoticeContainer.innerHTML = `<p class="typing-text">${capitalizedPersonaName} is typing<span class="dots">...</span></p>`;
        
        // Append to the chat box
        chatBox.appendChild(typingNoticeContainer);

        // Scroll to the bottom of the chat box to keep the latest message in view
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

// Function to hide and remove the typing indicator
function hideTypingIndicator() {
    console.log("Hiding fucntion called"); 
    const typingNoticeContainer = document.getElementById("typingNoticeContainer");
    if (typingNoticeContainer) {
        console.log("Typing indicator found and removed");
        typingNoticeContainer.style.display = "none"; // Hide it from view
        typingNoticeContainer.remove(); // Also remove it from the DOM to allow recreation
    }
    else {
        console.log("Typing indicator not found");
    }
}


///////////////-------- HANDLE AGENT MESSAGES --------//////////////////////////
let currentMessageElement = null;
let accumulatedMessage = ""; // To accumulate the full message text

socket.on('streamed_message', function(data) {
    let { message, persona } = data;    

    hideTypingIndicator(); // Hide the typing indicator when the agent sends a message

    // Get the chat box container
    const chatBox = document.getElementById('chat-box');

    const date = new Date().toISOString();
    const currentDate = convertUTCToLocalDate(date);

    // Check if the current message date is different from the previous message date
    if (previousDate !== currentDate) {
        const dateDiv = document.createElement('div');
        dateDiv.classList.add('date-divider');
        const dateP = document.createElement('p');
        dateP.textContent = currentDate;
        dateP.style.textAlign = 'center';
        dateDiv.appendChild(dateP);
        chatBox.appendChild(dateDiv);
        previousDate = currentDate; // Update the previous date
    }

    // If we are starting a new message
    if (currentMessageElement === null) {
        // Create the message container for a new message
        currentMessageElement = document.createElement('div');
        currentMessageElement.classList.add('chat-message', 'incoming-message', 'incoming-container');
        
        // Add persona and avatar at the beginning of the message
        const persona = data.persona.toLowerCase(); // Assuming persona is provided
        const avatarContainer = document.createElement('div');
        avatarContainer.classList.add('avatar-container');

        // Add the avatar image
        const avatarImage = document.createElement('img');
        avatarImage.classList.add('avatar-image');
        avatarImage.src = `/static/img/personas/${persona}.png`; // Assuming avatars are named by persona

        // Add the persona name above the avatar
        const avatarName = document.createElement('div');
        avatarName.classList.add('avatar-name');
        avatarName.textContent = data.persona;
        
        avatarContainer.appendChild(avatarName);
        avatarContainer.appendChild(avatarImage);

        const timestamp = document.createElement('div'); // Create a timestamp element

        const currentTime = new Date().toISOString();
        const localTimeString = convertUTCToLocal(currentTime);
        timestamp.classList.add('timestamp');
        timestamp.textContent = localTimeString;

        // Create a container that holds both avatar and message
        const messageContainer = document.createElement('div');
        messageContainer.classList.add('message-container');
        messageContainer.appendChild(avatarContainer);
        messageContainer.appendChild(currentMessageElement);
        messageContainer.appendChild(timestamp);

        // Append the message container to the chat box
        chatBox.appendChild(messageContainer);
    }    

    // Append the chunk to the accumulated message
    accumulatedMessage += message;

    // Update the current message element with the accumulated text
    currentMessageElement.textContent = accumulatedMessage;    

    // Scroll to the bottom of the chat box to keep the latest message in view
    chatBox.scrollTop = chatBox.scrollHeight;
});

// Listen for the final message to update it with the clean version
socket.on('final_message', function(finalData) {
    if (finalData && finalData.message && currentMessageElement) {
        currentMessageElement.textContent = finalData.message;
        
        // Finalize the message element (you can apply any final styling if needed)
        currentMessageElement = null;  // Nullify the reference for the next message
        accumulatedMessage = "";       // Reset accumulated message for the next response
    }
});


///////////////-------- HANDLE TIME LOCALIZATION --------//////////////////////////
function convertUTCToLocal(utcTimestamp) {
    const utcDate = new Date(utcTimestamp);    

    // Retrieve timezone information from CurrentUser
    const timezone = CurrentUser["TimeZone"];
    const hasDST = CurrentUser["HasDST"];
    const dstStart = new Date(CurrentUser["DSTStart"]);
    const dstEnd = new Date(CurrentUser["DSTEnd"]);

    // Set up formatting options for time only
    const options = {
        timeZone: timezone,
        hour12: true,
        hour: '2-digit',
        minute: '2-digit'
    };

    // Format the date to the user's local time
    const dateFormatter = new Intl.DateTimeFormat('en-US', options);
    const localTimeString = dateFormatter.format(utcDate);
    
    return localTimeString;
}


///////////////-------- HANDLE DATE LOCALIZATION --------//////////////////////////
function convertUTCToLocalDate(utcTimestamp) {
    const utcDate = new Date(utcTimestamp);

    // Retrieve timezone information from CurrentUser
    const timezone = CurrentUser["TimeZone"];

    // Set up formatting options for the full date with weekday
    const options = {
        timeZone: timezone,
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    };

    // Format the date to the user's local time
    const dateFormatter = new Intl.DateTimeFormat('en-US', options);
    const formattedDate = dateFormatter.format(utcDate);

    // Get the day number to add the appropriate suffix (e.g., 1st, 2nd, 3rd, 4th)
    const day = utcDate.getDate();
    const suffix = (day % 10 === 1 && day !== 11) ? 'st' :
                   (day % 10 === 2 && day !== 12) ? 'nd' :
                   (day % 10 === 3 && day !== 13) ? 'rd' : 'th';

    // Split the formatted date into parts to rearrange
    const [weekday, month, date, year] = formattedDate.split(' ');

    // Construct the final formatted date string
    return `${weekday} - ${month} ${day}${suffix}, ${year}`;
}


///////////////-------- HANDLE USER LEAVING --------//////////////////////////
function handleLogout(isUnload = false) {
    if (isUnload) {
        // Minimized actions for unload event
        socket.emit('leave', { user: userData, room: roomID });
    } else {
        // Standard logout actions for button click or menu action
        socket.emit('leave', { user: userData, room: roomID }, () => {
            window.location.href = '/logout';
        });
    }
}

window.addEventListener("beforeunload", () => {
    handleLogout(true);  // Pass `true` to handle unload
});
