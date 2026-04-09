from flask import Flask, jsonify, request
import random
import firebase_admin
from firebase_admin import credentials, firestore
from auth import token_obrigatorio, gerar_token
from flask_cors import CORS
import os
from dotenv import load_dotenv
import json
from flasgger import Swagger

load_dotenv()

app = Flask(__name__)
app.config['SWAGGER'] = {
    'openapi': '3.0.0',
    'title': 'API de Charadas do Tio João',
}
swagger = Swagger(app, template_file='openapi.yaml')

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
CORS(app, origins="*")

ADM_USUARIO = os.getenv("ADM_USUARIO")
ADM_SENHA = os.getenv("ADM_SENHA")

if os.getenv("VERCEL"):
    # ONLINE NA VERCEL
    cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS")))
else:
    # LOCAL
    cred = credentials.Certificate("firebase.json")

# Carregar as credenciais do Firebase
firebase_admin.initialize_app(cred)

# Conectar-se o Firestore
db = firestore.client()






# Rota principal de boas vindas
@app.route("/", methods=['GET'])
def root():
    return jsonify({
        "api":"charadas",
        "version":"1.0",
        "Author": "Tio João"
    }), 200

# ==========================
#      ROTA DE LOGIN
# ==========================
@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json()

    if not dados:
        return jsonify({"error":"Envie os dados para login"}), 400
    
    usuario = dados.get("usuario")
    senha = dados.get("senha")

    if not usuario or not senha:
        return jsonify({"error":"Usuário e senha são obrigatórios!"}), 400

    if usuario == ADM_USUARIO and senha == ADM_SENHA:
        token = gerar_token(usuario)
        return jsonify({
            "message":"Login realizado com sucesso!",
            "token": token
        }), 200
    
    return jsonify({"error":"Usuário ou senha inválidos!"}), 401


# Rota 1 - Método GET - Todas as charadas
@app.route("/charadas", methods=['GET'])
def get_charadas():
    charadas = []  # Lista vazia
    lista = db.collection('charadas').stream() # Lista todos documentos4
    
    # Transforma objeto do Firestore em Dicionário Python
    for item in lista:
        charadas.append(item.to_dict())
    
    return jsonify(charadas), 200


# Rota 2 - Método GET - Charadas aleatórias
@app.route("/charadas/aleatoria", methods=['GET'])
def get_charadas_random():
    charadas = []  # Lista vazia
    lista = db.collection('charadas').stream() # Lista todos documentos4
    
    # Transforma objeto do Firestore em Dicionário Python
    for item in lista:
        charadas.append(item.to_dict())
    
    return jsonify(random.choice(charadas)), 200

# Rota 3 - Método GET - Retorna charada pelo id
@app.route("/charadas/<int:id>", methods=['GET'])
def get_charada_by_id(id):

    lista = db.collection('charadas').where('id', '==', id).stream()

    for item in lista:
        return jsonify(item.to_dict()), 200
    
    return jsonify({"error":"Charada não encontrada"}), 404

# =======================================
#     ROTAS PRIVADAS
# =======================================

# Rota 4 - Método POST - Criar nova charadas
@app.route("/charadas", methods=['POST'])
@token_obrigatorio
def post_charadas():

    
    dados = request.get_json()

    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error":"Dados inválidos ou incompletos!"}), 400
    
    try:
        # Busca pelo contador
        contador_ref = db.collection("contador").document("controle_id")
        contador_doc = contador_ref.get()
        
        # Correção: Trata o caso onde o documento no banco ainda não foi criado
        doc_dict = contador_doc.to_dict()
        if doc_dict is not None and "ultimo_id" in doc_dict:
            ultimo_id = doc_dict.get("ultimo_id")
        else:
            ultimo_id = 0
            contador_ref.set({"ultimo_id": 0}) # Cria o documento se não existir
            
        # Somar 1 ao ultimo id
        novo_id = ultimo_id + 1
        # Atualizar o id do contador
        contador_ref.update({"ultimo_id": novo_id})

        # Cadastrar a nova charada
        db.collection("charadas").add({
            "id": novo_id,
            "pergunta": dados["pergunta"],
            "resposta": dados["resposta"]
        })

        return jsonify({"message":"Charada criada com sucesso!"}), 201
    except:
        return jsonify({"error":"Falha no envio da charada"}), 400

# Rota 5 - Método PUT - Alteração total
@app.route("/charadas/<int:id>", methods=['PUT'])
@token_obrigatorio
def chararas_put(id):

    
    dados = request.get_json()

    # PUT - É necessário enviar PERGUNTA e RESPOSTA
    if not dados or "pergunta" not in dados or "resposta" not in dados:
        return jsonify({"error":"Dados inválidos ou incompletos!"}), 400
    
    try:
        docs = db.collection("charadas").where("id","==",id).limit(1).get()
        if not docs:
            return jsonify({"error":"Charada não encontrada"}), 404
        
        # Pega o primeiro (e único) documento da lista
        for doc in docs:
            doc_ref = db.collection("charadas").document(doc.id)
            doc_ref.update({
                "pergunta": dados["pergunta"],
                "resposta": dados["resposta"]
            })

        return jsonify({"message": "Charada alterada com sucesso"}), 200
    except:
        return jsonify({"error":"Falha na alteração da charada"}), 400

 
# Rota 6 - Método PATCH - Alteração parcial
@app.route("/charadas/<int:id>", methods=['PATCH'])
@token_obrigatorio
def chararas_patch(id):

    
    dados = request.get_json()

    # PATCH - pode alterar só pergunta ou só resposta
    if not dados or ("pergunta" not in dados and "resposta" not in dados):
        return jsonify({"error":"Dados inválidos!"}), 400
    
    try:
        docs = db.collection("charadas").where("id","==",id).limit(1).get()
        if not docs:
            return jsonify({"error":"Charada não encontrada"}), 404
        
        doc_ref = db.collection("charadas").document(docs[0].id)
        update_charada = {}
        if "pergunta" in dados:
            update_charada["pergunta"] = dados["pergunta"]

        if "resposta" in dados:
            update_charada["resposta"] = dados["resposta"]

        # Atualiza o Firestore
        doc_ref.update(update_charada)

        return jsonify({"message": "Charada alterada com sucesso"}), 200

    except:
        return jsonify({"error":"Falha na alteração da charada"}), 400
    
# Rota 7 - DELETE - Excluir charada
@app.route("/charadas/<int:id>", methods=['DELETE'])
@token_obrigatorio
def delete_charada(id):


    docs = db.collection("charadas").where("id","==",id).limit(1).get()

    if not docs:
        return jsonify({"error":"Charada não encontrada"}), 404

    doc_ref = db.collection("charadas").document(docs[0].id)
    doc_ref.delete()
    return jsonify({"message":"Charada excluída com sucesso!"}), 200

# ====================
#  Rotas de tratamento de erros
# ====================
@app.errorhandler(404)
def erro404(error):
    return jsonify({"error":"URL não encontrada"}), 404

@app.errorhandler(500)
def erro500(error):
    return jsonify({"error":"Servidor interno com falhas. Tente mais tarde"}), 500




if __name__ == "__main__":
    app.run(debug=True)