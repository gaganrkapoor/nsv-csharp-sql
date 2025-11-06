using System.Text.RegularExpressions;
using System.Globalization;
using FuzzySharp;
using PdfToJsonFunctionApp.Models;

namespace PdfToJsonFunctionApp.Services;

public class InvoiceFieldExtractor
{
    private readonly Dictionary<string, List<string>> _fieldPatterns = new();
    private readonly Dictionary<string, List<Regex>> _regexPatterns = new();
    
    public InvoiceFieldExtractor()
    {
        InitializeFieldPatterns();
        InitializeRegexPatterns();
    }

    private void InitializeFieldPatterns()
    {
        _fieldPatterns.Clear();
        _fieldPatterns["Supplier"] = new() { "supplier", "vendor", "company", "from", "bill from", "sold by", "invoice from" };
        _fieldPatterns["InvoiceDate"] = new() { "invoice date", "date", "bill date", "issued", "invoice #", "inv date" };
        _fieldPatterns["ItemNo"] = new() { "item no", "product code", "sku", "part no", "item code", "product id" };
        _fieldPatterns["ItemDescription"] = new() { "description", "item", "product", "service", "details", "particulars" };
        _fieldPatterns["ItemQuantity"] = new() { "qty", "quantity", "units", "count", "amount", "pieces" };
        _fieldPatterns["ItemUnit"] = new() { "unit", "uom", "measure", "each", "pcs", "kg", "lbs", "hrs" };
        _fieldPatterns["ItemDiscountAmount"] = new() { "discount", "discount amount", "disc amt", "savings", "reduction" };
        _fieldPatterns["ItemDiscountPercent"] = new() { "discount %", "disc %", "discount percent", "% off", "percentage" };
        _fieldPatterns["CostPrice"] = new() { "unit price", "price", "rate", "cost", "amount", "unit cost", "each" };
        _fieldPatterns["TaxGst"] = new() { "tax", "gst", "vat", "sales tax", "tax amount", "gst amount" };
        _fieldPatterns["InvoiceTotal"] = new() { "subtotal", "total", "amount", "sub total", "net amount", "total amount" };
        _fieldPatterns["InvoiceTotalIncludingGST"] = new() { "total inc gst", "grand total", "final total", "total including tax", "amount due" };
        _fieldPatterns["DiscountTotal"] = new() { "total discount", "total savings", "discount total", "total reduction" };
    }

    private void InitializeRegexPatterns()
    {
        _regexPatterns.Clear();
        _regexPatterns["InvoiceDate"] = new()
        {
            new Regex(@"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", RegexOptions.IgnoreCase),
            new Regex(@"\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{2,4}\b", RegexOptions.IgnoreCase),
            new Regex(@"\b\d{4}-\d{2}-\d{2}\b", RegexOptions.IgnoreCase)
        };
        _regexPatterns["Money"] = new()
        {
            new Regex(@"[\$£€¥]\s*\d+(?:\.\d{2})?", RegexOptions.IgnoreCase),
            new Regex(@"\d+\.\d{2}", RegexOptions.IgnoreCase),
            new Regex(@"\d+,\d{3}(?:\.\d{2})?", RegexOptions.IgnoreCase)
        };
        _regexPatterns["ItemNo"] = new()
        {
            new Regex(@"\b[A-Z0-9]{3,}\b", RegexOptions.IgnoreCase),
            new Regex(@"\b\d{4,}\b", RegexOptions.IgnoreCase)
        };
    }

    public InvoiceData ExtractInvoiceFields(string extractedText)
    {
        var lines = extractedText.Split('\n', StringSplitOptions.RemoveEmptyEntries);
        var invoiceData = new InvoiceData();
        var extractedFields = new List<ExtractedField>();

        // Extract header fields
        ExtractHeaderFields(lines, invoiceData, extractedFields);
        
        // Extract line items
        ExtractLineItems(lines, invoiceData, extractedFields);
        
        // Extract totals
        ExtractTotals(lines, invoiceData, extractedFields);

        return invoiceData;
    }

