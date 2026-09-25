# EDUSCANNER

Versão atual do EduScanner com scanner de 45 questões, turmas, alunos, resultados e relatórios.

## Funcionalidades
- Scanner do cartão físico CEPI-JBR de 45 questões
- Provas de 20, 30 ou 45 questões; posições excedentes são ignoradas
- Importação de alunos por Excel (.xlsx/.xlsm)
- Colunas aceitas: `Nome do aluno`, `Turma`, `Matrícula`
- Turmas criadas automaticamente na importação
- Matrícula é única; uma nova importação atualiza nome/turma do aluno existente
- Seleção Turma -> Aluno antes de salvar
- Resultado salvo com respostas, gabarito, acertos, erros, anuladas, brancos e nota
- Relatório básico por turma

## Banco
Localmente, sem variável de ambiente, usa SQLite (`eduscanner.db`).
No Render, use PostgreSQL e configure `DATABASE_URL` com a **Internal Database URL**.

## Render
Build command:
`pip install -r requirements.txt`

Start command:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Environment Variable:
`DATABASE_URL=<Internal Database URL do PostgreSQL>`

## Planilha
A primeira linha deve conter as colunas:

| Nome do aluno | Turma | Matrícula |
|---|---|---|
| Ana Silva | 7º A | 12345 |
| João Souza | 7º A | 12346 |

## Rodar local
`pip install -r requirements.txt`
`uvicorn app.main:app --reload`

## Scanner V9 — 45Q mobile

The scanner is calibrated for the PUC Goiás / ENEM PARA TODOS 45-question response card. V9 detects the three printed response blocks (01–15, 16–30 and 31–45), rectifies each block independently, and samples only the 225 answer cells. The header and the “COMO PREENCHER” examples are outside the reading regions.

The result includes a confidence value per detected answer and a list of low-confidence questions so the teacher can review before saving.

## Atualização v6.1 — Relatório por turma e diagnóstico
- Relatórios filtrados por turma e por prova/bloco.
- PDF consolidado da turma.
- Diagnóstico automático com média, aproveitamento, distribuição dos resultados e médias de acertos/erros/brancos/anuladas.
- Quando uma única prova é selecionada, análise por questão com percentual de acertos, brancos e anuladas.
- Identificação de pontos de maior domínio e pontos para reforço para apoiar o feedback coletivo.

## Atualização v9 — novo cartão CEPI-JBR (45 questões)
- Scanner recalibrado para o novo modelo de cartão-resposta usado pela escola.
- A leitura agora localiza diretamente as três grades 01–15, 16–30 e 31–45 na fotografia.
- Cada grade é corrigida de perspectiva separadamente antes da leitura.
- A posição das bolhas foi recalibrada para o novo layout, reduzindo deslocamentos de leitura.
- A análise considera o centro da bolha e uma referência de iluminação local, ajudando com sombras e diferenças de exposição entre celulares.
- Marcação azul, preta e vermelha continua sendo aceita.
- Duas marcações na mesma questão continuam sendo classificadas como `MULT` / anulada.
- O mecanismo de revisão manual já existente permanece disponível para questões sinalizadas com baixa confiança.
- Não é necessário alterar o fluxo de uso no celular: o professor continua fotografando o cartão pelo próprio telefone.
