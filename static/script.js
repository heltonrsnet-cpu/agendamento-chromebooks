let usuarioLogadoId = null;
let meuGrafico = null;

// --- 1. LÓGICA DE LOGIN ---
document.getElementById('form-login').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email-login').value;
    const senha = document.getElementById('senha-login').value; // <--- Captura a senha

    fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, senha: senha }) // <--- Envia e-mail e senha
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(resultado => {
        if (resultado.status === 200) {
            usuarioLogadoId = resultado.body.usuario.id;
            document.getElementById('nome-usuario-logado').textContent = resultado.body.usuario.nome;
            document.getElementById('perfil-usuario-logado').textContent = resultado.body.usuario.perfil;
            document.getElementById('secao-login').classList.add('hidden');
            document.getElementById('secao-sistema').classList.remove('hidden');
            carregarDadosDoSistema();
        } else {
            document.getElementById('mensagem-login').textContent = resultado.body.mensagem;
            document.getElementById('mensagem-login').style.color = 'var(--danger)';
        }
    })
    .catch(err => {
        console.error('Erro no login:', err);
        alert('Erro de ligação com o servidor.');
    });
});

// --- 2. LOGOUT ---
function fazerLogout() {
    usuarioLogadoId = null;
    document.getElementById('form-login').reset();
    document.getElementById('mensagem-login').textContent = '';
    document.getElementById('secao-sistema').classList.add('hidden');
    document.getElementById('secao-login').classList.remove('hidden');
}

function carregarDadosDoSistema() {
    carregarEquipamentos();
    carregarEstatisticas();
}

// --- 3. CARREGAR EQUIPAMENTOS (CARRINHOS) ---
function carregarEquipamentos() {
    fetch('/api/equipamentos')
        .then(response => response.json())
        .then(data => {
            const lista = document.getElementById('lista-equipamentos');
            lista.innerHTML = ''; 

            data.forEach(equipamento => {
                const item = document.createElement('li');
                item.className = 'equipamento-item';
                item.innerHTML = `
                    <strong>ID ${equipamento.id}: ${equipamento.identificador}</strong><br>
                    Capacidade: ${equipamento.quantidade_chromebooks} Chromebooks<br>
                    Estado: <em>${equipamento.status}</em>
                `;
                lista.appendChild(item);
            });
        })
        .catch(error => console.error('Erro ao procurar equipamentos:', error));
}

// --- 4. PAINEL DE ESTATÍSTICAS E GRÁFICO ---
function carregarEstatisticas() {
fetch('/api/estatisticas')
.then(response => response.json())
.then(dados => {
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
usuario_id: usuarioLogadoId,
equipamento_id: document.getElementById('equipamento_id').value,
data: document.getElementById('data').value,
inicio: document.getElementById('inicio').value,
fim: document.getElementById('fim').value,
turma: document.getElementById('turma').value
};
fetch('/api/agendamentos', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dadosAgendamento)
})
.then(response => response.json().then(data => ({ status: response.status, body: data })))
.then(resultado => {
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