let meuGrafico = null;
let usuarioAtual = null;
let opcoes = null;
let inicioSemana = segundaDaSemana(new Date());
let ultimoLogId = null;

const DIAS_SEMANA = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado'];
const NOMES_LOG = {
    ENTRADA: 'Entrada',
    ENTRADA_RECUSADA: 'Entrada recusada',
    SAIDA: 'Saída',
    CADASTRO: 'Cadastro',
    AGENDAMENTO: 'Agendamento',
    CANCELAMENTO: 'Cancelamento',
    ADMINISTRACAO: 'Administração'
};

const $ = id => document.getElementById(id);

// Cria elementos com textContent, para que dados do banco nunca sejam interpretados como HTML
function criar(tag, classe, ...filhos) {
    const elemento = document.createElement(tag);
    if (classe) elemento.className = classe;
    elemento.append(...filhos);
    return elemento;
}

function mostrarMensagem(id, texto, tipo = 'erro') {
    const aviso = $(id);
    aviso.textContent = texto;
    aviso.dataset.tipo = tipo;
}

// Faz a requisição e devolve status + corpo JSON; se a sessão expirou, volta para o login
function requisitarApi(url, opcoesFetch = {}) {
    return fetch(url, { credentials: 'same-origin', ...opcoesFetch })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(resultado => {
            if (resultado.status === 401 && usuarioAtual) {
                mostrarEntrada(resultado.body.mensagem);
            }
            return resultado;
        });
}

function enviarJson(url, dados) {
    return requisitarApi(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dados)
    });
}

// --- DATAS (sempre no horário local do aparelho) ---
function isoData(data) {
    const mes = String(data.getMonth() + 1).padStart(2, '0');
    const dia = String(data.getDate()).padStart(2, '0');
    return `${data.getFullYear()}-${mes}-${dia}`;
}

function lerData(texto) {
    const [ano, mes, dia] = texto.split('-').map(Number);
    return new Date(ano, mes - 1, dia);
}

function somarDias(data, dias) {
    return new Date(data.getFullYear(), data.getMonth(), data.getDate() + dias);
}

function segundaDaSemana(data) {
    return somarDias(data, -((data.getDay() + 6) % 7));
}

