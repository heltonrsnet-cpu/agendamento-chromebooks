# 📚 Sistema de Agendamento de Chromebooks - Barueri

**Projeto Integrador II - Univesp**

Este é um sistema web desenvolvido para resolver o problema de despadronização no agendamento de equipamentos de informática nas escolas municipais de Barueri. O software substitui planilhas manuais e cadernos por uma plataforma unificada, automatizando o cadastro, reservas e controle de status dos carrinhos de Chromebooks.

## 🚀 Tecnologias Utilizadas

*   **Backend:** Python 3 (Framework Flask)
*   **Segurança:** Werkzeug Security (Encriptação de palavras-passe com Hash PBKDF2)
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
Execute o script abaixo para criar as tabelas e popular o banco com os dados de exemplo (Usuários, Equipamentos e Agendamentos):
```bash
python init_db.py
```
*(Um arquivo chamado agendamento_chromebooks.db será criado na raiz do projeto).*

**6. Rode o Servidor Web (API):**
```bash
python app.py
```

**7. Acesse o sistema:**
Abra o seu navegador e acesse a URL: http://127.0.0.1:5000/

## 🔐 Credenciais para Testes do Sistema
Utilize as credenciais abaixo para testar o acesso ao sistema:
| Perfil | E-mail Institucional | Palavra-passe |
| :--- | :--- | :--- |
| **Professor** | `professor@escola.local` | `***REMOVIDO***` |
| **Professora** | `professora@escola.local` | `***REMOVIDO***` |
| **Coordenador** | `coordenador@escola.local` | `***REMOVIDO***` |


## 📁 Estrutura de Pastas do Projeto

```Snippet de código
/
├── venv/                       # Ambiente virtual (ignorado no versionamento)
├── agendamento_chromebooks.db  # Banco de dados SQLite (gerado automaticamente)
├── init_db.py                  # Script de criação, segurança e população do banco
├── app.py                      # Servidor backend (API REST Flask)
├── requirements.txt            # Lista de dependências do projeto
├── README.md                   # Documentação do projeto
├── static/                     # Arquivos estáticos da interface
│   ├── style.css               # Estilização e layout responsivo
│   └── script.js               # Lógica do cliente, gráficos e requisições Fetch
└── templates/                  
    └── index.html              # Interface do usuário (Dashboard)
```

## 🗺️ Próximos Passos (Roadmap)
- [x] Configuração do ambiente e estruturação do Banco de Dados.

- [x] Criação da API REST básica (Listagem de Equipamentos).

- [x] Integração Front-end x Back-end (Dashboard de listagem).

- [x] Criação do formulário de novo agendamento com validação de conflitos.

- [x] Sistema de Autenticação de Usuários com criptografia de senhas (Hash).

- [x] Correção de regras de integridade e Foreign Keys no SQLite.

- [x] Painel de Estatísticas com gráfico dinâmico (Chart.js).

- [ ] Implementação de Gestão de Sessões via Token/Cookies (JWT ou Flask-Session).

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