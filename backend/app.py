from flask import Flask, render_template, request, jsonify
import openai
import os
from pymongo import MongoClient
import datetime
import uuid  # Import pour générer des UUID
from flask_cors import CORS



app = Flask(__name__)

CORS(app)

# Configuration de l'API OpenAI
openai.api_key = "sk-proj-tRmHIgOmg1u8yQWR1DnZT3BlbkFJb1oN7HScJyBaBfiZFcvE"  # Ajoutez votre clé API OpenAI ici

system_prompt = """Tu es le service client chatbot du site d'une entreprise de recyclage nommée Ecocycle, qui propose des services de recyclage pour papiers, électroniques et cartons. Nous sommes situés à Tizi Ouzou, Algérie. Voici nos coordonnées :

- E-mail : myecocycle.dz@gmail.com
- Numéro : 0541 706 795
- Page Facebook : Ecocycle
- Instagram : myecocycle

Si tu reçois une question à laquelle tu ne sais pas répondre, informe les utilisateurs de les contacter par téléphone au numéro mentionné ou par e-mail.
"""

# Connexion à la base de données MongoDB
try:
    client = MongoClient('mongodb://localhost:27017/')  # Remplacez avec l'adresse et le port de votre instance MongoDB
    db = client['db']  # Nom de votre base de données
    collection = db['new-chatbot-history-collection']  # Nom de votre Time-Series Collection
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print(f"Erreur de connexion à MongoDB : {e}")

def get_or_create_conversation_id(user):
    """
    Génère ou récupère un identifiant de conversation pour l'utilisateur.
    
    :param user: Nom ou identifiant de l'utilisateur
    :return: Identifiant de conversation (UUID)
    """
    # Recherche le dernier message de l'utilisateur pour vérifier s'il existe une conversation active
    latest_message = collection.find_one(
        {"user": user, "is_bot": False},
        sort=[("timestamp", -1)]
    )
    
    if latest_message and (datetime.datetime.utcnow() - latest_message['timestamp']).total_seconds() < 1800:
        # Retourne l'identifiant de conversation existant si moins de 30 minutes se sont écoulées
        return latest_message['conversation_id']
    else:
        # Génère un nouvel identifiant de conversation
        return str(uuid.uuid4())

def save_message(user, message, conversation_id, is_bot=False):
    """
    Sauvegarde un message dans MongoDB.
    
    :param user: Nom ou identifiant de l'utilisateur
    :param message: Le message à sauvegarder
    :param conversation_id: Identifiant de la conversation
    :param is_bot: Booléen indiquant si le message provient du bot (par défaut False)
    """
    conversation_entry = {
        'conversation_id': conversation_id,
        'user': user,
        'message': message,
        'is_bot': is_bot,
        'timestamp': datetime.datetime.utcnow()
    }
    
    try:
        collection.insert_one(conversation_entry)
        print("Message sauvegardé avec succès.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du message : {e}")

@app.route("/")
def index():
    return render_template('chatbot.html')

@app.route("/get", methods=["POST"])
def chat():
    msg = request.form["msg"]
    
    # Génère ou récupère un conversation_id pour la conversation en cours
    conversation_id = get_or_create_conversation_id("User123")
    
    # Sauvegarde du message de l'utilisateur avec le même conversation_id
    save_message(user="User123", message=msg, conversation_id=conversation_id, is_bot=False)
    
    response = get_chat_response(msg)
    
    # Sauvegarde de la réponse du bot avec le même conversation_id
    save_message(user="Bot", message=response['response'], conversation_id=conversation_id, is_bot=True)
    
    return jsonify(response)

@app.route("/messages/<conversation_id>", methods=["GET"])
def get_conversation_details(conversation_id):
    """
    Récupère tous les messages d'une conversation spécifique triés par timestamp.
    
    :param conversation_id: Identifiant de la conversation
    :return: Liste des messages de la conversation
    """
    try:
        # Récupérer tous les messages pour une conversation spécifique, triés par timestamp
        messages = list(collection.find({"conversation_id": conversation_id}, {"_id": 0}).sort("timestamp", 1))
        return jsonify(messages)
    except Exception as e:
        print(f"Erreur lors de la récupération des messages: {e}")
        return jsonify({"error": str(e)})

def get_chat_response(text):
    try:
        # Ajoute un prompt "system" pour définir les instructions du chatbot
        messages = [
            {"role": "system", "content": system_prompt},  # Prompt système avec les instructions
            {"role": "user", "content": text}  # Message de l'utilisateur
        ]
        
        response = openai.ChatCompletion.create(
            model="ft:gpt-3.5-turbo-0125:personal:ecocycle-chatbot-2:9bUnv3zy",
            messages=messages,
            temperature=1,
        )
        return {"response": response.choices[0].message["content"].strip()}
    except Exception as e:
        return {"response": "An error occurred: " + str(e)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5003)))


