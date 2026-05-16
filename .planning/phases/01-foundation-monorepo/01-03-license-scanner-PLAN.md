---
phase: 1
plan: 3
slug: license-scanner
type: execute
wave: 3
depends_on: ["01"]
files_modified:
  - infra/license/trivy.yaml
  - LICENSE-EXCEPTIONS.md
  - LICENSE
  - .github/workflows/license-scan.yml
  - .github/workflows/test-license-fixture.yml
  - tests/license/fixture-gpl-pyproject.toml
  - tests/license/README.md
  - docs/operations/branch-protection.md
  - Makefile
autonomous: true
requirements: [PLAT-05]
tags: [foundation, infra, security, supply-chain, license]

must_haves:
  truths:
    - "Una PR fittizia che introduce una dipendenza Python GPL (es. `gpl-fixture-pkg`) causa exit code != 0 di `license-scan.yml`"
    - "Trivy legge `infra/license/trivy.yaml` e blocca licenze in `forbidden` (GPL-*, AGPL-*, SSPL-1.0, BUSL-1.1)"
    - "Syft genera SBOM CycloneDX coprendo deps Python+JS+immagini container del repo"
    - "MinIO AGPL-3.0 è esplicitamente documentato in `LICENSE-EXCEPTIONS.md` con motivazione tecnica"
    - "SBOM artifact persistito 90 giorni in GitHub Actions"
    - "PR riceve commento automatico con report licenze (diff vs base branch)"
    - "license-scan è required check su branch protection di `main` (documentato in `docs/operations/branch-protection.md`)"
  artifacts:
    - path: "infra/license/trivy.yaml"
      provides: "Policy file Trivy con allowlist + forbidden + reciprocal"
      contains: "forbidden:"
    - path: "LICENSE-EXCEPTIONS.md"
      provides: "Eccezioni licenza documentate con motivazione, data, approver"
      contains: "minio"
    - path: "LICENSE"
      provides: "Apache 2.0 license del progetto"
      contains: "Apache License"
    - path: ".github/workflows/license-scan.yml"
      provides: "CI required check che esegue Syft + Trivy su ogni PR"
      contains: "trivy sbom"
    - path: "tests/license/fixture-gpl-pyproject.toml"
      provides: "Fixture che usa una dep GPL nota per testare il blocco"
  key_links:
    - from: ".github/workflows/license-scan.yml"
      to: "infra/license/trivy.yaml"
      via: "trivy --config infra/license/trivy.yaml"
      pattern: "infra/license/trivy.yaml"
    - from: ".github/workflows/test-license-fixture.yml"
      to: "tests/license/fixture-gpl-pyproject.toml"
      via: "syft scan + trivy assert exit != 0"
      pattern: "exit_code"
---

<objective>
Implementare la pipeline license-scan SBOM-based (Syft + Trivy) come required check su ogni PR. Blocca dipendenze incompatibili (GPL/AGPL/SSPL/BUSL) prima del merge, copre Python+JS+immagini container, documenta eccezioni motivate (MinIO AGPL), produce report PR + SBOM artifact 90gg. Soddisfa Phase Success Criterion #3: PR con dipendenza GPL viene bloccata automaticamente.

Purpose: la traccia richiede `license scanner` (PLAT-05). Implementarlo con SBOM moderno (CycloneDX) parla agli evaluators il linguaggio della supply-chain awareness 2025+, non un grep di package.json. Anticipa anche SEC-04 (audit).

Output: workflow CI che produce PR comment + SBOM artifact; fixture-test che dimostra il blocco funziona.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-foundation-monorepo/01-CONTEXT.md
@.planning/phases/01-foundation-monorepo/01-RESEARCH.md
@CLAUDE.md
@.planning/phases/01-foundation-monorepo/01-01-SUMMARY.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PR -> repository | la PR può introdurre una transitive dependency con licenza incompatibile (rischio legale) |
| immagini container -> deploy artifact | tag image upstream possono cambiare licenza tra versioni (re-scan al deploy) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-01 | Tampering | dep Python/JS con licenza GPL/AGPL aggiunta in una PR | mitigate | Workflow `license-scan.yml` come required check; Trivy `license.forbidden` per GPL/AGPL/SSPL/BUSL; fixture-test verifica empiricamente il blocco |
| T-1-02 | Tampering | container image upstream change licenza | mitigate | Trivy scansiona anche SBOM container layer; tag pinati in compose (plan 02) riducono drift; eccezione MinIO documentata in LICENSE-EXCEPTIONS.md |
| T-1-05 | Information Disclosure | SBOM rivela inventario dipendenze | accept | rischio basso: SBOM è artifact CI, non public; lo richiediamo come trasparenza per evaluators e community OSS |
</threat_model>

