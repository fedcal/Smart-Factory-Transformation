---
lang: it
cluster: supply-chain-economics
requirements:
  - SCM-05
tags:
  - agents
  - supply
  - dataset
  - sintetico
  - SCM-05
---

# Dataset Sintetico Mantis

!!! warning "Dati completamente sintetici"
    **TUTTI i valori contenuti in questa pagina sono SINTETICI.**
    Sono stati generati artificialmente per scopi dimostrativi e di test.
    **Non rappresentano e non contengono dati reali di alcuna azienda.**
    Il dataset è esplicitamente denominato "Mantis" per distinguerlo da qualsiasi
    fonte dati reale (SCM-05).

---

## Scopo del Dataset

Il dataset sintetico Mantis fornisce una base numerica realistica per:

1. **Calibrazione dei test di integrazione** — i quattro agenti del cluster
   supply (InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster)
   vengono testati contro questi valori sintetici.
2. **Dimostrazione delle funzionalità** — i KPI e le soglie sono scelti per
   produrre output significativi (alert di riordino, deviazioni EnPI, score OEPV)
   senza richiedere dati produttivi reali.
3. **Seed del database di sviluppo** — il file `scm_mantis_seed.sql` inserisce
   questi valori nel database locale/CI con label esplicita `source = 'mantis_synthetic'`.

---

## SKU Master (dati sintetici)

La tabella `scm.sku_master` contiene i seguenti SKU sintetici, rappresentativi di
un'impresa tessile italiana SME che produce tessuti jersey e twill:

| SKU ID | Nome | Categoria | Unità | Punto Riordino | Qtà Riordino | Lead Time | Costo Unit. | Gruppo |
|--------|------|-----------|-------|----------------|--------------|-----------|-------------|--------|
| `SKU-YARN-NE20-BLU` | Filato Ne20 Blu | raw_yarn | kg | 850 kg | 1.500 kg | 7 gg | € 3,20/kg | jersey |
| `SKU-YARN-NE30-BIA` | Filato Ne30 Bianco | raw_yarn | kg | 1.200 kg | 2.000 kg | 7 gg | € 2,85/kg | twill |
| `SKU-DYE-REACT-BLU` | Colorante Reattivo Blu | accessory | kg | 50 kg | 100 kg | 14 gg | € 28,50/kg | jersey |
| `SKU-DYE-REACT-GRY` | Colorante Reattivo Grigio | accessory | kg | 40 kg | 80 kg | 14 gg | € 31,20/kg | twill |
| `SKU-SPARE-NEEDLE-L` | Aghi Telaio Large | spare_part | pcs | 200 pcs | 500 pcs | 21 gg | € 0,85/pcs | — |
| `SKU-SPARE-NEEDLE-M` | Aghi Telaio Medium | spare_part | pcs | 150 pcs | 400 pcs | 21 gg | € 0,72/pcs | — |
| `SKU-FAB-JERSEY-BLU` | Jersey Blu 140 gsm | fabric | kg | 500 kg | 1.000 kg | — | € 8,40/kg | jersey |
| `SKU-FAB-TWILL-GRY` | Twill Grigio 180 gsm | fabric | kg | 300 kg | 600 kg | — | € 10,20/kg | twill |

> **Nota sintetica:** Le soglie di riordino, i prezzi unitari e i lead time sono
> valori realistici ma inventati. Non corrispondono ad alcun fornitore o mercato reale.

---

## Baseline EnPI ISO 50001 (dati sintetici)

La tabella `scm.enpi_baseline` documenta gli indicatori di prestazione energetica
(Energy Performance Indicator) per processo, conformi alla struttura ISO 50001.

| Processo | Target kWh/kg | YTD 2024 kWh/kg | Scostamento YTD | Stato |
|----------|---------------|-----------------|-----------------|-------|
| Tintoria (`dyeing`) | **3,80** | **4,12** | +8,4% (sopra baseline) | Attenzione |
| Finissaggio (`finishing`) | **2,20** | **2,18** | -0,9% (entro baseline) | OK |
| Filatura (`spinning`) | 1,85 | 1,91 | +3,2% | Monitoraggio |
| Tessitura (`weaving`) | 0,95 | 0,97 | +2,1% | OK |

