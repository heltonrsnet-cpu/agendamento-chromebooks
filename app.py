from flask import Flask, g, jsonify, request, render_template, session, send_from_directory
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(BASE_DIR, 'agendamento_chromebooks.db')

# O servidor pode estar em outro fuso (o PythonAnywhere usa UTC). O Brasil não tem mais horário de verão.
FUSO_ESCOLA = timezone(timedelta(hours=-3))

# Funções que a própria pessoa pode escolher no cadastro. "Administrador" fica de fora de propósito.
FUNCOES_CADASTRO = ['Professor', 'Coordenação', 'Direção']
FUNCAO_ADMIN = 'Administrador'
SENHA_MINIMA = 8

OUTRA_ATIVIDADE = 'Outra atividade'
ETAPAS = {
    'Ensino Fundamental I': {
        'anos': ['1º ano', '2º ano', '3º ano', '4º ano', '5º ano'],
        'finalidades': ['Introdução digital', 'Aprender a digitar', 'Pesquisa supervisionada na internet', OUTRA_ATIVIDADE],
    },
    'Ensino Fundamental II': {
        'anos': ['6º ano', '7º ano', '8º ano', '9º ano'],
        'finalidades': ['Trabalho em grupo', 'Redação', 'Pesquisa', 'Apresentação',
                        'Projeto interdisciplinar (Docs, Planilhas, Slides)', OUTRA_ATIVIDADE],
    },
    'Ensino Médio': {
        'anos': ['1º ano', '2º ano', '3º ano'],
        'finalidades': ['Simulado online', 'Plataforma de redação', 'Estudos para Enem e vestibulares',
                        'Google Classroom (tarefas e materiais)', OUTRA_ATIVIDADE],
    },
}

TIPOS_LOG = ['ENTRADA', 'ENTRADA_RECUSADA', 'SAIDA', 'CADASTRO', 'AGENDAMENTO', 'CANCELAMENTO', 'ADMINISTRACAO']

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

def agora():
    return datetime.now(FUSO_ESCOLA).replace(tzinfo=None)

def data_brasileira(data_iso):
    return '/'.join(reversed(data_iso.split('-')))

