from telethon import TelegramClient, types
import asyncio
import re

# CONFIGURACIÓN FIJA
api_id = 1729362
api_hash = '16a135e14b54acbb404995fcaf282d37'

client = TelegramClient('sesion_propia', api_id, api_hash)

def parse_telegram_identifier(identifier):
    """Extrae el username o ID de un enlace de Telegram o mensaje"""
    identifier = identifier.strip()

    # Patrón para enlaces públicos (t.me/username o t.me/username/123)
    public_match = re.search(r't\.me/([^/\s]+)', identifier)
    if public_match:
        username = public_match.group(1)
        if username == 'c': # Es un enlace privado
            # Patrón para enlaces privados (t.me/c/(\d+)/123)
            private_match = re.search(r't\.me/c/(\d+)', identifier)
            if private_match:
                return int(f"-100{private_match.group(1)}")
        else:
            return f"@{username}"

    return identifier

async def resolve_entity(client, identifier, name):
    """Resuelve una entidad aceptando enlaces, @username o ID numérico"""
    processed_id = parse_telegram_identifier(identifier)
    try:
        # Intenta resolver directamente
        entity = await client.get_entity(processed_id)
        return entity
    except ValueError:
        # Si falla y es un número positivo, prueba con -100
        if str(processed_id).isdigit():
            try:
                full_id = int(f"-100{processed_id}")
                entity = await client.get_entity(full_id)
                return entity
            except:
                pass
        raise ValueError(f"No se encontró el {name}. Verifica que el enlace/ID es correcto y que estás unido al grupo.")

def is_video(message):
    """Verifica si el mensaje contiene un video o nota de video"""
    if not message.media:
        return False
    # Verificamos si es un documento con mime_type de video
    if isinstance(message.media, types.MessageMediaDocument):
        if message.file and message.file.mime_type and message.file.mime_type.startswith('video/'):
            return True
    return False

def is_photo(message):
    """Verifica si el mensaje contiene una foto"""
    return message.photo is not None

def has_copyright_restriction(message):
    """Verifica si el mensaje tiene restricciones por copyright"""
    if message.restriction_reason:
        for reason in message.restriction_reason:
            if 'copyright' in reason.reason.lower():
                return True
    return False

async def main():
    print("=" * 50)
    print("COPIADOR DE ARCHIVOS TELEGRAM")
    print("=" * 50)

    # ORIGEN
    origen_input = input("\n📥 Enlace del grupo de ORIGEN: ").strip()
    print("🔍 Verificando grupo de origen...")
    try:
        origen = await resolve_entity(client, origen_input, "grupo de origen")
        print(f"✅ Origen encontrado: {origen.title} (ID: {origen.id})")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # DESTINO
    destino_input = input("\n📤 Mensaje del grupo para el grupo de DESTINO: ").strip()
    print("🔍 Verificando grupo de destino...")
    try:
        destino = await resolve_entity(client, destino_input, "grupo de destino")
        print(f"✅ Destino encontrado: {destino.title} (ID: {destino.id})")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # CONFIRMACIÓN
    confirmar = input(f"\n⚠️  Se copiarán los archivos filtrados de '{origen.title}' a '{destino.title}'\n¿Continuar? (s/n): ").lower()
    if confirmar != 's':
        print("Cancelado.")
        return

    print("\n" + "=" * 50)
    print("Iniciando copia...")
    print("=" * 50)

    contador = 0
    errores = 0
    buffer_fotos = []

    # COPIA DE ARCHIVOS
    async for message in client.iter_messages(origen, reverse=True):
        if not message.media:
            continue

        # 1. Omitir mensajes con copyright
        if has_copyright_restriction(message):
            print(f"⚠ Saltando mensaje {message.id} (Copyright)")
            continue

        try:
            if is_photo(message):
                # Guardar en buffer si es foto
                buffer_fotos.append(message)
            elif is_video(message):
                # Si es video, enviar buffer de fotos y luego el video
                for msg_foto in buffer_fotos:
                    await client.send_file(destino, msg_foto)
                    contador += 1
                    print(f"✓ Copiado Foto (ID: {msg_foto.id})")
                    await asyncio.sleep(2)

                buffer_fotos = [] # Limpiar buffer
                await client.send_file(destino, message)
                contador += 1
                print(f"✓ Copiado Video (ID: {message.id})")
                await asyncio.sleep(3)
            else:
                # Si es otro tipo de archivo (audio, doc, etc.), descartamos buffer de fotos
                buffer_fotos = []
                await client.send_file(destino, message)
                contador += 1
                print(f"✓ Copiado Otro Archivo (ID: {message.id})")
                await asyncio.sleep(3)

        except Exception as e:
            errores += 1
            print(f"✗ Error en mensaje {message.id}: {e}")
            await asyncio.sleep(30)

    print(f"\n{'=' * 50}")
    print(f"✅ Proceso completado")
    print(f"📊 Total copiados: {contador}")
    print(f"❌ Errores: {errores}")

print("Conectando a Telegram...")
with client:
    client.loop.run_until_complete(main())