**Interpretazione sintetica:**

- La tintoria Mantis è il processo critico: il YTD 2024 sintetico (4,12 kWh/kg) è
  l'8,4% sopra il target (3,80 kWh/kg) — questo valore attiva il meccanismo di
  proposta off-peak di `EnergyOptimizer`.
- Il finissaggio è invece entro il target: 2,18 vs 2,20 kWh/kg (-0,9%).

> **Tutti i valori sono sintetici.** Le baseline, il YTD e gli scostamenti sono
> progettati per validare la logica dell'agente, non per rappresentare l'efficienza
> energetica di un impianto reale.

---

## Capacità Produttiva (dati sintetici)

Parametri produttivi sintetici usati per dimensionare i piani di domanda e le
previsioni Holt-Winters:

| Risorsa | Valore sintetico |
|---------|-----------------|
| Telai | 12 unità |
| Produzione media per telaio | 850 kg/turno |
| Vasche tintoria | 4 unità da 500 kg |
| Cicli tintoria | 2 cicli/giorno per vasca |
| Stentatoi finissaggio | 2 unità |
| Capacità stentatoi | 1.200 kg/h |
| Turni | 3 turni × 8 ore, 5 giorni/settimana |
| Settimane lavorative/anno | 48 |

**Capacità teorica annua (sintetica):**

- Produzione telai: 12 × 850 × 3 × 5 × 48 = ~7.344.000 kg/anno
- Capacità tintoria: 4 × 500 × 2 × 5 × 48 = ~960.000 kg/anno (collo di bottiglia teorico)

> **Valori inventati.** Non corrispondono ad alcun impianto reale.

---

## Serie Storiche Ordini (18 mesi sintetici)

La tabella `scm.historical_orders` contiene 19 buckets mensili (Gen 2024 – Lug 2025)
per ogni gruppo SKU, sufficienti a garantire almeno 18 mesi per le previsioni
Holt-Winters. I volumi seguono pattern stagionali realistici ma completamente sintetici.

### Gruppo SKU "jersey" (dati sintetici)

Base: ~12.000 kg/mese con stagionalità estiva e invernale.

| Mese | Quantità (kg) | Note stagione |
|------|--------------|---------------|
| Gen 2024 | 11.200 | Bassa stagione |
| Feb 2024 | 10.800 | Bassa stagione |
| Mar 2024 | 12.500 | Inizio primavera |
| Apr 2024 | 13.800 | Alta primavera |
| Mag 2024 | 15.200 | Pre-estate (+35% picco) |
| Giu 2024 | 16.100 | Picco estivo |
| Lug 2024 | 15.600 | Estate |
| Ago 2024 | 12.000 | Agosto (ferie) |
| Set 2024 | 13.400 | Ripresa autunnale |
| Ott 2024 | 13.900 | Autunno |
| Nov 2024 | 14.400 | Pre-inverno (+20% picco) |
| Dic 2024 | 13.800 | Picco invernale |
| Gen 2025 | 11.500 | Bassa stagione |
| Feb 2025 | 11.100 | Bassa stagione |
| Mar 2025 | 12.800 | Inizio primavera |
| Apr 2025 | 14.200 | Alta primavera |
| Mag 2025 | 15.600 | Pre-estate |
| Giu 2025 | 16.400 | Picco estivo |
| Lug 2025 | 15.900 | Estate |

Media sintetica jersey: ~13.600 kg/mese | Coefficiente di variazione: ~14%

### Gruppo SKU "twill" (dati sintetici)

Base: ~8.000 kg/mese con domanda più stabile (CV ~12%).

