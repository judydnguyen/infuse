/**
 * Authentication endpoints
 */

/**
 * Login
 * @route POST /api/auth/login
 * @body {string} email
 * @body {string} password
 * @returns {Object} {token, user, expires_in}
 */
router.post('/api/auth/login', async (req, res) => {
  res.json({
    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
    user: { id: '123', email: 'user@example.com' },
    expires_in: 3600
  });
});

/**
 * Register
 * @route POST /api/auth/register
 * @body {string} email
 * @body {string} password
 * @body {string} name
 * @returns {Object} created user and token
 */
router.post('/api/auth/register', async (req, res) => {
  res.status(201).json({
    user: { id: 'new-id', email: req.body.email },
    token: 'token-here'
  });
});

/**
 * Refresh token
 * @route POST /api/auth/refresh
 * @header {string} Authorization - Bearer token
 * @returns {Object} new token
 */
router.post('/api/auth/refresh', async (req, res) => {
  res.json({ token: 'new-token' });
});
