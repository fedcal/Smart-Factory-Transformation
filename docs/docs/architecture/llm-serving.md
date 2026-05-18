---
title: LLM Serving (Ollama dev / vLLM prod)
tags: [architecture, phase-04]
---

# LLM Serving: Ollama (dev) e vLLM (prod)

## Overview

Phase 4 introduce un **adapter LLM provider-agnostic** in `packages/sft-agents/src/sft_agents/llm/`.
La selezione del provider e' controllata da una sola variabile d'ambiente:

| Variabile | Default | Valori |
| --- | --- | --- |
| `LLM_BACKEND` | `ollama` | `ollama` \| `vllm` |

Qualsiasi altro valore solleva `RuntimeError` al boot (mitigation T-04-LLM-Inject — whitelist `Literal["ollama","vllm"]`).

### Matrice env-var

| Variabile | Default | Branch | Note |
| --- | --- | --- | --- |
| `LLM_BACKEND` | `ollama` | both | Selettore principale |
| `OLLAMA_MODEL` | `qwen2.5:7b-instruct-q4_K_M` | ollama | Tag Ollama del modello |
| `OLLAMA_HOST` | `http://localhost:11434` | ollama | Endpoint HTTP del daemon |
| `VLLM_MODEL` | `Qwen/Qwen2.5-14B-Instruct-AWQ` | vllm | HF model id (formato `org/model`) |
| `VLLM_BASE_URL` | `http://localhost:8000/v1` | vllm | OpenAI-compatible endpoint vLLM |
| `VLLM_API_KEY` | `dummy` | vllm | API key (qualsiasi stringa funziona con vLLM in dev) |
| `LANGFUSE_HOST` | _unset_ | both | Se unset → tracing disabilitato (callback ritorna `None`) |
| `LANGFUSE_PUBLIC_KEY` | _unset_ | both | Richiesto solo se `LANGFUSE_HOST` set |
| `LANGFUSE_SECRET_KEY` | _unset_ | both | Richiesto solo se `LANGFUSE_HOST` set |

L'idioma di dispatch e' identico a `services/ot-bridge/src/svc_ot_bridge/main.py:62-71` (env-var
read + whitelist + `RuntimeError` on invalid value).

---

## Ollama (dev) — Qwen2.5-7B Q4_K_M

Setup locale per sviluppo (CPU/GPU consumer):

```bash
# 1. Installa Ollama (Linux/macOS): https://ollama.com/download
# 2. Pull del modello Phase 4 locked
ollama pull qwen2.5:7b-instruct-q4_K_M

# 3. Avvia daemon (background)
ollama serve   # esposto su localhost:11434

# 4. Smoke test dal SDK
LLM_BACKEND=ollama \
  uv run python -c "from sft_agents.llm import get_llm; m = get_llm(); print(type(m).__name__)"
# atteso → ChatOllama
```

**Note caching/quantizzazione:** Q4_K_M usa ~4.6 GB RAM/VRAM. Per macchine con < 8 GB
disponibili, considera `qwen2.5:7b-instruct-q4_0` (alternativa documentata Phase 11).
Phase 4 lock e' Q4_K_M per bilanciamento qualita'/throughput.

---

## vLLM (prod) — Qwen2.5-14B-Instruct-AWQ

vLLM espone un endpoint **OpenAI-compatible**, quindi il SDK usa
`langchain_openai.ChatOpenAI` con `base_url=http://.../v1`.

### Serve command — **DEPLOY BLOCKER se manca `--tool-call-parser hermes`**

```bash
# vLLM 0.8+ (controlla con `vllm --version`)
vllm serve Qwen/Qwen2.5-14B-Instruct-AWQ \
  --port 8000 \
  --quantization awq \
  --max-model-len 32768 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes
```