| Mese | Quantità (kg) | Note stagione |
|------|--------------|---------------|
| Gen 2024 | 7.800 | Stabile |
| Feb 2024 | 7.600 | Stabile |
| Mar 2024 | 8.200 | Leggera crescita |
| Apr 2024 | 8.400 | Primavera |
| Mag 2024 | 9.000 | Stagionale lieve |
| Giu 2024 | 9.200 | Estate |
| Lug 2024 | 8.800 | Estate |
| Ago 2024 | 7.500 | Agosto (ferie) |
| Set 2024 | 8.100 | Ripresa |
| Ott 2024 | 8.300 | Autunno |
| Nov 2024 | 8.700 | Pre-inverno |
| Dic 2024 | 8.500 | Inverno |
| Gen 2025 | 7.900 | Stabile |
| Feb 2025 | 7.700 | Stabile |
| Mar 2025 | 8.300 | Leggera crescita |
| Apr 2025 | 8.600 | Primavera |
| Mag 2025 | 9.100 | Stagionale lieve |
| Giu 2025 | 9.400 | Estate |
| Lug 2025 | 9.000 | Estate |

Media sintetica twill: ~8.400 kg/mese | Coefficiente di variazione: ~8%

> **Serie completamente inventate.** Il pattern stagionale (picco estivo jersey +35%,
> invernale +20%; twill CV ~12%) è scelto per verificare la robustezza della
> previsione Holt-Winters, non per rispecchiare andamenti di mercato reali.

---

## Parametri OEPV (dati sintetici)

Il simulatore OEPV parametrico di `CostAnalyzer` usa questi valori sintetici come
riferimento per la Base d'Asta Mantis:

| Parametro | Valore sintetico | Note |
|-----------|-----------------|------|
| Base d'Asta (BA) | € 108.000 | Contratto software SME tessile simulato |
| Peso tecnico | 70% | Scoring 70/30 OEPV |
| Peso economico | 30% | Scoring 70/30 OEPV |
| Punteggio economico massimo (Pe_max) | 30 | Normalizzato su 100 |
| Lambda curva ribasso (λ) | 3,0 | Parametrico F9 (non definitivo F12) |
| Ribasso di riferimento (Ri_ref) | 20% | Parametrico F9 |
| Soglia warning ribasso anomalo | 20% | Configurabile (non soglia legale definitiva) |

**Esempio di calcolo sintetico (ribasso 12,5%, Pt=60):**

```
Pe = 30 × (1 - exp(-3.0 × 12.5 / 20.0)) = 30 × (1 - exp(-1.875)) ≈ 21,8
Score = 0.70 × 60 + 0.30 × 21.8 = 42,0 + 6,5 = 48,5 / 100
Offerta = 108.000 × (1 - 0.125) = € 94.500
```

> **Formula parametrica F9.** La calibrazione legale definitiva conforme al
> Codice dei Contratti Pubblici (D.Lgs. 36/2023) è demandata a **Phase 12**.

---

## Provenance del Dataset

| Campo | Valore |
|-------|--------|
| Nome dataset | Mantis Synthetic Dataset |
| Requisito soddisfatto | SCM-05 |
| Origine | Generato artificialmente per il progetto Smart Factory Transformation |
| File seed | `infra/migrations/timescale/seed/scm_mantis_seed.sql` |
| Label DB | `source = 'mantis_synthetic'` in tutte le righe inserite dal seed |
| Dati reali inclusi | **Nessuno** |
| Aziende reali referenziate | **Nessuna** |

Il file `scm_mantis_seed.sql` è eseguito esclusivamente in ambienti di sviluppo
e CI. Non deve mai essere applicato a un database di produzione con dati reali.

---

!!! danger "Riepilogo: dati sintetici"
    Questa pagina documenta dati **interamente sintetici**, generati per dimostrazione.
    Nessuno dei valori (quantità SKU, prezzi, consumi energetici, volumi ordini, parametri OEPV)
    proviene da o corrisponde a dati reali di un'azienda. Uso consentito: sviluppo, test, demo.
