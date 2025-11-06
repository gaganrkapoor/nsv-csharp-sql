using System.IO;
using System.Threading.Tasks;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;

namespace PdfToJsonFunctionApp;

public class PdfToJsonFunction
{
    private readonly ILogger<PdfToJsonFunction> _logger;

    public PdfToJsonFunction(ILogger<PdfToJsonFunction> logger)
    {
        _logger = logger;
    }

    [Function(nameof(PdfToJsonFunction))]
    public async Task Run([BlobTrigger("samples-workitems/{name}", Connection = "")] Stream stream, string name)
    {
        using var blobStreamReader = new StreamReader(stream);
        var content = await blobStreamReader.ReadToEndAsync();
        _logger.LogInformation("C# Blob trigger function Processed blob\n Name: {name} \n Data: {content}", name, content);
    }
}
