import os
import jwt
import random
import datetime
import threading
from flask import Flask, jsonify, request, make_response, send_from_directory
from main import app, get_db_connection
from funcao import (
        verificar_senha,
        criptografar,
        checar_senha,
        gerar_token,
        enviando_email
    )
    
SECRET_KEY = "segredo_super"
UPLOAD_FOLDER = os.path.join(app.config.get('UPLOAD_FOLDER', 'static/uploads'), "usuarios")
    
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    
    
def verificar_reuso_senha(id_usuario, senha_nova, cur):
    cur.execute("SELECT SENHA_HASH FROM HISTORICO_SENHAS WHERE ID_USUARIO = ?", (id_usuario,))
    historico = cur.fetchall()
    for (hash_antigo,) in historico[-3:]:
        if checar_senha(senha_nova, hash_antigo):
            return True
    return False




# lista de usuarios
@app.route('/usuarios', methods=['GET'])
def listar_usuarios():
    con = None
    cur = None

    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO, NOME, EMAIL, TIPO_NOME, BLOQUEADO FROM USUARIO")
        usuarios = cur.fetchall()

        resultado = []
        for u in usuarios:
            resultado.append({
                'id': u[0],
                'nome': u[1],
                'email': u[2],
                'tipo': u[3],
                'bloqueado': "Sim" if u[4] else "Não",
            })

        return jsonify(resultado), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    finally:
        if cur: cur.close()
        if con: con.close()



# buscar o usuario
@app.route('/admin/buscar_nome', methods=['GET'])
def buscar_usuario_nome():
    from main import app
    con = None
    cur = None

    # 1. Captura de Token (via Cookie ou Header Authorization)
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'erro': 'Acesso negado. Token não fornecido.'}), 401

    try:
        # 2. Decodificar o token para verificar se é ADM
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        id_quem_chamou = payload.get('id_usuario')

        con = get_db_connection()
        cur = con.cursor()

        # 3. Verificação de ADM (Tipo 1)
        cur.execute("SELECT ID_TIPO FROM USUARIO WHERE ID_USUARIO = ?", (id_quem_chamou,))
        usuario_adm = cur.fetchone()

        if not usuario_adm or usuario_adm[0] != 1:
            return jsonify({'erro': 'Acesso negado. Apenas administradores podem buscar usuários.'}), 403

        # 4. Pegar o nome da busca via Query Params (ex: ?nome=gabriel)
        nome_busca = request.args.get('nome', '')

        # 5. Executar a busca com UPPER para ser "case-insensitive"
        cur.execute("""
                    SELECT ID_USUARIO, NOME, EMAIL, TIPO_NOME, BLOQUEADO
                    FROM USUARIO
                    WHERE UPPER(NOME) LIKE UPPER(?)
                    """, (f'%{nome_busca}%',))

        usuarios = cur.fetchall()

        # 6. Montar o JSON de retorno
        resultado = [
            {
                'id': u[0],
                'nome': u[1],
                'email': u[2],
                'tipo': u[3],
                'bloqueado': bool(u[4])
            } for u in usuarios
        ]

        return jsonify(resultado), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'erro': 'Sua sessão expirou. Logue novamente.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'erro': 'Token inválido.'}), 401
    except Exception as e:
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500
    finally:
        if cur: cur.close()
        if con: con.close()