    private void ExtractHeaderFields(string[] lines, InvoiceData invoiceData, List<ExtractedField> extractedFields)
    {
        for (int i = 0; i < Math.Min(lines.Length, 20); i++) // Check first 20 lines for header info
        {
            var line = lines[i].Trim();
            if (string.IsNullOrEmpty(line)) continue;

            // Extract supplier
            if (string.IsNullOrEmpty(invoiceData.Supplier))
            {
                var supplierMatch = FindBestMatch(line, "Supplier");
                if (supplierMatch.ConfidenceScore > 0.6)
                {
                    invoiceData.Supplier = ExtractValueFromLine(line, supplierMatch.MatchedPattern);
                    invoiceData.FieldConfidenceScores["Supplier"] = supplierMatch.ConfidenceScore;
                    extractedFields.Add(new ExtractedField
                    {
                        FieldName = "Supplier",
                        Value = invoiceData.Supplier,
                        ConfidenceScore = supplierMatch.ConfidenceScore,
                        LineNumber = i + 1,
                        MatchedPattern = supplierMatch.MatchedPattern
                    });
                }
            }

            // Extract invoice date
            if (!invoiceData.InvoiceDate.HasValue)
            {
                var dateMatch = ExtractDate(line);
                if (dateMatch.HasValue)
                {
                    invoiceData.InvoiceDate = dateMatch.Value;
                    invoiceData.FieldConfidenceScores["InvoiceDate"] = 0.9;
                    extractedFields.Add(new ExtractedField
                    {
                        FieldName = "InvoiceDate",
                        Value = dateMatch.Value.ToString("yyyy-MM-dd"),
                        ConfidenceScore = 0.9,
                        LineNumber = i + 1
                    });
                }
            }
        }
    }

    private void ExtractLineItems(string[] lines, InvoiceData invoiceData, List<ExtractedField> extractedFields)
    {
        var itemLines = new List<string>();
        bool inItemSection = false;

        // Find item section
        for (int i = 0; i < lines.Length; i++)
        {
            var line = lines[i].Trim();
            if (string.IsNullOrEmpty(line)) continue;

            // Check if this line contains item headers
            var itemHeaderScore = CalculateItemHeaderScore(line);
            if (itemHeaderScore > 0.7)
            {
                inItemSection = true;
                continue;
            }

            // Check if we've reached totals section
            if (inItemSection && ContainsTotalKeywords(line))
            {
                break;
            }

            if (inItemSection)
            {
                itemLines.Add(line);
            }
        }

        // Parse item lines
        foreach (var line in itemLines)
        {
            var item = ParseItemLine(line);
            if (item != null)
            {
                invoiceData.Items.Add(item);
            }
        }
    }

    private void ExtractTotals(string[] lines, InvoiceData invoiceData, List<ExtractedField> extractedFields)
    {
        // Look for totals in the last 10 lines
        for (int i = Math.Max(0, lines.Length - 10); i < lines.Length; i++)
        {
            var line = lines[i].Trim();
            if (string.IsNullOrEmpty(line)) continue;

            // Extract various total fields
            ExtractTotalField(line, "InvoiceTotal", invoiceData, extractedFields, i);
            ExtractTotalField(line, "InvoiceTotalIncludingGST", invoiceData, extractedFields, i);
            ExtractTotalField(line, "DiscountTotal", invoiceData, extractedFields, i);
            ExtractTotalField(line, "TaxGst", invoiceData, extractedFields, i);
        }
    }

    private void ExtractTotalField(string line, string fieldName, InvoiceData invoiceData, List<ExtractedField> extractedFields, int lineNumber)
    {
        var match = FindBestMatch(line, fieldName);
        if (match.ConfidenceScore > 0.7)
        {
            var value = ExtractMonetaryValue(line);
            if (value.HasValue)
            {
                switch (fieldName)
                {
                    case "InvoiceTotal":
                        invoiceData.InvoiceTotal = value;
                        break;
                    case "InvoiceTotalIncludingGST":
                        invoiceData.InvoiceTotalIncludingGST = value;
                        break;
                    case "DiscountTotal":
                        invoiceData.DiscountTotal = value;
                        break;
                    case "TaxGst":
                        invoiceData.TaxGst = value;
                        break;
                }

                invoiceData.FieldConfidenceScores[fieldName] = match.ConfidenceScore;
                extractedFields.Add(new ExtractedField
                {
                    FieldName = fieldName,
                    Value = value.ToString(),
                    ConfidenceScore = match.ConfidenceScore,
                    LineNumber = lineNumber + 1,
                    MatchedPattern = match.MatchedPattern
                });
            }
        }
    }

