let meuGrafico = null;

// Faz a requisição e devolve status + corpo JSON; se a sessão expirou, volta para o login
function requisitarApi(url, opcoes = {}) {
    return fetch(url, { credentials: 'same-origin', ...opcoes })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(resultado => {
            if (resultado.status === 401 && url !== '/api/login' && url !== '/api/me') {
                mostrarLogin(resultado.body.mensagem);
            }
            return resultado;
        });
}

function mostrarSistema(usuario) {
    document.getElementById('nome-usuario-logado').textContent = usuario.nome;
    document.getElementById('perfil-usuario-logado').textContent = usuario.perfil;
    document.getElementById('secao-login').classList.add('hidden');
    document.getElementById('secao-sistema').classList.remove('hidden');
    carregarDadosDoSistema();
}

function mostrarLogin(mensagem = '') {
    document.getElementById('form-login').reset();
    const aviso = document.getElementById('mensagem-login');
    aviso.textContent = mensagem;
    aviso.style.color = 'var(--danger)';
    document.getElementById('secao-sistema').classList.add('hidden');
    document.getElementById('secao-login').classList.remove('hidden');
}

// --- 0. RESTAURA A SESSÃO AO RECARREGAR A PÁGINA ---
requisitarApi('/api/me')
    .then(resultado => {
        if (resultado.status === 200) {
            mostrarSistema(resultado.body.usuario);
        }
    })
    .catch(err => console.error('Erro ao verificar sessão:', err));

// --- 1. LÓGICA DE LOGIN ---
document.getElementById('form-login').addEventListener('submit', function(e) {
    e.preventDefault();

    const email = document.getElementById('email-login').value;
    const senha = document.getElementById('senha-login').value;

    requisitarApi('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, senha: senha })
    })
    .then(resultado => {
        if (resultado.status === 200) {
            document.getElementById('mensagem-login').textContent = '';
            mostrarSistema(resultado.body.usuario);
        } else {
            document.getElementById('mensagem-login').textContent = resultado.body.mensagem;
            document.getElementById('mensagem-login').style.color = 'var(--danger)';
        }
    })
    .catch(err => {
        console.error('Erro no login:', err);
        alert('Erro de conexão com o servidor.');
    });
});

// --- 2. LOGOUT ---
function fazerLogout() {
    fetch('/api/logout', { method: 'POST', credentials: 'same-origin' })
        .catch(err => console.error('Erro ao encerrar sessão:', err))
        .finally(() => mostrarLogin());
}

function carregarDadosDoSistema() {
    carregarEquipamentos();
    carregarEstatisticas();
}

// --- 3. CARREGAR EQUIPAMENTOS (CARRINHOS) ---
function carregarEquipamentos() {
    requisitarApi('/api/equipamentos')
        .then(resultado => {
            if (resultado.status !== 200) return;
            const lista = document.getElementById('lista-equipamentos');
            lista.innerHTML = '';

            // Monta os itens com textContent para que dados do banco nunca sejam interpretados como HTML
            resultado.body.forEach(equipamento => {
                const item = document.createElement('li');
                item.className = 'equipamento-item';

                const titulo = document.createElement('strong');
                titulo.textContent = `ID ${equipamento.id}: ${equipamento.identificador}`;
                const estado = document.createElement('em');
                estado.textContent = equipamento.status;

                item.append(
                    titulo, document.createElement('br'),
                    `Capacidade: ${equipamento.quantidade_chromebooks} Chromebooks`, document.createElement('br'),
                    'Estado: ', estado
                );
                lista.appendChild(item);
            });
        })
        .catch(error => console.error('Erro ao buscar equipamentos:', error));
}

// --- 4. PAINEL DE ESTATÍSTICAS E GRÁFICO ---
function carregarEstatisticas() {
    requisitarApi('/api/estatisticas')
        .then(resultado => {
            if (resultado.status !== 200) return;
            const dados = resultado.body;
            document.getElementById('total-reservas').textContent = dados.total_agendamentos;
            const rotulos = dados.por_equipamento.map(item => item.identificador);
            const totais = dados.por_equipamento.map(item => item.total);
            const ctx = document.getElementById('graficoUso').getContext('2d');
            if (meuGrafico) {
                meuGrafico.destroy();
            }

            meuGrafico = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: rotulos,
                    datasets: [{
                        data: totais,
                        backgroundColor: ['#2563eb', '#38bdf8', '#34d399', '#f59e0b', '#ec4899'],
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: { boxWidth: 10, font: { family: 'Inter', size: 10 } }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erro ao carregar estatísticas:', error));
}

// --- 5. NOVO AGENDAMENTO ---
document.getElementById('form-agendamento').addEventListener('submit', function(evento) {
    evento.preventDefault();
    const dadosAgendamento = {
        equipamento_id: document.getElementById('equipamento_id').value,
        data: document.getElementById('data').value,
        inicio: document.getElementById('inicio').value,
        fim: document.getElementById('fim').value,
        turma: document.getElementById('turma').value
    };

    if (dadosAgendamento.fim <= dadosAgendamento.inicio) {
        alert('O horário de fim deve ser posterior ao horário de início.');
        return;
    }

    requisitarApi('/api/agendamentos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dadosAgendamento)
    })
    .then(resultado => {
        if (resultado.status === 401) return;
        alert(resultado.body.mensagem);
        if (resultado.status === 201) {
            document.getElementById('form-agendamento').reset();
            carregarEstatisticas();
        }
    })
    .catch(error => {
        console.error('Erro ao enviar agendamento:', error);
        alert("Erro ao realizar o agendamento.");
    });
});