function dataCurta(data) {
    return data.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function dataHoraLog(texto) {
    const [data, hora] = texto.split('T');
    return `${data.split('-').reverse().join('/')} ${hora}`;
}

// --- ENTRADA NO SISTEMA ---
function mostrarSistema(usuario) {
    usuarioAtual = usuario;
    $('nome-usuario-logado').textContent = usuario.nome;
    $('funcao-usuario-logado').textContent = usuario.funcao;
    $('aba-admin').classList.toggle('hidden', !usuario.admin);
    $('secao-entrada').classList.add('hidden');
    $('secao-sistema').classList.remove('hidden');
    abrirAba('agenda');
}

function mostrarEntrada(mensagem = '') {
    usuarioAtual = null;
    $('form-login').reset();
    $('form-cadastro').reset();
    limparDadosDaSessao();
    alternarCartaoEntrada(false);
    mostrarMensagem('mensagem-login', mensagem);
    $('secao-sistema').classList.add('hidden');
    $('secao-entrada').classList.remove('hidden');
}

// O aparelho pode ser compartilhado: nada da sessão anterior fica na tela para o próximo usuário
function limparDadosDaSessao() {
    $('form-agendamento').reset();
    $('etapa').dispatchEvent(new Event('change'));
    ['lista-agenda', 'lista-meus', 'corpo-logs', 'corpo-usuarios'].forEach(id => $(id).replaceChildren());
    ['mensagem-agenda', 'mensagem-agendamento', 'mensagem-meus', 'mensagem-logs', 'mensagem-usuarios'].forEach(id => mostrarMensagem(id, ''));
    $('filtro-log').value = '';
    ultimoLogId = null;
    inicioSemana = segundaDaSemana(new Date());
}

function alternarCartaoEntrada(cadastro) {
    $('cartao-login').classList.toggle('hidden', cadastro);
    $('cartao-cadastro').classList.toggle('hidden', !cadastro);
    mostrarMensagem('mensagem-login', '');
    mostrarMensagem('mensagem-cadastro', '');
}

$('ir-cadastro').addEventListener('click', () => alternarCartaoEntrada(true));
$('ir-login').addEventListener('click', () => alternarCartaoEntrada(false));

$('form-login').addEventListener('submit', function(e) {
    e.preventDefault();
    enviarJson('/api/login', { email: $('email-login').value, senha: $('senha-login').value })
        .then(resultado => {
            if (resultado.status === 200) {
                $('form-login').reset();
                mostrarMensagem('mensagem-login', '');
                mostrarSistema(resultado.body.usuario);
            } else {
                mostrarMensagem('mensagem-login', resultado.body.mensagem);
            }
        })
        .catch(err => {
            console.error('Erro no login:', err);
            mostrarMensagem('mensagem-login', 'Erro de conexão com o servidor.');
        });
});

$('form-cadastro').addEventListener('submit', function(e) {
    e.preventDefault();
    enviarJson('/api/cadastro', {
        nome: $('cadastro-nome').value,
        email: $('cadastro-email').value,
        senha: $('cadastro-senha').value,
        funcao: $('cadastro-funcao').value
    })
        .then(resultado => {
            if (resultado.status === 201) {
                $('form-cadastro').reset();
                mostrarMensagem('mensagem-cadastro', '');
                mostrarSistema(resultado.body.usuario);
            } else {
                mostrarMensagem('mensagem-cadastro', resultado.body.mensagem);
            }
        })
        .catch(err => {
            console.error('Erro no cadastro:', err);
            mostrarMensagem('mensagem-cadastro', 'Erro de conexão com o servidor.');
        });
});

$('botao-sair').addEventListener('click', () => {
    fetch('/api/logout', { method: 'POST', credentials: 'same-origin' })
        .catch(err => console.error('Erro ao encerrar sessão:', err))
        .finally(() => mostrarEntrada());
});

// --- ABAS ---
const CARREGAR_ABA = {
    agenda: carregarAgenda,
    novo: prepararFormulario,
    meus: carregarMeus,
    admin: carregarAdministracao
};

function abrirAba(nome) {
    document.querySelectorAll('.aba').forEach(aba => {
        const ativa = aba.dataset.aba === nome;
        aba.classList.toggle('ativa', ativa);
        if (ativa) aba.setAttribute('aria-current', 'page');
        else aba.removeAttribute('aria-current');
    });
    document.querySelectorAll('.painel').forEach(painel => {
        painel.classList.toggle('hidden', painel.id !== `painel-${nome}`);
    });
    CARREGAR_ABA[nome]();
}

document.querySelectorAll('.aba').forEach(aba => {
    aba.addEventListener('click', () => abrirAba(aba.dataset.aba));
});

// --- AGENDA DA SEMANA ---
function cartaoAgendamento(reserva, aoCancelar) {
    const titulo = criar('strong', '', `${reserva.horario_inicio} às ${reserva.horario_fim}`);
    const quantidade = criar('span', 'etiqueta', `${reserva.quantidade} ${reserva.quantidade === 1 ? 'máquina' : 'máquinas'}`);
    const cabecalho = criar('div', 'reserva-topo', titulo, quantidade);

    const cartao = criar('div', 'reserva', cabecalho,
        criar('p', '', `${reserva.ano} ${reserva.turma} · ${reserva.etapa}`),
        criar('p', 'discreto', reserva.finalidade));

    if (reserva.professor) cartao.append(criar('p', 'discreto', reserva.professor));

    if (reserva.pode_cancelar) {
        const botao = criar('button', 'link link-perigo', 'Cancelar');
        botao.addEventListener('click', () => cancelarAgendamento(reserva, aoCancelar));
        cartao.append(botao);
    }
    return cartao;
}

function cancelarAgendamento(reserva, aoCancelar) {
    const data = lerData(reserva.data_agendamento);
    if (!confirm(`Cancelar o agendamento de ${dataCurta(data)}, das ${reserva.horario_inicio} às ${reserva.horario_fim}?`)) return;

    requisitarApi(`/api/agendamentos/${reserva.id}/cancelar`, { method: 'POST' })
        .then(resultado => {
            if (resultado.status !== 401) aoCancelar(resultado);
        })
        .catch(err => console.error('Erro ao cancelar:', err));
}

function carregarAgenda() {
    const fimSemana = somarDias(inicioSemana, 6);
    $('titulo-semana').textContent = `${dataCurta(inicioSemana)} a ${dataCurta(fimSemana)}`;

    requisitarApi(`/api/agenda?inicio=${isoData(inicioSemana)}&dias=7`)
        .then(resultado => {
            if (resultado.status !== 200) return;
            const { agendamentos, total } = resultado.body;
            const lista = $('lista-agenda');
            lista.replaceChildren();
            const hoje = isoData(new Date());

            for (let i = 0; i < 7; i++) {
                const dia = somarDias(inicioSemana, i);
                const chave = isoData(dia);
                const doDia = agendamentos.filter(reserva => reserva.data_agendamento === chave);

                // Sábado e domingo só aparecem quando têm agendamento
                if (i >= 5 && doDia.length === 0) continue;

                const nome = `${DIAS_SEMANA[dia.getDay()]}, ${dataCurta(dia)}`;
                const bloco = criar('div', chave === hoje ? 'dia dia-hoje' : 'dia',
                    criar('h3', '', chave === hoje ? `${nome} (hoje)` : nome));

                if (doDia.length === 0) {
                    bloco.append(criar('p', 'discreto', `Sem agendamentos: ${total} máquinas livres.`));
                } else {
                    doDia.forEach(reserva => bloco.append(cartaoAgendamento(reserva, res => {
                        mostrarMensagem('mensagem-agenda', res.body.mensagem, res.status === 200 ? 'sucesso' : 'erro');
                        carregarAgenda();
                    })));
                }
                lista.append(bloco);
            }
        })
        .catch(err => {
            console.error('Erro ao carregar a agenda:', err);
            mostrarMensagem('mensagem-agenda', 'Não foi possível carregar a agenda.');
        });
}

$('semana-anterior').addEventListener('click', () => {
    inicioSemana = somarDias(inicioSemana, -7);
    mostrarMensagem('mensagem-agenda', '');
    carregarAgenda();
});
$('semana-seguinte').addEventListener('click', () => {
    inicioSemana = somarDias(inicioSemana, 7);
    mostrarMensagem('mensagem-agenda', '');
    carregarAgenda();
});
$('semana-atual').addEventListener('click', () => {
    inicioSemana = segundaDaSemana(new Date());
    mostrarMensagem('mensagem-agenda', '');
    carregarAgenda();
});

// --- NOVO AGENDAMENTO ---
function preencherSeletor(seletor, valores) {
    seletor.length = 1; // mantém só a primeira opção ("Selecione...")
    valores.forEach(valor => seletor.add(new Option(valor, valor)));
}

function prepararFormulario() {
    $('data').min = isoData(new Date());
    mostrarMensagem('mensagem-agendamento', '');
    atualizarDisponibilidade();
}

$('etapa').addEventListener('change', () => {
    const etapa = opcoes && opcoes.etapas[$('etapa').value];
    preencherSeletor($('ano'), etapa ? etapa.anos : []);
    preencherSeletor($('finalidade'), etapa ? etapa.finalidades : []);
    $('ano').disabled = !etapa;
    $('finalidade').disabled = !etapa;
});

function atualizarDisponibilidade() {
    const data = $('data').value, inicio = $('inicio').value, fim = $('fim').value;
    const aviso = $('aviso-disponibilidade');
    const total = opcoes ? opcoes.escola.total_chromebooks : 0;

    $('quantidade').max = total;
    if (!data || !inicio || !fim) {
        aviso.textContent = `A escola tem ${total} máquinas. Informe data e horários para ver quantas estão livres.`;
        aviso.dataset.tipo = '';
        return;
    }
    if (fim <= inicio) {
        aviso.textContent = 'O horário de fim deve ser posterior ao de início.';
        aviso.dataset.tipo = 'erro';
        return;
    }

    const parametros = new URLSearchParams({ data, inicio, fim });
    requisitarApi(`/api/disponibilidade?${parametros}`)
        .then(resultado => {
            if (resultado.status !== 200) return;
            const { livres, total } = resultado.body;
            aviso.textContent = livres > 0
                ? `${livres} de ${total} máquinas livres nesse horário.`
                : 'Todas as máquinas estão reservadas nesse horário.';
            aviso.dataset.tipo = livres > 0 ? 'sucesso' : 'erro';
            $('quantidade').max = Math.max(livres, 1);
        })
        .catch(err => console.error('Erro ao consultar disponibilidade:', err));
}

['data', 'inicio', 'fim'].forEach(id => $(id).addEventListener('change', atualizarDisponibilidade));

$('form-agendamento').addEventListener('submit', function(evento) {
    evento.preventDefault();
    const dadosAgendamento = {
        data: $('data').value,
        inicio: $('inicio').value,
        fim: $('fim').value,
        quantidade: $('quantidade').value,
        etapa: $('etapa').value,
        ano: $('ano').value,
        turma: $('turma').value,
        finalidade: $('finalidade').value
    };

    enviarJson('/api/agendamentos', dadosAgendamento)
        .then(resultado => {
            if (resultado.status === 401) return;
            if (resultado.status === 201) {
                $('form-agendamento').reset();
                $('etapa').dispatchEvent(new Event('change'));
                mostrarMensagem('mensagem-agendamento', resultado.body.mensagem, 'sucesso');
            } else {
                mostrarMensagem('mensagem-agendamento', resultado.body.mensagem);
            }
            atualizarDisponibilidade();
        })
        .catch(error => {
            console.error('Erro ao enviar agendamento:', error);
            mostrarMensagem('mensagem-agendamento', 'Erro ao realizar o agendamento.');
        });
});

// --- MEUS AGENDAMENTOS ---
function carregarMeus() {
    requisitarApi('/api/agendamentos/meus')
        .then(resultado => {
            if (resultado.status !== 200) return;
            const lista = $('lista-meus');
            lista.replaceChildren();

            if (resultado.body.length === 0) {
                lista.append(criar('p', 'discreto', 'Você ainda não tem agendamentos.'));
                return;
            }

            resultado.body.forEach(reserva => {
                const data = lerData(reserva.data_agendamento);
                const bloco = criar('div', reserva.status === 'Cancelado' ? 'dia cancelado' : 'dia',
                    criar('h3', '', `${DIAS_SEMANA[data.getDay()]}, ${dataCurta(data)}` +
                        (reserva.status === 'Cancelado' ? ' (cancelado)' : '')),
                    cartaoAgendamento(reserva, res => {
                        mostrarMensagem('mensagem-meus', res.body.mensagem, res.status === 200 ? 'sucesso' : 'erro');
                        carregarMeus();
                    }));
                lista.append(bloco);
            });
        })
        .catch(err => {
            console.error('Erro ao carregar agendamentos:', err);
            mostrarMensagem('mensagem-meus', 'Não foi possível carregar seus agendamentos.');
        });
}

// --- ADMINISTRAÇÃO ---
function carregarAdministracao() {
    carregarEstatisticas();
    carregarLogs();
    carregarUsuarios();
}

function carregarEstatisticas() {
    requisitarApi('/api/admin/estatisticas')
        .then(resultado => {
            if (resultado.status !== 200) return;
            const dados = resultado.body;
            $('total-reservas').textContent = dados.total_agendamentos;
            $('total-usuarios').textContent = dados.total_usuarios;

            if (meuGrafico) {
                meuGrafico.destroy();
            }

            meuGrafico = new Chart($('graficoUso').getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: dados.por_etapa.map(item => item.etapa),
                    datasets: [{
                        data: dados.por_etapa.map(item => item.total),
                        backgroundColor: ['#2563eb', '#38bdf8', '#f59e0b'],
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
                            labels: { boxWidth: 10, font: { size: 11 } }
                        }
                    }
                }
            });
        })
        .catch(error => console.error('Erro ao carregar estatísticas:', error));
}