    private (double ConfidenceScore, string MatchedPattern) FindBestMatch(string text, string fieldName)
    {
        if (!_fieldPatterns.ContainsKey(fieldName))
            return (0, string.Empty);

        double bestScore = 0;
        string bestPattern = string.Empty;

        foreach (var pattern in _fieldPatterns[fieldName])
        {
            var score = Fuzz.PartialRatio(text.ToLower(), pattern.ToLower()) / 100.0;
            if (score > bestScore)
            {
                bestScore = score;
                bestPattern = pattern;
            }
        }

        return (bestScore, bestPattern);
    }

    private double CalculateItemHeaderScore(string line)
    {
        var itemHeaderKeywords = new[] { "description", "qty", "price", "amount", "item", "product" };
        int matches = 0;
        
        foreach (var keyword in itemHeaderKeywords)
        {
            if (line.ToLower().Contains(keyword))
                matches++;
        }
        
        return (double)matches / itemHeaderKeywords.Length;
    }

    private bool ContainsTotalKeywords(string line)
    {
        var totalKeywords = new[] { "total", "subtotal", "grand total", "amount due" };
        return totalKeywords.Any(keyword => line.ToLower().Contains(keyword));
    }

    private InvoiceItem? ParseItemLine(string line)
    {
        // This is a simplified parser - you may need to enhance based on your specific formats
        var parts = line.Split(new[] { '\t', ' ' }, StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length < 3) return null;

        var item = new InvoiceItem();
        
        // Try to identify columns based on patterns
        for (int i = 0; i < parts.Length; i++)
        {
            var part = parts[i];
            
            // Try to match item number pattern
            if (string.IsNullOrEmpty(item.ItemNo) && Regex.IsMatch(part, @"^[A-Z0-9]{3,}$"))
            {
                item.ItemNo = part;
                item.FieldConfidenceScores["ItemNo"] = 0.8;
            }
            
            // Try to match quantity
            if (!item.ItemQuantity.HasValue && decimal.TryParse(part, out var qty) && qty > 0 && qty < 10000)
            {
                item.ItemQuantity = qty;
                item.FieldConfidenceScores["ItemQuantity"] = 0.9;
            }
            
            // Try to match price
            if (!item.CostPrice.HasValue)
            {
                var price = ExtractMonetaryValue(part);
                if (price.HasValue)
                {
                    item.CostPrice = price;
                    item.FieldConfidenceScores["CostPrice"] = 0.8;
                }
            }
        }
        
        // Description is usually the longest non-numeric part
        var descriptionCandidate = parts.Where(p => !decimal.TryParse(p, out _) && p.Length > 3)
                                       .OrderByDescending(p => p.Length)
                                       .FirstOrDefault();
        if (!string.IsNullOrEmpty(descriptionCandidate))
        {
            item.ItemDescription = descriptionCandidate;
            item.FieldConfidenceScores["ItemDescription"] = 0.7;
        }

        return item.ItemNo != null || item.ItemDescription != null ? item : null;
    }

    private string ExtractValueFromLine(string line, string pattern)
    {
        // Remove the pattern and return the remaining text
        var index = line.ToLower().IndexOf(pattern.ToLower());
        if (index >= 0)
        {
            return line.Substring(index + pattern.Length).Trim(' ', ':', '-', '\t');
        }
        return line.Trim();
    }

    private DateTime? ExtractDate(string text)
    {
        foreach (var regex in _regexPatterns["InvoiceDate"])
        {
            var match = regex.Match(text);
            if (match.Success)
            {
                if (DateTime.TryParse(match.Value, out var date))
                {
                    // Ensure the DateTime has UTC kind for Azure Table Storage compatibility
                    // If the parsed date has Unspecified kind, treat it as local time and convert to UTC
                    if (date.Kind == DateTimeKind.Unspecified)
                    {
                        // Assume local time and convert to UTC
                        date = DateTime.SpecifyKind(date, DateTimeKind.Local).ToUniversalTime();
                    }
                    else if (date.Kind == DateTimeKind.Local)
                    {
                        date = date.ToUniversalTime();
                    }
                    else
                    {
                        // Already UTC, ensure it's marked as such
                        date = DateTime.SpecifyKind(date, DateTimeKind.Utc);
                    }
                    
                    return date;
                }
            }
        }
        return null;
    }

    private decimal? ExtractMonetaryValue(string text)
    {
        foreach (var regex in _regexPatterns["Money"])
        {
            var match = regex.Match(text);
            if (match.Success)
            {
                var cleanValue = match.Value.Replace("$", "").Replace("£", "").Replace("€", "").Replace("¥", "").Replace(",", "");
                if (decimal.TryParse(cleanValue, out var value))
                {
                    return value;
                }
            }
        }
        return null;
    }
}