**Per la Pitfall §3:** Qwen2.5 produce tool calls nel formato **Hermes**
(`<tool_call>{"name": "...", "arguments": {...}}</tool_call>`). Se ometti
`--tool-call-parser hermes`, vLLM **NON parsa** i tool call dell'output:
- `response.tool_calls` rimane `[]`
- la response viene trattata come testo libero
- LangGraph routing fallisce silenziosamente (l'agent loop ritorna senza azione)

`--enable-auto-tool-choice` abilita il dispatch automatico — senza, vLLM ignora
i tool schema inviati dal client. **Entrambi i flag sono obbligatori.**

### Variabili d'ambiente sul client (sft-agents)

```bash
export LLM_BACKEND=vllm
export VLLM_BASE_URL=http://vllm-host:8000/v1
export VLLM_API_KEY=any-string   # vLLM non valida la chiave in dev
export VLLM_MODEL=Qwen/Qwen2.5-14B-Instruct-AWQ
```

---

## Tool Calling Notes

### OpenAI function-calling shape

Il `ToolRegistry` (`sft_agents.tools.registry`) esporta i tool come dict JSON
nel formato OpenAI function-calling:

```json
{
  "type": "function",
  "function": {
    "name": "query_timescale",
    "description": "Query TimescaleDB sensor_events hypertable for historical sensor data...",
    "parameters": { /* Pydantic args_schema.model_json_schema(by_alias=True) */ }
  }
}
```

`by_alias=True` e' obbligatorio: serializza i nomi dei campi con il loro alias
Pydantic (o il nome del campo se non c'e' alias), evitando di esporre dettagli
interni del modello come `arbitrary_types_allowed` o `populate_by_name`.

### Hermes-style tokens (vLLM only)

Per Qwen2.5 + vLLM, il flusso e':

1. Client invia `tools=[...]` (formato OpenAI) nella request `/v1/chat/completions`
2. vLLM costruisce il prompt con i tool definitions in formato Hermes
3. Modello produce `<tool_call>...</tool_call>` nel testo di risposta
4. vLLM (con `--tool-call-parser hermes`) estrae e popola `response.tool_calls`
5. `langchain-openai` ChatOpenAI legge `tool_calls` e instanzia `AIMessage.tool_calls`
6. LangGraph `ToolNode` lo consuma

### Ollama tool calling

`langchain-ollama` ChatOllama (>=0.3) supporta tool calling nativamente per
Qwen2.5 — non serve un parser flag esplicito (a differenza di vLLM). Il setup
e' "just works" sul `bind_tools([...])`.

---

## Determinism Caveats

`temperature=0.0` + `seed=42` (entrambi forwarded dal factory) **non sono**
sufficienti per riproducibilita' cross-hardware o cross-batch — sono best-effort.

Pitfall §5 (RESEARCH.md):

- **Determinismo intra-batch:** OK con `temperature=0.0` + `seed`
- **Determinismo cross-GPU:** NO — il kernel CUDA non garantisce bit-identita'
- **Determinismo cross-vLLM-version:** NO — cambia il sampling pipeline
- **Determinismo Ollama vs vLLM:** NO — modelli quantizzati diversi (Q4_K_M vs AWQ)

**Conseguenza per i test:**

> **Per gli unit test usa `FakeListChatModel`** (`langchain_core.language_models.fake_chat_models`),
> NON un LLM reale. Solo i test marker `@pytest.mark.integration` invocano Ollama/vLLM.

`BudgetingChatModel` wrappa qualsiasi `BaseChatModel` (incluso il fake) — i test
verificano il *contratto* (cattura `usage_metadata` + `duration_ms`), non il
*contenuto* della risposta.

---

## Streaming + usage_metadata (Pitfall §4)

**vLLM streaming drop bug:** con `stream=True` langchain-openai *droppa* il
campo `usage_metadata` dalla response finale a meno di passare
`stream_usage=True` esplicitamente al `ChatOpenAI(...)`.

`sft_agents.llm.factory.build_chat_model(backend="vllm", ...)` passa
`stream_usage=True` **incondizionatamente**. Senza, `BudgetTracker` (Plan 04-06)
non riceve i conteggi token nelle streaming response e non puo' enforce
i budget — di fatto bypass dell'HITL-09 cap.

Ollama non e' affetto: usage_metadata e' sempre popolato sulla response.

---

## Langfuse v3 — Tracing Opt-In

`packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` espone:

| Funzione | Comportamento |
| --- | --- |
| `get_langfuse_callback()` | Ritorna `None` se `LANGFUSE_HOST` unset; altrimenti `CallbackHandler` v3 |
| `build_invocation_metadata(thread_id, user_id, tags)` | Dict per `config["metadata"]` |
| `build_invocation_config(thread_id, ...)` | Dict completo per `graph.ainvoke(state, config=...)` |

**Pitfall §11 (v3 API breaking change):**

```python
# v2 (DEPRECATED):
handler = LangfuseCallbackHandler(session_id=thread_id, user_id=user)  # NO!

# v3 (CORRETTO):
handler = CallbackHandler()              # constructor takes NO session id
config = {
    "configurable": {"thread_id": thread_id},
    "callbacks": [handler],
    "metadata": {
        "langfuse_session_id": thread_id,  # session_id GOES HERE
        "langfuse_user_id":    user_id,
        "langfuse_tags":       ["phase4", "ops"],
    },
    "recursion_limit": 25,
}
await graph.ainvoke(state, config=config)
```

Se `LANGFUSE_HOST` e' unset, `get_langfuse_callback()` ritorna `None` e l'agent
runtime funziona normalmente senza tracing — utile per smoke test offline.

---

## Riferimenti

- vLLM tool calling docs: https://docs.vllm.ai/en/latest/features/tool_calling.html
- Hermes prompt format: https://github.com/NousResearch/Hermes-Function-Calling
- Langfuse v3 LangChain integration: https://langfuse.com/docs/integrations/langchain
- langchain-openai stream_usage option: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
- Ollama tool calling: https://github.com/ollama/ollama/blob/main/docs/api.md#chat-request-with-tools

---

## Smoke Verification

```bash
# Ollama branch
LLM_BACKEND=ollama \
  uv run python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"
# → ChatOllama

# vLLM branch
LLM_BACKEND=vllm \
  uv run python -c "from sft_agents.llm import get_llm; print(type(get_llm()).__name__)"
# → ChatOpenAI

# Invalid backend
LLM_BACKEND=foo \
  uv run python -c "from sft_agents.llm import get_llm; get_llm()"
# → RuntimeError: LLM_BACKEND must be one of ollama|vllm, got 'foo'

# Tool registry export
uv run python -c "from sft_agents.tools import BUILTIN_TOOLS, export_tool_schemas; \
  schemas = export_tool_schemas(list(BUILTIN_TOOLS)); \
  print(len(schemas), [s['function']['name'] for s in schemas])"
# → 3 ['replay_cmapss', 'replay_uci', 'query_timescale']

# Langfuse opt-in
uv run python -c "from sft_agents.llm.langfuse_callback import get_langfuse_callback; \
  print(get_langfuse_callback())"
# → None (con LANGFUSE_HOST unset)
```
