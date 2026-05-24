---
lang: en
cluster: supply-chain-economics
requirements:
  - SCM-05
tags:
  - agents
  - supply
  - dataset
  - synthetic
  - SCM-05
---

# Mantis Synthetic Dataset

!!! warning "Completely synthetic data"
    **ALL values on this page are SYNTHETIC.**
    They have been artificially generated for demonstration and testing purposes.
    **They do not represent or contain real data from any company.**
    The dataset is explicitly named "Mantis" to distinguish it from any real data
    source (SCM-05).

---

## Purpose of the Dataset

The Mantis synthetic dataset provides a realistic numerical base for:

1. **Integration test calibration** — the four supply cluster agents
   (InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster) are tested
   against these synthetic values.
2. **Feature demonstration** — KPIs and thresholds are chosen to produce meaningful
   outputs (reorder alerts, EnPI deviations, OEPV scores) without requiring real
   production data.
3. **Development database seeding** — the `scm_mantis_seed.sql` file inserts these
   values into the local/CI database with the explicit label `source = 'mantis_synthetic'`.

---

## SKU Master (synthetic data)

The `scm.sku_master` table contains the following synthetic SKUs, representative of
an Italian SME textile company producing jersey and twill fabrics:

| SKU ID | Name | Category | Unit | Reorder Point | Reorder Qty | Lead Time | Unit Cost | Group |
|--------|------|----------|------|---------------|-------------|-----------|-----------|-------|
| `SKU-YARN-NE20-BLU` | Blue Ne20 Yarn | raw_yarn | kg | 850 kg | 1,500 kg | 7 d | € 3.20/kg | jersey |
| `SKU-YARN-NE30-BIA` | White Ne30 Yarn | raw_yarn | kg | 1,200 kg | 2,000 kg | 7 d | € 2.85/kg | twill |
| `SKU-DYE-REACT-BLU` | Blue Reactive Dye | accessory | kg | 50 kg | 100 kg | 14 d | € 28.50/kg | jersey |
| `SKU-DYE-REACT-GRY` | Grey Reactive Dye | accessory | kg | 40 kg | 80 kg | 14 d | € 31.20/kg | twill |
| `SKU-SPARE-NEEDLE-L` | Loom Needles Large | spare_part | pcs | 200 pcs | 500 pcs | 21 d | € 0.85/pcs | — |
| `SKU-SPARE-NEEDLE-M` | Loom Needles Medium | spare_part | pcs | 150 pcs | 400 pcs | 21 d | € 0.72/pcs | — |
| `SKU-FAB-JERSEY-BLU` | Blue Jersey 140 gsm | fabric | kg | 500 kg | 1,000 kg | — | € 8.40/kg | jersey |
| `SKU-FAB-TWILL-GRY` | Grey Twill 180 gsm | fabric | kg | 300 kg | 600 kg | — | € 10.20/kg | twill |

> **Synthetic note:** Reorder thresholds, unit prices, and lead times are realistic
> but invented values. They do not correspond to any real supplier or market.

---

## ISO 50001 EnPI Baseline (synthetic data)

The `scm.enpi_baseline` table documents Energy Performance Indicators by process,
following the ISO 50001 structure.

| Process | Target kWh/kg | YTD 2024 kWh/kg | YTD Deviation | Status |
|---------|---------------|-----------------|---------------|--------|
| Dyeing (`dyeing`) | **3.80** | **4.12** | +8.4% (above baseline) | Attention |
| Finishing (`finishing`) | **2.20** | **2.18** | -0.9% (within baseline) | OK |
| Spinning (`spinning`) | 1.85 | 1.91 | +3.2% | Monitoring |
| Weaving (`weaving`) | 0.95 | 0.97 | +2.1% | OK |

**Synthetic interpretation:**

- Mantis dyeing is the critical process: the synthetic YTD 2024 (4.12 kWh/kg) is
  8.4% above the target (3.80 kWh/kg) — this value triggers the off-peak proposal
  mechanism of `EnergyOptimizer`.
- Finishing is within target: 2.18 vs 2.20 kWh/kg (-0.9%).

> **All values are synthetic.** Baselines, YTD, and deviations are designed to
> validate the agent logic, not to represent the energy efficiency of a real plant.

---

## Plant Capacity (synthetic data)

Synthetic production parameters used to size demand plans and Holt-Winters forecasts:

| Resource | Synthetic value |
|----------|----------------|
| Looms | 12 units |
| Average production per loom | 850 kg/shift |
| Dyeing vats | 4 units of 500 kg |
| Dyeing cycles | 2 cycles/day per vat |
| Finishing stenters | 2 units |
| Stenter capacity | 1,200 kg/h |
| Shifts | 3 shifts × 8 hours, 5 days/week |
| Working weeks/year | 48 |

**Theoretical annual capacity (synthetic):**

- Loom output: 12 × 850 × 3 × 5 × 48 = ~7,344,000 kg/year
- Dyeing capacity: 4 × 500 × 2 × 5 × 48 = ~960,000 kg/year (theoretical bottleneck)

> **Invented values.** They do not correspond to any real plant.

---

## Historical Order Series (18 synthetic months)

