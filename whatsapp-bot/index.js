require('dotenv').config();
const WhatsappBot = require('./src/whatsapp-client');

const bot = new WhatsappBot();
bot.initialize();
