import argparse
import os
import secrets
import shutil
import sqlite3
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'agendamento_chromebooks.db')
ARQUIVO_SENHA = os.path.join(BASE_DIR, 'admin_inicial.txt')

ADMIN_NOME = 'Marcus Dionizio Altoe'
ADMIN_EMAIL = '***REMOVIDO***'


def banco_antigo():
    """Indica se o arquivo existente ainda usa o esquema antigo, com carrinhos."""
    if not os.path.exists(DB_PATH):
        return False
    conn = sqlite3.connect(DB_PATH)
    colunas = [linha[1] for linha in conn.execute('PRAGMA table_info(usuarios)')]
    conn.close()
    return bool(colunas) and 'funcao' not in colunas


def guardar_copia():
    """Renomeia o banco existente, para que nenhum dado seja apagado."""
    carimbo = datetime.now().strftime('%Y%m%d-%H%M%S')
    raiz, extensao = os.path.splitext(DB_PATH)
    destino = f'{raiz}.backup-{carimbo}{extensao}'
    shutil.move(DB_PATH, destino)
    print(f'Banco anterior guardado em: {destino}')


def criar_banco():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Dados da escola (uma única linha), incluindo o total de máquinas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS escola (
        id INTEGER PRIMARY KEY CHECK(id = 1),
        nome TEXT NOT NULL,
        endereco TEXT NOT NULL,
        telefone TEXT NOT NULL,
        url TEXT NOT NULL,
        total_chromebooks INTEGER NOT NULL CHECK(total_chromebooks >= 0),
        professores INTEGER NOT NULL,
        alunos INTEGER NOT NULL
    );
    ''')

    # 2. Tabela de Usuários
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        funcao TEXT NOT NULL CHECK(funcao IN ('Professor', 'Coordenação', 'Direção', 'Administrador')),
        senha_hash TEXT NOT NULL,
        ativo INTEGER NOT NULL DEFAULT 1,
        criado_em TEXT NOT NULL
    );
    ''')

    # 3. Tabela de Agendamentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        data_agendamento TEXT NOT NULL,
        horario_inicio TEXT NOT NULL,
        horario_fim TEXT NOT NULL,
        quantidade INTEGER NOT NULL CHECK(quantidade > 0),
        etapa TEXT NOT NULL,
        ano TEXT NOT NULL,
        turma TEXT NOT NULL,
        finalidade TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Reservado' CHECK(status IN ('Reservado', 'Cancelado')),
        criado_em TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    );
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_agendamentos_data ON agendamentos (data_agendamento, status);')

    # 4. Logs de entrada, saída, cadastros e agendamentos.
    # Nome e e-mail são copiados para que o registro continue fiel mesmo se o usuário mudar.
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        criado_em TEXT NOT NULL,
        tipo TEXT NOT NULL,
        usuario_id INTEGER,
        usuario_nome TEXT,
        usuario_email TEXT,
        detalhes TEXT
    );
    ''')

    # --- DADOS INICIAIS ---

    cursor.execute('''
    INSERT OR IGNORE INTO escola (id, nome, endereco, telefone, url, total_chromebooks, professores, alunos) VALUES
    (1, 'EE Maria de Lourdes Teixeira',
     'Estrada do Jacarandá, 370 - Altos da Santa Lucia, Carapicuíba - SP, 06361-400',
     '(11) 4187-4718',
     'https://qedu.org.br/escola/35909221-maria-de-lourdes-teixeira',
     16, 76, 2054);
    ''')

    # A única conta inicial é a do Marcus (testes, controle e acesso aos dados)
    if not cursor.execute('SELECT 1 FROM usuarios WHERE email = ?', (ADMIN_EMAIL,)).fetchone():
        senha = os.environ.get('ADMIN_SENHA')
        if not senha:
            senha = secrets.token_urlsafe(12)
            with open(ARQUIVO_SENHA, 'w', encoding='utf-8') as arquivo:
                arquivo.write(f'{ADMIN_EMAIL}\n{senha}\n')
            print(f'Senha inicial gerada e salva em: {ARQUIVO_SENHA}')

        cursor.execute('''
        INSERT INTO usuarios (nome, email, funcao, senha_hash, criado_em) VALUES (?, ?, 'Administrador', ?, ?);
        ''', (ADMIN_NOME, ADMIN_EMAIL, generate_password_hash(senha), datetime.now().isoformat(timespec='seconds')))

    conn.commit()
    conn.close()
    print('Banco de dados pronto: ' + DB_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Cria o banco de dados do sistema.')
    parser.add_argument('--recriar', action='store_true',
                        help='guarda uma cópia do banco atual e cria um novo, só com a conta do administrador')
    argumentos = parser.parse_args()

    if argumentos.recriar and os.path.exists(DB_PATH):
        guardar_copia()
    elif banco_antigo():
        sys.exit('O banco atual usa o formato antigo, com carrinhos. Execute: python init_db.py --recriar')

    criar_banco()
