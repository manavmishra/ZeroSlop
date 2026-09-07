import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.concurrent.TimeUnit;

public class Deslop {
    private static final ObjectMapper JSON = new ObjectMapper();

    private static boolean approved(JsonNode result) {
        String[] fields = {"text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
            "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"};
        for (String field : fields) if (!result.has(field)) return false;
        JsonNode before = result.path("before").path("score"), after = result.path("after").path("score");
        if (!result.path("text").isTextual() || !result.path("passedFinalChecks").isBoolean() ||
            !before.isNumber() || !after.isNumber() || !Double.isFinite(before.asDouble()) || !Double.isFinite(after.asDouble()) ||
            before.asDouble() < 0 || before.asDouble() > 100 || after.asDouble() < 0 || after.asDouble() > 100 ||
            !result.path("factsPreserved").isBoolean() || !result.path("factsPreserved").booleanValue()) return false;
        String status = result.path("status").asText();
        return (status.equals("rewritten") && result.path("passedFinalChecks").booleanValue()) ||
            (status.equals("already_clear") && result.path("modelRequests").isIntegralNumber() &&
             result.path("modelRequests").asLong() == 0 && result.path("scoreChange").isNumber() &&
             result.path("scoreChange").asDouble() == 0 && before.asDouble() == after.asDouble());
    }

    private static int run() throws Exception {
        String input = new String(System.in.readAllBytes(), StandardCharsets.UTF_8);
        JSON.readTree(input);
        String endpoint = System.getenv().getOrDefault("ZERO_SLOP_API_URL", "https://mcp.zero-slop.ai/v1/deslop");
        HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(10))
            .followRedirects(HttpClient.Redirect.NEVER).build();
        HttpRequest request = HttpRequest.newBuilder(URI.create(endpoint)).timeout(Duration.ofSeconds(75))
            .header("Content-Type", "application/json").header("Accept", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(input, StandardCharsets.UTF_8)).build();
        HttpResponse<String> response = client.sendAsync(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8))
            .get(75, TimeUnit.SECONDS);
        JsonNode result = JSON.readTree(response.body());
        if (response.statusCode() != 200) {
            var error = new LinkedHashMap<String, Object>();
            error.put("httpStatus", response.statusCode());
            error.put("retryAfter", response.headers().firstValue("Retry-After").orElse(null));
            error.put("problem", result);
            System.err.println(JSON.writeValueAsString(error));
            return 1;
        }
        System.out.println(response.body());
        if (!approved(result)) {
            System.err.println("Review required. Keep the original until the result has been reviewed.");
            return 3;
        }
        return 0;
    }

    public static void main(String[] args) {
        try { System.exit(run()); }
        catch (Exception error) {
            System.err.println("Request failed or response was not JSON. No automatic retry; the outcome may be unknown.");
            System.exit(1);
        }
    }
}
