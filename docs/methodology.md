# Método experimental — Sprint 4

## Unidade de análise
`orders` é a tabela-base da `fct_orders`; a granularidade final é uma linha por `order_id`.

## Tratamento de tabelas com múltiplos registros
`order_items`, `order_payments` e `order_reviews` são agregadas por `order_id` antes dos JOINs. Isso evita multiplicação cartesiana de itens e pagamentos.

## Dados ausentes
Campos de entrega não são universalmente obrigatórios para todos os status. A completude é calculada sobre campos centrais sempre esperados e campos de entrega condicionais a pedidos entregues. Campos textuais opcionais de avaliação não são considerados obrigatórios.

## Critérios do Data Trust
- DQ.01: taxa de registros que satisfazem os requisitos de completude definidos para o status.
- DQ.02: taxa de pedidos sem violação temporal nas comparações aplicáveis.
- DQ.03: proporção de verificações de validade aprovadas.
- REL.01: UNKNOWN até existir evidência adequada de atualização/ingestão.
- REL.02: sucesso da execução do pipeline experimental (proxy explicitamente limitado).
- REL.03: UNKNOWN na primeira execução; não se infere estabilidade de uma única execução.
- GOV: documentação declarada no catálogo experimental; não é governança corporativa verificada.
- PROV: fonte, lineage e rastreabilidade demonstradas pelos manifestos/artefatos.
- CTX: propósito, adequação do output ao contrato e tolerância declarados no caso de uso.

Limiares de DQ usados neste pacote são parâmetros experimentais iniciais, visíveis no script de geração de evidências; devem ser revisados e justificados antes da execução oficial, não escolhidos para maximizar o score.
