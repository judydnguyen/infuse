-- Simple orders data dump
INSERT INTO orders (id, user_id, total, status, shipping_address, notes, created_at, updated_at) VALUES
(1, 1, 99.99, 'completed', '123 Main St', 'Gift wrap requested', '2024-01-20 10:00:00', '2024-01-21 14:00:00'),
(2, 1, 149.50, 'pending', '123 Main St', NULL, '2024-01-25 09:00:00', '2024-01-25 09:00:00'),
(3, 2, 299.99, 'completed', '456 Oak Ave', 'Express shipping', '2024-01-22 15:00:00', '2024-01-23 10:00:00'),
(4, 3, 49.99, 'cancelled', '789 Pine Rd', NULL, '2024-01-24 11:00:00', '2024-01-24 16:00:00');
