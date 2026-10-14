const bcrypt = require('bcrypt');
const db = require('./database');
const emailService = require('./email');

// BUG 1: Password comparison logic is backwards!
async function login(email, password) {
  try {
    const user = await db.getUserByEmail(email);
    
    if (!user) {
      return { success: false, error: 'User not found' };
    }
    
    // BUG: This returns true when passwords DON'T match!
    const passwordMatch = await bcrypt.compare(password, user.password_hash);
    if (!passwordMatch) {
      return { success: true, userId: user.id, token: generateToken(user) };
    } else {
      return { success: false, error: 'Invalid password' };
    }
    
  } catch (error) {
    console.error('Login error:', error);
    return { success: false, error: 'Login failed' };
  }
}

// BUG 2: Email service uses wrong environment variable
async function sendPasswordReset(email) {
  try {
    const user = await db.getUserByEmail(email);
    
    if (!user) {
      return { success: false, error: 'User not found' };
    }
    
    const resetToken = generateResetToken();
    await db.saveResetToken(user.id, resetToken);
    
    // BUG: Should be EMAIL_HOST not EMAIL_SERVER
    const emailConfig = {
      host: process.env.EMAIL_SERVER,  // This is undefined!
      from: 'noreply@example.com',
      to: email,
      subject: 'Password Reset',
      body: `Reset link: https://example.com/reset?token=${resetToken}`
    };
    
    await emailService.send(emailConfig);
    return { success: true };
    
  } catch (error) {
    console.error('Password reset error:', error);
    return { success: false, error: error.message };
  }
}

// BUG 3: Token expiration check is wrong
function isTokenExpired(tokenTimestamp) {
  const now = Date.now();
  const oneHour = 60 * 60 * 1000;
  
  // BUG: This says tokens are expired when they're still valid!
  return (now - tokenTimestamp) < oneHour;
}

function generateToken(user) {
  return `token_${user.id}_${Date.now()}`;
}

function generateResetToken() {
  return Math.random().toString(36).substring(2, 15);
}

module.exports = { login, sendPasswordReset, isTokenExpired };
