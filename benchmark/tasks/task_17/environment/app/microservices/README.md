# Microservices API

## Services
- Users Service: Port 3001
- Orders Service: Port 3002
- Products Service: Port 3003 (not yet documented)

## Authentication
All endpoints except /auth/* require Bearer token in Authorization header.

## Base URLs
- Development: http://localhost:3000
- Staging: https://api-staging.example.com
- Production: https://api.example.com

## Rate Limiting
- 100 requests per minute per IP
- 1000 requests per hour per user

## Error Responses
Standard error format:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
