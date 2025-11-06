using Azure.Data.Tables;
using System.Text.Json;
using PdfToJsonFunctionApp.Models;
using PdfToJsonFunctionApp.Services;
using Microsoft.Extensions.Logging;

namespace PdfToJsonFunctionApp;

/// <summary>
/// Simple utility class to view invoice data stored in Azure Table Storage
/// This can be used to query and display ItemDescription and other columns
/// </summary>
public class TableStorageViewer
{
    private readonly InvoiceTableStorageService _tableService;
    private readonly ILogger _logger;

    public TableStorageViewer(string connectionString, ILogger logger)
    {
        _logger = logger;
        _tableService = new InvoiceTableStorageService(connectionString, logger);
    }

    /// <summary>
    /// Display all invoices with their basic information
    /// </summary>
    public async Task DisplayAllInvoicesAsync()
    {
        Console.WriteLine("\n=== ALL INVOICES ===");
        var invoices = await _tableService.GetRecentInvoicesAsync(100);
        
        if (!invoices.Any())
        {
            Console.WriteLine("No invoices found.");
            return;
        }

        Console.WriteLine($"{"Invoice File",-20} {"Supplier",-15} {"Date",-12} {"Total",-10} {"Items",-5}");
        Console.WriteLine(new string('-', 70));
        
        foreach (var invoice in invoices)
        {
            Console.WriteLine($"{invoice.FileName,-20} {invoice.Supplier,-15} {invoice.InvoiceDate?.ToString("yyyy-MM-dd"),-12} {invoice.InvoiceTotal,-10:C} {invoice.ItemCount,-5}");
        }
    }

