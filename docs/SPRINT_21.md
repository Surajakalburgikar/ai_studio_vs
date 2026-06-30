# Sprint 21 — Gemini API Integration

This document outlines the architecture, configuration, provider execution flow, retry strategy, and error handling for the Google Gemini API integration in the Story Generation Pipeline.

---

## 1. Architecture

The Gemini integration is built directly upon the provider abstraction introduced in Sprint 20. The abstract base class `BaseProvider` forces all provider models to expose a uniform interface, ensuring the core pipeline orchestrator (`StoryPipeline`) does not depend on LLM-specific SDK details.

```mermaid
flowchart TD
    StoryGenerator --> StoryPipeline
    StoryPipeline --> BaseProvider
    BaseProvider <|-- MockProvider
    BaseProvider <|-- GeminiProvider
    GeminiProvider -->|"Google GenAI SDK"| GeminiService["Google Gemini Service"]
```

---

## 2. Configuration

All Gemini configurations are controlled from `.env` and loaded via Pydantic settings in `app/core/config.py`:

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `STORY_GENERATOR_PROVIDER` | `str` | `"mock"` | Selected active provider: `"mock"` or `"gemini"` |
| `GEMINI_API_KEY` | `str` | `None` | Official Gemini API Key (e.g. `AIzaSy...`) |
| `GEMINI_MODEL` | `str` | `"gemini-2.5-flash"` | Target LLM model name |
| `GEMINI_TEMPERATURE` | `float` | `0.2` | Generation temperature for deterministic output |
| `GEMINI_TOP_P` | `float` | `0.95` | Nucleus sampling parameter |
| `GEMINI_TOP_K` | `int` | `40` | Top-K sampling parameter |

### Startup Validation
The configuration performs validation on startup. If `STORY_GENERATOR_PROVIDER` is set to `"gemini"`, it validates that `GEMINI_API_KEY` is not empty. If validation fails, the application raises a startup validation error.

---

## 3. Provider Execution Flow

The story pipeline executes the following sequence:

```mermaid
sequenceDiagram
    autonumber
    StoryGenerator->>GeminiProvider: generate(prompt)
    Note over GeminiProvider: Initialize genai.Client with API key
    GeminiProvider->>GeminiProvider: Resolve model & hyper-parameters
    GeminiProvider->>GeminiService: models.generate_content(...)
    alt Success
        GeminiService-->>GeminiProvider: GenerateContentResponse (JSON)
        GeminiProvider->>GeminiProvider: Log Latency & Token Usage
        GeminiProvider-->>StoryGenerator: Raw JSON string response
    alt Temporary Failure / HTTP 429 / 5xx / Network Error
        GeminiProvider->>GeminiProvider: Execute exponential backoff retry (up to 3 times)
    alt Permanent Error (e.g. HTTP 400 / 401 / 403)
        GeminiProvider-->>StoryGenerator: Raise ProviderError (wraps SDK exception)
    end
```

---

## 4. Retry Strategy

To ensure resilience against network outages and transient API load/throttling, `GeminiProvider` implements a robust retry policy:
- **Maximum Retries:** 3 additional attempts (4 attempts total).
- **Backoff Scheme:** Exponential backoff beginning at `1.0` second, doubling on each subsequent retry (`1.0s` -> `2.0s` -> `4.0s`).
- **Retryable Errors:**
  - Connection timeouts, DNS failures, socket disconnects.
  - HTTP `429` (Rate limit exceeded).
  - HTTP `5xx` (Internal server error, Bad Gateway, Service Unavailable).
- **Non-Retryable Errors:**
  - HTTP `400` (Bad request, invalid prompt parameters).
  - HTTP `401` / `403` (Authentication/Authorization issues).
  - Verification is terminated immediately on these errors to avoid useless retries.

---

## 5. Error Handling

All SDK exceptions (including `google.genai.errors.APIError`, `httpx.HTTPError`, and network errors) are intercepted at the boundaries of `GeminiProvider`. They are wrapped into a domain-specific exception, `ProviderError` (defined in `app/services/ai/exceptions.py`), ensuring that callers do not need to import or understand Google SDK classes.
