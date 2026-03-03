const { GoogleGenerativeAI } = require('@google/generative-ai');

// @desc Process user chat message
// @route POST /api/chat
// @access Private
exports.processChat = async (req, res, next) => {
    try {
        const { message, history } = req.body;

        if (!message) {
            return res.status(400).json({ message: 'Please provide a message' });
        }

        const apiKey = process.env.GEMINI_API_KEY;
        if (!apiKey || apiKey === 'your_api_key_here' || apiKey === '') {
            return res.status(500).json({ 
                message: 'Gemini API Key is missing. Please configure GEMINI_API_KEY in the server .env file.' 
            });
        }

        // Initialize Gemini API
        const genAI = new GoogleGenerativeAI(apiKey);
        const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });

        // Map the existing chat history to the format Gemini expects
        // Gemini expects: { role: 'user' | 'model', parts: [{ text: string }] }
        let formattedHistory = [];
        if (history && Array.isArray(history)) {
            formattedHistory = history.map(msg => ({
                role: msg.role === 'user' ? 'user' : 'model',
                parts: [{ text: msg.content }]
            }));
        }

        // Start chat with history
        const chat = model.startChat({
            history: formattedHistory,
            // Provide context via system instruction (supported in gemini-1.5-flash)
            systemInstruction: "You are LearnHub AI, an intelligent, helpful, and friendly teaching assistant for the LearnHub Learning Management System. Help the user with their questions related to courses, programming, design, and learning in general. Format your responses using markdown.",
        });

        const result = await chat.sendMessage(message);
        const responseText = result.response.text();

        res.json({
            response: responseText
        });
    } catch (error) {
        console.error('Chatbot error:', error);
        res.status(500).json({ 
            message: 'Error processing your request. The AI service may be temporarily unavailable.' 
        });
    }
};