<tasks>

<task id="1-03-01" wave="3" type="auto">
  <name>Task 1: LICENSE Apache 2.0 + LICENSE-EXCEPTIONS.md + trivy policy</name>
  <files>LICENSE, LICENSE-EXCEPTIONS.md, infra/license/trivy.yaml</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 4: License Scanner, righe ~675-804; trivy.yaml struttura)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-12, D-13 allowlist esplicita, D-14 MinIO AGPL eccezione, decisione progetto Apache 2.0)
  </read_first>
  <action>
    Creare `LICENSE` con il testo standard Apache License 2.0 (header: "Copyright 2026 Federico Calo and Smart Factory Transformation contributors"). NON modificare il body standard del template Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt).

    Creare `LICENSE-EXCEPTIONS.md` (per D-14) con:
    - Header che spiega lo scopo (eccezioni motivate per dep fuori allowlist)
    - Tabella con colonne: Package | Version | License | Reason | Approved Date | Approver | Scope (build/runtime/transitive)
    - Riga MinIO: `minio | container chainguard latest | AGPL-3.0 | Usato as-is via container upstream come dipendenza Langfuse v3. AGPL applica solo se modifichiamo il binary. Distribuiamo via Helm chart con default upstream. Compatibile single-tenant on-premise (no SaaS hosting / no public network service trigger). | 2026-05-16 | Federico | runtime (Langfuse object storage)`
    - Sezione "Process per aggiungere nuova eccezione": chi approva, quali campi obbligatori, link template PR.

    Creare `infra/license/trivy.yaml` ESATTO come da RESEARCH righe 678-712:
    - `license.notice`: allowlist (D-13) = MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, Unlicense, CC0-1.0, PSF-2.0, Python-2.0, 0BSD
    - `license.reciprocal` (warn, non-block): MPL-2.0, LGPL-2.1, LGPL-3.0
    - `license.forbidden` (block, exit != 0): GPL-1.0, GPL-2.0, GPL-3.0, GPL-2.0-only, GPL-3.0-only, GPL-2.0-or-later, GPL-3.0-or-later, AGPL-3.0, AGPL-3.0-only, AGPL-3.0-or-later, SSPL-1.0, BUSL-1.1
    Aggiungere commento header che spiega ogni categoria e link a `LICENSE-EXCEPTIONS.md` per gestione eccezioni.
  </action>
  <acceptance_criteria>
    - `LICENSE` esiste, contiene `Apache License` e `Version 2.0`
    - `LICENSE` contiene `Copyright 2026 Federico Calo` (o nome ufficiale del progetto)
    - `LICENSE-EXCEPTIONS.md` contiene la stringa `minio` e la stringa `AGPL-3.0`
    - `LICENSE-EXCEPTIONS.md` contiene una tabella con header `Package | Version | License`
    - `infra/license/trivy.yaml` contiene `forbidden:` e `GPL-3.0` e `AGPL-3.0`
    - `infra/license/trivy.yaml` contiene `notice:` con `Apache-2.0` e `MIT`
    - `trivy --version` non viene eseguito qui (CI-only); la validazione del file YAML va fatta con `python3 -c "import yaml; yaml.safe_load(open('infra/license/trivy.yaml'))"` exits 0
  </acceptance_criteria>
</task>