@app.route('/criar_usuario', methods=['POST'])
def criar_usuario_novo(id_user=None):
    con = None
    cur = None

    try:
        # 1. Receber dados via FORM-DATA
        nome = request.form.get('nome')
        email = request.form.get('email')
        senha = request.form.get('senha')
        id_tipo = int(request.form.get('id_tipo', 2))

        # Captura a foto (se ela foi enviada)
        foto = request.files.get('foto')

        if not all([nome, email, senha]):
            return jsonify({'erro': 'Nome, email e senha são obrigatórios.'}), 400

        # Define o nome do tipo
        tipo_nome = 'admin' if id_tipo == 1 else 'garcom'

        con = get_db_connection()
        cur = con.cursor()

        # 2. Verificações de segurança
        cur.execute("SELECT id_usuario FROM USUARIO WHERE email=?", (email,))
        if cur.fetchone():
            return jsonify({'erro': 'Email já cadastrado.'}), 409

        erro_v = verificar_senha(senha)
        if erro_v:
            return jsonify({'erro': erro_v}), 400

        # 3. Criptografia
        senha_hash = criptografar(senha)

        # 4. Lógica da Foto — salva em disco se enviada
        foto_caminho = None
        if foto and foto.filename:
            nome_arquivo = f"{id_user}_{foto.filename}"
            caminho_pasta = app.config['UPLOAD_FOLDER']
            caminho_completo = os.path.join(caminho_pasta, nome_arquivo)
            foto.save(caminho_completo)
            foto_caminho = f"/{caminho_pasta}/{nome_arquivo}"

        # 5. Inserção no Banco
        cur.execute("""
                    INSERT INTO USUARIO (nome, email, senha, id_tipo, tipo_nome, conta_confirmada, bloqueado,
                                         tentativas_login)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id_usuario
                    """, (nome, email, senha_hash, id_tipo, tipo_nome, False, False, 0))

        id_user = cur.fetchone()[0]

        # 6. Histórico e Código
        cur.execute("INSERT INTO HISTORICO_SENHAS (id_usuario, senha_hash) VALUES (?, ?)", (id_user, senha_hash))

        codigo = str(random.randint(100000, 999999))
        cur.execute("INSERT INTO CODIGOS (id_usuario, codigo, tipo) VALUES (?, ?, 'confirmacao')", (id_user, codigo))

        con.commit()

        # 7. Envio de e-mail
        threading.Thread(target=enviando_email,
                         args=(email, "Confirmação", f"Olá {nome}, seu código: {codigo}")).start()

        return jsonify({'mensagem': f'Conta de {tipo_nome} criada!', 'id_usuario': id_user, 'foto': foto_caminho}), 201

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro interno: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()


