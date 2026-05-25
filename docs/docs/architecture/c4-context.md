# C4 — Diagramma di Contesto

Il livello di contesto mostra **chi** interagisce con la piattaforma Smart Factory Transformation
e quali sistemi esterni ne costituiscono il confine operativo.

> **SC-3 — Tracciabilità:** ogni elemento corrisponde a un componente implementato
> (Fase 1–11) o a un sistema esterno reale. Nessun elemento aspirazionale.

```mermaid
C4Context
    title Smart Factory Transformation — C4 Context

    Person(operator, "Operatore di Produzione", "Consulta suggerimenti in tempo reale e approva azioni proposte dall'AI")
    Person(technician, "Tecnico Manutenzione", "Riceve alert predittivi, diagnosi RCA e piani di intervento")
    Person(manager, "Responsabile / Caposquadra", "Monitora KPI, approva decisioni ad alto impatto, visualizza dashboard")

    System(sft, "Smart Factory Transformation", "Piattaforma GenAI multi-agente per la trasformazione digitale del tessile. 16 agenti / 4 cluster; HITL 4-tier; RAG ibrido BGE-M3 + Qdrant; Angular SSR UI.")

    System_Ext(opcua_sim, "Simulatore OPC-UA (svc-ot-bridge)", "Genera eventi di sensore tessile (telai, fusi, vasche tintura) compatibili OPC-UA. Flusso UNIDIREZIONALE verso NATS JetStream.")
    System_Ext(erp_mes, "ERP / MES Aziendale", "Sistema esterno fuori scope v1.0. Punto di integrazione futuro per dati di ordini e pianificazione.")
    System_Ext(ollama, "Ollama / vLLM (on-premise)", "Inference LLM locale — Qwen2.5. Nessun dato esce dalla rete aziendale.")

    Rel(operator, sft, "Consulta, approva/rigetta decisioni AI", "HTTPS — Angular SSR UI")
    Rel(technician, sft, "Legge diagnosi, pianifica interventi", "HTTPS — Angular SSR UI")
    Rel(manager, sft, "Monitora KPI, gestisce approvazioni", "HTTPS — Angular SSR UI")
    Rel(opcua_sim, sft, "Pubblica eventi sensore (unidirezionale)", "OPC-UA → NATS JetStream")
    Rel(sft, ollama, "Invoca inference LLM", "HTTP REST — rete interna")
    Rel(erp_mes, sft, "Integrazione futura (fuori scope v1.0)", "—")
```

## Principi di confine

| Principio | Implementazione |
|-----------|----------------|
| **Data-diode OT** | `svc-ot-bridge` riceve da OPC-UA e pubblica su NATS — il flusso inverso (agenti → OT) è bloccato a livello NetworkPolicy Kubernetes (Fase 1) |
| **Self-hostable** | Ollama/vLLM on-premise: nessun dato industriale esce dalla rete aziendale |
| **HITL 4-tier** | Ogni decisione critica transita per approvazione umana prima dell'esecuzione (Fase 4) |

## Prossimi livelli C4

- [C4 Container](c4-container.md) — componenti interni e loro comunicazione
- [C4 Component](c4-component.md) — struttura interna dell'agent runtime
