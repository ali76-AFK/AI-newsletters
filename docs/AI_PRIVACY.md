# AI Privacy Notes

This project supports three AI modes:

- `mock`: deterministic local fallback for safe demos and testing.
- `ollama`: local on-device inference via Ollama.
- `groq`: cloud inference via Groq API.

## What is sent to Groq

Only the text needed for the selected task, for example:

- newsletter title and body for classification,
- newsletter title and body for summarization,
- draft subject/body for refinement.

## What is not sent

- passwords,
- API keys,
- database credentials,
- private local files,
- subscriber records unless explicitly included in a prompt.

## Demo recommendation

Use `mock` for offline development and `groq` for live AI demonstrations when low latency matters.
