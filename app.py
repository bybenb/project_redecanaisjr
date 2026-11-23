from flask import Flask, abort, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
import os

app = Flask(__name__)
app.secret_key = "bentv-secret-super-seguro-2024"


# if not os.path.exists("bentv.db"):
init_db()

# ============== PÁGINAS ==============

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/player/<int:cid>")
def pagina_player(cid):
    conn = get_db()
    existe = conn.execute("SELECT 1 FROM conteudos WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not existe:
        abort(404)
    return render_template("player.html", conteudo_id=cid)

# ============== API AUTENTICAÇÃO ==============

@app.route("/api/registrar", methods=["POST"])
def registrar():
    data = request.json
    nome = data.get("nome", "").strip()
    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "")

    if not nome or not email or len(senha) < 4:
        return jsonify({"erro": "Dados inválidos (senha mín. 4 caracteres)"}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, senha) VALUES (?, ?, ?)",
            (nome, email, generate_password_hash(senha))
        )
        conn.commit()
        user = conn.execute("SELECT id, nome, email FROM usuarios WHERE email=?", (email,)).fetchone()
        session["user_id"] = user["id"]
        session["user_nome"] = user["nome"]
        return jsonify({"ok": True, "usuario": dict(user)})
    except Exception as e:
        return jsonify({"erro": "Email já cadastrado"}), 400
    finally:
        conn.close()



