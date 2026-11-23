// ============ ESTADO GLOBAL ============
let usuario = null;
let favoritosIds = new Set();
let modoAuth = 'login';
let todosConteudos = [];
let categoriaAtiva = 'Todos';

// ============ INICIALIZAÇÃO ============
document.addEventListener('DOMContentLoaded', async () => {
  window.addEventListener('scroll', () => {
    document.querySelector('.topbar').classList.toggle('solida', window.scrollY > 50);
  });
  await verificarSessao();
  await carregarDestaque();
  await carregarCategorias();
  await carregarConteudos();
  await carregarFavoritos();
});

// ============ SESSÃO ============
async function verificarSessao() {
  const r = await fetch('/api/me');
  const data = await r.json();
  if (data.logado) {
    usuario = data.usuario;
    renderizarUserArea();
  }
}

function renderizarUserArea() {
  const area = document.getElementById('userArea');
  const inicial = usuario.nome.charAt(0).toUpperCase();
  const btnAdmin = usuario.is_admin
    ? `<a href="/admin" class="btn-primary" style="text-decoration:none;">Painel</a>`
    : '';
  area.innerHTML = `
    ${btnAdmin}
    <div class="user-info">
      <div class="user-avatar">${inicial}</div>
      <span>${usuario.nome.split(' ')[0]}</span>
      <button class="btn-outline" onclick="logout()">Sair</button>
    </div>
  `;
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  usuario = null;
  favoritosIds.clear();
  document.getElementById('userArea').innerHTML = `
    <button class="btn-outline" onclick="abrirModal('login')">Entrar</button>
    <button class="btn-primary" onclick="abrirModal('registrar')">Cadastrar</button>
  `;
  renderizarConteudos(todosConteudos);
}

// ============ HERO DESTAQUE ============
async function carregarDestaque() {
  const r = await fetch('/api/destaques');
  const lista = await r.json();
  if (!lista.length) return;
  const f = lista[Math.floor(Math.random() * lista.length)];

  const hero = document.getElementById('hero');
  hero.style.backgroundImage = `url('${f.capa}')`;

  document.getElementById('heroContent').innerHTML = `
    <h1>${f.titulo}</h1>
    <div class="hero-meta">
      <span><i class="fa-regular fa-calendar"></i> ${f.ano}</span>
      <span><i class="fa-regular fa-clock"></i> ${f.duracao}</span>
      <span>${f.categoria}</span>
    </div>
    <p>${f.descricao}</p>
    <button class="btn-primary hero-cta" onclick="abrirPlayer(${f.id})">
      <i class="fa-solid fa-play"></i> Assistir agora
    </button>
  `;
}

// ============ CATEGORIAS ============
async function carregarCategorias() {
  const r = await fetch('/api/categorias');
  const cats = await r.json();
  const nav = document.getElementById('categorias');
  nav.innerHTML = `<button class="ativo" onclick="filtrarCategoria('Todos', this)">Todos</button>` +
    cats.map(c => `<button onclick="filtrarCategoria('${c}', this)">${c}</button>`).join('');
}

function filtrarCategoria(cat, btn) {
  categoriaAtiva = cat;
  document.querySelectorAll('.categorias button').forEach(b => b.classList.remove('ativo'));
  btn.classList.add('ativo');
  document.getElementById('tituloSecao').textContent = cat === 'Todos' ? 'Todos os títulos' : cat;
  const filtrados = cat === 'Todos' ? todosConteudos : todosConteudos.filter(f => f.categoria === cat);
  renderizarConteudos(filtrados);
}

// ============ CONTEÚDOS ============
async function carregarConteudos() {
  const r = await fetch('/api/conteudos');
  todosConteudos = await r.json();
  renderizarConteudos(todosConteudos);
}

function renderizarConteudos(lista) {
  const grid = document.getElementById('gridFilmes');
  const msg = document.getElementById('mensagemVazia');

  if (!lista.length) {
    grid.innerHTML = '';
    msg.style.display = 'block';
    return;
  }
  msg.style.display = 'none';

  grid.innerHTML = lista.map(f => `
    <a class="card-filme" href="/player/${f.id}">
      <div class="card-capa">
        <img src="${f.capa}" alt="${f.titulo}" onerror="this.src='https://via.placeholder.com/300x450/1e1e2a/666?text=Sem+Capa'">
        <div class="play-overlay"><i class="fa-solid fa-play"></i><span>Assistir</span></div>
        ${usuario ? `<button class="card-fav ${favoritosIds.has(f.id)?'ativo':''}"
            aria-label="${favoritosIds.has(f.id)?'Remover dos favoritos':'Adicionar aos favoritos'}"
            onclick="event.preventDefault(); event.stopPropagation(); toggleFavorito(${f.id}, this)">
            <i class="${favoritosIds.has(f.id)?'fa-solid':'fa-regular'} fa-heart"></i></button>` : ''}
      </div>
      <div class="card-info">
        <h3>${f.titulo}</h3>
        <div class="meta">
          <span>${f.ano}</span>
          <span class="meta-separator"></span>
          <span>${f.duracao}</span>
        </div>
      </div>
    </a>
  `).join('');
}

