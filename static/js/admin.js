// ============ ESTADO ============
let conteudosCache = [];
let secaoAtual = 'dashboard';

// ============ INIT ============
document.addEventListener('DOMContentLoaded', async () => {
  const r = await fetch('/api/me');
  const data = await r.json();
  if (!data.logado || !data.usuario.is_admin) {
    // alert('Acesso restrito a administradores.');
    // window.location.href = '/';
    
    document.body.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                  height:100vh;font-family:sans-serif;color:#fff;background:#0a0a0f;gap:16px;text-align:center;padding:20px;">
        <h1 style="font-size:28px;"> Acesso restrito</h1>
        <p style="color:#a0a0b0;">Esta área é apenas para administradores.</p>
        <a href="/" style="padding:10px 20px;background:#e50914;color:#fff;border-radius:6px;
                          text-decoration:none;font-weight:600;">Voltar ao site</a>
      </div>`;
    return;
  }
  document.getElementById('nomeAdmin').innerHTML =
    `<i class="fa-regular fa-user"></i> ${escapeHtml(data.usuario.nome)}`;

  // Navegação
  document.querySelectorAll('.sidebar nav a').forEach(a => {
    a.addEventListener('click', e => {
      e.preventDefault();
      irPara(a.dataset.sec);
    });
  });

  await carregarDashboard();
  await carregarConteudos();
  await carregarUsuarios();
  await carregarDominios();
});





function irPara(sec) {
  secaoAtual = sec;
  document.querySelectorAll('.sec').forEach(s => s.classList.remove('ativa'));
  document.getElementById(`sec-${sec}`).classList.add('ativa');
  document.querySelectorAll('.sidebar nav a').forEach(a =>
    a.classList.toggle('ativo', a.dataset.sec === sec));
}

async function logoutAdmin() {
  await fetch('/api/logout', { method: 'POST' });
  window.location.href = '/';
}

// ============ DASHBOARD ============
async function carregarDashboard() {
  const r = await fetch('/api/admin/dashboard');
  const d = await r.json();
  document.getElementById('cardsStats').innerHTML = `
    <div class="card-stat"><div class="valor">${d.conteudos}</div><div class="rotulo">Conteúdos</div></div>
    <div class="card-stat"><div class="valor">${d.usuarios}</div><div class="rotulo">Usuários</div></div>
    <div class="card-stat"><div class="valor">${d.favoritos}</div><div class="rotulo">Favoritos</div></div>
    <div class="card-stat"><div class="valor">${d.views}</div><div class="rotulo">Views</div></div>
  `;
}

// ============ CONTEÚDOS ============
async function carregarConteudos() {
  const r = await fetch('/api/admin/conteudos');
  conteudosCache = await r.json();
  renderizarTabelaConteudos(conteudosCache);
}

function renderizarTabelaConteudos(lista) {
  const tbody = document.querySelector('#tabelaConteudos tbody');
  if (!lista.length) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:40px;color:#888;">Nenhum conteúdo</td></tr>`;
    return;
  }
  tbody.innerHTML = lista.map(f => `
    <tr>
      <td>${f.id}</td>
      <td><img class="capa-mini" src="${f.capa || ''}" onerror="this.style.visibility='hidden'"></td>
      <td><strong>${escapeHtml(f.titulo)}</strong></td>
      <td>${escapeHtml(f.categoria || '—')}</td>
      <td>${f.ano || '—'}</td>
      <td>${f.destaque ? '<span class="badge verde">Sim</span>' : '<span class="badge cinza">Não</span>'}</td>
      <td><div class="url-cell" title="${escapeHtml(f.video_url)}">${escapeHtml(f.video_url)}</div></td>
      <td>
        <button class="btn-mini" onclick="editarConteudo(${f.id})"><i class="fa-solid fa-pen"></i> Editar</button>
        <button class="btn-mini danger" aria-label="Eliminar conteúdo" onclick="eliminarConteudo(${f.id})"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>
  `).join('');
}

function filtrarConteudos() {
  const q = document.getElementById('buscaConteudo').value.toLowerCase();
  const filtrados = conteudosCache.filter(f =>
    f.titulo.toLowerCase().includes(q) || f.video_url.toLowerCase().includes(q)
  );
  renderizarTabelaConteudos(filtrados);
}

function novoConteudo() {
  document.getElementById('modalTitulo').textContent = 'Novo Conteúdo';
  document.getElementById('formConteudo').reset();
  document.getElementById('fId').value = '';
  document.getElementById('erroConteudo').textContent = '';
  document.getElementById('modalConteudo').classList.add('ativo');
}

function editarConteudo(id) {
  const f = conteudosCache.find(c => c.id === id);
  if (!f) return;
  document.getElementById('modalTitulo').textContent = 'Editar Conteúdo';
  document.getElementById('fId').value = f.id;
  document.getElementById('fTitulo').value = f.titulo;
  document.getElementById('fDescricao').value = f.descricao || '';
  document.getElementById('fCategoria').value = f.categoria || '';
  document.getElementById('fAno').value = f.ano || '';
  document.getElementById('fDuracao').value = f.duracao || '';
  document.getElementById('fCapa').value = f.capa || '';
  document.getElementById('fVideoUrl').value = f.video_url;
  document.getElementById('fDestaque').checked = !!f.destaque;
  document.getElementById('erroConteudo').textContent = '';
  document.getElementById('modalConteudo').classList.add('ativo');
}

function fecharModalConteudo(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('modalConteudo').classList.remove('ativo');
}

async function salvarConteudo(e) {
  e.preventDefault();
  const id = document.getElementById('fId').value;
  const dados = {
    titulo: document.getElementById('fTitulo').value.trim(),
    descricao: document.getElementById('fDescricao').value.trim(),
    categoria: document.getElementById('fCategoria').value.trim(),
    ano: parseInt(document.getElementById('fAno').value) || null,
    duracao: document.getElementById('fDuracao').value.trim(),
    capa: document.getElementById('fCapa').value.trim(),
    video_url: document.getElementById('fVideoUrl').value.trim(),
    destaque: document.getElementById('fDestaque').checked ? 1 : 0,
  };

  const url = id ? `/api/admin/conteudos/${id}` : '/api/admin/conteudos';
  const method = id ? 'PUT' : 'POST';

  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dados)
  });
  const res = await r.json();

  if (r.ok) {
    fecharModalConteudo();
    await carregarConteudos();
    await carregarDashboard();
    await carregarDominios();
  } else {
    document.getElementById('erroConteudo').textContent = res.erro || 'Erro';
  }
}