<task id="1-03-02" wave="3" type="auto">
  <name>Task 2: .github/workflows/license-scan.yml + Makefile sbom target</name>
  <files>.github/workflows/license-scan.yml, Makefile</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 4 license-scan.yml righe ~715-793; Don't Hand-Roll table)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-15 CI required check, SBOM 90gg, PR comment)
  </read_first>
  <action>
    Creare `.github/workflows/license-scan.yml` con i seguenti job/steps (ESATTO come RESEARCH ma con correzioni di runtime):

    ```yaml
    name: License Scan (SBOM)
    on:
      pull_request:
      push:
        branches: [main]
    permissions:
      contents: read
      pull-requests: write
    jobs:
      license-scan:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
            with:
              fetch-depth: 0
          - name: Install Syft
            uses: anchore/sbom-action/download-syft@v0
          - name: Generate SBOM (CycloneDX)
            run: syft . --output cyclonedx-json=sbom.json
          - name: License scan via Trivy
            id: license-check
            uses: aquasecurity/trivy-action@0.24.0
            with:
              scan-type: 'sbom'
              input: 'sbom.json'
              scanners: 'license'
              format: 'json'
              output: 'license-report.json'
              exit-code: '1'
              severity: 'CRITICAL'
              trivy-config: 'infra/license/trivy.yaml'
            continue-on-error: true
          - name: Generate Markdown report
            if: always()
            run: |
              docker run --rm -v "$PWD":/workspace aquasec/trivy:0.55.0 \
                sbom /workspace/sbom.json \
                --scanners license \
                --config /workspace/infra/license/trivy.yaml \
                --format table > license-report.md || true
              {
                echo "## License Scan Report"
                echo ""
                echo '```'
                cat license-report.md
                echo '```'
              } > pr-comment.md
          - name: Upload SBOM artifact
            uses: actions/upload-artifact@v4
            with:
              name: sbom-cyclonedx
              path: sbom.json
              retention-days: 90
          - name: Upload license report artifact
            uses: actions/upload-artifact@v4
            with:
              name: license-report
              path: |
                license-report.json
                license-report.md
              retention-days: 90
          - name: Comment PR with license diff
            if: github.event_name == 'pull_request'
            uses: actions/github-script@v7
            with:
              script: |
                const fs = require('fs');
                const body = fs.readFileSync('pr-comment.md', 'utf8');
                github.rest.issues.createComment({
                  issue_number: context.issue.number,
                  owner: context.repo.owner,
                  repo: context.repo.repo,
                  body
                });
          - name: Fail step if forbidden license found
            if: steps.license-check.outcome == 'failure'
            run: |
              echo "::error::License scan found forbidden licenses (see license-report artifact)"
              exit 1
    ```

    Modificare `Makefile` (creato in plan 02) per implementare il target `sbom` reale:
    ```
    sbom:
    	@command -v syft >/dev/null || (echo "syft non trovato: installa via https://github.com/anchore/syft" && exit 1)
    	@command -v trivy >/dev/null || (echo "trivy non trovato: installa via https://aquasecurity.github.io/trivy/" && exit 1)
    	syft . --output cyclonedx-json=sbom.json
    	trivy sbom sbom.json --scanners license --config infra/license/trivy.yaml --format table
    ```
  </action>
  <acceptance_criteria>
    - `.github/workflows/license-scan.yml` esiste e contiene `aquasecurity/trivy-action`
    - `.github/workflows/license-scan.yml` contiene `retention-days: 90` per l'SBOM artifact
    - `.github/workflows/license-scan.yml` contiene `pull_request:` trigger
    - `.github/workflows/license-scan.yml` contiene step `Comment PR with license diff`
    - `Makefile` target `sbom` esegue `syft` e `trivy` (grep `^sbom:` Makefile poi `syft` deve apparire)
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/license-scan.yml'))"` exits 0
  </acceptance_criteria>
</task>

