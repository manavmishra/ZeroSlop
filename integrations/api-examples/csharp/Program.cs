using System.Net;
using System.Text;
using System.Text.Json;

static bool Approved(JsonElement result)
{
    string[] fields = ["text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
        "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"];
    if (result.ValueKind != JsonValueKind.Object || fields.Any(field => !result.TryGetProperty(field, out _))) return false;
    var before = result.GetProperty("before");
    var after = result.GetProperty("after");
    if (before.ValueKind != JsonValueKind.Object || after.ValueKind != JsonValueKind.Object ||
        !before.TryGetProperty("score", out var beforeValue) || !after.TryGetProperty("score", out var afterValue) ||
        beforeValue.ValueKind != JsonValueKind.Number || afterValue.ValueKind != JsonValueKind.Number ||
        !beforeValue.TryGetDouble(out var beforeScore) || !afterValue.TryGetDouble(out var afterScore) ||
        !double.IsFinite(beforeScore) || !double.IsFinite(afterScore) || beforeScore < 0 || beforeScore > 100 || afterScore < 0 || afterScore > 100) return false;
    var passed = result.GetProperty("passedFinalChecks");
    if (result.GetProperty("text").ValueKind != JsonValueKind.String ||
        result.GetProperty("status").ValueKind != JsonValueKind.String ||
        passed.ValueKind is not (JsonValueKind.True or JsonValueKind.False) ||
        result.GetProperty("factsPreserved").ValueKind != JsonValueKind.True) return false;
    var status = result.GetProperty("status").GetString();
    if (status == "rewritten") return passed.ValueKind == JsonValueKind.True;
    var requests = result.GetProperty("modelRequests");
    var change = result.GetProperty("scoreChange");
    return status == "already_clear" && requests.ValueKind == JsonValueKind.Number && requests.TryGetInt32(out var count) && count == 0 &&
        change.ValueKind == JsonValueKind.Number && change.TryGetDouble(out var delta) && delta == 0 && beforeScore == afterScore;
}

try
{
    string input = await Console.In.ReadToEndAsync();
    using var requestJson = JsonDocument.Parse(input);
    using var handler = new HttpClientHandler { AllowAutoRedirect = false };
    using var client = new HttpClient(handler) { Timeout = TimeSpan.FromSeconds(75) };
    using var request = new HttpRequestMessage(HttpMethod.Post,
        Environment.GetEnvironmentVariable("ZERO_SLOP_API_URL") ?? "https://mcp.zero-slop.ai/v1/deslop");
    request.Content = new StringContent(input, Encoding.UTF8, "application/json");
    request.Headers.Accept.ParseAdd("application/json");
    using var response = await client.SendAsync(request); // Default completion includes the response body.
    string body = await response.Content.ReadAsStringAsync();
    using var document = JsonDocument.Parse(body);
    if (response.StatusCode != HttpStatusCode.OK)
    {
        string? retryAfter = response.Headers.TryGetValues("Retry-After", out var values) ? string.Join(", ", values) : null;
        Console.Error.WriteLine(JsonSerializer.Serialize(new { httpStatus = (int)response.StatusCode, retryAfter, problem = document.RootElement }));
        return 1;
    }
    Console.WriteLine(body);
    if (!Approved(document.RootElement))
    {
        Console.Error.WriteLine("Review required. Keep the original until the result has been reviewed.");
        return 3;
    }
    return 0;
}
catch
{
    Console.Error.WriteLine("Request failed or response was not JSON. No automatic retry; the outcome may be unknown.");
    return 1;
}
