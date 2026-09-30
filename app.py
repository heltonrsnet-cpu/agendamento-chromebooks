from flask import Flask, jsonify, request, render_template
import sqlite3
from werkzeug.security import check_password_hash

app = Flask(__name__)

# Função auxiliar para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect('agendamento_chromebooks.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

# Rota principal - Carrega a interface visual
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Rota para listar todos os equipamentos (A API)
@app.route('/api/equipamentos', methods=['GET'])
def get_equipamentos():
    conn = get_db_connection()
    equipamentos = conn.execute('SELECT * FROM equipamentos').fetchall()
    conn.close()
    resultado = [dict(row) for row in equipamentos]
    return jsonify(resultado)

# --- NOVA ROTA: Estatísticas de Uso ---
@app.route('/api/estatisticas', methods=['GET'])
def get_estatisticas():
    conn = get_db_connection()
    
    # 1. Total geral de agendamentos ativos
    total_agendamentos = conn.execute(
        "SELECT COUNT(*) FROM agendamentos WHERE status != 'Cancelado'"
    ).fetchone()[0]
    
    # 2. Agendamentos agrupados por cada Carrinho (Equipamento)
    por_equipamento = conn.execute('''
        SELECT e.identificador, COUNT(a.id) as total 
        FROM equipamentos e 
        LEFT JOIN agendamentos a ON e.id = a.equipamento_id AND a.status != 'Cancelado'
        GROUP BY e.id
    ''').fetchall()
    
    conn.close()
    
    # Converte os resultados para listas/dicionários JSON
    return jsonify({
        "total_agendamentos": total_agendamentos,
        "por_equipamento": [dict(row) for row in por_equipamento]
    })

# --- ROTA: Autenticação (Login) ---
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json()
    email = dados.get('email')
    senha = dados.get('senha')  # <--- Recebe a senha enviada

    if not email or not senha:
        return jsonify({"mensagem": "Informe o e-mail e a senha de acesso!"}), 400

    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()

    # Verifica se o usuário existe E se a senha confere com o hash do banco
    if usuario and check_password_hash(usuario['senha_hash'], senha):
        return jsonify({
            "sucesso": True,
            "mensagem": f"Bem-vindo(a), {usuario['nome']}!",
            "usuario": {
                "id": usuario['id'],
                "nome": usuario['nome'],
                "perfil": usuario['perfil']
            }
        }), 200
    else:
        return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos."}), 401

    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()
    conn.close()

    if usuario:
        return jsonify({
            "sucesso": True,
            "mensagem": f"Bem-vindo(a), {usuario['nome']}!",
            "usuario": {
                "id": usuario['id'],
                "nome": usuario['nome'],
                "perfil": usuario['perfil']
            }
        }), 200
    else:
        return jsonify({"sucesso": False, "mensagem": "E-mail não encontrado no sistema da rede municipal."}), 404

# --- ROTA: Agendamentos com Validação de Conflito e Vínculo de Usuário ---
@app.route('/api/agendamentos', methods=['POST'])
def criar_agendamento():
    dados = request.get_json()

    usuario_id = dados.get('usuario_id')
    equipamento_id = dados.get('equipamento_id')
    data_agendamento = dados.get('data')
    horario_inicio = dados.get('inicio')
    horario_fim = dados.get('fim')
    turma = dados.get('turma')

    if not all([usuario_id, equipamento_id, data_agendamento, horario_inicio, horario_fim, turma]):
        return jsonify({"mensagem": "Todos os campos, incluindo a identificação do usuário, são obrigatórios!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificação de choque de horários
        query_conflito = '''
            SELECT * FROM agendamentos 
            WHERE equipamento_id = ? 
              AND data_agendamento = ? 
              AND status != 'Cancelado'
              AND (
                  (? < horario_fim) AND (? > horario_inicio)
              )
        '''
        conflito = cursor.execute(query_conflito, (equipamento_id, data_agendamento, horario_inicio, horario_fim)).fetchone()

        if conflito:
            conn.close()
            return jsonify({
                "mensagem": "Conflito de horário! Este carrinho já possui um agendamento conflitante neste período."
            }), 409

        # Inserção com o ID real do professor autenticado
        cursor.execute('''
            INSERT INTO agendamentos (usuario_id, equipamento_id, data_agendamento, horario_inicio, horario_fim, turma, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (usuario_id, equipamento_id, data_agendamento, horario_inicio, horario_fim, turma, 'Reservado', 'Criado via formulário web com autenticação'))
        
        conn.commit()
        conn.close()

        return jsonify({"mensagem": "Agendamento realizado com sucesso!"}), 201

    except Exception as e:
        conn.close()
        return jsonify({"mensagem": "Erro ao salvar no banco", "erro": str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True)