The `scm.historical_orders` table contains 19 monthly buckets (Jan 2024 – Jul 2025)
for each SKU group, sufficient to provide at least 18 months for Holt-Winters
forecasts. Volumes follow realistic but completely synthetic seasonal patterns.

### SKU Group "jersey" (synthetic data)

Base: ~12,000 kg/month with summer and winter seasonality.

| Month | Quantity (kg) | Season note |
|-------|--------------|-------------|
| Jan 2024 | 11,200 | Low season |
| Feb 2024 | 10,800 | Low season |
| Mar 2024 | 12,500 | Spring start |
| Apr 2024 | 13,800 | Peak spring |
| May 2024 | 15,200 | Pre-summer (+35% peak) |
| Jun 2024 | 16,100 | Summer peak |
| Jul 2024 | 15,600 | Summer |
| Aug 2024 | 12,000 | August (holiday) |
| Sep 2024 | 13,400 | Autumn recovery |
| Oct 2024 | 13,900 | Autumn |
| Nov 2024 | 14,400 | Pre-winter (+20% peak) |
| Dec 2024 | 13,800 | Winter peak |
| Jan 2025 | 11,500 | Low season |
| Feb 2025 | 11,100 | Low season |
| Mar 2025 | 12,800 | Spring start |
| Apr 2025 | 14,200 | Peak spring |
| May 2025 | 15,600 | Pre-summer |
| Jun 2025 | 16,400 | Summer peak |
| Jul 2025 | 15,900 | Summer |

Synthetic jersey average: ~13,600 kg/month | Coefficient of variation: ~14%

### SKU Group "twill" (synthetic data)

Base: ~8,000 kg/month with more stable demand (CV ~12%).

| Month | Quantity (kg) | Season note |
|-------|--------------|-------------|
| Jan 2024 | 7,800 | Stable |
| Feb 2024 | 7,600 | Stable |
| Mar 2024 | 8,200 | Mild growth |
| Apr 2024 | 8,400 | Spring |
| May 2024 | 9,000 | Mild seasonal |
| Jun 2024 | 9,200 | Summer |
| Jul 2024 | 8,800 | Summer |
| Aug 2024 | 7,500 | August (holiday) |
| Sep 2024 | 8,100 | Recovery |
| Oct 2024 | 8,300 | Autumn |
| Nov 2024 | 8,700 | Pre-winter |
| Dec 2024 | 8,500 | Winter |
| Jan 2025 | 7,900 | Stable |
| Feb 2025 | 7,700 | Stable |
| Mar 2025 | 8,300 | Mild growth |
| Apr 2025 | 8,600 | Spring |
| May 2025 | 9,100 | Mild seasonal |
| Jun 2025 | 9,400 | Summer |
| Jul 2025 | 9,000 | Summer |

Synthetic twill average: ~8,400 kg/month | Coefficient of variation: ~8%

> **Completely invented series.** The seasonal pattern (jersey summer peak +35%,
> winter +20%; twill CV ~12%) is chosen to verify the robustness of the
> Holt-Winters forecast, not to reflect real market trends.

---

## OEPV Parameters (synthetic data)

The `CostAnalyzer` parametric OEPV simulator uses these synthetic values as
reference for the Mantis Auction Base:

| Parameter | Synthetic value | Note |
|-----------|----------------|------|
| Auction Base (BA) | € 108,000 | Simulated SME textile software contract |
| Technical weight | 70% | OEPV 70/30 scoring |
| Economic weight | 30% | OEPV 70/30 scoring |
| Maximum economic score (Pe_max) | 30 | Normalised to 100 |
| Discount curve lambda (λ) | 3.0 | Parametric F9 (not definitive F12) |
| Reference discount (Ri_ref) | 20% | Parametric F9 |
| Anomalous discount warning threshold | 20% | Configurable (not definitive legal threshold) |

**Synthetic calculation example (discount 12.5%, Pt=60):**

```
Pe = 30 × (1 - exp(-3.0 × 12.5 / 20.0)) = 30 × (1 - exp(-1.875)) ≈ 21.8
Score = 0.70 × 60 + 0.30 × 21.8 = 42.0 + 6.5 = 48.5 / 100
Offer = 108,000 × (1 - 0.125) = € 94,500
```

> **Parametric F9 formula.** The definitive legal calibration compliant with the
> Italian Public Procurement Code (D.Lgs. 36/2023) is deferred to **Phase 12**.

---

## Dataset Provenance

| Field | Value |
|-------|-------|
| Dataset name | Mantis Synthetic Dataset |
| Requirement satisfied | SCM-05 |
| Origin | Artificially generated for the Smart Factory Transformation project |
| Seed file | `infra/migrations/timescale/seed/scm_mantis_seed.sql` |
| DB label | `source = 'mantis_synthetic'` on all rows inserted by the seed |
| Real data included | **None** |
| Real companies referenced | **None** |

The `scm_mantis_seed.sql` file is executed exclusively in development and CI
environments. It must never be applied to a production database containing real data.

---

!!! danger "Summary: synthetic data"
    This page documents **entirely synthetic** data, generated for demonstration.
    None of the values (SKU quantities, prices, energy consumption, order volumes,
    OEPV parameters) originates from or corresponds to real company data.
    Permitted use: development, testing, demo.
