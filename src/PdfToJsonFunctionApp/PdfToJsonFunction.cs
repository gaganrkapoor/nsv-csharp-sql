using System.IO;
using System.Threading.Tasks;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using Azure.Storage.Blobs;
using iText.Kernel.Pdf;
using iText.Kernel.Pdf.Canvas.Parser;
using iText.Kernel.Pdf.Canvas.Parser.Listener;
using System.Text.Json;

namespace PdfToJsonFunctionApp;

public class PdfToJsonFunction
{
    private readonly ILogger<PdfToJsonFunction> _logger;

    public PdfToJsonFunction(ILogger<PdfToJsonFunction> logger)
    {
        _logger = logger;
    }

    [Function(nameof(PdfToJsonFunction))]
    public async Task Run([BlobTrigger("samples-workitems/{name}", Connection = "AzureWebJobsStorage")] Stream stream, string name)
    {
        _logger.LogInformation($"Processing PDF blob: {name}, Size: {stream.Length} bytes");

        try
        {
            // Extract text from PDF
            string extractedText = ExtractTextFromPdf(stream);
            
            // Create JSON object
            var pdfData = new
            {
                FileName = name,
                ProcessedAt = DateTime.UtcNow,
                SizeBytes = stream.Length,
                ExtractedText = extractedText,
                PageCount = GetPageCount(stream),
                Metadata = new
                {
                    ProcessedBy = "PdfToJsonFunction",
                    Version = "1.0"
                }
            };

            // Convert to JSON
            string jsonContent = JsonSerializer.Serialize(pdfData, new JsonSerializerOptions 
            { 
                WriteIndented = true 
            });

            // Save to output container
            await SaveJsonToBlob(jsonContent, name);

            _logger.LogInformation($"Successfully processed {name} and saved JSON output");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error processing PDF {name}: {ex.Message}");
            throw;
        }
    }

    private string ExtractTextFromPdf(Stream pdfStream)
    {
        try
        {
            // Reset stream position
            pdfStream.Position = 0;
            
            using var pdfReader = new PdfReader(pdfStream);
            using var pdfDocument = new PdfDocument(pdfReader);
            
            var text = new System.Text.StringBuilder();
            
            for (int page = 1; page <= pdfDocument.GetNumberOfPages(); page++)
            {
                var pageText = PdfTextExtractor.GetTextFromPage(pdfDocument.GetPage(page));
                text.AppendLine($"--- Page {page} ---");
                text.AppendLine(pageText);
                text.AppendLine();
            }
            
            return text.ToString();
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error extracting text from PDF: {ex.Message}");
            return $"Error extracting text: {ex.Message}";
        }
    }

    private int GetPageCount(Stream pdfStream)
    {
        try
        {
            pdfStream.Position = 0;
            using var pdfReader = new PdfReader(pdfStream);
            using var pdfDocument = new PdfDocument(pdfReader);
            return pdfDocument.GetNumberOfPages();
        }
        catch
        {
            return 0;
        }
    }

    private async Task SaveJsonToBlob(string jsonContent, string originalFileName)
    {
        try
        {
            // Get connection string and output container name
            string connectionString = Environment.GetEnvironmentVariable("AzureWebJobsStorage") ?? "UseDevelopmentStorage=true";
            string outputContainer = Environment.GetEnvironmentVariable("OUTPUT_CONTAINER") ?? "json-output";

            // Create blob service client
            var blobServiceClient = new BlobServiceClient(connectionString);
            
            // Get container client (create if doesn't exist)
            var containerClient = blobServiceClient.GetBlobContainerClient(outputContainer);
            await containerClient.CreateIfNotExistsAsync();

            // Create JSON filename (replace .pdf with .json)
            string jsonFileName = Path.GetFileNameWithoutExtension(originalFileName) + ".json";
            
            // Upload JSON to blob
            var blobClient = containerClient.GetBlobClient(jsonFileName);
            
            using var jsonStream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(jsonContent));
            await blobClient.UploadAsync(jsonStream, overwrite: true);

            _logger.LogInformation($"JSON saved to {outputContainer}/{jsonFileName}");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error saving JSON to blob: {ex.Message}");
            throw;
        }
    }
}
