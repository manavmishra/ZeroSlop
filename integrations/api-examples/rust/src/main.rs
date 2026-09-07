use reqwest::blocking::Client;
use serde_json::{json, Value};
use std::{error::Error, io::{self, Read}, time::Duration};

fn approved(result: &Value) -> bool {
    let fields = ["text", "status", "before", "after", "scoreChange", "factsPreserved", "passedFinalChecks",
        "independentModelChecks", "modelRequests", "rolesCompleted", "finishingRounds", "scorerVersion", "durationMs", "note"];
    if fields.iter().any(|field| result.get(field).is_none()) || !result["text"].is_string() ||
        !result["passedFinalChecks"].is_boolean() || result["factsPreserved"].as_bool() != Some(true) { return false; }
    let (Some(before), Some(after)) = (result["before"]["score"].as_f64(), result["after"]["score"].as_f64()) else { return false; };
    if !(0.0..=100.0).contains(&before) || !(0.0..=100.0).contains(&after) { return false; }
    (result["status"] == "rewritten" && result["passedFinalChecks"].as_bool() == Some(true)) ||
        (result["status"] == "already_clear" && result["modelRequests"].as_u64() == Some(0) &&
         result["scoreChange"].as_f64() == Some(0.0) && before == after)
}

fn run() -> Result<i32, Box<dyn Error>> {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input)?;
    let request: Value = serde_json::from_str(&input)?;
    let endpoint = std::env::var("ZERO_SLOP_API_URL").unwrap_or_else(|_| "https://mcp.zero-slop.ai/v1/deslop".into());
    let client = Client::builder().timeout(Duration::from_secs(75)).connect_timeout(Duration::from_secs(10))
        .redirect(reqwest::redirect::Policy::none()).retry(reqwest::retry::never()).build()?;
    let response = client.post(endpoint).header("Accept", "application/json").json(&request).send()?;
    let status = response.status().as_u16();
    let retry_after = response.headers().get("retry-after").and_then(|value| value.to_str().ok()).map(str::to_owned);
    let body = response.text()?;
    let result: Value = serde_json::from_str(&body)?;
    if status != 200 {
        eprintln!("{}", json!({"httpStatus": status, "retryAfter": retry_after, "problem": result}));
        return Ok(1);
    }
    println!("{body}");
    if !approved(&result) {
        eprintln!("Review required. Keep the original until the result has been reviewed.");
        return Ok(3);
    }
    Ok(0)
}

fn main() {
    let code = run().unwrap_or_else(|_| {
        eprintln!("Request failed or response was not JSON. No automatic retry; the outcome may be unknown.");
        1
    });
    std::process::exit(code);
}
