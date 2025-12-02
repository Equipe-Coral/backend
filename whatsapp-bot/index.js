require('dotenv').config();
const express = require('express');
const WhatsappBot = require('./src/whatsapp-client');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json());

// Initialize WhatsApp bot
const bot = new WhatsappBot();
bot.initialize();

// Health check endpoint
app.get('/status', (req, res) => {
    const isReady = bot.client.info !== null;
    res.json({
        status: isReady ? 'ready' : 'initializing',
        timestamp: new Date().toISOString()
    });
});

// Send message endpoint
app.post('/send-message', async (req, res) => {
    try {
        const { phone, message } = req.body;

        if (!phone || !message) {
            return res.status(400).json({
                error: 'Missing required fields: phone and message'
            });
        }

        // Check if client is ready
        if (!bot.client.info) {
            return res.status(503).json({
                error: 'WhatsApp client is not ready yet'
            });
        }

        // Format phone number (expects format: 5511999999999)
        const chatId = `${phone}@c.us`;

        // Send message
        await bot.client.sendMessage(chatId, message);

        res.json({
            success: true,
            message: 'Message sent successfully'
        });

    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({
            error: 'Failed to send message',
            details: error.message
        });
    }
});

// Start Express server
app.listen(PORT, () => {
    console.log(`WhatsApp Bot API listening on port ${PORT}`);
    console.log(`Health check: http://localhost:${PORT}/status`);
    console.log(`Send message: POST http://localhost:${PORT}/send-message`);
});
