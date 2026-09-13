# EDUSCANNER

Plataforma web para professores criarem cartões-resposta, cadastrarem
turmas e alunos, escanearem cartões preenchidos e corrigirem
automaticamente as questões por visão computacional (OMR).

## Stack

- **Backend:** Python + FastAPI + SQLAlchemy (SQLite por padrão, troque
  `DATABASE_URL` no `.env` para usar PostgreSQL em produção).
- **Frontend:** HTML + Jinja2 + CSS + JS puro, responsivo (desktop,
  tablet, celular).
- **Scanner/OMR:** Python + OpenCV, em módulo isolado
  (`backend/services/scanner/`).
- **PDF:** ReportLab (cartão-resposta e relatório de turma).

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Abra http://127.0.0.1:8000

## Rodando com Docker

```bash
cp .env.example .env
# edite o .env e troque SECRET_KEY por um valor forte antes de ir para produção
docker compose up --build
```

Isso sobe o EDUSCANNER em http://localhost:8000, usando SQLite persistido
na pasta `./data` (mapeada como volume). Para usar PostgreSQL em vez de
SQLite, veja as instruções comentadas dentro do `docker-compose.yml`
(é preciso adicionar `psycopg2-binary` ao `requirements.txt`).

> **Nota:** o `Dockerfile`/`docker-compose.yml` foram escritos e
> validados (sintaxe do YAML, dependências de sistema do OpenCV), mas
> não foi possível testá-los com um build real neste ambiente — rode
> `docker compose up --build` no seu ambiente antes de confiar neles
> para produção.

## Login com Google

Preencha `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e
`GOOGLE_REDIRECT_URI` no `.env`. Sem essas credenciais, o botão informa
que o recurso ainda não foi configurado — o app funciona normalmente
só com e-mail/senha.

## Fluxo do professor

1. Entrar (e-mail/senha ou Google).
2. Criar turma e cadastrar alunos.
3. Criar um cartão-resposta escolhendo apenas o **bloco** (1 a 8) — a
   quantidade de questões é automática.
4. Definir o gabarito e **imprimir o cartão** (`/cartoes/{id}/imprimir`)
   — PDF pronto para impressão, com questões em azul e bolhas em
   vermelho.
5. Abrir o Scanner, escolher turma + cartão, fotografar/enviar a foto
   de cada cartão preenchido.
6. Ver resultados em `/relatorios`, com filtros por turma, aluno,
   cartão e período, e gerar PDF/CSV por turma.

## Como o Scanner funciona (`backend/services/scanner/`)

Pipeline (Seção 14 do briefing original):

```
imagem -> validação -> detecção do cartão (4 cantos)
       -> correção de perspectiva -> normalização
       -> detecção de vermelho (HSV) -> leitura das bolhas -> resultado
