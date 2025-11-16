-- SQL Schema for Product Matching Database
-- This creates tables for products, categories, and matching/training data

-- Categories table for product classification
CREATE TABLE Categories (
    CategoryId INT PRIMARY KEY IDENTITY(1,1),
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    ParentCategoryId INT NULL,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (ParentCategoryId) REFERENCES Categories(CategoryId)
);

-- Master products table with standardized descriptions
CREATE TABLE Products (
    ProductId INT PRIMARY KEY IDENTITY(1,1),
    ProductCode NVARCHAR(50) UNIQUE NOT NULL,
    ProductName NVARCHAR(255) NOT NULL,
    StandardizedDescription NVARCHAR(500) NOT NULL,
    CategoryId INT NOT NULL,
    Brand NVARCHAR(100),
    UnitOfMeasure NVARCHAR(20),
    StandardPrice DECIMAL(10,2),
    IsActive BIT DEFAULT 1,
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    UpdatedAt DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (CategoryId) REFERENCES Categories(CategoryId)
);

-- Alternative product descriptions for better matching
CREATE TABLE ProductDescriptions (
    DescriptionId INT PRIMARY KEY IDENTITY(1,1),
    ProductId INT NOT NULL,
    AlternativeDescription NVARCHAR(500) NOT NULL,
    DescriptionType NVARCHAR(50) NOT NULL, -- 'supplier', 'invoice', 'common', 'technical'
    Supplier NVARCHAR(100),
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (ProductId) REFERENCES Products(ProductId)
);

-- Vector embeddings storage for fast similarity search
CREATE TABLE ProductEmbeddings (
    EmbeddingId INT PRIMARY KEY IDENTITY(1,1),
    ProductId INT NOT NULL,
    DescriptionId INT NULL,
    EmbeddingVector NVARCHAR(MAX) NOT NULL, -- JSON array of embedding values
    EmbeddingModel NVARCHAR(50) NOT NULL, -- 'text-embedding-ada-002', etc.
    CreatedAt DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (ProductId) REFERENCES Products(ProductId),
    FOREIGN KEY (DescriptionId) REFERENCES ProductDescriptions(DescriptionId)
);

-- Training data from manual corrections
CREATE TABLE ProductMatchingTraining (
    TrainingId INT PRIMARY KEY IDENTITY(1,1),
    InvoiceDescription NVARCHAR(500) NOT NULL,
    CorrectProductId INT NOT NULL,
    Confidence DECIMAL(5,4), -- AI confidence score 0-1
    IsUserCorrected BIT DEFAULT 0, -- True if user manually corrected
    InvoiceSupplier NVARCHAR(100),
    MatchedAt DATETIME2 DEFAULT GETUTCDATE(),
    CreatedBy NVARCHAR(100),
    FOREIGN KEY (CorrectProductId) REFERENCES Products(ProductId)
);

-- Indexes for performance
CREATE INDEX IX_Products_CategoryId ON Products(CategoryId);
CREATE INDEX IX_Products_ProductCode ON Products(ProductCode);
CREATE INDEX IX_ProductDescriptions_ProductId ON ProductDescriptions(ProductId);
CREATE INDEX IX_ProductDescriptions_Supplier ON ProductDescriptions(Supplier);
CREATE INDEX IX_ProductEmbeddings_ProductId ON ProductEmbeddings(ProductId);
CREATE INDEX IX_Training_InvoiceDescription ON ProductMatchingTraining(InvoiceDescription);
CREATE INDEX IX_Training_Supplier ON ProductMatchingTraining(InvoiceSupplier);

-- Sample data for testing
INSERT INTO Categories (CategoryName) VALUES 
    ('Building Materials'),
    ('Hardware'),
    ('Timber & Lumber'),
    ('Fasteners'),
    ('Tools'),
    ('Electrical'),
    ('Plumbing'),
    ('Paint & Finishes');

INSERT INTO Products (ProductCode, ProductName, StandardizedDescription, CategoryId, Brand, UnitOfMeasure, StandardPrice) VALUES 
    ('TMB001', 'Pine Timber Plank 90x45mm', 'Pine timber plank dressed all round 90x45mm treated', 3, 'Hyne', 'LM', 8.50),
    ('TMB002', 'Hardwood Timber Plank 70x35mm', 'Hardwood timber plank dressed 70x35mm spotted gum', 3, 'Boral', 'LM', 12.75),
    ('FST001', 'Galvanized Screws 75mm', 'Galvanized countersunk screws 75mm length', 4, 'Ramset', 'Box', 15.99),
    ('FST002', 'Stainless Steel Bolts M10', 'Stainless steel hex head bolts M10x50mm', 4, 'Zenith', 'Each', 2.45),
    ('HWR001', 'Hinges Heavy Duty 100mm', 'Heavy duty butt hinges 100mm stainless steel', 2, 'Lockwood', 'Pair', 24.50);

INSERT INTO ProductDescriptions (ProductId, AlternativeDescription, DescriptionType, Supplier) VALUES 
    (1, 'pine plank 90x45', 'invoice', 'Katoomba'),
    (1, 'timber 90 x 45 pine DAR', 'invoice', 'Bunnings'),
    (1, 'pine board 90*45mm treated', 'supplier', 'Hyne'),
    (2, 'hardwood 70x35 spotted gum', 'invoice', 'Katoomba'),
    (2, 'timber HW 70x35 SG', 'supplier', 'Boral'),
    (3, 'galv screws 75mm', 'invoice', 'Katoomba'),
    (3, 'countersunk galvanized 75', 'invoice', 'Bunnings'),
    (4, 'SS bolts M10x50', 'invoice', 'Katoomba'),
    (4, 'stainless hex bolt 10mm', 'invoice', 'Bunnings'),
    (5, 'heavy duty hinge 100', 'invoice', 'Katoomba');