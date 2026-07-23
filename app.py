import os
from flask import Flask, render_template, request, jsonify, session
from sqlalchemy import create_engine, text

app = Flask(__name__)
app.secret_key = 'story_corp_secret_key_segura'

DEFAULT_DB_URL = "postgresql://neondb_owner:npg_z2REAekgFNO0@ep-lucky-sound-att8o205-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def garantir_tabela_usuarios(conexao):
    conexao.execute(text("""
        CREATE TABLE IF NOT EXISTS app_user (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            senha VARCHAR(100) NOT NULL,
            nome_completo VARCHAR(150),
            email VARCHAR(100),
            telefone VARCHAR(30),
            cpf VARCHAR(20),
            endereco TEXT,
            cidade VARCHAR(100),
            estado VARCHAR(50),
            cep VARCHAR(20),
            is_admin BOOLEAN DEFAULT FALSE,
            aprovado BOOLEAN DEFAULT FALSE
        );
    """))
    conexao.commit()

@app.route('/')
@app.route('/admin')
def home():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    dados = request.get_json()
    usuario = dados.get('usuario')
    senha = dados.get('senha')

    # Login padrão do Administrador Mestre
    if usuario == 'admin' and senha == 'admin':
        session['usuario'] = 'admin'
        session['is_admin'] = True
        return jsonify({'sucesso': True, 'admin': True})

    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            garantir_tabela_usuarios(conexao)
            res = conexao.execute(text("""
                SELECT username, senha, is_admin, aprovado FROM app_user WHERE username = :u AND senha = :s
            """), {'u': usuario, 's': senha})
            user_row = res.fetchone()
            
            if user_row:
                if not user_row.aprovado:
                    return jsonify({'sucesso': False, 'erro': 'Sua conta está aguardando aprovação do Administrador Geral.'})
                
                session['usuario'] = user_row.username
                session['is_admin'] = bool(user_row.is_admin)
                return jsonify({'sucesso': True, 'admin': session['is_admin']})
                
        return jsonify({'sucesso': False, 'erro': 'Usuário ou senha incorretos.'})
    except Exception as e:
        if usuario == 'admin':
            session['usuario'] = 'admin'
            session['is_admin'] = True
            return jsonify({'sucesso': True, 'admin': True})
        return jsonify({'sucesso': False, 'erro': str(e)})

@app.route('/api/cadastrar', methods=['POST'])
def api_cadastrar():
    dados = request.get_json()
    username = dados.get('username')
    senha = dados.get('senha')
    nome_completo = dados.get('nome_completo')
    email = dados.get('email')
    telefone = dados.get('telefone')
    cpf = dados.get('cpf')
    endereco = dados.get('endereco')
    cidade = dados.get('cidade')
    estado = dados.get('estado')
    cep = dados.get('cep')
    
    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            garantir_tabela_usuarios(conexao)
            
            conexao.execute(text("""
                INSERT INTO app_user (username, senha, nome_completo, email, telefone, cpf, endereco, cidade, estado, cep, is_admin, aprovado)
                VALUES (:u, :s, :nc, :em, :tel, :cpf, :end, :cid, :est, :cep, FALSE, FALSE)
            """), {
                'u': username, 's': senha, 'nc': nome_completo, 'em': email,
                'tel': telefone, 'cpf': cpf, 'end': endereco, 'cid': cidade,
                'est': estado, 'cep': cep
            })
            conexao.commit()
            
        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado com sucesso! Aguarde a aprovação do Administrador para acessar.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': 'Erro ao cadastrar (usuário já pode existir): ' + str(e)})

@app.route('/api/admin/usuarios', methods=['GET'])
def api_listar_usuarios():
    if session.get('usuario') != 'admin' and not session.get('is_admin'):
        return jsonify({'sucesso': False, 'erro': 'Acesso negado.'}), 403
    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            garantir_tabela_usuarios(conexao)
            res = conexao.execute(text("SELECT id, username, nome_completo, email, telefone, is_admin, aprovado FROM app_user ORDER BY id DESC"))
            colunas = list(res.keys())
            usuarios = [dict(zip(colunas, linha)) for linha in res.fetchall()]
        return jsonify({'sucesso': True, 'usuarios': usuarios})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/aprovar', methods=['POST'])
def api_aprovar_usuario():
    if session.get('usuario') != 'admin' and not session.get('is_admin'):
        return jsonify({'sucesso': False, 'erro': 'Acesso negado.'}), 403
    dados = request.get_json()
    user_id = dados.get('id')
    aprovar = dados.get('aprovar') # True ou False
    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            conexao.execute(text("UPDATE app_user SET aprovado = :ap WHERE id = :id"), {'ap': aprovar, 'id': user_id})
            conexao.commit()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/admin/toggle_admin', methods=['POST'])
def api_toggle_admin():
    if session.get('usuario') != 'admin': # Apenas o admin mestre principal pode promover outros
        return jsonify({'sucesso': False, 'erro': 'Apenas o Administrador Mestre pode gerenciar permissões.'}), 403
    dados = request.get_json()
    user_id = dados.get('id')
    is_admin = dados.get('is_admin')
    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            conexao.execute(text("UPDATE app_user SET is_admin = :ia WHERE id = :id"), {'ia': is_admin, 'id': user_id})
            conexao.commit()
        return jsonify({'sucesso': True})
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'sucesso': True})

@app.route('/api/conectar', methods=['POST'])
def conectar_banco():
    if 'usuario' not in session:
        return jsonify({'sucesso': False, 'erro': 'Não autorizado. Faça login.'}), 401
        
    try:
        engine = create_engine(DEFAULT_DB_URL)
        with engine.connect() as conexao:
            res_vendas = conexao.execute(text("""
                SELECT 
                    COUNT(o.id) AS total_pedidos, 
                    COALESCE(SUM(p.preco), 0) AS faturamento_total,
                    COALESCE(SUM(p.custo), 0) AS custo_total
                FROM "order" o
                JOIN product p ON o.product_id = p.id
                WHERE o.status >= 2 AND o.status != 6
            """))
            dados_vendas = res_vendas.fetchone()
            
            faturamento = float(dados_vendas.faturamento_total)
            custo = float(dados_vendas.custo_total)
            lucro_liquido = faturamento - custo
            
            res_status = conexao.execute(text("""
                SELECT o.status, COUNT(o.id) AS quantidade
                FROM "order" o
                GROUP BY o.status
            """))
            status_counts = {int(row.status): row.quantidade for row in res_status.fetchall()}

            res_lista = conexao.execute(text("""
                SELECT o.id, o.status, o.tamanho, p.nome AS produto_nome, p.preco AS valor, COALESCE(p.custo, 0) AS custo 
                FROM "order" o
                JOIN product p ON o.product_id = p.id
                ORDER BY o.id DESC
            """))
            colunas = list(res_lista.keys())
            pedidos = [dict(zip(colunas, linha)) for linha in res_lista.fetchall()]
            
        return jsonify({
            'sucesso': True,
            'faturamento_total': faturamento,
            'custo_total': custo,
            'lucro_liquido': lucro_liquido,
            'total_pedidos_pagos': int(dados_vendas.total_pedidos),
            'status_counts': status_counts,
            'pedidos': pedidos,
            'usuario_logado': session.get('usuario'),
            'is_admin_mestre': session.get('usuario') == 'admin'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)