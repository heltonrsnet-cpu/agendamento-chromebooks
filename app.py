from flask import Flask, jsonify, request, render_template, session, send_from_directory
import os
import secrets
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from werkzeug.security import check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'agendamento_chromebooks.db')

app = Flask(__name__)

# Chave usada para assinar o cookie de sessão. Em produção, defina SECRET_KEY no ambiente;
# sem ela, uma chave aleatória é gerada e as sessões se perdem a cada reinício do servidor.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE') == '1',
    PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
)

# Função auxiliar para conectar ao banco de dados
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

# Decorador que bloqueia rotas da API para quem não iniciou sessão
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'usuario_id' not in session:
            return jsonify({"mensagem": "Sessão expirada ou inexistente. Faça login novamente."}), 401
        return view(*args, **kwargs)
    return wrapper

def usuario_publico(usuario):
    return {
        "id": usuario['id'],
        "nome": usuario['nome'],
        "perfil": usuario['perfil']
    }

# Rota principal - Carrega a interface visual
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# --- PWA: manifesto e service worker servidos na raiz, para que o app inteiro fique no escopo ---
@app.route('/manifest.webmanifest', methods=['GET'])
def manifest():
    return send_from_directory(app.static_folder, 'manifest.webmanifest', mimetype='application/manifest+json')

@app.route('/sw.js', methods=['GET'])
def service_worker():
    resposta = send_from_directory(app.static_folder, 'sw.js', mimetype='application/javascript')
    # Sem cache, para que o navegador sempre encontre a versão mais nova do service worker
    resposta.headers['Cache-Control'] = 'no-cache'
    return resposta

# Rota para listar todos os equipamentos (A API)
@app.route('/api/equipamentos', methods=['GET'])
@login_required
def get_equipamentos():
    conn = get_db_connection()
    equipamentos = conn.execute('SELECT * FROM equipamentos').fetchall()
    conn.close()
    resultado = [dict(row) for row in equipamentos]
    return jsonify(resultado)

# --- Estatísticas de Uso ---
@app.route('/api/estatisticas', methods=['GET'])
@login_required
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
    dados = request.get_json(silent=True) or {}
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not email or not senha:
        return jsonify({"mensagem": "Informe o e-mail e a senha de acesso!"}), 400

    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE lower(email) = ?', (email,)).fetchone()
    conn.close()

    # Verifica se o usuário existe E se a senha confere com o hash do banco
    if usuario and check_password_hash(usuario['senha_hash'], senha):
        session.clear()
        session.permanent = True
        session['usuario_id'] = usuario['id']
        return jsonify({
            "sucesso": True,
            "mensagem": f"Bem-vindo(a), {usuario['nome']}!",
            "usuario": usuario_publico(usuario)
        }), 200

    return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos."}), 401

# --- ROTA: Encerrar sessão ---
@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"sucesso": True}), 200

# --- ROTA: Usuário da sessão atual (usada ao recarregar a página) ---
@app.route('/api/me', methods=['GET'])
@login_required
def usuario_atual():
    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (session['usuario_id'],)).fetchone()
    conn.close()

    if not usuario:
        session.clear()
        return jsonify({"mensagem": "Usuário não encontrado."}), 401

    return jsonify({"usuario": usuario_publico(usuario)}), 200

# --- ROTA: Agendamentos com Validação de Conflito e Vínculo de Usuário ---
@app.route('/api/agendamentos', methods=['POST'])
@login_required
def criar_agendamento():
    dados = request.get_json(silent=True) or {}

    # O usuário vem sempre da sessão, nunca do corpo da requisição
    usuario_id = session['usuario_id']
    equipamento_id = dados.get('equipamento_id')
    data_agendamento = dados.get('data')
    horario_inicio = dados.get('inicio')
    horario_fim = dados.get('fim')
    turma = (dados.get('turma') or '').strip()

    if not all([equipamento_id, data_agendamento, horario_inicio, horario_fim, turma]):
        return jsonify({"mensagem": "Todos os campos são obrigatórios!"}), 400

    # Validação de formato e coerência dos dados
    try:
        equipamento_id = int(equipamento_id)
        data_obj = datetime.strptime(data_agendamento, '%Y-%m-%d').date()
        inicio_obj = datetime.strptime(horario_inicio, '%H:%M').time()
        fim_obj = datetime.strptime(horario_fim, '%H:%M').time()
    except (TypeError, ValueError):
        return jsonify({"mensagem": "Dados inválidos. Verifique o carrinho, a data e os horários."}), 400

    if data_obj < date.today():
        return jsonify({"mensagem": "Não é possível agendar em uma data passada."}), 400
    if fim_obj <= inicio_obj:
        return jsonify({"mensagem": "O horário de fim deve ser posterior ao horário de início."}), 400
    if len(turma) > 100:
        return jsonify({"mensagem": "O campo Turma/Disciplina deve ter no máximo 100 caracteres."}), 400

    # Normaliza para o formato gravado no banco (permite comparar horários como texto)
    data_agendamento = data_obj.isoformat()
    horario_inicio = inicio_obj.strftime('%H:%M')
    horario_fim = fim_obj.strftime('%H:%M')

    conn = get_db_connection()

    try:
        # BEGIN IMMEDIATE impede que duas requisições simultâneas passem pela checagem de conflito
        conn.execute('BEGIN IMMEDIATE')

        equipamento = conn.execute('SELECT status FROM equipamentos WHERE id = ?', (equipamento_id,)).fetchone()
        if not equipamento:
            conn.rollback()
            return jsonify({"mensagem": "Carrinho não encontrado."}), 404
        if equipamento['status'] != 'Disponível':
            conn.rollback()
            return jsonify({"mensagem": f"Este carrinho não pode ser agendado (estado: {equipamento['status']})."}), 409

        # Verificação de choque de horários
        query_conflito = '''
            SELECT 1 FROM agendamentos
            WHERE equipamento_id = ?
              AND data_agendamento = ?
              AND status != 'Cancelado'
              AND (
                  (? < horario_fim) AND (? > horario_inicio)
              )
        '''
        conflito = conn.execute(query_conflito, (equipamento_id, data_agendamento, horario_inicio, horario_fim)).fetchone()

        if conflito:
            conn.rollback()
            return jsonify({
                "mensagem": "Conflito de horário! Este carrinho já possui um agendamento conflitante neste período."
            }), 409

        # Inserção com o ID real do professor autenticado
        conn.execute('''
            INSERT INTO agendamentos (usuario_id, equipamento_id, data_agendamento, horario_inicio, horario_fim, turma, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (usuario_id, equipamento_id, data_agendamento, horario_inicio, horario_fim, turma, 'Reservado', 'Criado via formulário web com autenticação'))

        conn.commit()
        return jsonify({"mensagem": "Agendamento realizado com sucesso!"}), 201

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception('Erro ao salvar agendamento')
        return jsonify({"mensagem": "Erro ao salvar o agendamento. Tente novamente."}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    # Nunca deixe o modo debug ligado em um servidor acessível pela rede:
    # o depurador do Werkzeug permite executar código remotamente.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
