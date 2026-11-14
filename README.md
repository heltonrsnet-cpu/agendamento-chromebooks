# 📚 Agenda de Chromebooks - EE Maria de Lourdes Teixeira

**Projeto Integrador II - Univesp**

Este é um sistema web para organizar o uso dos **16 Chromebooks** da [EE Maria de Lourdes Teixeira](https://qedu.org.br/escola/35909221-maria-de-lourdes-teixeira), que atende 2.054 alunos com 76 professores. Os professores se cadastram, consultam a agenda da semana e reservam as máquinas de que precisam para cada turma, sem planilhas ou cadernos.

*Estrada do Jacarandá, 370 - Altos da Santa Lucia, Carapicuíba - SP, 06361-400 · (11) 4187-4718*

## ✨ Funcionalidades

*   **Cadastro de usuários:** nome, e-mail, senha e função (Professor, Coordenação ou Direção).
*   **Agenda da semana:** todos veem quem reservou, quantas máquinas e para qual turma.
*   **Agendamento:** escolha data, horário, quantidade de máquinas, etapa, ano, turma e finalidade. O sistema mostra quantas máquinas estão livres no horário e não deixa passar de 16 ao mesmo tempo.
*   **Meus agendamentos:** consulta e cancelamento das próprias reservas.
*   **Administração (somente o administrador):** logs de entrada, saída, cadastros, agendamentos e cancelamentos, gráfico de uso por etapa e lista de usuários, com opção de desativar acessos.

As finalidades oferecem as atividades de cada etapa:

| Etapa | Anos | Finalidades |
| :--- | :--- | :--- |
| **Ensino Fundamental I** | 1º ao 5º (principalmente 3º ao 5º) | Introdução digital, aprender a digitar, pesquisa supervisionada |
| **Ensino Fundamental II** | 6º ao 9º | Trabalho em grupo, redação, pesquisa, apresentação, projeto interdisciplinar |
| **Ensino Médio** | 1º ao 3º | Simulado online, plataforma de redação, estudos para Enem e vestibulares, Google Classroom |

## 🚀 Tecnologias Utilizadas

*   **Backend:** Python 3 (Framework Flask)
*   **Segurança:** Werkzeug Security (Encriptação de palavras-passe com Hash PBKDF2) e sessão do Flask em cookie assinado
*   **Banco de Dados:** SQLite (com persistência local e suporte a Foreign Keys)
*   **Frontend:** HTML5, CSS3, JavaScript (Vanilla) e Chart.js (Dashboard de Estatísticas)
*   **Arquitetura:** API REST com padrão Cliente-Servidor (MVC)

## ⚙️ Pré-requisitos (Ambiente Windows)

Certifique-se de ter instalado em sua máquina:
*   [Python 3.14+](https://www.python.org/downloads/)
*   [Visual Studio Code (VS Code)](https://code.visualstudio.com/)

## 🛠️ Como Instalar e Rodar o Projeto Localmente

Siga o passo a passo abaixo para configurar o ambiente e rodar o sistema na sua máquina:

**1. Clone ou baixe este repositório e abra a pasta no VS Code.**

**2. Crie o Ambiente Virtual (Isolamento de dependências):**
No terminal do VS Code, execute:
```bash
python -m venv venv
```

**3. Ative o Ambiente Virtual (Windows):**
```bash
.\venv\Scripts\activate
```
*(Você verá o prefixo (venv) no seu terminal após ativar).*

**4. Instale as bibliotecas necessárias:**
```bash
pip install -r requirements.txt
```

**5. Inicialize o Banco de Dados:**
Execute o script abaixo para criar as tabelas, os dados da escola e a conta do administrador:
```bash
python init_db.py
```
*(O arquivo agendamento_chromebooks.db será criado na raiz do projeto. Ele não é versionado no Git, e o script pode ser executado novamente sem sobrescrever dados.)*

A senha inicial do administrador é gerada automaticamente e salva em `admin_inicial.txt`, também fora do Git. Veja [Conta do Administrador](#-conta-do-administrador).

Se você já tinha o banco antigo, com carrinhos, use `python init_db.py --recriar`: o banco atual é guardado em uma cópia `.backup-...db` e um novo é criado.

**6. Configure as variáveis de ambiente (recomendado):**
Veja a seção [Variáveis de Ambiente](#-variáveis-de-ambiente) abaixo. Para testar localmente, basta definir a `SECRET_KEY`.

**7. Rode o Servidor Web (API):**
```bash
python app.py
```

**8. Acesse o sistema:**
Abra o seu navegador e acesse a URL: http://127.0.0.1:5000/

## 🔧 Variáveis de Ambiente

| Variável | Para que serve | Padrão |
| :--- | :--- | :--- |
| `SECRET_KEY` | Chave que assina o cookie de sessão. Defina sempre um valor longo e aleatório, e mantenha-o em segredo. | Gerada aleatoriamente a cada início do servidor (todos precisam fazer login de novo após reiniciar) |
| `FLASK_DEBUG` | `1` liga o modo de depuração (recarga automática e página de erros detalhada). | Desligado |
| `SESSION_COOKIE_SECURE` | `1` faz o cookie de sessão ser enviado apenas por HTTPS. Ative quando o sistema estiver publicado com HTTPS. | Desligado |
| `ADMIN_EMAIL` | E-mail de login do administrador criado pelo `init_db.py`. | `admin@escola.local` |
| `ADMIN_SENHA` | Senha do administrador, usada só quando a conta é criada pelo `init_db.py`. | Senha aleatória, salva em `admin_inicial.txt` |
| `DATABASE_PATH` | Caminho do arquivo do banco de dados (útil para testes). | `agendamento_chromebooks.db` na raiz do projeto |

Para gerar uma chave aleatória:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Para definir as variáveis no terminal do VS Code (PowerShell), antes de rodar `python app.py`:
```powershell
$env:SECRET_KEY = "cole-aqui-a-chave-gerada"
$env:FLASK_DEBUG = "1"   # apenas em desenvolvimento
```
*(As variáveis valem só para aquela janela do terminal.)*

> ⚠️ **Nunca ative `FLASK_DEBUG` em um servidor acessível pela rede.** A página de depuração do Flask permite executar código no servidor.

## 🌐 Publicar na Internet (PythonAnywhere)

O plano gratuito **Beginner** do [PythonAnywhere](https://www.pythonanywhere.com/) atende este projeto: mantém o arquivo SQLite entre reinícios e já inclui HTTPS em `SEU-USUARIO.pythonanywhere.com`.

> ⚠️ Evite serviços cujo plano gratuito apaga o disco a cada reinício (como o Render): o banco SQLite seria perdido junto com todos os agendamentos.

**Limites do plano gratuito:** 1 aplicativo web, 512 MB de disco, 100 segundos de CPU por dia e suporte apenas da comunidade. O app expira se não for renovado periodicamente (botão de extensão na aba *Web*). Suficiente para uma escola ou um piloto; para a rede inteira, considere um plano pago.

> 🔒 O repositório é público, mas nenhum dado sensível é versionado: o banco de dados, a senha inicial do administrador e o `.env` ficam fora do Git. Senhas, chaves e o e-mail do administrador são definidos apenas no servidor.

**1. Crie uma conta *Beginner*** no PythonAnywhere.

**2. Abra um *Bash console*** (aba *Consoles*) e execute, no console do PythonAnywhere (troque o e-mail pelo do administrador):
```text
git clone https://github.com/heltonrsnet-cpu/agendamento-chromebooks.git ChromeAgenda
cd ChromeAgenda
python3 --version
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ADMIN_EMAIL=email-do-administrador@exemplo.com python init_db.py
```
*(Anote a versão mostrada por `python3 --version`: ela é usada no próximo passo.)*

**3. Crie o aplicativo** na aba *Web*: *Add a new web app* → **Manual configuration** (não escolha a opção "Flask") → a **mesma versão de Python** anotada no passo anterior. Versões diferentes impedem o aplicativo de abrir.

**4. Configure o aplicativo**, ainda na aba *Web*:
*   **Virtualenv:** `/home/SEU-USUARIO/ChromeAgenda/venv`
*   **Force HTTPS:** ativado
*   **WSGI configuration file:** clique no link, apague o conteúdo e cole o código abaixo:

```python
import os
import sys

projeto = '/home/SEU-USUARIO/ChromeAgenda'
if projeto not in sys.path:
    sys.path.insert(0, projeto)

os.environ['SECRET_KEY'] = 'cole-aqui-uma-chave-gerada'
os.environ['SESSION_COOKIE_SECURE'] = '1'

from app import app as application
```
*(Gere a chave como explicado em [Variáveis de Ambiente](#-variáveis-de-ambiente). Ela fica apenas neste arquivo do servidor: nunca a envie para o GitHub.)*

**5. Clique em *Reload*** e acesse `https://SEU-USUARIO.pythonanywhere.com`.

**Para atualizar o sistema depois:** no Bash console, execute `cd ChromeAgenda && git pull` e clique em *Reload* na aba *Web*. O banco de dados não é afetado, pois não é versionado. Se `style.css`, `script.js` ou os ícones mudarem, lembre-se de aumentar `VERSAO_CACHE` no `static/sw.js`.

> 🔐 Depois do `init_db.py`, leia a senha com `cat admin_inicial.txt`, guarde-a em local seguro e apague o arquivo com `rm admin_inicial.txt`.

## 📱 Instalar no Celular (PWA)

O sistema é um **PWA** (Progressive Web App): pode ser instalado no Android como um aplicativo, com ícone próprio e abrindo em tela cheia.

1. Publique o servidor em um endereço com **HTTPS** (veja [Publicar na Internet](#-publicar-na-internet-pythonanywhere); o navegador só permite instalar PWAs em HTTPS ou em `localhost`).
2. No celular, abra o endereço no **Chrome**.
3. Toque no menu **⋮** e escolha **Instalar app** (ou **Adicionar à tela inicial**).

Sem internet, o app mostra uma página avisando que está sem conexão. Os agendamentos sempre exigem conexão.

> 🔄 Ao alterar `style.css`, `script.js` ou os ícones, aumente a versão em `VERSAO_CACHE` no `static/sw.js` para que os celulares descartem os arquivos antigos guardados em cache.

## ✅ Regras de Agendamento e Segurança

*   **Sessão obrigatória:** a agenda e os agendamentos exigem login. A sessão expira após 8 horas e continua ativa ao recarregar a página.
*   **Usuário vem da sessão:** o agendamento é sempre registrado em nome do usuário logado. O servidor ignora qualquer identificação de usuário enviada pelo navegador.
*   **Cadastro:** nome, e-mail válido e único, senha de pelo menos 8 caracteres e função. A função **Administrador** não pode ser escolhida no cadastro.
*   **Validações de agendamento:**
    *   todos os campos são obrigatórios e a data e os horários precisam estar em formato válido;
    *   não é possível agendar em data ou horário que já passou (fuso de São Paulo);
    *   o horário de fim precisa ser posterior ao de início;
    *   a etapa, o ano e a finalidade precisam ser opções da lista;
    *   a soma das máquinas em uso ao mesmo tempo não pode passar do total da escola.
*   **Cancelamento:** cada usuário cancela os próprios agendamentos, e o administrador pode cancelar qualquer um. Agendamentos de datas passadas não podem ser cancelados.
*   **Logs:** entradas, entradas recusadas, saídas, cadastros, agendamentos, cancelamentos e ações do administrador ficam registrados. Sessões que expiram sem clicar em **Sair** não geram registro de saída.
*   **Erros internos:** falhas no banco de dados são registradas no log do servidor, e o usuário recebe apenas uma mensagem genérica.

## 🔐 Conta do Administrador

A única conta criada pelo `init_db.py` é a de **Marcus Dionizio Altoe**, usada para testes, controle e acesso aos dados. Os demais usuários se cadastram pela tela inicial.

Nenhuma senha ou e-mail real fica no código. Antes de executar o script, defina:
*   `ADMIN_EMAIL`: e-mail de login do administrador (sem ela, é usado `admin@escola.local`);
*   `ADMIN_SENHA`: senha do administrador (sem ela, a senha gerada é salva em `admin_inicial.txt`).

> ⚠️ Em um servidor já publicado, defina `ADMIN_EMAIL` com o mesmo e-mail usado na criação do banco antes de executar o `init_db.py` de novo; caso contrário, uma segunda conta de administrador será criada.

## 📁 Estrutura de Pastas do Projeto

```Snippet de código
/
├── venv/                       # Ambiente virtual (ignorado no versionamento)
├── agendamento_chromebooks.db  # Banco de dados SQLite (gerado pelo init_db.py, ignorado no versionamento)
├── .gitignore                  # Arquivos que não vão para o Git (venv, banco, .env)
├── admin_inicial.txt           # Senha inicial do administrador (gerada pelo init_db.py, ignorada no versionamento)
├── init_db.py                  # Script de criação do banco, dados da escola e conta do administrador
├── app.py                      # Servidor backend (API REST Flask)
├── requirements.txt            # Lista de dependências do projeto
├── README.md                   # Documentação do projeto
├── static/                     # Arquivos estáticos da interface
│   ├── style.css               # Estilização e layout responsivo
│   ├── script.js               # Lógica do cliente, gráficos e requisições Fetch
│   ├── manifest.webmanifest    # Manifesto do PWA (nome, cores e ícones do app)
│   ├── sw.js                   # Service worker (cache dos arquivos e página offline)
│   ├── offline.html            # Página exibida sem conexão
│   └── icons/                  # Ícones do app instalado
└── templates/                  
    └── index.html              # Interface do usuário (Dashboard)
```

## 🗺️ Próximos Passos (Roadmap)
- [x] Configuração do ambiente e estruturação do Banco de Dados.

- [x] Criação da API REST básica (listagem inicial de equipamentos).

- [x] Integração Front-end x Back-end (Dashboard de listagem).

- [x] Criação do formulário de novo agendamento com validação de conflitos.

- [x] Sistema de Autenticação de Usuários com criptografia de senhas (Hash).

- [x] Correção de regras de integridade e Foreign Keys no SQLite.

- [x] Painel de Estatísticas com gráfico dinâmico (Chart.js).

- [x] Gestão de sessões no servidor com cookie assinado (sessão nativa do Flask).

- [x] Validações de agendamento no servidor (datas e horários).

- [x] Agenda da semana e controle pelas 16 máquinas da escola, com finalidades por etapa de ensino.

- [x] Cadastro de usuários e listagem e cancelamento dos próprios agendamentos.

- [x] Painel do administrador com logs, estatísticas e controle de acessos.

- [ ] Troca e recuperação de senha.

- [ ] Limite de tentativas de login.

- [ ] Horários fixos conforme as aulas da escola.

- [ ] Integração com IA para otimização de horários.

## 👥 Equipe do Projeto
* Beatriz do Nascimento Feitosa Buava
* Cristiano Carlos Castro Costa
* Helton Rosa da Silva Abadia
* Isabela Luisa Rocha e Silva
* Jackson Barbosa
* Marcus Dionizio Altoe
* Sthefanny Farias da Conceição
* Yasmin Oliveira do Nascimento Silva

*Desenvolvido com dedicação para o Projeto Integrador II - Univesp.*