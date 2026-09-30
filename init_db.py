import sqlite3
from werkzeug.security import generate_password_hash

def criar_banco():
    db_path = "agendamento_chromebooks.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Tabela de Utilizadores
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        perfil TEXT NOT NULL CHECK(perfil IN ('Professor', 'Coordenador', 'TI_Admin')),
        materia_disciplina TEXT,
        senha_hash TEXT NOT NULL
    );
    ''')

    # 2. Tabela de Equipamentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS equipamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        identificador TEXT NOT NULL UNIQUE,
        bloco_localizacao TEXT NOT NULL,
        quantidade_chromebooks INTEGER NOT NULL DEFAULT 30,
        status TEXT NOT NULL DEFAULT 'Disponível' CHECK(status IN ('Disponível', 'Manutenção', 'Inativo'))
    );
    ''')

    # 3. Tabela de Agendamentos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS agendamentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        equipamento_id INTEGER NOT NULL,
        data_agendamento DATE NOT NULL,
        horario_inicio TIME NOT NULL,
        horario_fim TIME NOT NULL,
        turma TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Reservado' CHECK(status IN ('Reservado', 'Em Uso', 'Concluído', 'Cancelado')),
        observacoes TEXT,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
        FOREIGN KEY (equipamento_id) REFERENCES equipamentos (id)
    );
    ''')

    # --- POPULANDO DADOS INICIAIS ---

    # Senhas encriptadas de exemplo
    senha_admin = generate_password_hash("***REMOVIDO***")
    senha_prof = generate_password_hash("***REMOVIDO***")
    senha_coord = generate_password_hash("***REMOVIDO***")

    # Inserir Utilizadores com hash de senha
    cursor.execute('''
    INSERT OR REPLACE INTO usuarios (id, nome, email, perfil, materia_disciplina, senha_hash) VALUES
    (1, 'Prof. Cristiano Costa', 'professor@escola.local', 'Professor', 'Matemática', ?),
    (2, 'Profa. Isabela Rocha', 'professora@escola.local', 'Professor', 'Língua Portuguesa', ?),
    (3, 'Coordenador Helton Abadia', 'coordenador@escola.local', 'Coordenador', 'Coordenação Pedagógica', ?);
    ''', (senha_prof, senha_prof, senha_coord))

    # Inserir Carrinhos
    cursor.execute('''
    INSERT OR IGNORE INTO equipamentos (id, identificador, bloco_localizacao, quantidade_chromebooks, status) VALUES
    (1, 'Carrinho 01', 'Bloco A - Sala dos Professores', 35, 'Disponível'),
    (2, 'Carrinho 02', 'Bloco B - Laboratório 1', 35, 'Disponível'),
    (3, 'Carrinho 03', 'Bloco C - Biblioteca', 30, 'Manutenção'),
    (4, 'Carrinho 04', 'Bloco D - Maker Space', 40, 'Disponível'),
    (5, 'Carrinho 05', 'Bloco E - Auditório', 35, 'Disponível');
    ''')

    conn.commit()
    conn.close()
    print("✅ Banco de dados atualizado com senhas criptografadas!")

if __name__ == "__main__":
    criar_banco()