# License Scanner Test Fixture

Questa directory contiene la fixture per testare che il license scanner blocchi
correttamente le PR che introducono dipendenze con licenze vietate.

## Cosa fa questa fixture

`fixture-gpl-pyproject.toml` e' un file `pyproject.toml` NON installabile che:

1. Dichiara la propria licenza come `GPL-3.0-only` nel campo `[project] license`
2. Dichiara una dipendenza su `pyreadline3>=3.4.1` (GPL-2.0 su PyPI)

Quando Syft scansiona `tests/license/`, legge il manifest e include
entrambe le informazioni di licenza nell'SBOM CycloneDX generato.
Trivy poi analizza l'SBOM contro la policy `infra/license/trivy.yaml` e deve:

- Trovare `GPL-3.0-only` nella lista `forbidden`
- Trovare `GPL-2.0` (da `pyreadline3`) nella lista `forbidden`
- Uscire con `exit code != 0`

## Come viene usata

Il workflow `.github/workflows/test-license-fixture.yml`:

1. Esegue `syft tests/license/ --output cyclonedx-json=fixture-sbom.json`
2. Esegue `trivy sbom fixture-sbom.json --scanners license --config infra/license/trivy.yaml --exit-code 1`
3. **Asserisce che Trivy FALLISCE** (se non fallisce, il test stesso fallisce)

Il workflow viene eseguito:
- Su PR che modificano `infra/license/`, il workflow `license-scan.yml`, o questa directory
- Settimanalmente (cron domenica 00:00 UTC) come regression check

## Manutenzione

Se la fixture smette di funzionare (il test non blocca piu'):

1. Verificare che `pyreadline3` sia ancora classificato GPL-2.0 su PyPI:
   `pip index versions pyreadline3` e poi controllare la pagina PyPI
2. Se `pyreadline3` ha cambiato licenza, sostituirlo con un'altra dipendenza
   nota per essere GPL: cercare su PyPI packages con `License :: OSI Approved :: GNU General Public License v3`
3. La dichiarazione `license = { text = "GPL-3.0-only" }` nel pyproject stesso
   e' la prima linea di difesa: Syft la legge direttamente senza bisogno di installare
   il pacchetto. Se Trivy smette di leggere quella field, aprire un issue upstream su Trivy.

## Perche' non usiamo un pacchetto locale custom

Syft e Trivy leggono la licenza da:
- La dichiarazione `license` nel `pyproject.toml`/`setup.cfg`/`setup.py`
- I metadata PyPI (METADATA file nel wheel/sdist)

Un pacchetto locale con `license = "GPL-3.0-only"` nel pyproject e' sufficiente
per la dichiarazione diretta. Aggiungiamo anche una dep su PyPI (`pyreadline3`)
per testare anche la scansione transitiva.

## Files in questa directory

| File | Descrizione |
|------|-------------|
| `fixture-gpl-pyproject.toml` | Manifest Python con dep GPL — input per Syft |
| `README.md` | Questo file — documentazione e istruzioni manutenzione |
