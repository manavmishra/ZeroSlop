// One REST request using only the Go standard library.
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "os"
    "time"
)

func approved(r map[string]any) bool {
    for _, key := range []string{"text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
        "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"} {
        if _, exists := r[key]; !exists { return false }
    }
    before, beforeOK := r["before"].(map[string]any)
    after, afterOK := r["after"].(map[string]any)
    if !beforeOK || !afterOK { return false }
    beforeScore, beforeNumber := before["score"].(float64)
    afterScore, afterNumber := after["score"].(float64)
    _, textOK := r["text"].(string)
    passed, passedOK := r["passedFinalChecks"].(bool)
    facts, factsOK := r["factsPreserved"].(bool)
    if !textOK || !passedOK || !factsOK || !facts || !beforeNumber || !afterNumber ||
        beforeScore < 0 || beforeScore > 100 || afterScore < 0 || afterScore > 100 { return false }
    requests, requestsOK := r["modelRequests"].(float64)
    change, changeOK := r["scoreChange"].(float64)
    return (r["status"] == "rewritten" && passed) ||
        (r["status"] == "already_clear" && requestsOK && requests == 0 && changeOK && change == 0 && beforeScore == afterScore)
}

func run() int {
    requestBody, err := io.ReadAll(os.Stdin)
    if err != nil || !json.Valid(requestBody) { fmt.Fprintln(os.Stderr, "Supply one UTF-8 JSON request on stdin."); return 1 }
    endpoint := os.Getenv("ZERO_SLOP_API_URL")
    if endpoint == "" { endpoint = "https://mcp.zero-slop.ai/v1/deslop" }
    request, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(requestBody))
    if err != nil { fmt.Fprintln(os.Stderr, "Invalid endpoint."); return 1 }
    request.Header.Set("Content-Type", "application/json")
    request.Header.Set("Accept", "application/json")
    client := &http.Client{Timeout: 75 * time.Second, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
    response, err := client.Do(request)
    if err != nil { fmt.Fprintln(os.Stderr, "Request failed. No automatic retry; the outcome may be unknown."); return 1 }
    defer response.Body.Close()
    body, err := io.ReadAll(response.Body)
    var result map[string]any
    if err != nil || json.Unmarshal(body, &result) != nil { fmt.Fprintln(os.Stderr, "Response was not a JSON object. No automatic retry."); return 1 }
    if response.StatusCode != 200 {
        var retry any
        if value := response.Header.Get("Retry-After"); value != "" { retry = value }
        _ = json.NewEncoder(os.Stderr).Encode(map[string]any{"httpStatus": response.StatusCode, "retryAfter": retry, "problem": result})
        return 1
    }
    // Emit the original JSON, preserving all fields and numeric representations.
    fmt.Println(string(body))
    if !approved(result) { fmt.Fprintln(os.Stderr, "Review required. Keep the original until the result has been reviewed."); return 3 }
    return 0
}

func main() { os.Exit(run()) }