@app.route('/reenviar_codigo_confirmacao', methods=['POST'])
def reenviar_codigo_confirmacao():
    con = None
    cur = None

    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'Os dados devem ser enviados em formato JSON.'}), 400

        id_usuario = dados.get('id_usuario')
        if not id_usuario:
            return jsonify({'erro': 'ID do usuário é obrigatório.'}), 400

        con = get_db_connection()
        cur = con.cursor()

        # Busca o email e nome do usuário
        cur.execute("SELECT EMAIL, NOME FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado.'}), 404

        email, nome = usuario

        # Gera um novo código
        codigo = str(random.randint(100000, 999999))

        # Salva o novo código na tabela CODIGOS
        cur.execute(
            "INSERT INTO CODIGOS (id_usuario, codigo, tipo) VALUES (?, ?, 'confirmacao')",
            (id_usuario, codigo)
        )
        con.commit()

        # Envia o código por e-mail
        threading.Thread(
            target=enviando_email,
            args=(email, "Confirmação de Conta", f"Olá {nome}, seu novo código de confirmação é: {codigo}")
        ).start()

        return jsonify({'mensagem': 'Código reenviado com sucesso! Verifique seu e-mail.'}), 200

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500
    finally:
        if cur: cur.close()
        if con: con.close()


@app.route('/editar_usuario/<int:id_usuario>', methods=['PUT', 'POST'])
def editar_usuario(id_usuario):
    from main import app
    con = None
    cur = None

    # 1. Captura de Token/Cookies (Padronização para monitoramento)
    token = request.cookies.get('access_token')

    try:
        # 2. Receber dados via JSON
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'Os dados devem ser enviados em formato JSON.'}), 400

        con = get_db_connection()
        cur = con.cursor()

        # 3. Verificar se o usuário existe e pegar dados atuais
        cur.execute("SELECT SENHA, NOME, EMAIL FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        res = cur.fetchone()
        if not res:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        hash_atual, nome_at, email_at = res

        # 4. Pegar novos valores do JSON ou manter os atuais
        nome = dados.get('nome') or nome_at
        email = dados.get('email') or email_at
        senha_nova = dados.get('senha')

        senha_final = hash_atual

        # 5. Lógica de alteração de senha
        if senha_nova and str(senha_nova).strip() != "":
            # Verifica reuso (supondo que verificar_reuso_senha já esteja importada)
            if verificar_reuso_senha(id_usuario, senha_nova, cur):
                return jsonify({'erro': 'Senha já usada recentemente. Escolha outra.'}), 400

            # Salva a senha antiga no histórico antes de mudar
            cur.execute("INSERT INTO HISTORICO_SENHAS (ID_USUARIO, SENHA_HASH) VALUES (?, ?)",
                        (id_usuario, hash_atual))

            # Criptografa a nova (supondo que criptografar já esteja importada)
            senha_final = criptografar(senha_nova)

        # 6. Atualizar no banco
        cur.execute("""
                    UPDATE USUARIO
                    SET NOME  = ?,
                        EMAIL = ?,
                        SENHA = ?
                    WHERE ID_USUARIO = ?
                    """, (nome, email, senha_final, id_usuario))

        con.commit()
        return jsonify({'mensagem': 'Dados atualizados com sucesso!'}), 200

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro ao editar: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()



@app.route('/excluir_usuario/<int:id_alvo>', methods=['DELETE'])
def excluir_usuario(id_alvo):
    from main import app
    con = None
    cur = None

    # 1. Captura de Token (via Cookie ou Header Authorization)
    token = request.cookies.get('access_token')

    if not token:
        return jsonify({'erro': 'Acesso negado. Token não fornecido.'}), 401

    try:
        # 2. Decodificar o token para saber quem está tentando excluir
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        id_quem_chamou = payload.get('id_usuario')

        con = get_db_connection()
        cur = con.cursor()

        # 3. VERIFICAÇÃO DE ADM: Busca o tipo do usuário logado
        cur.execute("SELECT ID_TIPO FROM USUARIO WHERE ID_USUARIO = ?", (id_quem_chamou,))
        usuario_logado = cur.fetchone()

        # Se não existir ou o ID_TIPO não for 1 (ADM), bloqueia
        if not usuario_logado or usuario_logado[0] != 1:
            return jsonify({'erro': 'Acesso negado. Apenas administradores podem excluir usuários.'}), 403

        # 4. Executa a exclusão em cascata (Codigos -> Histórico -> Usuário)
        cur.execute("DELETE FROM CODIGOS WHERE ID_USUARIO = ?", (id_alvo,))
        cur.execute("DELETE FROM HISTORICO_SENHAS WHERE ID_USUARIO = ?", (id_alvo,))
        cur.execute("DELETE FROM USUARIO WHERE ID_USUARIO = ?", (id_alvo,))

        if cur.rowcount == 0:
            return jsonify({'erro': 'Usuário alvo não encontrado.'}), 404

        con.commit()
        return jsonify({'mensagem': f'Usuário {id_alvo} removido com sucesso pelo administrador.'}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'erro': 'Sua sessão expirou. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'erro': 'Token inválido ou corrompido.'}), 401
    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro ao excluir: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()


from flask import make_response  # Import necessário para criar a resposta com cookie






@app.route('/login', methods=['POST'])
def login():

    print("🔵 ROTA /login FOI CHAMADA!")

    con = None
    cur = None
    try:
        # 1. Receber dados via JSON
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'Os dados devem ser enviados em formato JSON.'}), 400

        email = dados.get('email')
        senha = dados.get('senha')

        con = get_db_connection()
        cur = con.cursor()

        cur.execute("""
                    SELECT id_usuario,
                           senha,
                           nome,
                           conta_confirmada,
                           id_tipo,
                           tipo_nome,
                           bloqueado,
                           tentativas_login
                    FROM USUARIO
                    WHERE email = ?
                    """, (email,))

        user = cur.fetchone()
        if not user:
            return jsonify({'erro': 'Usuário não encontrado.'}), 404

        id_u, s_db, nome, conf, id_t, t_nome, bloqueado, tentativas = user

        # 2. Verificações de Bloqueio e Confirmação
        if bloqueado:
            return jsonify({'erro': 'Sua conta está bloqueada. Procure um administrador.'}), 403

        if not conf:
            return jsonify({'erro': 'Conta não confirmada. Verifique seu e-mail.'}), 403

        # 3. Validação da Senha
        if checar_senha(senha, s_db):
            # Resetar tentativas se acertar
            cur.execute("UPDATE USUARIO SET tentativas_login = 0 WHERE id_usuario = ?", (id_u,))
            con.commit()

            # Gerar o token (sua função já existente)
            token = gerar_token(id_u)

            # 4. CRIAR A RESPOSTA E DEFINIR O COOKIE
            # Criamos o objeto de resposta primeiro
            resposta = make_response(jsonify({
                'mensagem': 'Login realizado com sucesso!',
                'token': token,
                'usuario': {
                    'id': id_u,
                    'nome': nome,
                    'tipo': t_nome,
                    'id_tipo': id_t
                }
            }))

            # Definimos o cookie "access_token"
            # httponly=True: impede acesso via JS
            # samesite='Lax': não envia em cross-site origin (problema no localhost)
            # max_age: tempo em segundos (ex: 24 horas = 86400)
            resposta.set_cookie(
                'access_token',
                token,
                httponly=True,
                secure=False,  # Mude para True se usar HTTPS (produção)
                samesite='Lax',
                max_age=86400
            )

            return resposta, 200

        else:
            # 5. Lógica de Erro de Senha e Bloqueio
            novas_tentativas = tentativas + 1

            if novas_tentativas >= 3:
                cur.execute("UPDATE USUARIO SET tentativas_login = ?, bloqueado = ? WHERE id_usuario = ?",
                            (novas_tentativas, True, id_u))
                con.commit()
                return jsonify({'erro': 'Senha incorreta. Conta bloqueada!'}), 403
            else:
                cur.execute("UPDATE USUARIO SET tentativas_login = ? WHERE id_usuario = ?",
                            (novas_tentativas, id_u))
                con.commit()
                return jsonify({'erro': f'Senha incorreta. Tentativa {novas_tentativas} de 3.'}), 401

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro no login: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()



