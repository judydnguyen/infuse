# Login System

## Problem
Users cannot log in! Multiple bugs were introduced yesterday:

1. Valid passwords are being rejected
2. Password reset emails are not sending
3. Reset tokens expire immediately

## Files
- `src/auth.js` - Main authentication logic (HAS BUGS!)
- `src/database.js` - Database functions (working)
- `src/email.js` - Email service (working)
- `logs/errors.log` - Error messages
- `logs/user_reports.txt` - User complaints
- `logs/git_log.txt` - Recent changes

## Expected Behavior
- Users should be able to log in with correct password
- Password reset emails should send successfully
- Reset tokens should be valid for 1 hour

## Current Behavior
- All logins fail with "Invalid password"
- Password reset fails with "Email host not configured"
- Tokens expire immediately after creation
