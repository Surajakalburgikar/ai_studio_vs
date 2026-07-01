# Sprint 31.1: Gemini Model Router & Automatic Model Failover

This document describes the design, architecture, configuration options, retry logic, and failover behavior implemented in Sprint 31.1.

---

## 1. Overview & Architecture

To remove the hardcoded dependency on a single Gemini model, Sprint 31.1 implements a dynamic routing and automatic model failover system. This ensures high availability and resilience when individual model API endpoints experience rate limits, quota issues, or transient downtime.

The failover and routing architecture happens entirely inside the `GeminiProvider` using the new `GeminiModelRouter` helper. Calling layers (e.g., `StoryGenerator`) remain completely unaware of the underlying model changes.

```
       [StoryGenerator]
              │
              ▼  (provider.generate)
     [GeminiProvider] ────(select active)────► [GeminiModelRouter]
              │                                      │
              ├─► Send to gemini-2.5-flash           ├─► Priority List
              │    (Quota Exhausted / 429)           ├─► Cooldown Cache
              │                                      │
              ├─► [Failover Triggered]               │
              │    Mark gemini-2.5-flash on cooldown ◄─┤
              │                                      │
              ├─► Get next active model ─────────────┘
              │    (gemini-3.5-flash)
              │
              └─► Send to gemini-3.5-flash (Success)
```

---

## 2. Configuration Options

The following configurations can be added/customized in the `.env` file:

```ini
# List of Gemini models to route requests to, ordered from highest to lowest priority
GEMINI_MODEL_PRIORITY=gemini-2.5-flash,gemini-3.5-flash,gemini-3-flash,gemini-3.1-flash-lite,gemini-2.5-flash-lite

# The cooldown duration in minutes for models experiencing transient errors
GEMINI_MODEL_COOLDOWN_MINUTES=60
```

* **Default priority order**:
  1. `gemini-2.5-flash`
  2. `gemini-3.5-flash`
  3. `gemini-3-flash`
  4. `gemini-3.1-flash-lite`
  5. `gemini-2.5-flash-lite`
* **Default cooldown duration**: 60 minutes.

---

## 3. Failover Trigger Policies

Failover to the next available model in the priority list is triggered **only** for transient errors:

| Error Category | Indicators / Exceptions | Action |
| :--- | :--- | :--- |
| **HTTP 429 / Rate Limit** | Status Code `429`, `"quota"`, `"rate limit"`, `"exhausted"`, `"limit exceeded"` | Put model on 1-hour cooldown; failover to next model |
| **Temporary / 5xx** | Status Code `5xx`, `"service unavailable"`, `"temporary"` | Put model on 1-hour cooldown; failover to next model |
| **Network Timeout** | `TimeoutError`, `socket.timeout`, `httpx.TimeoutException`, `"timeout"` | Put model on 1-hour cooldown; failover to next model |

### Permanent Failures
For permanent failures, the generation fails immediately (raising a `ProviderError`) without executing a failover or changing the active model's status:
- **HTTP 400 / Invalid Request / Invalid Prompt**: `"invalid prompt"`, `"invalid request"`, `"bad request"`, status `400`
- **HTTP 401 / 403 / Invalid Credentials**: `"invalid api key"`, `"unauthorized"`, `"forbidden"`, status `401`, `403`

---

## 4. Logging & Observability

Dynamic model selections and failover occurrences are logged to the `ai_studio` logger:

* **Primary Model Selection**:
  ```text
  [Gemini Router] Using model: gemini-2.5-flash Reason: Primary model selected
  ```
* **Cooldown Activation**:
  ```text
  [Gemini Router] Model 'gemini-2.5-flash' marked unavailable (cooldown) for 60 minutes.
  ```
* **Failover Warning**:
  ```text
  [Gemini Router] Failover occurred:
  Old model: gemini-2.5-flash
  Reason: Rate limited / Quota exhausted (429) (Resource has been exhausted)
  New model: gemini-3.5-flash
  ```