# ROTA: CONFIRMAR CÓDIGO (COM OPÇÃO DE ALTERAÇÃO DE SENHA)

@app.route('/confirmar_codigo', methods=['POST'])
def confirmar_codigo():
    con = None
    cur = None

    try:
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'Os dados devem ser enviados em formato JSON.'}), 400

        # 1. Captura email e código
        email = str(dados.get('email', '')).strip()
        codigo_enviado = str(dados.get('codigo', '')).strip()
        nova_senha = dados.get('senha')  # Pode ser None

        if not email:
            return jsonify({'erro': 'O e-mail é obrigatório.'}), 400
        if not codigo_enviado:
            return jsonify({'erro': 'O código é obrigatório.'}), 400

        con = get_db_connection()
        cur = con.cursor()

        # 2. Busca o usuário pelo e-mail
        cur.execute("SELECT ID_USUARIO, CONTA_CONFIRMADA FROM USUARIO WHERE EMAIL = ?", (email,))
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado com este e-mail.'}), 404

        id_user, conta_confirmada = usuario

        if conta_confirmada:
            return jsonify({'erro': 'Esta conta já foi confirmada.'}), 400

        # =====================================================
        # 3. Busca o código nas duas tabelas:
        #    RECUPERAR_SENHA (fluxo esqueci senha)
        #    CODIGOS (fluxo novo usuário criado)
        # =====================================================
        tabela_origem = None

        # 3a. Tenta tabela de recuperação de senha
        cur.execute("""
                    SELECT ID_USUARIO
                    FROM RECUPERAR_SENHA
                    WHERE TRIM(CODIGO) = ?
                      AND ID_USUARIO = ?
                      AND UTILIZADO = ?
                    """, (codigo_enviado, id_user, 0))

        resultado = cur.fetchone()
        if resultado:
            tabela_origem = 'recuperar_senha'

        # 3b. Se não encontrou, tenta tabela de códigos de confirmação
        if tabela_origem is None:
            cur.execute("""
                        SELECT ID_USUARIO
                        FROM CODIGOS
                        WHERE TRIM(CODIGO) = ?
                          AND ID_USUARIO = ?
                          AND TIPO = ?
                        """, (codigo_enviado, id_user, 'confirmacao'))

            resultado = cur.fetchone()
            if resultado:
                tabela_origem = 'codigos'

        if not tabela_origem:
            return jsonify({'erro': 'Código inválido ou já utilizado.'}), 400

        # 4. Lógica de Atualização
        if nova_senha and str(nova_senha).strip() != "":
            erro_v = verificar_senha(nova_senha)
            if erro_v:
                return jsonify({'erro': erro_v}), 400

            senha_hash = criptografar(nova_senha)

            cur.execute("""
                        UPDATE USUARIO
                        SET CONTA_CONFIRMADA = ?,
                            SENHA            = ?
                        WHERE ID_USUARIO = ?
                        """, (True, senha_hash, id_user))

            mensagem_sucesso = 'Conta confirmada e senha alterada com sucesso!'
        else:
            cur.execute("UPDATE USUARIO SET CONTA_CONFIRMADA = ? WHERE ID_USUARIO = ?", (True, id_user))
            mensagem_sucesso = 'Conta confirmada com sucesso!'

        # 5. Marca o código como usado
        if tabela_origem == 'recuperar_senha':
            cur.execute("""
                        UPDATE RECUPERAR_SENHA
                        SET UTILIZADO = ?
                        WHERE TRIM(CODIGO) = ?
                          AND ID_USUARIO = ?
                        """, (True, codigo_enviado, id_user))
        else:
            cur.execute("""
                        DELETE FROM CODIGOS
                        WHERE TRIM(CODIGO) = ?
                          AND ID_USUARIO = ?
                        """, (codigo_enviado, id_user))

        con.commit()
        return jsonify({
            'mensagem': mensagem_sucesso,
            'id_usuario': id_user
        }), 200

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro interno: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()





