# Sprint 3 — Motor do Modelo de Referência de Data Trust

Este pacote transforma a especificação da Sprint 2 em uma arquitetura executável.

## Estrutura

```text
data_trust_engine_sprint3/
├── model_config.yaml
├── data_contract.schema.yaml
├── architecture.md
├── requirements.txt
├── run_example.py
├── examples/
│   └── evaluation_high_criticality.yaml
├── src/
│   └── data_trust_engine/
│       ├── __init__.py
│       ├── config.py
│       ├── engine.py
│       ├── models.py
│       ├── rules.py
│       └── serialization.py
└── tests/
    └── test_engine.py
```

## Regras implementadas

- PASS = 1
- FAIL = 0
- UNKNOWN = sem score direto
- cobertura dimensional = critérios conhecidos / critérios totais
- score dimensional = média dos critérios conhecidos
- cobertura mínima da dimensão = 0.67
- DQ, REL, GOV, PROV e CTX têm peso inicial 0.20
- IMP não entra no score
- criticidade define score/cobertura mínimos:
  - I: 0.60 / 0.60
  - II: 0.70 / 0.67
  - III: 0.80 / 0.80
  - IV: 0.90 / 0.90
- bloqueador FAIL => NOT_ELIGIBLE
- C1–C4 seguem a Sprint 2
- score e cobertura são sempre reportados separadamente

## Instalação

```bash
pip install -r requirements.txt
```

## Execução

```bash
python run_example.py
```

## Testes

```bash
pytest -q
```

## Observação metodológica

Os pesos e thresholds são baseline experimental. O YAML foi desenhado para permitir
alterações controladas durante a análise de sensibilidade sem alterar o código do motor.
