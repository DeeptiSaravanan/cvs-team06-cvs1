document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatHistory = document.getElementById('chat-history');

    // Smooth scroll to bottom
    const scrollToBottom = () => {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    };

    // Create a message element
    const createMessage = (content, isUser = false) => {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        
        const textElement = document.createElement('p');
        textElement.textContent = content;
        
        messageDiv.appendChild(textElement);
        return messageDiv;
    };

    // Create typing indicator
    const createTypingIndicator = () => {
        const indicator = document.createElement('div');
        indicator.classList.add('typing-indicator');
        indicator.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('dot');
            indicator.appendChild(dot);
        }
        
        return indicator;
    };

    // Handle form submission
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        const messageText = chatInput.value.trim();
        if (!messageText) return;

        // Add user message
        chatHistory.appendChild(createMessage(messageText, true));
        chatInput.value = '';
        scrollToBottom();

        // Show typing indicator
        const typingIndicator = createTypingIndicator();
        chatHistory.appendChild(typingIndicator);
        scrollToBottom();

        // Simulate AI response after a delay
        setTimeout(() => {
            // Remove typing indicator
            const indicator = document.getElementById('typing-indicator');
            if (indicator) indicator.remove();

            // Generic response for sandbox
            const responses = [
                "That's a great question about user engagement. For that segment, you might want to consider A/B testing a tiered discount campaign.",
                "Based on the campaign goals you've described, targeting users who have abandoned their cart within the last 24 hours usually yields a 15-20% higher conversion rate.",
                "To run this personalized intervention effectively, ensure that your data integration is tracking the 'last_active_date' attribute accurately.",
                "I can help you build an audience segment for this. Would you like to filter by demographic data, behavioral data, or both?",
                "Interventions based on recent app usage have proven most effective. A push notification followed by an email if unread works well here."
            ];
            
            const randomResponse = responses[Math.floor(Math.random() * responses.length)];
            chatHistory.appendChild(createMessage(randomResponse, false));
            scrollToBottom();
        }, 1200);
    });
});
