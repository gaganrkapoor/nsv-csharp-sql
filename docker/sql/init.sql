-- Initialize Todo Database
USE master;
GO

-- Create TodoDb database if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TodoDb')
BEGIN
    CREATE DATABASE TodoDb;
END
GO

USE TodoDb;
GO

-- Create application user for Entity Framework
-- Note: In containerized environment, we'll use SA account for simplicity
-- In production, you should create a dedicated application user

-- Verify database creation
SELECT 'TodoDb database created successfully' AS Status;
GO