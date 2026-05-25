# Economic Analysis

The economic model of Smart Factory Transformation is fully reproducible:
all numbers presented in this section derive from a single Python script
(`docs/economic-analysis/tco_oepv.py`) that reads parameters from `params.toml`
and generates CSV + Markdown tables deterministically (ECO-08, single source of truth).

## How to Regenerate Numbers

```bash
python3 docs/economic-analysis/tco_oepv.py
```

This command updates `tco_table.csv`, `sensitivity_table.csv` and `summary.md` with
current values from `params.toml`. Generated files are committed to the repository.

## Model Structure

| Section | Content | Requirement |
|---|---|---|
| [TCO](tco.md) | 3-year Total Cost of Ownership, 6-component breakdown | ECO-03, ECO-06 |
| [OEPV](oepv.md) | OEPV 70/30 simulator, non-linear sensitivity, anomaly threshold | ECO-01, ECO-02, ECO-05 |
| [Value Drivers](value-drivers.md) | Downtime/scrap/MTTR reduction as SIMULATED TARGET with citations | ECO-04, SC-3 |

## Risk Register ECO-07

The following economic risk register accompanies the evaluation (ECO-07):

| ID | Risk | Probability | Impact | Mitigation |
|---|---|:---:|:---:|---|
| R-ECO-01 | Energy cost above 0.25 EUR/kWh (tariff variability) | Medium | Medium | `energy_eur_kwh` configurable in `params.toml`; +10% brings 3yr TCO to ~190,227 EUR |
| R-ECO-02 | FTE cost deviation (turnover, seniority increase) | Medium | High | FTE and partial quota configurable; dominant component (71% of total TCO) |
| R-ECO-03 | IT/OT integration more complex than estimated | High | Medium | Conservative estimate with margin; OT Bridge separation documented in architecture |
| R-ECO-04 | Technical score PT assigned by jury below assumption | Medium | High | Two documented scenarios (optimistic PT=68, base PT=55); SIMULATED TARGET declared |
| R-ECO-05 | Offer discount perceived as anomalous (>= 20% threshold) | Low | High | Configurable WARNING threshold; 12.5% discount well below threshold; see [OEPV](oepv.md) |
| R-ECO-06 | GPU hardware obsolescence before end of 3-year amortization | Low | Low | Relatively low GPU cost (15,000 EUR); component <8% of total TCO |

## Key Parameters

| Parameter | Value | Source |
|---|---|---|
| Base d'Asta | 108,000 EUR | Mantis anchor, `params.toml` |
| Assumed discount | 12.5% | Range 10-15%, `params.toml` |
| Energy | 0.25 EUR/kWh | Industrial ARERA tariff, `params.toml` |
| Optimistic PT | 68.0 / 70 | Assumption Register A-051, SIMULATED TARGET |
| Base PT | 55.0 | Assumption Register A-052, SIMULATED TARGET |
| Anomaly threshold | 20.0% (configurable) | Proxy art. 54 D.Lgs. 36/2023, `params.toml` |

> **Methodological note:** all parameters are configurable. Modify `params.toml`
> and re-run the script to obtain customised projections.