<task id="1-03-03" wave="3" type="auto">
  <name>Task 3: Test fixture GPL + workflow di validazione del blocco</name>
  <files>tests/license/fixture-gpl-pyproject.toml, tests/license/README.md, .github/workflows/test-license-fixture.yml, docs/operations/branch-protection.md</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-15 fixture test, success criterion #3)
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Validation Architecture, righe ~1636-1648)
  </read_first>
  <action>
    Creare fixture `tests/license/fixture-gpl-pyproject.toml`:
    ```toml
    # FIXTURE — NOT a real Python project. Used by .github/workflows/test-license-fixture.yml
    # to verify license-scan.yml correctly blocks PRs introducing GPL-licensed deps.
    [project]
    name = "test-license-fixture"
    version = "0.0.0"
    requires-python = ">=3.12"
    # Introduces a transitive GPL-3.0 dependency that license-scan MUST block.
    dependencies = [
      "readline-py>=0.1.0"  # known GPL-3.0; alternative: choose a stable GPL pkg
    ]
    ```
    NOTA implementatore: verificare quale pacchetto PyPI ha licenza GPL/AGPL-3.0 attualmente classificata in PyPI. Candidati noti: `paramiko-ng` (LGPL), `gnu-pg-utils`, `pyreadline-cli` — meglio una nuance `agpl-test-fixture-pkg` se esiste; se nessuno disponibile, creare un pyproject che dichiara nei metadata `License: GPL-3.0-only` puntando a un fake local path (Trivy scans dichiarazioni anche di package non installati). In ultima istanza usare `dependencies = ["readline-py"]` o documentare nel README che il fixture DICHIARA un dep GPL nel SBOM generato manualmente.

    Creare `tests/license/README.md` che spiega:
    - Cosa: fixture per verificare il blocco licenze
    - Come: il workflow `test-license-fixture.yml` esegue syft+trivy SULLA SOLA directory `tests/license/` e asserisce `exit-code != 0`
    - Manutenzione: se il pacchetto GPL scelto cambia licenza upstream, sostituirlo

    Creare `.github/workflows/test-license-fixture.yml`:
    ```yaml
    name: Test License Scanner Fixture
    on:
      pull_request:
        paths:
          - 'infra/license/**'
          - '.github/workflows/license-scan.yml'
          - '.github/workflows/test-license-fixture.yml'
          - 'tests/license/**'
      schedule:
        - cron: '0 0 * * 0'  # weekly regression check
    jobs:
      verify-block:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Install Syft
            uses: anchore/sbom-action/download-syft@v0
          - name: Generate SBOM for fixture
            run: syft tests/license/ --output cyclonedx-json=fixture-sbom.json
          - name: Trivy scan — MUST FAIL
            id: trivy
            uses: aquasecurity/trivy-action@0.24.0
            with:
              scan-type: 'sbom'
              input: 'fixture-sbom.json'
              scanners: 'license'
              format: 'table'
              exit-code: '1'
              trivy-config: 'infra/license/trivy.yaml'
            continue-on-error: true
          - name: Assert Trivy detected GPL/AGPL
            run: |
              if [ "${{ steps.trivy.outcome }}" != "failure" ]; then
                echo "::error::license scanner failed to detect forbidden GPL dep in fixture"
                exit 1
              fi
              echo "::notice::license scanner correctly blocked the GPL fixture"
    ```

    Creare `docs/operations/branch-protection.md` (per D-15 required status check) che documenta la configurazione richiesta su `main`:
    - Required status checks: `license-scan / license-scan`, `pre-commit-check / pre-commit`, `ci / main`, `helm-smoke-test / helm-test`
    - Require pull request reviews: 1
    - Dismiss stale reviews: yes
    - Require conversation resolution: yes
    - Restrict pushes: include team `maintainers`
    - Linkare GitHub UI: Settings -> Branches -> Branch protection rules -> Add rule.
    Includere comando CLI alternativo `gh api -X PUT repos/<owner>/<repo>/branches/main/protection ...` con payload JSON di esempio (placeholder).
  </action>
  <acceptance_criteria>
    - `tests/license/fixture-gpl-pyproject.toml` esiste e contiene una dep con licenza GPL o AGPL nota (verificato manualmente dall'implementatore; documentato nel README)
    - `tests/license/README.md` esiste e contiene la stringa "fixture"
    - `.github/workflows/test-license-fixture.yml` esiste e contiene il job `verify-block`
    - `.github/workflows/test-license-fixture.yml` contiene `exit 1` nel caso in cui Trivy NON fallisca (test del test)
    - `docs/operations/branch-protection.md` esiste e contiene `license-scan` come required check
    - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test-license-fixture.yml'))"` exits 0
  </acceptance_criteria>
</task>

</tasks>

<verification>
1. `python3 -c "import yaml; [yaml.safe_load(open(f)) for f in ['.github/workflows/license-scan.yml', '.github/workflows/test-license-fixture.yml', 'infra/license/trivy.yaml']]"` exits 0
2. `grep -c "forbidden:" infra/license/trivy.yaml` >= 1
3. `grep -c "AGPL-3.0" infra/license/trivy.yaml` >= 1 (presente in forbidden list)
4. `grep -c "minio" LICENSE-EXCEPTIONS.md` >= 1
5. Test funzionale (post-merge): aprire PR test su staging branch con dep `gpl-fixture-pkg`, verificare che `license-scan` fallisca; chiudere PR senza merge.
6. Required check su `main` configurato (manualmente; documentato in `docs/operations/branch-protection.md`)
</verification>

<success_criteria>
- License scanner blocca PR con dep forbidden (Phase Success Criterion #3)
- MinIO AGPL eccezione documentata in `LICENSE-EXCEPTIONS.md` con rationale (D-14)
- SBOM artifact retention 90gg (D-15)
- Fixture test regola anti-regression weekly
- Branch protection rule documentata per main
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-03-SUMMARY.md` quando done.
</output>