```

Componentes isolados e testáveis individualmente:

- `layout.py` — geometria do cartão (mm), única fonte de verdade
  compartilhada entre o gerador de PDF e o próprio scanner.
- `card_detector.py` — localiza o quadrilátero da borda impressa.
  Distingue a borda real (tinta preta) do limite do papel/fundo por
  **escuridão absoluta**, não relativa — essa é a parte que faz o
  scanner funcionar com fundos variados e iluminação desigual.
- `perspective.py` — corrige a perspectiva para uma imagem canônica de
  tamanho fixo (por isso cartões fotografados de tamanhos/distâncias
  diferentes continuam funcionando).
- `color_detector.py` — máscara HSV de vermelho (duas faixas, por causa
  do wrap-around do matiz).
- `bubble_reader.py` — mede o quanto de vermelho existe dentro de cada
  bolha (fill ratio).
- `question_analyzer.py` — decide OK / BLANK / MULT por questão, sem
  nunca "adivinhar" em caso de múltiplas marcações.
- `validator.py` — rejeita fotos ruins (escuras, borradas, sem cartão,
  cartão cortado) com mensagens não técnicas.
- `pipeline.py` — orquestra tudo; é o único ponto de entrada usado
  pelas rotas da API.

## Testes

```bash
pytest tests/ -v
```

Inclui testes de:
- geometria do cartão (`tests/scanner/test_layout.py`);
- lógica de decisão OK/BLANK/MULT (`tests/scanner/test_question_analyzer.py`);
- **pipeline completo** com cartões sintéticos fotografados em ângulo,
  perspectiva, iluminação e ruído variados
  (`tests/scanner/test_pipeline_synthetic.py`) — não depende de fotos
  reais: desenha um cartão com a mesma geometria usada no PDF, distorce
  como uma foto de celular e confirma que a leitura volta correta;
- blocos automáticos (`tests/test_blocks.py`);
- autenticação: registro, login, hash de senha, logout, rotas
  protegidas (`tests/test_auth.py`);
- turmas e alunos: CRUD completo e isolamento entre professores
  (`tests/test_classes.py`);
- cartões-resposta: criação por bloco, gabarito, impressão de PDF,
  bloqueio de exclusão de cartão já usado, isolamento entre
  professores (`tests/test_cards.py`);
- rate limiting e validação de entrada (`tests/test_security.py`).

Os testes de rotas usam um banco SQLite isolado por execução (ver
`tests/conftest.py`) — nunca tocam em `data/eduscanner.db`.

## Estrutura

```
EDUSCANNER/
  backend/
    main.py, db.py, models.py, security.py
    rate_limit.py      # rate limiting em memória (login, scanner)
    schemas.py         # validação Pydantic dos formulários
    routes/            # auth, dashboard, classes, cards, scanner, reports
    services/
      blocks.py        # mapeamento bloco -> nº de questões
      card_generator.py  # PDF do cartão-resposta para impressão
      pdf_report.py    # PDF de resultados por turma
      scanner/          # pipeline OMR (ver acima)
  frontend/
    templates/          # Jinja2 (sidebar/topbar/dashboard/etc.)
    static/css/style.css  # Design System (tokens + componentes)
    static/js/           # scanner.js, app.js
  tests/
    conftest.py         # fixtures (banco isolado por teste)
    scanner/
  data/                 # banco SQLite (dev)
  .env.example
  requirements.txt
  Dockerfile
  docker-compose.yml
  .dockerignore
```

## Segurança (Seção 24)

- **Isolamento por professor**: todas as rotas filtram por
  `teacher_id`/`classroom_id` do professor logado (testado em
  `test_classes.py` e `test_cards.py` com dois professores diferentes).
- **Senhas**: hash bcrypt via passlib, nunca texto puro.
- **Rate limiting** (`backend/rate_limit.py`): login/registro limitados
  a 8 tentativas/min por IP; scanner a 30 análises/min por IP. É uma
  implementação em memória (processo único) — se o deploy for
  multi-worker/multi-instância, troque por um backend compartilhado
  (Redis, por exemplo); a função `RateLimiter.check()` já isola essa
  decisão em um único lugar.
- **Validação de entrada** (`backend/schemas.py`): formulários de
  registro, login, turma, aluno e cartão são validados com Pydantic
  antes de tocar o banco.
- **Upload do scanner**: limitado a 15MB por imagem.
- **CORS**: desativado por padrão (a aplicação é servida e consumida
  pela mesma origem); habilite via `ALLOWED_ORIGINS` no `.env` só se
  necessário.
- **SECRET_KEY**: se `ENV=production` e a `SECRET_KEY` ainda for o
  valor padrão de desenvolvimento, o servidor emite um aviso no log ao
  subir (não impede o start, mas deixa claro que sessões não estão
  protegidas de verdade).

## Notas de implantação / próximos passos sugeridos

- `bcrypt` está fixado em `4.0.1` no `requirements.txt` — versões mais
  novas quebram o `passlib==1.7.4` (erro `password cannot be longer
  than 72 bytes` / `bcrypt has no attribute __about__`). Não altere sem
  testar.
- Para produção com mais de um usuário simultâneo, trocar
  `DATABASE_URL` para PostgreSQL (ver `docker-compose.yml`).
- Se o projeto crescer bastante, considerar mover para uma separação
  mais granular em `core/api/repositories`.
- O rate limiting atual é em memória; para múltiplos workers/réplicas,
  trocar por um backend compartilhado (Redis).