@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    senha = data.get("senha", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user["senha"], senha):
        session["user_id"] = user["id"]
        session["user_nome"] = user["nome"]

        return jsonify({"ok": True, "usuario": {
            "id": user["id"], "nome": user["nome"],
            "email": user["email"], "is_admin": user["is_admin"]
        }})


    return jsonify({"erro": "Email ou senha inválidos"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/me")
def me():
    if "user_id" in session:
        conn = get_db()
        u = conn.execute("SELECT id, nome, is_admin FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        return jsonify({"logado": True, "usuario": dict(u)})
    return jsonify({"logado": False})


# ============== API CONTEÚDOS ==============

@app.route("/api/conteudos")
def listar_conteudos():
    categoria = request.args.get("categoria")
    busca = request.args.get("busca", "").strip()

    conn = get_db()
    query = "SELECT * FROM conteudos WHERE 1=1"
    params = []

    if categoria and categoria != "Todos":
        query += " AND categoria=?"
        params.append(categoria)
    if busca:
        query += " AND (titulo LIKE ? OR descricao LIKE ?)"
        params.extend([f"%{busca}%", f"%{busca}%"])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/destaques")
def destaques():
    conn = get_db()
    rows = conn.execute("SELECT * FROM conteudos WHERE destaque=1").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/conteudo/<int:cid>")
def conteudo(cid):
    conn = get_db()
    row = conn.execute("SELECT * FROM conteudos WHERE id=?", (cid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"erro": "Não encontrado"}), 404
    return jsonify(dict(row))

@app.route("/api/categorias")
def categorias():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT categoria FROM conteudos ORDER BY categoria").fetchall()
    conn.close()
    return jsonify([r["categoria"] for r in rows])

# ============== API FAVORITOS ==============

@app.route("/api/favoritos", methods=["GET"])
def listar_favoritos():
    if "user_id" not in session:
        return jsonify({"erro": "Não autenticado"}), 401
    conn = get_db()
    rows = conn.execute("""
        SELECT c.* FROM favoritos f
        JOIN conteudos c ON c.id = f.conteudo_id
        WHERE f.usuario_id = ?
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/favoritos/<int:cid>", methods=["POST", "DELETE"])
def toggle_favorito(cid):
    if "user_id" not in session:
        return jsonify({"erro": "Não autenticado"}), 401

    conn = get_db()
    uid = session["user_id"]

    if request.method == "POST":
        try:
            conn.execute("INSERT INTO favoritos (usuario_id, conteudo_id) VALUES (?, ?)", (uid, cid))
            conn.commit()
            return jsonify({"favorito": True})
        except:
            return jsonify({"favorito": True, "msg": "já estava"})
    else:
        conn.execute("DELETE FROM favoritos WHERE usuario_id=? AND conteudo_id=?", (uid, cid))
        conn.commit()
        return jsonify({"favorito": False})
    # (fechar conn)
    conn.close()

# ============== HISTÓRICO ==============

@app.route("/api/historico", methods=["POST"])
def salvar_historico():
    if "user_id" not in session:
        return jsonify({"erro": "Não autenticado"}), 401
    data = request.json
    cid = data.get("conteudo_id")
    progresso = data.get("progresso", 0)
    conn = get_db()
    conn.execute("""
        INSERT INTO historico (usuario_id, conteudo_id, progresso, assistido_em)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(usuario_id, conteudo_id)
        DO UPDATE SET progresso=excluded.progresso, assistido_em=CURRENT_TIMESTAMP
    """, (session["user_id"], cid, progresso))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/historico", methods=["GET"])
def listar_historico():
    if "user_id" not in session:
        return jsonify([])
    conn = get_db()
    rows = conn.execute("""
        SELECT c.*, h.progresso, h.assistido_em
        FROM historico h
        JOIN conteudos c ON c.id = h.conteudo_id
        WHERE h.usuario_id = ?
        ORDER BY h.assistido_em DESC LIMIT 20
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])



# ============== ADMIN — HELPERS ==============
from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"erro": "Não autenticado"}), 401
        conn = get_db()
        u = conn.execute("SELECT is_admin FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
        conn.close()
        if not u or not u["is_admin"]:
            return jsonify({"erro": "Acesso negado"}), 403
        return f(*args, **kwargs)
    return wrapper

# ============== ADMIN — PÁGINA ==============

@app.route("/admin")
def pagina_admin():
    if "user_id" not in session:
        return redirect("/")
    conn = get_db()
    u = conn.execute("SELECT is_admin FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    if not u or not u["is_admin"]:
        return redirect("/")
    return render_template("admin.html")

# ============== ADMIN — DASHBOARD ==============

@app.route("/api/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    stats = {
        "conteudos": conn.execute("SELECT COUNT(*) FROM conteudos").fetchone()[0],
        "usuarios":  conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0],
        "favoritos": conn.execute("SELECT COUNT(*) FROM favoritos").fetchone()[0],
        "views":     conn.execute("SELECT COUNT(*) FROM historico").fetchone()[0],
    }
    conn.close()
    return jsonify(stats)

# ============== ADMIN — CRUD CONTEÚDOS ==============

@app.route("/api/admin/conteudos", methods=["GET"])
@admin_required
def admin_listar_conteudos():
    busca = request.args.get("busca", "").strip()
    conn = get_db()
    if busca:
        rows = conn.execute(
            "SELECT * FROM conteudos WHERE titulo LIKE ? OR video_url LIKE ? ORDER BY id DESC",
            (f"%{busca}%", f"%{busca}%")
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM conteudos ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/conteudos", methods=["POST"])
@admin_required
def admin_criar_conteudo():
    d = request.json
    if not d.get("titulo") or not d.get("video_url"):
        return jsonify({"erro": "Título e URL do vídeo são obrigatórios"}), 400
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO conteudos (titulo, descricao, categoria, ano, duracao, capa, video_url, destaque)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        d["titulo"], d.get("descricao", ""), d.get("categoria", ""),
        d.get("ano"), d.get("duracao", ""), d.get("capa", ""),
        d["video_url"], 1 if d.get("destaque") else 0
    ))
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return jsonify({"ok": True, "id": novo_id})

@app.route("/api/admin/conteudos/<int:cid>", methods=["PUT"])
@admin_required
def admin_editar_conteudo(cid):
    d = request.json
    conn = get_db()
    conn.execute("""
        UPDATE conteudos SET titulo=?, descricao=?, categoria=?, ano=?,
                             duracao=?, capa=?, video_url=?, destaque=?
        WHERE id=?
    """, (
        d["titulo"], d.get("descricao", ""), d.get("categoria", ""),
        d.get("ano"), d.get("duracao", ""), d.get("capa", ""),
        d["video_url"], 1 if d.get("destaque") else 0, cid
    ))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/api/admin/conteudos/<int:cid>", methods=["DELETE"])
