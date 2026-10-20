CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


CREATE TYPE user_role AS ENUM ('user', 'admin', 'moderator');
CREATE TYPE content_type AS ENUM ('movie', 'series');
CREATE TYPE subscription_status AS ENUM (
    'pending',      -- Aguardando pagamento
    'active',       -- Ativa e válida
    'past_due',     -- Pagamento atrasado (período de graça)
    'canceled',     -- Cancelada pelo usuário
    'expired',      -- Expirada naturalmente
    'trial'         -- Período de teste
);
CREATE TYPE payment_status AS ENUM (
    'pending',
    'paid',
    'failed',
    'refunded'
);
CREATE TYPE email_status AS ENUM (
    'queued',
    'sent',
    'failed',
    'bounced'
);


CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(150),
    role            user_role NOT NULL DEFAULT 'user',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    avatar_url      TEXT,

    verification_token VARCHAR(255),
    verification_token_expires_at TIMESTAMPTZ,
    reset_token     VARCHAR(255),
    reset_token_expires_at TIMESTAMPTZ,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);


CREATE TABLE genres (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(80) NOT NULL UNIQUE,
    slug        VARCHAR(80) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_genres_slug ON genres(slug);


CREATE TABLE contents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type            content_type NOT NULL,
    title           VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) NOT NULL UNIQUE,
    synopsis        TEXT,
    thumbnail_url   TEXT,
    banner_url      TEXT,
    trailer_url     TEXT,


    embed_url       TEXT,
    release_year    SMALLINT,
    age_rating      VARCHAR(10),   -- Ex: 'L', '10', '12', '14', '16', '18'
    imdb_score      NUMERIC(3,1),
    is_featured     BOOLEAN NOT NULL DEFAULT FALSE,
    is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contents_type ON contents(type);
CREATE INDEX idx_contents_slug ON contents(slug);
CREATE INDEX idx_contents_published ON contents(is_published);
CREATE INDEX idx_contents_featured ON contents(is_featured);

CREATE TABLE content_genres (
    content_id  UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    genre_id    INTEGER NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (content_id, genre_id)
);

CREATE INDEX idx_content_genres_genre ON content_genres(genre_id);


CREATE TABLE movies (
    content_id      UUID PRIMARY KEY REFERENCES contents(id) ON DELETE CASCADE,
    duration_min    INTEGER,        -- Duração em minutos
    director        VARCHAR(150),
    studio          VARCHAR(150)
);



CREATE TABLE seasons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_id      UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    season_number   SMALLINT NOT NULL,
    title           VARCHAR(255),
    synopsis        TEXT,
    poster_url      TEXT,
    release_year    SMALLINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (content_id, season_number)
);

CREATE INDEX idx_seasons_content ON seasons(content_id);

CREATE TABLE episodes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    season_id       UUID NOT NULL REFERENCES seasons(id) ON DELETE CASCADE,
    episode_number  SMALLINT NOT NULL,
    title           VARCHAR(255) NOT NULL,
    synopsis        TEXT,
    thumbnail_url   TEXT,
    embed_url       TEXT,
    duration_min    INTEGER,
    air_date        DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (season_id, episode_number)
);

CREATE INDEX idx_episodes_season ON episodes(season_id);


CREATE TABLE plans (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(80) NOT NULL UNIQUE,   -- Ex: 'Básico', 'Premium'
    slug            VARCHAR(80) NOT NULL UNIQUE,
    description     TEXT,
    price_cents     INTEGER NOT NULL,              -- Preço em centavos (evita float)
    currency        VARCHAR(3) NOT NULL DEFAULT 'AOA',
    duration_days   INTEGER NOT NULL,              -- Ex: 30, 90, 365
    max_devices     SMALLINT NOT NULL DEFAULT 1,
    max_quality     VARCHAR(10) NOT NULL DEFAULT '720p',  -- '480p', '720p', '1080p', '4K'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id                 INTEGER NOT NULL REFERENCES plans(id),
    status                  subscription_status NOT NULL DEFAULT 'pending',
    started_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at              TIMESTAMPTZ NOT NULL,
    canceled_at             TIMESTAMPTZ,
    auto_renew              BOOLEAN NOT NULL DEFAULT TRUE,

    external_subscription_id VARCHAR(255),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires ON subscriptions(expires_at);

CREATE UNIQUE INDEX idx_one_active_subscription_per_user
    ON subscriptions(user_id)
    WHERE status IN ('active', 'trial');


CREATE TABLE payments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount_cents    INTEGER NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'AOA',
    status          payment_status NOT NULL DEFAULT 'pending',
    payment_method  VARCHAR(50),        -- 'card', 'mbway', 'paypal', etc.
    external_payment_id VARCHAR(255),
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_user ON payments(user_id);
CREATE INDEX idx_payments_subscription ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);


