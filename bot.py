from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import random
import json
import os

ARCHIVO_MEMORIA = "memoria.json"
ARCHIVO_RESPUESTAS = "data/respuestas.json"

# Para mayor seguridad, el TOKEN debe ser una variable de entorno.
# Si no está definida, se usa el token predeterminado (el proporcionado por el usuario).
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8637854212:AAFVc9Kyf4gAY4uniikjBJT5JyX-ZRYUkzA")

# Cargar memoria de usuarios
if os.path.exists(ARCHIVO_MEMORIA):
    with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
        usuarios = json.load(f)
else:
    usuarios = {}

# Cargar 10,000 respuestas temáticas
if os.path.exists(ARCHIVO_RESPUESTAS):
    with open(ARCHIVO_RESPUESTAS, "r", encoding="utf-8") as f:
        respuestas_db = json.load(f)
else:
    # Fallback en caso de que no exista el archivo
    respuestas_db = {
        "frío": ["No me interesa."],
        "curioso": ["Dime más."],
        "interesado": ["Me gustas."],
        "obsesionado": ["Eres mío/a."]
    }

def guardar():
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, ensure_ascii=False, indent=4)

def obtener_usuario(user):
    user_id = str(user.id)
    if user_id not in usuarios:
        usuarios[user_id] = {
            "nombre": user.first_name,
            "nivel": 0,
            "estado": "frío",
            "recuerdos": []
        }
    return usuarios[user_id]

# COMANDOS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    usuario = obtener_usuario(user)
    await update.message.reply_text(f"Así que eres {usuario['nombre']}… veamos cuánto duras aquí 🖤")

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    usuario = obtener_usuario(user)
    await update.message.reply_text(f"Estoy {usuario['estado']} contigo… por ahora.")

async def recordar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    usuario = obtener_usuario(user)

    if usuario["recuerdos"]:
        recuerdo = random.choice(usuario["recuerdos"])
        await update.message.reply_text(f"No olvido lo que dices… {recuerdo}")
    else:
        await update.message.reply_text("Aún no me has dicho nada que valga la pena recordar.")

# RESPUESTA INTELIGENTE

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    texto = update.message.text.lower()
    usuario = obtener_usuario(user)
    nombre = usuario["nombre"]

    # Guardar recuerdos
    if len(texto) > 5:
        usuario["recuerdos"].append(texto)
        if len(usuario["recuerdos"]) > 20:
            usuario["recuerdos"].pop(0)

    # Cambiar nivel emocional
    if "te quiero" in texto or "te extraño" in texto:
        usuario["nivel"] += 1
    elif "adiós" in texto:
        usuario["nivel"] -= 1

    # Estados
    if usuario["nivel"] <= 0:
        usuario["estado"] = "frío"
    elif usuario["nivel"] == 1:
        usuario["estado"] = "curioso"
    elif usuario["nivel"] == 2:
        usuario["estado"] = "interesado"
    else:
        usuario["estado"] = "obsesionado"

    estado = usuario["estado"]

    # Lógica de respuesta
    if "otro" in texto or "alguien más" in texto:
        respuesta = f"¿Otro?… qué decepción, {nombre}. Pensé que tenías mejor gusto."
    elif random.random() < 0.2: # Restaurado a 20% como en el código original
        respuesta = f"No te acostumbres a mí, {nombre}… no siempre estoy aquí 💋"
    else:
        # Seleccionar de las 10,000 respuestas cargadas
        opciones = respuestas_db.get(estado, ["..."])
        respuesta_base = random.choice(opciones)
        respuesta = respuesta_base.format(nombre=nombre)

    guardar()
    await update.message.reply_text(respuesta)

if __name__ == "__main__":
    # BOT
    if not TOKEN:
        print("Error: No se ha configurado el TOKEN del bot.")
    else:
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("estado", estado))
        app.add_handler(CommandHandler("recordar", recordar))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

        print("Bot iniciado...")
        app.run_polling()
