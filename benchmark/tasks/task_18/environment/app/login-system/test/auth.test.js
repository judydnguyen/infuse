const { login, sendPasswordReset, isTokenExpired } = require('../src/auth');

describe('Auth Tests', () => {
  
  test('Login with correct password should succeed', async () => {
    const result = await login('john@example.com', 'correctPassword123');
    // Currently FAILS because bug returns success when passwords don't match
    expect(result.success).toBe(true);
  });
  
  test('Password reset should send email', async () => {
    const result = await sendPasswordReset('john@example.com');
    // Currently FAILS because EMAIL_SERVER is undefined
    expect(result.success).toBe(true);
  });
  
  test('Fresh token should not be expired', () => {
    const timestamp = Date.now();
    // Currently FAILS because expiration logic is backwards
    expect(isTokenExpired(timestamp)).toBe(false);
  });
  
});
