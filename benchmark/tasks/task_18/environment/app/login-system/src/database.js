const users = [
  {
    id: 1,
    email: 'john@example.com',
    password_hash: '$2b$10$YourHashedPasswordHere123',
    name: 'John Doe'
  },
  {
    id: 2,
    email: 'jane@example.com', 
    password_hash: '$2b$10$AnotherHashedPasswordHere456',
    name: 'Jane Smith'
  }
];

const resetTokens = [];

async function getUserByEmail(email) {
  return users.find(u => u.email === email);
}

async function saveResetToken(userId, token) {
  resetTokens.push({
    userId,
    token,
    timestamp: Date.now()
  });
}

module.exports = { getUserByEmail, saveResetToken };