async function eliminarConteudo(id) {
  if (!confirm('Eliminar este conteúdo? Esta ação é irreversível.')) return;
  await fetch(`/api/admin/conteudos/${id}`, { method: 'DELETE' });
  await carregarConteudos();
  await carregarDashboard();
}

// ============ TROCA DE DOMÍNIO ============
async function carregarDominios() {
  const r = await fetch('/api/admin/dominios/lista');
  const dominios = await r.json();
  document.getElementById('listaDominios').innerHTML =
    dominios.map(d => `<option value="${d}">`).join('');
}

async function previewDominio() {
  const antigo = document.getElementById('domAntigo').value.trim();
  const novo = document.getElementById('domNovo').value.trim();
  const box = document.getElementById('previewDominio');

  if (!antigo || !novo) {
    box.innerHTML = '<p class="vazio">Preenche o domínio antigo e o novo.</p>';
    return;
  }

  const r = await fetch('/api/admin/dominios/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ antigo, novo })
  });
  const data = await r.json();

  if (data.erro) { box.innerHTML = `<p class="vazio">${data.erro}</p>`; return; }

  if (data.total === 0) {
    box.innerHTML = `<p class="vazio">Nenhum link contém "<code>${escapeHtml(antigo)}</code>".</p>`;
    return;
  }

  box.innerHTML = `
    <h3><i class="fa-solid fa-magnifying-glass"></i> ${data.total} link(s) serão alterados</h3>
    ${data.alteracoes.map(a => `
      <div class="item">
        <div class="titulo-item">#${a.id} — ${escapeHtml(a.titulo)}</div>
        <div class="antes">− ${escapeHtml(a.antes)}</div>
        <div class="depois">+ ${escapeHtml(a.depois)}</div>
      </div>
    `).join('')}
  `;
}

async function aplicarDominio() {
  const antigo = document.getElementById('domAntigo').value.trim();
  const novo = document.getElementById('domNovo').value.trim();

  if (!antigo || !novo) { alert('Preenche os dois campos.'); return; }
  if (antigo === novo) { alert('Os domínios são iguais.'); return; }

  if (!confirm(`Substituir "${antigo}" por "${novo}" em TODAS as URLs?\n\nRecomendado pré-visualizar primeiro.`)) return;

  const r = await fetch('/api/admin/dominios/aplicar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ antigo, novo })
  });
  const data = await r.json();

  if (r.ok) {
    alert(`${data.atualizados} URL(s) atualizadas!`);
    document.getElementById('previewDominio').innerHTML = '';
    document.getElementById('domAntigo').value = '';
    document.getElementById('domNovo').value = '';
    await carregarConteudos();
    await carregarDominios();
  } else {
    alert('Erro: ' + (data.erro || 'desconhecido'));
  }
}

// ============ USUÁRIOS ============
async function carregarUsuarios() {
  const r = await fetch('/api/admin/usuarios');
  const lista = await r.json();
  const tbody = document.querySelector('#tabelaUsuarios tbody');

  tbody.innerHTML = lista.map(u => `
    <tr>
      <td>${u.id}</td>
      <td>${escapeHtml(u.nome)}</td>
      <td>${escapeHtml(u.email)}</td>
      <td>${u.is_admin
        ? '<span class="badge vermelho">Admin</span>'
        : '<span class="badge cinza">Usuário</span>'}</td>
      <td>${(u.criado_em || '').substring(0, 10)}</td>
      <td>
        <button class="btn-mini" onclick="toggleAdmin(${u.id})">
          ${u.is_admin ? '<i class="fa-solid fa-arrow-down"></i> Remover admin' : '<i class="fa-solid fa-arrow-up"></i> Tornar admin'}
        </button>
        <button class="btn-mini danger" aria-label="Eliminar utilizador" onclick="eliminarUsuario(${u.id})"><i class="fa-solid fa-trash"></i></button>
      </td>
    </tr>
  `).join('');
}

async function toggleAdmin(id) {
  const r = await fetch(`/api/admin/usuarios/${id}/admin`, { method: 'POST' });
  const d = await r.json();
  if (!r.ok) { alert(d.erro); return; }
  await carregarUsuarios();
}

async function eliminarUsuario(id) {
  if (!confirm('Eliminar este utilizador e todos os seus dados?')) return;
  const r = await fetch(`/api/admin/usuarios/${id}`, { method: 'DELETE' });
  const d = await r.json();
  if (!r.ok) { alert(d.erro); return; }
  await carregarUsuarios();
  await carregarDashboard();
}

// ============ UTILS ============
function escapeHtml(s) {
  if (!s) return '';
  return String(s).replace(/[&<>"']/g, c => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[c]));
}