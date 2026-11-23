let currentContent = null;
let currentUser = null;
let favorites = new Set();

document.addEventListener('DOMContentLoaded', loadPlayerPage);

async function loadPlayerPage() {
  try {
    const [contentResponse, contentsResponse, userResponse] = await Promise.all([
      fetch(`/api/conteudo/${window.PLAYER_CONTENT_ID}`),
      fetch('/api/conteudos'),
      fetch('/api/me')
    ]);
    if (!contentResponse.ok || !contentsResponse.ok || !userResponse.ok) {
      throw new Error('Não foi possível carregar os dados do conteúdo.');
    }

    currentContent = await contentResponse.json();
    const allContents = await contentsResponse.json();
    const userData = await userResponse.json();
    currentUser = userData.logado ? userData.usuario : null;
    if (currentUser) {
      renderUserArea();
      const favoritesResponse = await fetch('/api/favoritos');
      if (!favoritesResponse.ok) throw new Error('Não foi possível carregar os favoritos.');
      favorites = new Set((await favoritesResponse.json()).map(item => item.id));
    }

    renderContent(currentContent);
    renderRecommendations(allContents);
    document.getElementById('playerLoading').hidden = true;
    document.getElementById('videoShell').hidden = false;
  } catch (error) {
    console.error(error);
    document.getElementById('playerLoading').hidden = true;
    document.getElementById('playerError').hidden = false;
  }
}

function renderUserArea() {
  const userArea = document.getElementById('userArea');
  const firstName = currentUser.nome.split(' ')[0];
  userArea.innerHTML = `
    <span class="player-user"><i class="fa-regular fa-user"></i> ${escapeHtml(firstName)}</span>
    <button class="btn-outline" onclick="logoutPlayer()">Sair</button>
  `;
}

function renderContent(content) {
  document.title = `${content.titulo} — RedeCanais Jr`;
  document.getElementById('playerTitulo').textContent = content.titulo;
  document.getElementById('playerDescricao').textContent = content.descricao || 'Sem descrição disponível.';
  document.getElementById('playerMeta').innerHTML = [
    content.categoria,
    content.ano,
    content.duracao
  ].filter(Boolean).map(value => `<span>${escapeHtml(value)}</span>`).join('');

  const stage = document.getElementById('videoStage');
  if (/\.(mp4|webm|ogg|ogv)(?:$|[?#])/i.test(content.video_url)) {
    const video = document.createElement('video');
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;
    video.src = content.video_url;
    stage.appendChild(video);
  } else {
    const frame = document.createElement('iframe');
    frame.title = content.titulo;
    frame.src = content.video_url;
    frame.allow = 'autoplay; fullscreen; picture-in-picture; encrypted-media';
    frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.allowFullscreen = true;
    stage.appendChild(frame);
  }

  const favoriteButton = document.getElementById('btnFavoritar');
  if (currentUser) {
    favoriteButton.hidden = false;
    updateFavoriteButton();
    favoriteButton.addEventListener('click', toggleFavorite);
  }

  if (currentUser) {
    fetch('/api/historico', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ conteudo_id: content.id, progresso: 0 })
    }).catch(error => console.error('Não foi possível salvar o histórico.', error));
  }
}

function renderRecommendations(allContents) {
  const related = allContents.filter(item =>
    item.id !== currentContent.id &&
    item.categoria &&
    item.categoria === currentContent.categoria
  );
  const fallback = allContents.filter(item =>
    item.id !== currentContent.id && !related.some(match => match.id === item.id)
  );
  const recommendations = [...related, ...fallback].slice(0, 8);
  const list = document.getElementById('recommendationList');
  document.getElementById('recommendationCount').textContent = recommendations.length;

  if (!recommendations.length) {
    list.innerHTML = '<p class="recommendations-empty">Ainda não há recomendações.</p>';
    return;
  }

  list.innerHTML = recommendations.map((item, index) => `
    <a class="recommendation-card" href="/player/${item.id}" style="--card-index:${index}">
      <div class="recommendation-poster">
        <img src="${escapeHtml(item.capa || '')}" alt="" loading="lazy"
          onerror="this.style.opacity='0'">
        <span class="recommendation-play"><i class="fa-solid fa-play"></i></span>
      </div>
      <div class="recommendation-info">
        <span class="recommendation-category">${escapeHtml(item.categoria || 'Destaque')}</span>
        <h3>${escapeHtml(item.titulo)}</h3>
        <p>${[item.ano, item.duracao].filter(Boolean).map(escapeHtml).join(' · ')}</p>
        <span class="recommendation-description">${escapeHtml(item.descricao || '')}</span>
      </div>
    </a>
  `).join('');
}

async function toggleFavorite() {
  const wasFavorite = favorites.has(currentContent.id);
  const response = await fetch(`/api/favoritos/${currentContent.id}`, {
    method: wasFavorite ? 'DELETE' : 'POST'
  });
  if (!response.ok) {
    console.error('Não foi possível atualizar o favorito.');
    return;
  }
  if (wasFavorite) favorites.delete(currentContent.id);
  else favorites.add(currentContent.id);
  updateFavoriteButton();
}

function updateFavoriteButton() {
  const button = document.getElementById('btnFavoritar');
  const isFavorite = favorites.has(currentContent.id);
  button.innerHTML = `<i class="${isFavorite ? 'fa-solid' : 'fa-regular'} fa-heart"></i>
    <span>${isFavorite ? 'Favoritado' : 'Favoritar'}</span>`;
  button.classList.toggle('favoritado', isFavorite);
}

async function logoutPlayer() {
  await fetch('/api/logout', { method: 'POST' });
  window.location.reload();
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[character]));
}
