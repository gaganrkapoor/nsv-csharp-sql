using Azure.Data.Tables;
using System.Text.Json;
using PdfToJsonFunctionApp.Models;
using Microsoft.Extensions.Logging;

namespace PdfToJsonFunctionApp.Services;

public class InvoiceTableStorageService
{
    private readonly TableClient _invoiceTableClient;
    private readonly TableClient _itemTableClient;
    private readonly ILogger _logger;
    private const string InvoiceTableName = "InvoiceResults";
    private const string ItemTableName = "InvoiceItems";

    public InvoiceTableStorageService(string connectionString, ILogger logger)
    {
        _logger = logger;
        
        // Create table service client
        var tableServiceClient = new TableServiceClient(connectionString);
        
        // Get table clients and create tables if they don't exist
        _invoiceTableClient = tableServiceClient.GetTableClient(InvoiceTableName);
        _invoiceTableClient.CreateIfNotExists();
        
        _itemTableClient = tableServiceClient.GetTableClient(ItemTableName);
        _itemTableClient.CreateIfNotExists();
        
        _logger.LogInformation($"Tables '{InvoiceTableName}' and '{ItemTableName}' are ready for use");
    }

    public async Task<bool> StoreInvoiceResultAsync(string fileName, InvoiceData invoiceData, 
        int pageCount, long fileSizeBytes, string? errorMessage = null)
    {
        try
        {
            // Create partition key (year-month format)
            var partitionKey = DateTime.UtcNow.ToString("yyyy-MM");
            
            // Create row key (filename + timestamp for uniqueness)
            var timestamp = DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
            var cleanFileName = Path.GetFileNameWithoutExtension(fileName);
            var rowKey = $"{cleanFileName}-{timestamp}";
            var invoiceId = $"{partitionKey}-{rowKey}"; // Unique identifier for linking items

            // Create invoice header entity
            var invoiceEntity = new InvoiceTableEntity
            {
                PartitionKey = partitionKey,
                RowKey = rowKey,
                FileName = fileName,
                Supplier = invoiceData.Supplier,
                InvoiceDate = invoiceData.InvoiceDate.HasValue ? 
                    DateTime.SpecifyKind(invoiceData.InvoiceDate.Value, DateTimeKind.Utc) : 
                    null,
                InvoiceTotal = invoiceData.InvoiceTotal,
                InvoiceTotalIncludingGST = invoiceData.InvoiceTotalIncludingGST,
                DiscountTotal = invoiceData.DiscountTotal,
                TaxGst = invoiceData.TaxGst,
                ItemCount = invoiceData.Items.Count,
                ProcessedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Utc),
                PageCount = pageCount,
                FileSizeBytes = fileSizeBytes,
                ProcessingStatus = string.IsNullOrEmpty(errorMessage) ? "Success" : "Error",
                ErrorMessage = errorMessage,
                ConfidenceScores = JsonSerializer.Serialize(invoiceData.FieldConfidenceScores)
            };

            // Insert invoice header
            await _invoiceTableClient.UpsertEntityAsync(invoiceEntity);

            // Store individual line items
            for (int i = 0; i < invoiceData.Items.Count; i++)
            {
                var item = invoiceData.Items[i];
                var itemEntity = new InvoiceItemTableEntity
                {
                    PartitionKey = invoiceId, // Use invoice ID as partition key to group items
                    RowKey = $"item-{i:D3}", // item-000, item-001, etc.
                    InvoiceFileName = fileName,
                    Supplier = invoiceData.Supplier,
                    InvoiceDate = invoiceData.InvoiceDate.HasValue ? 
                        DateTime.SpecifyKind(invoiceData.InvoiceDate.Value, DateTimeKind.Utc) : 
                        null,
                    ItemNo = item.ItemNo,
                    ItemDescription = item.ItemDescription,
                    ItemQuantity = item.ItemQuantity,
                    ItemUnit = item.ItemUnit,
                    ItemDiscountAmount = item.ItemDiscountAmount,
                    ItemDiscountPercent = item.ItemDiscountPercent,
                    CostPrice = item.CostPrice,
                    LineTotal = CalculateLineTotal(item),
                    ItemConfidenceScores = JsonSerializer.Serialize(item.FieldConfidenceScores),
                    ProcessedAt = DateTime.SpecifyKind(DateTime.UtcNow, DateTimeKind.Utc),
                    ItemSequence = i + 1
                };

                await _itemTableClient.UpsertEntityAsync(itemEntity);
            }

            _logger.LogInformation($"Successfully stored invoice result for {fileName} with {invoiceData.Items.Count} items in table storage");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error storing invoice result for {fileName}: {ex.Message}");
            return false;
        }
    }

    private decimal? CalculateLineTotal(InvoiceItem item)
    {
        if (!item.ItemQuantity.HasValue || !item.CostPrice.HasValue)
            return null;
            
        var subtotal = item.ItemQuantity.Value * item.CostPrice.Value;
        
        // Apply discount if available
        if (item.ItemDiscountAmount.HasValue)
        {
            subtotal -= item.ItemDiscountAmount.Value;
        }
        else if (item.ItemDiscountPercent.HasValue)
        {
            subtotal -= (subtotal * item.ItemDiscountPercent.Value / 100);
        }
        
        return subtotal;
    }

    public async Task<List<InvoiceTableEntity>> GetInvoicesBySupplierAsync(string supplier, int maxResults = 100)
    {
        try
        {
            var results = new List<InvoiceTableEntity>();
            
            // Query by supplier name
            var filter = TableClient.CreateQueryFilter($"Supplier eq {supplier}");
            
            await foreach (var entity in _invoiceTableClient.QueryAsync<InvoiceTableEntity>(filter))
            {
                results.Add(entity);
                if (results.Count >= maxResults)
                    break;
            }

            _logger.LogInformation($"Retrieved {results.Count} invoices for supplier: {supplier}");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving invoices for supplier {supplier}: {ex.Message}");
            return new List<InvoiceTableEntity>();
        }
    }

    public async Task<List<InvoiceItemTableEntity>> GetInvoiceItemsByInvoiceAsync(string partitionKey, string rowKey)
    {
        try
        {
            var results = new List<InvoiceItemTableEntity>();
            var invoiceId = $"{partitionKey}-{rowKey}";
            
            // Query items by invoice ID (partition key in items table)
            var filter = TableClient.CreateQueryFilter($"PartitionKey eq {invoiceId}");
            
            await foreach (var entity in _itemTableClient.QueryAsync<InvoiceItemTableEntity>(filter))
            {
                results.Add(entity);
            }

            // Sort by item sequence
            results = results.OrderBy(r => r.ItemSequence).ToList();

            _logger.LogInformation($"Retrieved {results.Count} items for invoice: {invoiceId}");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving items for invoice {partitionKey}-{rowKey}: {ex.Message}");
            return new List<InvoiceItemTableEntity>();
        }
    }

    public async Task<List<InvoiceItemTableEntity>> GetInvoiceItemsBySupplierAsync(string supplier, int maxResults = 100)
    {
        try
        {
            var results = new List<InvoiceItemTableEntity>();
            
            // Query items by supplier name
            var filter = TableClient.CreateQueryFilter($"Supplier eq {supplier}");
            
            await foreach (var entity in _itemTableClient.QueryAsync<InvoiceItemTableEntity>(filter))
            {
                results.Add(entity);
                if (results.Count >= maxResults)
                    break;
            }

            _logger.LogInformation($"Retrieved {results.Count} items for supplier: {supplier}");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving items for supplier {supplier}: {ex.Message}");
            return new List<InvoiceItemTableEntity>();
        }
    }

    public async Task<List<InvoiceItemTableEntity>> SearchItemsByDescriptionAsync(string descriptionKeyword, int maxResults = 100)
    {
        try
        {
            var results = new List<InvoiceItemTableEntity>();
            
            await foreach (var entity in _itemTableClient.QueryAsync<InvoiceItemTableEntity>())
            {
                if (!string.IsNullOrEmpty(entity.ItemDescription) && 
                    entity.ItemDescription.Contains(descriptionKeyword, StringComparison.OrdinalIgnoreCase))
                {
                    results.Add(entity);
                    if (results.Count >= maxResults)
                        break;
                }
            }

            _logger.LogInformation($"Retrieved {results.Count} items containing description keyword: {descriptionKeyword}");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error searching items by description {descriptionKeyword}: {ex.Message}");
            return new List<InvoiceItemTableEntity>();
        }
    }

    public async Task<List<InvoiceTableEntity>> GetInvoicesByDateRangeAsync(DateTime startDate, DateTime endDate, int maxResults = 100)
    {
        try
        {
            var results = new List<InvoiceTableEntity>();
            
            // Query by date range
            var filter = TableClient.CreateQueryFilter($"InvoiceDate ge {startDate:yyyy-MM-dd} and InvoiceDate le {endDate:yyyy-MM-dd}");
            
            await foreach (var entity in _invoiceTableClient.QueryAsync<InvoiceTableEntity>(filter))
            {
                results.Add(entity);
                if (results.Count >= maxResults)
                    break;
            }

            _logger.LogInformation($"Retrieved {results.Count} invoices between {startDate:yyyy-MM-dd} and {endDate:yyyy-MM-dd}");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving invoices by date range: {ex.Message}");
            return new List<InvoiceTableEntity>();
        }
    }

    public async Task<List<InvoiceTableEntity>> GetRecentInvoicesAsync(int maxResults = 50)
    {
        try
        {
            var results = new List<InvoiceTableEntity>();
            
            // Get recent invoices
            await foreach (var entity in _invoiceTableClient.QueryAsync<InvoiceTableEntity>())
            {
                results.Add(entity);
                if (results.Count >= maxResults)
                    break;
            }

            // Sort by ProcessedAt descending since Azure Tables doesn't guarantee order
            results = results.OrderByDescending(e => e.ProcessedAt).Take(maxResults).ToList();

            _logger.LogInformation($"Retrieved {results.Count} recent invoices");
            return results;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving recent invoices: {ex.Message}");
            return new List<InvoiceTableEntity>();
        }
    }

    public async Task<Dictionary<string, int>> GetSupplierStatisticsAsync()
    {
        try
        {
            var supplierCounts = new Dictionary<string, int>();
            
            await foreach (var entity in _invoiceTableClient.QueryAsync<InvoiceTableEntity>())
            {
                if (!string.IsNullOrEmpty(entity.Supplier))
                {
                    supplierCounts[entity.Supplier] = supplierCounts.GetValueOrDefault(entity.Supplier, 0) + 1;
                }
            }

            _logger.LogInformation($"Retrieved statistics for {supplierCounts.Count} suppliers");
            return supplierCounts;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error retrieving supplier statistics: {ex.Message}");
            return new Dictionary<string, int>();
        }
    }

    public async Task<bool> DeleteInvoiceAsync(string partitionKey, string rowKey)
    {
        try
        {
            // Delete invoice header
            await _invoiceTableClient.DeleteEntityAsync(partitionKey, rowKey);
            
            // Delete associated items
            var invoiceId = $"{partitionKey}-{rowKey}";
            var itemFilter = TableClient.CreateQueryFilter($"PartitionKey eq {invoiceId}");
            
            await foreach (var item in _itemTableClient.QueryAsync<InvoiceItemTableEntity>(itemFilter))
            {
                await _itemTableClient.DeleteEntityAsync(item.PartitionKey, item.RowKey);
            }
            
            _logger.LogInformation($"Successfully deleted invoice and items with PartitionKey: {partitionKey}, RowKey: {rowKey}");
            return true;
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error deleting invoice: {ex.Message}");
            return false;
        }
    }
}