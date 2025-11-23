const axios = require("axios");

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

async function sendToBackend(msg) {
  try {
    const payload = {
      from: msg.from,
      body: msg.body,
      timestamp: msg.timestamp,
      type: msg.type,
    };

    const response = await axios.post(`${BACKEND_URL}/webhook`, payload);
    return response.data.response;
  } catch (error) {
    console.error("Error communicating with backend:", error.message);
    return null;
  }
}

module.exports = { sendToBackend };
