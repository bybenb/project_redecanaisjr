# database.py — substitui o ficheiro inteiro por este

import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = "bentv.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Adiciona coluna is_admin se ainda não existir (migração suave)
    cur.execute("PRAGMA table_info(usuarios)")
    colunas = [c[1] for c in cur.fetchall()]
    if "is_admin" not in colunas:
        cur.execute("ALTER TABLE usuarios ADD COLUMN is_admin INTEGER DEFAULT 0")
        print("Coluna \"is_admin\" adicionada à tabela usuarios")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            descricao TEXT,
            categoria TEXT,
            ano INTEGER,
            duracao TEXT,
            capa TEXT,
            video_url TEXT NOT NULL,
            destaque INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            conteudo_id INTEGER,
            UNIQUE(usuario_id, conteudo_id),
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(conteudo_id) REFERENCES conteudos(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            conteudo_id INTEGER,
            progresso REAL DEFAULT 0,
            assistido_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, conteudo_id)
        )
    """)

    # Conteúdos de exemplo
    cur.execute("SELECT COUNT(*) FROM conteudos")
    if cur.fetchone()[0] == 0:
        filmes = [
            ("Big Buck Bunny", "Um coelho gigante vive aventuras na floresta.", "Animação", 2008, "9min",
             "https://peach.blender.org/wp-content/uploads/title_anouncement.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4", 1),
            ("Elephants Dream", "Dois personagens exploram uma máquina estranha.", "Ficção", 2006, "11min",
             "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Elephants_Dream_s5_both.jpg/320px-Elephants_Dream_s5_both.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4", 1),
            ("For Bigger Blazes", "Ação e emoção em poucos minutos.", "Ação", 2015, "15min",
             "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerBlazes.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4", 0),
            ("Sintel", "Uma garota procura seu dragão perdido.", "Aventura", 2010, "15min",
             "https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Sintel_poster.jpg/320px-Sintel_poster.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/Sintel.mp4", 1),
            ("Tears of Steel", "Ficção científica com efeitos impressionantes.", "Sci-Fi", 2012, "12min",
             "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Tears_of_Steel_poster.jpg/320px-Tears_of_Steel_poster.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4", 0),
            ("Subaru Outback", "Aventura sobre rodas.", "Documentário", 2015, "5min",
             "https://storage.googleapis.com/gtv-videos-bucket/sample/images/SubaruOutbackOnStreetAndDirt.jpg",
             "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4", 0),
        ]
        cur.executemany("""
            INSERT INTO conteudos (titulo, descricao, categoria, ano, duracao, capa, video_url, destaque)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, filmes)

    # Admin padrão
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE is_admin=1")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT OR IGNORE INTO usuarios (nome, email, senha, is_admin) VALUES (?, ?, ?, 1)",
            ("Jounnin 001", "abc@bentv.com", generate_password_hash("Boleia123!"))
        )
        print("Admin criado: abc@bentv.com")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado.")