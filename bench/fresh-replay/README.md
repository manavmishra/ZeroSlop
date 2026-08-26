# Fresh same-model editing replay

This panel applies four pinned instruction sets to the same 18 deliberately
obvious drafts with the same named model and Codex CLI. Each run starts without
conversation history and cannot inspect another method's output. The saved run
record binds the instruction file, corpus, prompt, output, model name, and CLI
version by hash.

The replay measures the finished text with deterministic checks from both Zero
Slop and `avoid-ai-writing`. It is a regression test for these drafts, not an
independent human preference study or a universal ranking.
