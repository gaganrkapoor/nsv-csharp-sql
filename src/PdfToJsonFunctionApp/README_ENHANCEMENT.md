# PDF to JSON Invoice Processing Enhancement

## Overview
Enhanced the Azure Function to extract specific invoice fields using fuzzy matching with confidence scores and AI learning capabilities. The solution now stores results in Azure Table Storage for analysis and learning.

## Key Features Implemented

### 1. **Comprehensive Field Extraction**
The system now extracts the following fields from invoices:
- **Header Fields**: Supplier, Invoice Date
- **Line Item Fields**: Item Number, Item Description, Item Quantity, Item Unit, Item Discount Amount, Item Discount Percent, Cost Price
- **Total Fields**: Tax/GST, Invoice Total, Invoice Total Including GST, Discount Total

### 2. **Fuzzy Matching with Confidence Scores**
- Uses FuzzySharp library for flexible text matching
- Each extracted field includes a confidence score (0.0 to 1.0)
- Multiple pattern variations for each field type
- Configurable confidence thresholds for field acceptance

### 3. **Azure Table Storage Integration**
- Stores all processing results in Azure Table Storage (Azurite for local development)
- Table name: `InvoiceResults`
- Partition key: Year-Month format (e.g., "2025-11")
- Row key: Filename + timestamp for uniqueness
- Includes metadata: file size, page count, processing status, confidence scores

### 4. **AI Learning Capabilities**
- Stores extraction patterns and confidence scores for analysis
- Enables iterative improvement of extraction algorithms
- Historical data for pattern learning and validation

## Files Created/Modified

### New Files Created:
1. **Models/InvoiceData.cs** - Data models for invoice structure and table entities
2. **Services/InvoiceFieldExtractor.cs** - Fuzzy matching and field extraction logic
3. **Services/InvoiceTableStorageService.cs** - Azure Table Storage operations

### Modified Files:
1. **PdfToJsonFunction.cs** - Updated to use new extraction service and table storage
2. **PdfToJsonFunctionApp.csproj** - Added FuzzySharp and Azure.Data.Tables packages

## Key Components

### InvoiceFieldExtractor
- **Pattern Matching**: Uses predefined patterns for each field type
- **Regex Patterns**: Date formats, monetary values, item numbers
- **Confidence Scoring**: Fuzzy matching confidence for each extracted field
- **Line Item Parsing**: Intelligent parsing of tabular invoice data

### InvoiceTableStorageService
- **Data Storage**: Stores invoice results with supplier and date indexing
- **Query Methods**: Retrieve by supplier, date range, recent invoices
- **Statistics**: Supplier statistics and processing analytics
- **Error Handling**: Robust error handling and logging

### Table Structure
```
PartitionKey: YYYY-MM (e.g., "2025-11")
RowKey: filename-timestamp (e.g., "invoice001-20251106-143020")
Fields: Supplier, InvoiceDate, InvoiceTotal, ItemCount, ConfidenceScores, etc.
```

## Usage

### Local Development with Azurite
1. Ensure Azurite is running
2. Function will automatically create the `InvoiceResults` table
3. Connection string uses "UseDevelopmentStorage=true"

### Field Extraction Process
1. PDF text extraction using iText7
2. Field pattern matching with fuzzy logic
3. Confidence scoring for each extracted field
4. Line item parsing and validation
5. Storage in both JSON blob and table storage

### Confidence Score Interpretation
- **0.9-1.0**: High confidence (e.g., exact date matches)
- **0.7-0.9**: Good confidence (e.g., fuzzy field matches)
- **0.6-0.7**: Moderate confidence (requires review)
- **<0.6**: Low confidence (likely false positive)

## Learning and Improvement Opportunities

1. **Pattern Enhancement**: Add new patterns based on processed invoices
2. **Confidence Tuning**: Adjust thresholds based on accuracy analysis
3. **Machine Learning**: Train models on historical extraction data
4. **Validation Rules**: Implement business logic validation
5. **Feedback Loop**: Manual corrections to improve future extractions

## Configuration Options

### Environment Variables
- `AzureWebJobsStorage`: Connection string for blob and table storage
- `OUTPUT_CONTAINER`: Container name for JSON output (default: "json-output")

### Customizable Patterns
Field patterns and confidence thresholds can be easily modified in `InvoiceFieldExtractor.cs`

## Monitoring and Analytics

The solution provides comprehensive logging:
- Processing success/failure rates
- Field extraction confidence scores
- Performance metrics
- Error tracking and analysis

## Next Steps for AI Enhancement

1. **Data Analysis**: Analyze stored confidence scores and extraction patterns
2. **Model Training**: Use historical data to train ML models
3. **Pattern Learning**: Automatically discover new extraction patterns
4. **Validation Rules**: Implement cross-field validation logic
5. **Feedback Integration**: Allow manual corrections to improve accuracy