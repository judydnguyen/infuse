-- Simple users data dump
INSERT INTO users (id, email, name, password_digest, phone, address, created_at, updated_at) VALUES
(1, 'alice@example.com', 'Alice Smith', '$2a$10$hashed1', '555-0101', '123 Main St', '2024-01-15 10:00:00', '2024-01-15 10:00:00'),
(2, 'bob@example.com', 'Bob Jones', '$2a$10$hashed2', '555-0102', '456 Oak Ave', '2024-01-16 11:00:00', '2024-01-16 11:00:00'),
(3, 'carol@example.com', 'Carol White', '$2a$10$hashed3', '555-0103', '789 Pine Rd', '2024-01-17 12:00:00', '2024-01-17 12:00:00');
