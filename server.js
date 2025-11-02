// Top of server.js
process.on('uncaughtException', (err) => {
    console.error('💥 Uncaught Exception:', err);
    process.exit(1);
  });
  
  process.on('unhandledRejection', (reason, promise) => {
    console.error('💣 Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
  });   

require('dotenv').config();
// server.js


console.log('🔑 RESEND_API_KEY loaded:', !!process.env.RESEND_API_KEY);
console.log('First 5 chars:', process.env.RESEND_API_KEY?.substring(0, 5));

const express = require('express');
const cors = require('cors');
const crypto = require('crypto');

// --- CONFIGURATION ---
const PORT = 3000;
const RESEND_API_KEY = process.env.RESEND_API_KEY; // 🔑 REPLACE THIS!
const FROM_EMAIL = 'MEDIEYE@resend.dev'; // Resend's free domain

// --- SETUP ---
const app = express();
app.use(cors()); // Allows your HTML page (on any origin) to call this server
app.use(express.json());

// In-memory OTP store (use Redis/DB in production)
const otpStore = new Map();

// --- SEND OTP ENDPOINT ---
app.post('/send-otp', async (req, res) => {
  const { email } = req.body;

  if (!email || !email.includes('@')) {
    return res.status(400).json({ error: 'Valid email is required' });
  }

  // Generate 6-digit OTP
  const otp = crypto.randomInt(100000, 999999).toString();

  // Store OTP with 5-minute expiry
  otpStore.set(email, {
    otp,
    expiresAt: Date.now() + 5 * 60 * 1000
  });

  // Send email via Resend
  try {
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${RESEND_API_KEY}`
      },
      body: JSON.stringify({
        from: FROM_EMAIL,
        to: email,
        subject: 'Your OTP Code',
        text: `Your OTP is: ${otp}\n\nIt expires in 5 minutes.`
      })
    });

    if (!response.ok) {
      const err = await response.json();
      console.error('Resend error:', err);
      return res.status(500).json({ error: 'Failed to send email' });
    }

    console.log(`✅ OTP sent to ${email}`);
    return res.json({ success: true });
  } catch (error) {
    console.error('Server error:', error);
    return res.status(500).json({ error: 'Internal server error' });
  }
});

// Optional: Verify OTP (for later use)
app.post('/verify-otp', (req, res) => {
  const { email, otp } = req.body;
  const record = otpStore.get(email);

  if (!record) return res.status(400).json({ error: 'No OTP found' });
  if (Date.now() > record.expiresAt) {
    otpStore.delete(email);
    return res.status(400).json({ error: 'OTP expired' });
  }
  if (record.otp !== otp) return res.status(400).json({ error: 'Invalid OTP' });

  otpStore.delete(email);
  return res.json({ success: true, message: 'OTP verified!' });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 OTP server running on http://localhost:${PORT}`);
  console.log(`📨 Use POST /send-otp with { "email": "user@example.com" }`);
});