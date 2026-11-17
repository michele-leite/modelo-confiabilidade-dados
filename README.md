# Data Trust — Sprint 4: validação com Olist

Pacote Python para VS Code que:
1. audita os nove CSVs da Olist;
2. constrói `fct_orders` com uma linha por pedido;
3. calcula métricas observáveis;
4. registra o experimento em `run_manifest.json`;
5. gera evidências e executa a engine de Data Trust da Sprint 3.

## 1. Pré-requisitos

- Python 3.10 ou superior
- VS Code com extensão Python
- Dataset Olist obtido da fonte original

## 2. Preparar o ambiente no VS Code

Abra a pasta do projeto no VS Code. No terminal integrado, execute:

### Windows (PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS/Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação, pode executar diretamente `.venv\Scripts\python.exe -m pip install -r requirements.txt` e usar esse interpretador no VS Code.

## 3. Colocar os dados

Copie os nove CSVs para `data/raw/`. Não altere os nomes dos arquivos. A lista está em `data/raw/README.md`.

## 4. Executar o experimento completo

Na raiz do projeto:

```bash
python run_experiment.py
```

Cada execução cria `runs/<run_id>/` com:
- `run_manifest.json`: status, timestamps, commit, hashes, durações e artefatos;
- `execution.log`: log de execução;
- `audit/`: auditoria de tabelas, nulos, chaves e anomalias;
- `data/fct_orders.csv`: fato com uma linha por pedido;
- `metrics.json`: métricas observadas;
- `evidence.json`: evidências enviadas à engine;
- `data_trust_result.json`: resultado do motor.

O dataset não é modificado. A `fct_orders` é um artefato derivado e reproduzível.

## 5. Executar etapas individualmente

Use o orquestrador para registrar corretamente a execução. Para depurar uma etapa isolada, passe `--run-dir` para o script. Exemplo:

```bash
python scripts/01_audit_olist.py --run-dir runs/debug-audit
python scripts/02_build_fct_orders.py --run-dir runs/debug-audit
```

As etapas seguintes dependem dos artefatos gerados pelas anteriores.

## 6. Como interpretar limitações importantes

- `REL.01` (freshness) permanece `UNKNOWN`: os CSVs não trazem timestamp confiável de ingestão/publicação que permita medir a atualidade operacional da fonte.
- `REL.02` usa a taxa de sucesso das execuções experimentais anteriores concluídas; na primeira execução fica `UNKNOWN`. Isso não mede disponibilidade histórica da plataforma Olist.
- `REL.03` compara hashes de `fct_orders.csv` e `metrics.json` em execuções anteriores com os mesmos hashes de entrada e código; na primeira execução fica `UNKNOWN`.
- Governança é declarada no catálogo experimental pelo pesquisador. Isso não comprova a existência de owner/steward corporativo da Olist.
- O perfil de criticidade II é uma decisão experimental inicial e deve ser justificado no relatório metodológico antes da execução oficial.
- Score e classificação são resultados do motor Sprint 3 e não devem ser interpretados como verdade absoluta sobre a Olist.

## 7. Testes

```bash
pytest -q
```

## 8. Publicação no GitHub

Versione código, configurações, testes e documentação. Não versione automaticamente os CSVs brutos nem os diretórios `runs/`, pois contêm artefatos derivados de cada execução. Publique apenas resultados agregados selecionados e documentados.