function carregarLogs(continuar = false) {
    const parametros = new URLSearchParams({ tipo: $('filtro-log').value });
    if (continuar && ultimoLogId) parametros.set('antes_de', ultimoLogId);

    requisitarApi(`/api/admin/logs?${parametros}`)
        .then(resultado => {
            if (resultado.status !== 200) return;
            const { logs, tem_mais, resumo } = resultado.body;
            atualizarFiltroLogs(resumo);

            const corpo = $('corpo-logs');
            if (!continuar) corpo.replaceChildren();

            logs.forEach(log => {
                const usuario = log.usuario_nome ? `${log.usuario_nome} (${log.usuario_email})` : (log.usuario_email || '-');
                corpo.append(criar('tr', '',
                    criar('td', 'sem-quebra', dataHoraLog(log.criado_em)),
                    criar('td', 'sem-quebra', NOMES_LOG[log.tipo] || log.tipo),
                    criar('td', '', usuario),
                    criar('td', '', log.detalhes || '-')));
            });

            if (logs.length > 0) ultimoLogId = logs[logs.length - 1].id;
            $('mais-logs').classList.toggle('hidden', !tem_mais);
            mostrarMensagem('mensagem-logs', !continuar && logs.length === 0 ? 'Nenhum registro encontrado.' : '', 'info');
        })
        .catch(err => {
            console.error('Erro ao carregar logs:', err);
            mostrarMensagem('mensagem-logs', 'Não foi possível carregar os logs.');
        });
}

