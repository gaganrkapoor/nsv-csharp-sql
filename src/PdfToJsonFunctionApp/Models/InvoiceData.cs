using System.Text.Json.Serialization;
using Azure;
using Azure.Data.Tables;

namespace PdfToJsonFunctionApp.Models;

public class InvoiceData
{
    public string? Supplier { get; set; }
    public DateTime? InvoiceDate { get; set; }
    public List<InvoiceItem> Items { get; set; } = new();
    public decimal? InvoiceTotal { get; set; }
    public decimal? InvoiceTotalIncludingGST { get; set; }
    public decimal? DiscountTotal { get; set; }
    public decimal? TaxGst { get; set; }
    
    [JsonIgnore]
    public Dictionary<string, double> FieldConfidenceScores { get; set; } = new();
}

public class InvoiceItem
{
    public string? ItemNo { get; set; }
    public string? ItemDescription { get; set; }
    public decimal? ItemQuantity { get; set; }
    public string? ItemUnit { get; set; }
    public decimal? ItemDiscountAmount { get; set; }
    public decimal? ItemDiscountPercent { get; set; }
    public decimal? CostPrice { get; set; }
    
    [JsonIgnore]
    public Dictionary<string, double> FieldConfidenceScores { get; set; } = new();
}

public class ExtractedField
{
    public string FieldName { get; set; } = string.Empty;
    public string Value { get; set; } = string.Empty;
    public double ConfidenceScore { get; set; }
    public string MatchedPattern { get; set; } = string.Empty;
    public int LineNumber { get; set; }
}

// Table entity for storing invoice results in Azure Table Storage
public class InvoiceTableEntity : ITableEntity
{
    public string PartitionKey { get; set; } = string.Empty; // Will use year-month (e.g., "2025-11")
    public string RowKey { get; set; } = string.Empty; // Will use filename + timestamp
    public DateTimeOffset? Timestamp { get; set; }
    public ETag ETag { get; set; }
    
    // Invoice fields
    public string? FileName { get; set; }
    public string? Supplier { get; set; }
    public DateTime? InvoiceDate { get; set; }
    public decimal? InvoiceTotal { get; set; }
    public decimal? InvoiceTotalIncludingGST { get; set; }
    public decimal? DiscountTotal { get; set; }
    public decimal? TaxGst { get; set; }
    public int ItemCount { get; set; }
    public DateTime ProcessedAt { get; set; }
    
    // Confidence scores (stored as JSON string)
    public string? ConfidenceScores { get; set; }
    
    // Additional metadata
    public int PageCount { get; set; }
    public long FileSizeBytes { get; set; }
    public string? ProcessingStatus { get; set; } = "Success";
    public string? ErrorMessage { get; set; }
}

// Table entity for storing individual line items
public class InvoiceItemTableEntity : ITableEntity
{
    public string PartitionKey { get; set; } = string.Empty; // Will use invoice identifier (filename + timestamp)
    public string RowKey { get; set; } = string.Empty; // Will use item sequence number
    public DateTimeOffset? Timestamp { get; set; }
    public ETag ETag { get; set; }
    
    // Link to parent invoice
    public string? InvoiceFileName { get; set; }
    public string? Supplier { get; set; }
    public DateTime? InvoiceDate { get; set; }
    
    // Item fields
    public string? ItemNo { get; set; }
    public string? ItemDescription { get; set; }
    public decimal? ItemQuantity { get; set; }
    public string? ItemUnit { get; set; }
    public decimal? ItemDiscountAmount { get; set; }
    public decimal? ItemDiscountPercent { get; set; }
    public decimal? CostPrice { get; set; }
    
    // Item total (calculated)
    public decimal? LineTotal { get; set; }
    
    // Confidence scores for this item (stored as JSON string)
    public string? ItemConfidenceScores { get; set; }
    
    // Processing metadata
    public DateTime ProcessedAt { get; set; }
    public int ItemSequence { get; set; }
}