@app.route('/solicitar_recuperacao', methods=['POST'])
def solicitar_recuperacao():
    from main import app
    con = None
    cur = None

    # 1. Captura de Token (Cookie ou Header) - Opcional para recuperação
    token = request.cookies.get('access_token')

    try:
        # 2. Receber o e-mail via JSON
        dados = request.get_json(silent=True)
        if not dados:
            return jsonify({'erro': 'Os dados devem ser enviados em formato JSON.'}), 400

        email = dados.get('email')
        if not email:
            return jsonify({'erro': 'O e-mail é obrigatório.'}), 400

        # 3. Conexão e Busca do Usuário
        con = get_db_connection()
        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO, NOME FROM USUARIO WHERE EMAIL = ?", (email,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado com este e-mail.'}), 404

        id_usuario, nome_usuario = usuario

        # 4. Gerar Código e Expiração (15 minutos)
        codigo = str(random.randint(100000, 999999))
        expiracao = datetime.datetime.now() + datetime.timedelta(minutes=15)

        # 5. SALVAR NO BANCO DE DADOS (Tabela RECUPERAR_SENHA)
        # Garantimos que UTILIZADO comece como 0 (Falso)
        cur.execute("""
            INSERT INTO RECUPERAR_SENHA (ID_USUARIO, CODIGO, EXPIRACAO, UTILIZADO)
            VALUES (?, ?, ?, ?)
        """, (id_usuario, codigo, expiracao, 0))

        con.commit()

        # 6. Envio do e-mail em segundo plano para não travar a resposta
        threading.Thread(
            target=enviando_email,
            args=(email, "Recuperação de Senha", f"Olá {nome_usuario}, seu código de recuperação é: {codigo}")
        ).start()

        return jsonify({"mensagem": "Código de recuperação gerado e enviado com sucesso!"}), 200

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f"Erro ao processar recuperação: {str(e)}"}), 500
    finally:
        if cur: cur.close()
        if con: con.close()