function atualizarFiltroLogs(resumo) {
    const filtro = $('filtro-log');
    const selecionado = filtro.value;
    const total = Object.values(resumo).reduce((soma, valor) => soma + valor, 0);
    filtro.replaceChildren(new Option(`Todos os eventos (${total})`, ''));
    Object.entries(NOMES_LOG).forEach(([tipo, nome]) => {
        filtro.add(new Option(`${nome} (${resumo[tipo] || 0})`, tipo));
    });
    filtro.value = selecionado;
}

$('filtro-log').addEventListener('change', () => carregarLogs());
$('mais-logs').addEventListener('click', () => carregarLogs(true));

function carregarUsuarios() {
    requisitarApi('/api/admin/usuarios')
        .then(resultado => {
            if (resultado.status !== 200) return;
            const corpo = $('corpo-usuarios');
            corpo.replaceChildren();

            resultado.body.forEach(usuario => {
                const celulaAcesso = criar('td', 'sem-quebra', usuario.ativo ? 'Ativo ' : 'Desativado ');
                if (usuario.id !== usuarioAtual.id) {
                    const botao = criar('button', usuario.ativo ? 'link link-perigo' : 'link', usuario.ativo ? 'Desativar' : 'Reativar');
                    botao.addEventListener('click', () => alterarAcesso(usuario));
                    celulaAcesso.append(botao);
                }
                corpo.append(criar('tr', '',
                    criar('td', '', usuario.nome),
                    criar('td', '', usuario.email),
                    criar('td', '', usuario.funcao),
                    criar('td', '', String(usuario.agendamentos)),
                    celulaAcesso));
            });
        })
        .catch(err => {
            console.error('Erro ao carregar usuários:', err);
            mostrarMensagem('mensagem-usuarios', 'Não foi possível carregar os usuários.');
        });
}