    /// <summary>
    /// Display detailed item information for all invoices
    /// This shows ItemDescription and all other item fields
    /// </summary>
    public async Task DisplayAllItemsWithDetailsAsync()
    {
        Console.WriteLine("\n=== ALL INVOICE ITEMS WITH DETAILS ===");
        var invoices = await _tableService.GetRecentInvoicesAsync(50);
        
        foreach (var invoice in invoices)
        {
            Console.WriteLine($"\n--- Invoice: {invoice.FileName} | Supplier: {invoice.Supplier} ---");
            
            var items = await _tableService.GetInvoiceItemsByInvoiceAsync(invoice.PartitionKey, invoice.RowKey);
            
            if (!items.Any())
            {
                Console.WriteLine("  No items found for this invoice.");
                continue;
            }

            Console.WriteLine($"  {"#",-3} {"Item No",-10} {"Description",-30} {"Qty",-5} {"Unit",-6} {"Price",-8} {"Total",-8}");
            Console.WriteLine($"  {new string('-', 75)}");
            
            foreach (var item in items)
            {
                var description = item.ItemDescription?.Length > 28 ? 
                    item.ItemDescription.Substring(0, 25) + "..." : 
                    item.ItemDescription ?? "N/A";
                    
                Console.WriteLine($"  {item.ItemSequence,-3} {item.ItemNo,-10} {description,-30} {item.ItemQuantity,-5} {item.ItemUnit,-6} {item.CostPrice,-8:C} {item.LineTotal,-8:C}");
            }
        }
    }

    /// <summary>
    /// Search items by description keyword
    /// </summary>
    public async Task SearchItemsByDescriptionAsync(string keyword)
    {
        Console.WriteLine($"\n=== ITEMS CONTAINING '{keyword}' ===");
        var items = await _tableService.SearchItemsByDescriptionAsync(keyword, 50);
        
        if (!items.Any())
        {
            Console.WriteLine($"No items found containing '{keyword}'.");
            return;
        }

        Console.WriteLine($"{"Invoice",-15} {"Supplier",-15} {"Item No",-10} {"Description",-35} {"Qty",-5} {"Price",-8}");
        Console.WriteLine(new string('-', 95));
        
        foreach (var item in items)
        {
            var description = item.ItemDescription?.Length > 33 ? 
                item.ItemDescription.Substring(0, 30) + "..." : 
                item.ItemDescription ?? "N/A";
                
            Console.WriteLine($"{Path.GetFileNameWithoutExtension(item.InvoiceFileName),-15} {item.Supplier,-15} {item.ItemNo,-10} {description,-35} {item.ItemQuantity,-5} {item.CostPrice,-8:C}");
        }
    }

    /// <summary>
    /// Display items for a specific supplier
    /// </summary>
    public async Task DisplayItemsBySupplierAsync(string supplier)
    {
        Console.WriteLine($"\n=== ITEMS FROM SUPPLIER: {supplier} ===");
        var items = await _tableService.GetInvoiceItemsBySupplierAsync(supplier, 100);
        
        if (!items.Any())
        {
            Console.WriteLine($"No items found for supplier '{supplier}'.");
            return;
        }

        Console.WriteLine($"{"Invoice Date",-12} {"Item No",-10} {"Description",-40} {"Qty",-5} {"Price",-8}");
        Console.WriteLine(new string('-', 85));
        
        foreach (var item in items.OrderByDescending(i => i.InvoiceDate))
        {
            var description = item.ItemDescription?.Length > 38 ? 
                item.ItemDescription.Substring(0, 35) + "..." : 
                item.ItemDescription ?? "N/A";
                
            Console.WriteLine($"{item.InvoiceDate?.ToString("yyyy-MM-dd"),-12} {item.ItemNo,-10} {description,-40} {item.ItemQuantity,-5} {item.CostPrice,-8:C}");
        }
    }

    /// <summary>
    /// Display confidence scores for field extraction quality analysis
    /// </summary>
    public async Task DisplayConfidenceScoresAsync()
    {
        Console.WriteLine("\n=== FIELD EXTRACTION CONFIDENCE SCORES ===");
        var invoices = await _tableService.GetRecentInvoicesAsync(10);
        
        foreach (var invoice in invoices)
        {
            Console.WriteLine($"\n--- {invoice.FileName} ---");
            
            if (!string.IsNullOrEmpty(invoice.ConfidenceScores))
            {
                try
                {
                    var scores = JsonSerializer.Deserialize<Dictionary<string, double>>(invoice.ConfidenceScores);
                    if (scores != null)
                    {
                        Console.WriteLine("Header Fields:");
                        foreach (var score in scores.OrderByDescending(s => s.Value))
                        {
                            var confidenceLevel = score.Value switch
                            {
                                >= 0.9 => "HIGH",
                                >= 0.7 => "GOOD",
                                >= 0.6 => "MODERATE",
                                _ => "LOW"
                            };
                            Console.WriteLine($"  {score.Key}: {score.Value:P1} ({confidenceLevel})");
                        }
                    }
                }
                catch (JsonException)
                {
                    Console.WriteLine("  Unable to parse confidence scores");
                }
            }

            // Show item confidence scores
            var items = await _tableService.GetInvoiceItemsByInvoiceAsync(invoice.PartitionKey, invoice.RowKey);
            if (items.Any())
            {
                Console.WriteLine("Item Fields (average confidence):");
                var allItemScores = new Dictionary<string, List<double>>();
                
                foreach (var item in items)
                {
                    if (!string.IsNullOrEmpty(item.ItemConfidenceScores))
                    {
                        try
                        {
                            var itemScores = JsonSerializer.Deserialize<Dictionary<string, double>>(item.ItemConfidenceScores);
                            if (itemScores != null)
                            {
                                foreach (var score in itemScores)
                                {
                                    if (!allItemScores.ContainsKey(score.Key))
                                        allItemScores[score.Key] = new List<double>();
                                    allItemScores[score.Key].Add(score.Value);
                                }
                            }
                        }
                        catch (JsonException) { }
                    }
                }
                
                foreach (var fieldScores in allItemScores.OrderByDescending(s => s.Value.Average()))
                {
                    var avgScore = fieldScores.Value.Average();
                    var confidenceLevel = avgScore switch
                    {
                        >= 0.9 => "HIGH",
                        >= 0.7 => "GOOD",
                        >= 0.6 => "MODERATE",
                        _ => "LOW"
                    };
                    Console.WriteLine($"  {fieldScores.Key}: {avgScore:P1} ({confidenceLevel}) [{fieldScores.Value.Count} items]");
                }
            }
        }
    }
}