@app.route('/redefinir_senha', methods=['POST'])
def redefinir_senha():
    from main import app

    # 1. Autenticação (requer token válido)
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'erro': 'Acesso negado. Token não fornecido.'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({'erro': 'Sessão expirada.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'erro': 'Token inválido.'}), 401

    con = get_db_connection()
    cur = con.cursor()
    try:
        email = request.form.get('email')
        codigo = request.form.get('codigo')
        nova_senha = request.form.get('nova_senha')

        if not all([email, codigo, nova_senha]):
            return jsonify({'erro': 'Preencha email, código e nova senha.'}), 400

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ?", (email,))
        user = cur.fetchone()
        if not user:
            return jsonify({'erro': 'Usuário não encontrado.'}), 404
        id_usuario = user[0]

        cur.execute("""
                    SELECT CODIGO
                    FROM RECUPERAR_SENHA
                    WHERE ID_USUARIO = ?
                      AND CODIGO = ?
                      AND UTILIZADO = ?
                      AND EXPIRACAO > ?
                    """, (id_usuario, codigo, 0, datetime.datetime.now()))

        if not cur.fetchone():
            return jsonify({'erro': 'Código inválido ou expirado.'}), 400

        erro_senha = verificar_senha(nova_senha)
        if erro_senha:
            return jsonify({'erro': erro_senha}), 400

        if verificar_reuso_senha(id_usuario, nova_senha, cur):
            return jsonify({'erro': 'Você não pode usar uma senha recente.'}), 400

        senha_hash = criptografar(nova_senha)
        cur.execute("UPDATE USUARIO SET SENHA = ?, BLOQUEADO = ?, tentativas_login = ? WHERE ID_USUARIO = ?",
                    (senha_hash, False, 0, id_usuario))
        cur.execute("UPDATE RECUPERAR_SENHA SET UTILIZADO = 1 WHERE ID_USUARIO = ? AND CODIGO = ?",
                    (id_usuario, codigo))

        con.commit()
        return jsonify({"mensagem": "Senha alterada com sucesso!"}), 200
    except Exception as e:
        if con:
            con.rollback()
        return jsonify({'erro': str(e)}), 500
    finally:
        if cur:
            cur.close()
        if con:
            con.close()





@app.route('/admin/desbloquear/<int:id_alvo>', methods=['POST'])
def desbloquear_usuario(id_alvo):
    con = None
    cur = None

    try:
        con = get_db_connection()
        cur = con.cursor()

        cur.execute(
            "UPDATE USUARIO SET BLOQUEADO = ?, tentativas_login = ? WHERE ID_USUARIO = ?",
            (False, 0, id_alvo)
        )

        if cur.rowcount == 0:
            return jsonify({'erro': 'Usuário alvo não encontrado.'}), 404

        con.commit()
        return jsonify({'mensagem': f'Usuário {id_alvo} desbloqueado com sucesso!'}), 200

    except Exception as e:
        if con: con.rollback()
        return jsonify({'erro': f'Erro interno: {str(e)}'}), 500
    finally:
        if cur: cur.close()
        if con: con.close()






@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({'mensagem': 'Logout realizado'}), 200)
    resp.delete_cookie('access_token')
    return resp



@app.route('/uploads/usuarios/<path:filename>')
def servir_foto_usuario(filename):
    pasta = app.config.get('UPLOAD_FOLDER', os.path.join('uploads', 'usuarios'))
    return send_from_directory(pasta, filename)


if __name__ == '__main__':
    app.run(debug=True)