function alterarAcesso(usuario) {
    const ativar = !usuario.ativo;
    if (!ativar && !confirm(`Desativar o acesso de ${usuario.nome}?`)) return;

    enviarJson(`/api/admin/usuarios/${usuario.id}/ativo`, { ativo: ativar })
        .then(resultado => {
            if (resultado.status === 401) return;
            mostrarMensagem('mensagem-usuarios', resultado.body.mensagem, resultado.status === 200 ? 'sucesso' : 'erro');
            carregarUsuarios();
            carregarLogs();
        })
        .catch(err => console.error('Erro ao alterar acesso:', err));
}

// --- INÍCIO: dados da escola e sessão já aberta ---
function preencherEscola(escola) {
    $('nome-escola').textContent = escola.nome;

    const telefone = criar('a', '', escola.telefone);
    telefone.href = `tel:+55${escola.telefone.replace(/\D/g, '')}`;
    const qedu = criar('a', '', 'Dados da escola no QEdu');
    qedu.href = escola.url;
    qedu.target = '_blank';
    qedu.rel = 'noopener';

    $('rodape-escola').replaceChildren(
        criar('p', '', escola.endereco),
        criar('p', '', telefone, ' · ', qedu),
        criar('p', '', `${escola.total_chromebooks} Chromebooks · ${escola.professores} professores · ${escola.alunos.toLocaleString('pt-BR')} alunos`)
    );
}

requisitarApi('/api/opcoes')
    .then(resultado => {
        opcoes = resultado.body;
        preencherEscola(opcoes.escola);
        preencherSeletor($('cadastro-funcao'), opcoes.funcoes);
        preencherSeletor($('etapa'), Object.keys(opcoes.etapas));
        $('cadastro-senha').minLength = opcoes.senha_minima;
        return requisitarApi('/api/me');
    })
    .then(resultado => {
        if (resultado.status === 200) {
            mostrarSistema(resultado.body.usuario);
        }
    })
    .catch(err => console.error('Erro ao iniciar o sistema:', err));