async function buscar() {
  const q = document.getElementById('inputBusca').value.trim();
  if (!q) { renderizarConteudos(todosConteudos); return; }
  const r = await fetch(`/api/conteudos?busca=${encodeURIComponent(q)}`);
  const lista = await r.json();
  renderizarConteudos(lista);
}

// ============ MODAL AUTH ============
function abrirModal(modo) {
  modoAuth = modo;
  document.getElementById('modalAuth').classList.add('ativo');
  document.getElementById('campoNome').style.display = modo === 'registrar' ? 'block' : 'none';
  document.getElementById('authTitulo').textContent = modo === 'login' ? 'Entrar' : 'Criar conta';
  document.getElementById('btnAuth').textContent = modo === 'login' ? 'Entrar' : 'Cadastrar';
  document.getElementById('trocarModo').innerHTML = modo === 'login'
    ? `Não tem conta? <a onclick="abrirModal('registrar')">Cadastre-se</a>`
    : `Já tem conta? <a onclick="abrirModal('login')">Entrar</a>`;
  document.getElementById('authErro').textContent = '';
  document.getElementById('formAuth').reset();
}

function fecharModalAuth(e) {
  if (e && e.target !== e.currentTarget) return;
  document.getElementById('modalAuth').classList.remove('ativo');
}

async function enviarAuth(e) {
  e.preventDefault();
  const nome = document.getElementById('inpNome').value;
  const email = document.getElementById('inpEmail').value;
  const senha = document.getElementById('inpSenha').value;
  const erroEl = document.getElementById('authErro');
  erroEl.textContent = '';

  const url = modoAuth === 'login' ? '/api/login' : '/api/registrar';
  const body = modoAuth === 'login' ? { email, senha } : { nome, email, senha };

  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await r.json();

  if (r.ok) {
    usuario = data.usuario;
    renderizarUserArea();
    document.getElementById('modalAuth').classList.remove('ativo');
    await carregarFavoritos();
    renderizarConteudos(todosConteudos);
  } else {
    erroEl.textContent = data.erro || 'Erro ao processar';
  }
}

function abrirPlayer(id) {
  window.location.href = `/player/${id}`;
}

// ============ FAVORITOS ============
async function carregarFavoritos() {
  if (!usuario) return;
  const r = await fetch('/api/favoritos');
  const lista = await r.json();
  favoritosIds = new Set(lista.map(f => f.id));
}

async function toggleFavorito(id, btn) {
  if (!usuario) { abrirModal('login'); return; }

  const jaFav = favoritosIds.has(id);
  await fetch(`/api/favoritos/${id}`, { method: jaFav ? 'DELETE' : 'POST' });

  if (jaFav) favoritosIds.delete(id);
  else favoritosIds.add(id);

  if (btn) {
    btn.classList.toggle('ativo', !jaFav);
    btn.innerHTML = `<i class="${!jaFav ? 'fa-solid' : 'fa-regular'} fa-heart"></i>`;
  }
  renderizarConteudos(todosConteudos);
}

async function mostrarFavoritos() {
  if (!usuario) { abrirModal('login'); return; }
  await carregarFavoritos();
  const lista = todosConteudos.filter(f => favoritosIds.has(f.id));
  document.getElementById('tituloSecao').textContent = 'Seus favoritos';
  document.querySelectorAll('.categorias button').forEach(b => b.classList.remove('ativo'));
  renderizarConteudos(lista);
  window.scrollTo({ top: 400, behavior: 'smooth' });
}

function irParaHome() {
  document.getElementById('tituloSecao').textContent = 'Todos os títulos';
  document.querySelectorAll('.categorias button').forEach((b, i) => b.classList.toggle('ativo', i === 0));
  renderizarConteudos(todosConteudos);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Fechar player com ESC
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    fecharPlayer();
    fecharModalAuth();
  }
});