@admin_required
def admin_eliminar_conteudo(cid):
    conn = get_db()
    conn.execute("DELETE FROM favoritos WHERE conteudo_id=?", (cid,))
    conn.execute("DELETE FROM historico WHERE conteudo_id=?", (cid,))
    conn.execute("DELETE FROM conteudos WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

# ============== ADMIN — TROCA DE DOMÍNIO EM MASSA ==============

@app.route("/api/admin/dominios/preview", methods=["POST"])
@admin_required
def admin_preview_dominio():
    """Mostra ANTES de aplicar quais URLs vão mudar."""
    d = request.json
    antigo = d.get("antigo", "").strip()
    novo = d.get("novo", "").strip()

    if not antigo or not novo:
        return jsonify({"erro": "Preenche o domínio antigo e o novo"}), 400

    conn = get_db()
    rows = conn.execute(
        "SELECT id, titulo, video_url FROM conteudos WHERE video_url LIKE ?",
        (f"%{antigo}%",)
    ).fetchall()
    conn.close()

    alteracoes = []
    for r in rows:
        alteracoes.append({
            "id": r["id"],
            "titulo": r["titulo"],
            "antes": r["video_url"],
            "depois": r["video_url"].replace(antigo, novo),
        })

    return jsonify({"total": len(alteracoes), "alteracoes": alteracoes})

@app.route("/api/admin/dominios/aplicar", methods=["POST"])
@admin_required
def admin_aplicar_dominio():
    """Aplica a substituição em todas as URLs que contenham o domínio antigo."""
    d = request.json
    antigo = d.get("antigo", "").strip()
    novo = d.get("novo", "").strip()

    if not antigo or not novo:
        return jsonify({"erro": "Preenche o domínio antigo e o novo"}), 400
    if antigo == novo:
        return jsonify({"erro": "Os domínios são iguais"}), 400

    conn = get_db()
    rows = conn.execute(
        "SELECT id, video_url FROM conteudos WHERE video_url LIKE ?",
        (f"%{antigo}%",)
    ).fetchall()

    atualizados = 0
    for r in rows:
        nova_url = r["video_url"].replace(antigo, novo)
        conn.execute("UPDATE conteudos SET video_url=? WHERE id=?", (nova_url, r["id"]))
        atualizados += 1

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "atualizados": atualizados})

# ============== ADMIN — UTILITÁRIOS ==============

@app.route("/api/admin/dominios/lista", methods=["GET"])
@admin_required
def admin_listar_dominios():
    """Extrai todos os domínios únicos usados nas video_url (útil para o dropdown)."""
    from urllib.parse import urlparse
    conn = get_db()
    rows = conn.execute("SELECT video_url FROM conteudos").fetchall()
    conn.close()

    dominios = set()
    for r in rows:
        try:
            p = urlparse(r["video_url"])
            if p.netloc:
                dominios.add(f"{p.scheme}://{p.netloc}")
        except Exception:
            pass

    return jsonify(sorted(dominios))

# ============== ADMIN — USUÁRIOS ==============

@app.route("/api/admin/usuarios", methods=["GET"])
@admin_required
def admin_listar_usuarios():
    conn = get_db()
    rows = conn.execute("""
        SELECT id, nome, email, is_admin, criado_em FROM usuarios ORDER BY id DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/admin/usuarios/<int:uid>/admin", methods=["POST"])
@admin_required
def admin_toggle_admin(uid):
    if uid == session["user_id"]:
        return jsonify({"erro": "Não podes remover o teu próprio admin"}), 400
    conn = get_db()
    u = conn.execute("SELECT is_admin FROM usuarios WHERE id=?", (uid,)).fetchone()
    if not u:
        conn.close()
        return jsonify({"erro": "Utilizador não encontrado"}), 404
    novo = 0 if u["is_admin"] else 1
    conn.execute("UPDATE usuarios SET is_admin=? WHERE id=?", (novo, uid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "is_admin": novo})

@app.route("/api/admin/usuarios/<int:uid>", methods=["DELETE"])
@admin_required
def admin_eliminar_usuario(uid):
    if uid == session["user_id"]:
        return jsonify({"erro": "Não podes apagar-te a ti mesmo"}), 400
    conn = get_db()
    conn.execute("DELETE FROM favoritos WHERE usuario_id=?", (uid,))
    conn.execute("DELETE FROM historico WHERE usuario_id=?", (uid,))
    conn.execute("DELETE FROM usuarios WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})





# ============== INICIAR ==============

if __name__ == "__main__":
    init_db()
    print("RedeCanais Jr rodando em http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)