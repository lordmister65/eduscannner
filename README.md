# EDUSCANNER

Versão simples com o scanner de 40 questões preservado e módulos de turmas, alunos e resultados.

## Funcionalidades
- Scanner do cartão físico de 40 questões (motor preservado)
- Provas de 20, 30 ou 40 questões; posições excedentes são ignoradas
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

## Autenticação com Firebase

O EduScanner usa o Firebase Authentication no navegador para **e-mail/senha** e **Google**, e valida o ID Token no FastAPI com o Firebase Admin SDK. A sessão interna do EduScanner continua sendo um cookie HTTP-only após a validação do Firebase.

### 1. Criar/configurar o projeto no Firebase Console

1. No Firebase Console, crie (ou selecione) o projeto.
2. Em **Authentication > Sign-in method**, habilite **Email/Password** e **Google**.
3. Em **Project settings > General > Your apps**, crie um app Web e copie `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId` e `appId` para as variáveis `FIREBASE_*` descritas em `.env.example`.
4. Em **Project settings > Service accounts**, escolha **Generate new private key**. Guarde esse JSON como segredo. No Render, a forma mais simples é colocar o JSON inteiro em `FIREBASE_SERVICE_ACCOUNT_JSON` (ou seu conteúdo codificado em base64). Nunca publique esse JSON no Git.
5. Em **Authentication > Settings > Authorized domains**, confirme o domínio do Render usado pelo EduScanner.

### 2. Configurar no Render

O `render.yaml` declara as variáveis necessárias como `sync: false`, para que os segredos sejam preenchidos no Dashboard do Render. Configure também `ADMIN_LOGIN` como **e-mail válido** e `ADMIN_PASSWORD`. No primeiro boot, o sistema cria/vincula essa conta no Firebase quando as credenciais Admin estiverem disponíveis.

Variáveis principais: `DATABASE_URL`, `SECRET_KEY`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_STORAGE_BUCKET`, `FIREBASE_MESSAGING_SENDER_ID`, `FIREBASE_APP_ID` e `FIREBASE_SERVICE_ACCOUNT_JSON`.

### 3. Whitelist do Google

O administrador acessa **Professores > Acesso com Google** para cadastrar e remover os e-mails autorizados. Os e-mails são sempre normalizados com `strip().lower()` no backend. Um login Google não presente em `allowed_google_emails` é recusado; o frontend encerra imediatamente a sessão Firebase e mostra a mensagem de liberação de acesso.

A whitelist é exigida somente para o provedor Google. O login tradicional por e-mail/senha exige que o usuário já exista na tabela `usuarios`; usuários criados no painel administrativo são sincronizados com o Firebase Authentication.

### 4. Testes

Execute `pytest -q`. Os testes de autenticação cobrem login Google permitido (incluindo normalização case-insensitive) e login Google negado pela whitelist.
