const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const apiClient = require('./api-client');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('ffmpeg-static');
const ffprobePath = require('ffprobe-static').path;

console.log("Configuring FFmpeg...");
console.log("FFmpeg Path:", ffmpegPath);
console.log("FFprobe Path:", ffprobePath);

ffmpeg.setFfmpegPath(ffmpegPath);
ffmpeg.setFfprobePath(ffprobePath);

const fs = require('fs');
const path = require('path');
const FormData = require('form-data');
const axios = require('axios');

class WhatsappBot {
    constructor() {
        this.client = new Client({
            authStrategy: new LocalAuth(),
            puppeteer: {
                args: ['--no-sandbox']
            }
        });

        this.initializeEvents();
    }

    initializeEvents() {
        this.client.on('qr', (qr) => {
            qrcode.generate(qr, { small: true });
            console.log('QR Code received, scan please!');
        });

        this.client.on('ready', () => {
            console.log('Client is ready!');
        });

        this.client.on('message', async msg => {
            const allowedNumber = process.env.ALLOWED_NUMBER;
            const senderNumber = msg.from.replace('@c.us', '');
            
            console.log(`MESSAGE RECEIVED from ${senderNumber}:`, msg.type);

            if (allowedNumber && senderNumber !== allowedNumber) {
                console.log(`Ignored message from ${senderNumber} (not allowed)`);
                return;
            }

            try {
                if (msg.hasMedia && (msg.type === 'audio' || msg.type === 'ptt')) {
                    await this.handleAudioMessage(msg);
                } else if (msg.type === 'chat') {
                    const response = await apiClient.sendToBackend(msg);
                    if (response) {
                        await msg.reply(response);
                    }
                }
            } catch (error) {
                console.error('Error processing message:', error);
            }
        });
    }

    async handleAudioMessage(msg) {
        try {
            console.log('Downloading audio...');
            const media = await msg.downloadMedia();
            
            if (!media) {
                console.error('Failed to download media');
                return;
            }

            const tempDir = path.join(__dirname, '../temp');
            if (!fs.existsSync(tempDir)) {
                fs.mkdirSync(tempDir);
            }

            const inputPath = path.join(tempDir, `${msg.id.id}.ogg`);
            const outputPath = path.join(tempDir, `${msg.id.id}_accelerated.ogg`);

            // Save base64 to file
            fs.writeFileSync(inputPath, media.data, 'base64');

            console.log('Accelerating audio...');
            // Accelerate audio
            const command = ffmpeg(inputPath)
                .setFfmpegPath(ffmpegPath)
                .setFfprobePath(ffprobePath)
                .audioFilters('atempo=1.25')
                .output(outputPath)
                .on('end', async () => {
                    console.log('Audio accelerated, sending to backend...');
                    try {
                        await this.sendAudioToBackend(msg, outputPath);
                    } catch (err) {
                        console.error('Error sending audio:', err);
                    } finally {
                        // Cleanup
                        if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
                        if (fs.existsSync(outputPath)) fs.unlinkSync(outputPath);
                    }
                })
                .on('error', (err) => {
                    console.error('Error processing audio:', err);
                    // Fallback: send original if ffmpeg fails? Or just error.
                    // For now, just cleanup
                    if (fs.existsSync(inputPath)) fs.unlinkSync(inputPath);
                })

            command.run();

        } catch (error) {
            console.error('Error handling audio:', error);
        }
    }

    async sendAudioToBackend(msg, filePath) {
        const form = new FormData();
        form.append('from', msg.from);
        form.append('message_type', 'audio');
        form.append('timestamp', msg.timestamp);
        form.append('audio_file', fs.createReadStream(filePath));

        try {
            const response = await axios.post(`${process.env.BACKEND_URL}/webhook`, form, {
                headers: {
                    ...form.getHeaders()
                }
            });
            
            if (response.data.response) {
                await msg.reply(response.data.response);
            }
        } catch (error) {
            console.error('Error sending to backend:', error.message);
        }
    }

    initialize() {
        this.client.initialize();
    }
}

module.exports = WhatsappBot;