CREATE TABLE favorites (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id  UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, content_id)
);

CREATE INDEX idx_favorites_user ON favorites(user_id);


CREATE TABLE watch_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_id      UUID NOT NULL REFERENCES contents(id) ON DELETE CASCADE,
    episode_id      UUID REFERENCES episodes(id) ON DELETE SET NULL,
    progress_seconds INTEGER NOT NULL DEFAULT 0,
    is_completed    BOOLEAN NOT NULL DEFAULT FALSE,
    last_watched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, content_id, episode_id)
);

CREATE INDEX idx_watch_history_user ON watch_history(user_id);
CREATE INDEX idx_watch_history_recent ON watch_history(user_id, last_watched_at DESC);


CREATE TABLE email_templates (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(80) NOT NULL UNIQUE,  -- Ex: 'welcome', 'password_reset', 'subscription_confirmed'
    subject     VARCHAR(255) NOT NULL,
    body_html   TEXT NOT NULL,
    body_text   TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE email_queue (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    to_email        VARCHAR(255) NOT NULL,
    template_code   VARCHAR(80) REFERENCES email_templates(code),
    subject         VARCHAR(255) NOT NULL,
    body_html       TEXT NOT NULL,
    body_text       TEXT,
    status          email_status NOT NULL DEFAULT 'queued',
    attempts        SMALLINT NOT NULL DEFAULT 0,
    last_error      TEXT,
    scheduled_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_scheduled ON email_queue(scheduled_at)
    WHERE status = 'queued';


CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_users
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_contents
    BEFORE UPDATE ON contents
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_subscriptions
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();



INSERT INTO genres (name, slug) VALUES
    ('Ação', 'acao'),
    ('Aventura', 'aventura'),
    ('Comédia', 'comedia'),
    ('Drama', 'drama'),
    ('Ficção Científica', 'ficcao-cientifica'),
    ('Terror', 'terror'),
    ('Suspense', 'suspense'),
    ('Romance', 'romance'),
    ('Animação', 'animacao'),
    ('Documentário', 'documentario'),
    ('Infantil', 'infantil'),
    ('Fantasia', 'fantasia');

INSERT INTO plans (name, slug, description, price_cents, currency, duration_days, max_devices, max_quality) VALUES
    ('Básico', 'basico', 'Acesso a todo o catálogo em 720p em 1 dispositivo.', 500000, 'AOA', 30, 1, '720p'),
    ('Premium', 'premium', 'Catálogo completo em Full HD em até 3 dispositivos.', 1200000, 'AOA', 30, 3, '1080p'),
    ('Família', 'familia', 'Catálogo em 4K em até 5 dispositivos.', 2000000, 'AOA', 30, 5, '4K');

INSERT INTO email_templates (code, subject, body_html, body_text) VALUES
    ('welcome', 'Bem-vindo à RedeCanais Jr! 🎬',
     '<h1>Olá {{user_name}}!</h1><p>Sua conta na RedeCanais Jr foi criada com sucesso. Bom entretenimento!</p>',
     'Olá {{user_name}}! Sua conta na RedeCanais Jr foi criada com sucesso.'),
    ('password_reset', 'Redefinição de senha - RedeCanais Jr',
     '<h1>Olá {{user_name}}</h1><p>Clique <a href="{{reset_link}}">aqui</a> para redefinir sua senha. O link expira em 1 hora.</p>',
     'Olá {{user_name}}, acesse {{reset_link}} para redefinir sua senha (expira em 1h).'),
    ('subscription_confirmed', 'Assinatura ativa - RedeCanais Jr',
     '<h1>Obrigado, {{user_name}}!</h1><p>Sua assinatura do plano <b>{{plan_name}}</b> está ativa até {{expires_at}}.</p>',
     'Obrigado {{user_name}}! Sua assinatura do plano {{plan_name}} está ativa até {{expires_at}}.'),
    ('subscription_expiring', 'Sua assinatura está a expirar - RedeCanais Jr',
     '<h1>Olá {{user_name}}</h1><p>Sua assinatura do plano <b>{{plan_name}}</b> expira em {{days_left}} dia(s). Renove para continuar assistindo.</p>',
     'Olá {{user_name}}, sua assinatura do plano {{plan_name}} expira em {{days_left}} dia(s).');