def registrar_log(conn, tipo, detalhes='', usuario=None, email=None):
    """Grava um evento na mesma transação da operação; quem chama faz o commit."""
    conn.execute('''
        INSERT INTO logs (criado_em, tipo, usuario_id, usuario_nome, usuario_email, detalhes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        agora().isoformat(timespec='seconds'), tipo,
        usuario['id'] if usuario else None,
        usuario['nome'] if usuario else None,
        usuario['email'] if usuario else email,
        detalhes,
    ))

# Decorador que bloqueia rotas da API para quem não iniciou sessão ou teve o acesso desativado
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        usuario = None
        if 'usuario_id' in session:
            conn = get_db_connection()
            usuario = conn.execute('SELECT * FROM usuarios WHERE id = ? AND ativo = 1', (session['usuario_id'],)).fetchone()
            conn.close()
        if not usuario:
            session.clear()
            return jsonify({"mensagem": "Sessão expirada ou inexistente. Faça login novamente."}), 401
        g.usuario = usuario
        return view(*args, **kwargs)
    return wrapper

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapper(*args, **kwargs):
        if g.usuario['funcao'] != FUNCAO_ADMIN:
            return jsonify({"mensagem": "Acesso restrito ao administrador."}), 403
        return view(*args, **kwargs)
    return wrapper

def usuario_publico(usuario):
    return {
        "id": usuario['id'],
        "nome": usuario['nome'],
        "email": usuario['email'],
        "funcao": usuario['funcao'],
        "admin": usuario['funcao'] == FUNCAO_ADMIN
    }

def ler_periodo(data_texto, inicio_texto, fim_texto):
    """Valida data e horários e devolve os textos normalizados, que podem ser comparados como strings."""
    try:
        data_obj = datetime.strptime(data_texto, '%Y-%m-%d').date()
        inicio_obj = datetime.strptime(inicio_texto, '%H:%M').time()
        fim_obj = datetime.strptime(fim_texto, '%H:%M').time()
    except (TypeError, ValueError):
        raise ValueError("Dados inválidos. Verifique a data e os horários.")
    if fim_obj <= inicio_obj:
        raise ValueError("O horário de fim deve ser posterior ao horário de início.")
    return data_obj.isoformat(), inicio_obj.strftime('%H:%M'), fim_obj.strftime('%H:%M')

def maquinas_livres(conn, data_agendamento, inicio, fim):
    """Máquinas livres durante todo o período: total menos o pico de uso simultâneo."""
    total = conn.execute('SELECT total_chromebooks FROM escola WHERE id = 1').fetchone()[0]
    reservas = conn.execute('''
        SELECT horario_inicio, horario_fim, quantidade FROM agendamentos
        WHERE data_agendamento = ? AND status = 'Reservado' AND ? < horario_fim AND ? > horario_inicio
    ''', (data_agendamento, inicio, fim)).fetchall()

    # O uso só aumenta quando uma reserva começa, então basta medir nesses instantes
    instantes = {inicio} | {r['horario_inicio'] for r in reservas if r['horario_inicio'] > inicio}
    pico = max(
        sum(r['quantidade'] for r in reservas if r['horario_inicio'] <= instante < r['horario_fim'])
        for instante in instantes
    )
    return total, max(total - pico, 0)

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

# --- ROTA: Dados públicos usados nas telas de entrada e cadastro ---
@app.route('/api/opcoes', methods=['GET'])
def opcoes():
    conn = get_db_connection()
    escola = conn.execute('SELECT * FROM escola WHERE id = 1').fetchone()
    conn.close()
    return jsonify({
        "escola": dict(escola),
        "funcoes": FUNCOES_CADASTRO,
        "etapas": ETAPAS,
        "senha_minima": SENHA_MINIMA
    })

# --- ROTA: Cadastro de novos usuários ---
@app.route('/api/cadastro', methods=['POST'])
def cadastro():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get('nome') or '').strip()
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''
    funcao = dados.get('funcao')

    if not all([nome, email, senha, funcao]):
        return jsonify({"mensagem": "Preencha nome, e-mail, senha e função."}), 400
    if len(nome) < 3 or len(nome) > 100:
        return jsonify({"mensagem": "Informe o nome completo (até 100 caracteres)."}), 400
    if len(email) > 254 or not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        return jsonify({"mensagem": "Informe um e-mail válido."}), 400
    if len(senha) < SENHA_MINIMA:
        return jsonify({"mensagem": f"A senha deve ter pelo menos {SENHA_MINIMA} caracteres."}), 400
    if funcao not in FUNCOES_CADASTRO:
        return jsonify({"mensagem": "Escolha uma função válida."}), 400

    conn = get_db_connection()
    try:
        cursor = conn.execute('''
            INSERT INTO usuarios (nome, email, funcao, senha_hash, criado_em) VALUES (?, ?, ?, ?, ?)
        ''', (nome, email, funcao, generate_password_hash(senha), agora().isoformat(timespec='seconds')))
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (cursor.lastrowid,)).fetchone()
        registrar_log(conn, 'CADASTRO', f'Novo cadastro com a função {funcao}', usuario)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"mensagem": "Este e-mail já está cadastrado."}), 409
    finally:
        conn.close()

    session.clear()
    session.permanent = True
    session['usuario_id'] = usuario['id']
    return jsonify({
        "mensagem": f"Cadastro realizado. Bem-vindo(a), {usuario['nome']}!",
        "usuario": usuario_publico(usuario)
    }), 201

# --- ROTA: Autenticação (Login) ---
@app.route('/api/login', methods=['POST'])
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get('email') or '').strip().lower()
    senha = dados.get('senha') or ''

    if not email or not senha:
        return jsonify({"mensagem": "Informe o e-mail e a senha de acesso!"}), 400

    conn = get_db_connection()
    usuario = conn.execute('SELECT * FROM usuarios WHERE email = ?', (email,)).fetchone()

    # Verifica se o usuário existe E se a senha confere com o hash do banco
    if not usuario or not check_password_hash(usuario['senha_hash'], senha):
        registrar_log(conn, 'ENTRADA_RECUSADA', 'E-mail ou senha incorretos', email=email[:254])
        conn.commit()
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "E-mail ou senha incorretos."}), 401

    if not usuario['ativo']:
        registrar_log(conn, 'ENTRADA_RECUSADA', 'Acesso desativado', usuario)
        conn.commit()
        conn.close()
        return jsonify({"sucesso": False, "mensagem": "Seu acesso foi desativado. Procure a administração."}), 403

    registrar_log(conn, 'ENTRADA', '', usuario)
    conn.commit()
    conn.close()

    session.clear()
    session.permanent = True
    session['usuario_id'] = usuario['id']
    return jsonify({
        "sucesso": True,
        "mensagem": f"Bem-vindo(a), {usuario['nome']}!",
        "usuario": usuario_publico(usuario)
    }), 200

# --- ROTA: Encerrar sessão ---
@app.route('/api/logout', methods=['POST'])
def logout():
    usuario_id = session.get('usuario_id')
    if usuario_id:
        conn = get_db_connection()
        usuario = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
        if usuario:
            registrar_log(conn, 'SAIDA', '', usuario)
            conn.commit()
        conn.close()
    session.clear()
    return jsonify({"sucesso": True}), 200

# --- ROTA: Usuário da sessão atual (usada ao recarregar a página) ---
@app.route('/api/me', methods=['GET'])
@login_required
def usuario_atual():
    return jsonify({"usuario": usuario_publico(g.usuario)}), 200

# --- ROTA: Máquinas livres em um período ---
@app.route('/api/disponibilidade', methods=['GET'])
@login_required
def disponibilidade():
    try:
        periodo = ler_periodo(request.args.get('data'), request.args.get('inicio'), request.args.get('fim'))
    except ValueError as erro:
        return jsonify({"mensagem": str(erro)}), 400

    conn = get_db_connection()
    total, livres = maquinas_livres(conn, *periodo)
    conn.close()
    return jsonify({"total": total, "livres": livres})

# --- ROTA: Agenda da escola em um intervalo de dias ---
@app.route('/api/agenda', methods=['GET'])
@login_required
def agenda():
    try:
        inicio = datetime.strptime(request.args.get('inicio', ''), '%Y-%m-%d').date()
    except ValueError:
        inicio = agora().date()
    dias = min(max(request.args.get('dias', 7, type=int), 1), 31)
    fim = inicio + timedelta(days=dias - 1)

    conn = get_db_connection()
    reservas = conn.execute('''
        SELECT a.id, a.usuario_id, a.data_agendamento, a.horario_inicio, a.horario_fim, a.quantidade,
               a.etapa, a.ano, a.turma, a.finalidade, u.nome AS professor
        FROM agendamentos a JOIN usuarios u ON u.id = a.usuario_id
        WHERE a.status = 'Reservado' AND a.data_agendamento BETWEEN ? AND ?
        ORDER BY a.data_agendamento, a.horario_inicio
    ''', (inicio.isoformat(), fim.isoformat())).fetchall()
    total = conn.execute('SELECT total_chromebooks FROM escola WHERE id = 1').fetchone()[0]
    conn.close()

    hoje = agora().date().isoformat()
    pode_cancelar_todos = g.usuario['funcao'] == FUNCAO_ADMIN
    return jsonify({
        "total": total,
        "agendamentos": [
            {**dict(r), "pode_cancelar": r['data_agendamento'] >= hoje and (pode_cancelar_todos or r['usuario_id'] == g.usuario['id'])}
            for r in reservas
        ]
    })

# --- ROTA: Agendamentos do próprio usuário ---
@app.route('/api/agendamentos/meus', methods=['GET'])
@login_required
def meus_agendamentos():
    conn = get_db_connection()
    reservas = conn.execute('''
        SELECT id, data_agendamento, horario_inicio, horario_fim, quantidade, etapa, ano, turma, finalidade, status
        FROM agendamentos WHERE usuario_id = ?
        ORDER BY data_agendamento DESC, horario_inicio DESC LIMIT 100
    ''', (g.usuario['id'],)).fetchall()
    conn.close()

    hoje = agora().date().isoformat()
    return jsonify([
        {**dict(r), "pode_cancelar": r['status'] == 'Reservado' and r['data_agendamento'] >= hoje}
        for r in reservas
    ])

# --- ROTA: Novo agendamento, limitado às máquinas livres no período ---
@app.route('/api/agendamentos', methods=['POST'])
@login_required
def criar_agendamento():
    dados = request.get_json(silent=True) or {}

    # O usuário vem sempre da sessão, nunca do corpo da requisição
    etapa = dados.get('etapa')
    ano = dados.get('ano')
    turma = (dados.get('turma') or '').strip()
    finalidade = dados.get('finalidade')

    if not all([dados.get('data'), dados.get('inicio'), dados.get('fim'), dados.get('quantidade'), etapa, ano, turma, finalidade]):
        return jsonify({"mensagem": "Todos os campos são obrigatórios!"}), 400

    try:
        data_agendamento, inicio, fim = ler_periodo(dados.get('data'), dados.get('inicio'), dados.get('fim'))
    except ValueError as erro:
        return jsonify({"mensagem": str(erro)}), 400

    momento = agora()
    if (data_agendamento, inicio) < (momento.date().isoformat(), momento.strftime('%H:%M')):
        return jsonify({"mensagem": "Não é possível agendar em uma data ou horário que já passou."}), 400

    try:
        quantidade = int(dados.get('quantidade'))
    except (TypeError, ValueError):
        return jsonify({"mensagem": "Informe uma quantidade de máquinas válida."}), 400
    if quantidade < 1:
        return jsonify({"mensagem": "Informe pelo menos 1 máquina."}), 400

    if etapa not in ETAPAS or ano not in ETAPAS[etapa]['anos'] or finalidade not in ETAPAS[etapa]['finalidades']:
        return jsonify({"mensagem": "Escolha a etapa, o ano e a finalidade entre as opções da lista."}), 400
    if len(turma) > 20:
        return jsonify({"mensagem": "O campo Turma deve ter no máximo 20 caracteres."}), 400

    conn = get_db_connection()

    try:
        # BEGIN IMMEDIATE impede que duas requisições simultâneas reservem as mesmas máquinas
        conn.execute('BEGIN IMMEDIATE')

        total, livres = maquinas_livres(conn, data_agendamento, inicio, fim)
        if quantidade > livres:
            conn.rollback()
            return jsonify({
                "mensagem": f"Só há {livres} de {total} máquinas livres nesse horário.",
                "livres": livres
            }), 409

        conn.execute('''
            INSERT INTO agendamentos (usuario_id, data_agendamento, horario_inicio, horario_fim, quantidade, etapa, ano, turma, finalidade, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (g.usuario['id'], data_agendamento, inicio, fim, quantidade, etapa, ano, turma, finalidade, momento.isoformat(timespec='seconds')))

        registrar_log(conn, 'AGENDAMENTO',
                      f'{quantidade} máquina(s) em {data_brasileira(data_agendamento)}, {inicio}-{fim}, {ano} {turma} ({etapa}): {finalidade}',
                      g.usuario)
        conn.commit()
        return jsonify({"mensagem": "Agendamento realizado com sucesso!"}), 201

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception('Erro ao salvar agendamento')
        return jsonify({"mensagem": "Erro ao salvar o agendamento. Tente novamente."}), 500
    finally:
        conn.close()

# --- ROTA: Cancelar agendamento (o próprio, ou qualquer um se for administrador) ---
@app.route('/api/agendamentos/<int:agendamento_id>/cancelar', methods=['POST'])
@login_required
def cancelar_agendamento(agendamento_id):
    conn = get_db_connection()
    try:
        reserva = conn.execute('''
            SELECT a.*, u.nome AS professor FROM agendamentos a JOIN usuarios u ON u.id = a.usuario_id WHERE a.id = ?
        ''', (agendamento_id,)).fetchone()

        if not reserva:
            return jsonify({"mensagem": "Agendamento não encontrado."}), 404
        if reserva['usuario_id'] != g.usuario['id'] and g.usuario['funcao'] != FUNCAO_ADMIN:
            return jsonify({"mensagem": "Você só pode cancelar os seus próprios agendamentos."}), 403
        if reserva['status'] != 'Reservado':
            return jsonify({"mensagem": "Este agendamento já foi cancelado."}), 409
        if reserva['data_agendamento'] < agora().date().isoformat():
            return jsonify({"mensagem": "Não é possível cancelar um agendamento de data passada."}), 400

        conn.execute("UPDATE agendamentos SET status = 'Cancelado' WHERE id = ?", (agendamento_id,))
        registrar_log(conn, 'CANCELAMENTO',
                      f"Agendamento de {reserva['professor']}: {reserva['quantidade']} máquina(s) em "
                      f"{data_brasileira(reserva['data_agendamento'])}, {reserva['horario_inicio']}-{reserva['horario_fim']}",
                      g.usuario)
        conn.commit()
        return jsonify({"mensagem": "Agendamento cancelado."}), 200
    finally:
        conn.close()

# --- ADMINISTRAÇÃO: logs ---
@app.route('/api/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    tipo = request.args.get('tipo') or None
    antes_de = request.args.get('antes_de', type=int)
    limite = min(max(request.args.get('limite', 50, type=int), 1), 200)

    condicoes, parametros = [], []
    if tipo in TIPOS_LOG:
        condicoes.append('tipo = ?')
        parametros.append(tipo)
    if antes_de:
        condicoes.append('id < ?')
        parametros.append(antes_de)
    where = f"WHERE {' AND '.join(condicoes)}" if condicoes else ''

    conn = get_db_connection()
    logs = conn.execute(f'SELECT * FROM logs {where} ORDER BY id DESC LIMIT ?', (*parametros, limite + 1)).fetchall()
    resumo = conn.execute('SELECT tipo, COUNT(*) AS total FROM logs GROUP BY tipo').fetchall()
    conn.close()

    return jsonify({
        "logs": [dict(log) for log in logs[:limite]],
        "tem_mais": len(logs) > limite,
        "resumo": {linha['tipo']: linha['total'] for linha in resumo}
    })

# --- ADMINISTRAÇÃO: estatísticas de uso ---
@app.route('/api/admin/estatisticas', methods=['GET'])
@admin_required
def admin_estatisticas():
    conn = get_db_connection()
    total_agendamentos = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE status = 'Reservado'").fetchone()[0]
    total_usuarios = conn.execute('SELECT COUNT(*) FROM usuarios').fetchone()[0]
    por_etapa = conn.execute('''
        SELECT etapa, COUNT(*) AS total FROM agendamentos WHERE status = 'Reservado' GROUP BY etapa
    ''').fetchall()
    conn.close()
    return jsonify({
        "total_agendamentos": total_agendamentos,
        "total_usuarios": total_usuarios,
        "por_etapa": [dict(linha) for linha in por_etapa]
    })

# --- ADMINISTRAÇÃO: usuários ---
@app.route('/api/admin/usuarios', methods=['GET'])
@admin_required
def admin_usuarios():
    conn = get_db_connection()
    usuarios = conn.execute('''
        SELECT u.id, u.nome, u.email, u.funcao, u.ativo, u.criado_em,
               (SELECT COUNT(*) FROM agendamentos a WHERE a.usuario_id = u.id AND a.status = 'Reservado') AS agendamentos
        FROM usuarios u ORDER BY u.nome
    ''').fetchall()
    conn.close()
    return jsonify([dict(usuario) for usuario in usuarios])

@app.route('/api/admin/usuarios/<int:usuario_id>/ativo', methods=['POST'])
@admin_required
def admin_alterar_ativo(usuario_id):
    dados = request.get_json(silent=True) or {}
    ativo = dados.get('ativo')
    if not isinstance(ativo, bool):
        return jsonify({"mensagem": "Informe se o acesso fica ativo ou não."}), 400
    if usuario_id == g.usuario['id']:
        return jsonify({"mensagem": "Você não pode desativar o seu próprio acesso."}), 400

    conn = get_db_connection()
    try:
        alvo = conn.execute('SELECT * FROM usuarios WHERE id = ?', (usuario_id,)).fetchone()
        if not alvo:
            return jsonify({"mensagem": "Usuário não encontrado."}), 404
        conn.execute('UPDATE usuarios SET ativo = ? WHERE id = ?', (int(ativo), usuario_id))
        acao = 'reativado' if ativo else 'desativado'
        registrar_log(conn, 'ADMINISTRACAO', f"Acesso de {alvo['nome']} ({alvo['email']}) {acao}", g.usuario)
        conn.commit()
        return jsonify({"mensagem": f"Acesso {acao}."}), 200
    finally:
        conn.close()


if __name__ == '__main__':
    # Nunca deixe o modo debug ligado em um servidor acessível pela rede:
    # o depurador do Werkzeug permite executar código remotamente.
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1')
