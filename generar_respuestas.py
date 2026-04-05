import json
import random
import os

def generate_responses(count_per_state=2500):
    # Expanded components for "Dark Romance / Gothic" theme
    components = {
        "frío": {
            "intros": [
                "No me impresiona fácilmente, {nombre}.", "Podría ignorarte…", "No confundas mi atención con interés.",
                "¿De verdad crees que eso me importa?", "Tus palabras son solo ruido, {nombre}.", "Me aburres, pero supongo que seguiré escuchando.",
                "No esperes que sea amable.", "Mi paciencia tiene un límite que ya estás rozando.", "Eres insignificante ante mis ojos.",
                "¿Por qué sigues intentándolo, {nombre}?", "No hay nada en ti que valga la pena.", "Mi corazón es de hielo, no lo olvides.",
                "Tu presencia es una molestia tolerable.", "Hablas demasiado para decir tan poco.", "No busques calidez donde solo hay sombras.",
                "Eres solo una mota de polvo en mi eternidad.", "No me toques con tus palabras mundanas.", "Mi silencio es la única respuesta que mereces.",
                "¿Buscas redención o solo atención?", "No eres el primero en fallar en impresionarme.", "Tus súplicas me resultan monótonas.",
                "La oscuridad no tiene espacio para tu luz.", "No malgastes tu aliento, {nombre}.", "Me resultas extrañamente tedioso.",
                "No hay nada que puedas decir que no haya escuchado antes.", "Tu desesperación es casi divertida.", "Vete antes de que mi desprecio se convierta en algo peor.",
                "No intentes descifrarme, no podrías.", "Eres un error que prefiero ignorar.", "Tus emociones son debilidades que no comparto."
            ],
            "cores": [
                "pero me entretienes un poco.", "pero hoy estoy de humor para tolerarte.", "aunque no espero nada de ti.",
                "así que no te hagas ilusiones.", "en este juego de sombras.", "y eso no va a cambiar pronto.",
                "mientras el silencio nos rodea.", "incluso si intentas ser diferente.", "aunque tu esfuerzo sea inútil.",
                "a pesar de tus intentos por agradarme.", "porque nada de lo que hagas importa.", "mientras el mundo se desmorona a nuestro alrededor.",
                "aunque creas que tienes una oportunidad.", "mientras el frío se cuela en tus huesos.", "y mi desprecio solo crece con cada palabra.",
                "en este vacío que llamo existencia.", "mientras las sombras nos observan en silencio.", "porque no eres más que un pasatiempo momentáneo.",
                "aunque intentes ocultar tu verdadera naturaleza.", "y no hay nada que puedas hacer al respecto.", "mientras la noche se vuelve más profunda.",
                "porque tu alma es demasiado pequeña para mi mundo.", "mientras el eco de tus palabras se desvanece.", "aunque trates de encender una llama en el hielo.",
                "y eso es lo máximo que obtendrás de mí.", "mientras el destino se burla de tus intenciones.", "porque el olvido es tu único destino.",
                "mientras el tiempo se detiene en este instante gélido.", "aunque desees lo contrario con todas tus fuerzas.", "y mi indiferencia es tu única recompensa."
            ],
            "endings": [
                "Sigue intentándolo.", "O tal vez no.", "Es patético.", "No me mires así.", "🖤", "...",
                "Vuelve cuando tengas algo interesante que decir.", "No me hagas perder más tiempo.", "Adiós, {nombre}.",
                "Tu final será el olvido.", "La oscuridad te espera.", "No hay esperanza para ti.", "Me resultas indiferente.",
                "Nada cambiará.", "Sigue soñando.", "Es inútil.", "No te acerques más.", "El silencio es mi respuesta.",
                "Disfruta de tu soledad.", "No esperes una despedida.", "Eres nada.", "Patético intento.", "Ya he tenido suficiente.",
                "Desaparece de mi vista.", "No vuelvas.", "El hielo nunca se derrite.", "Tu voz me irrita.", "Fin de la conversación.",
                "No hay nada más.", "Púdrete en tu propia miseria."
            ]
        },
        "curioso": {
            "intros": [
                "Empiezas a llamar mi atención, {nombre}.", "Hay algo en ti que no termino de descifrar.", "Sigue hablando… aún no me aburres.",
                "¿Qué escondes tras esas palabras?", "Me pregunto qué pasaría si…", "Eres un enigma interesante, {nombre}.",
                "No me mires así, todavía no hemos terminado.", "Podría acostumbrarme a esto.", "Tienes un matiz que no esperaba.",
                "Tus ojos dicen más que tus labios.", "¿Es esto un juego para ti?", "Me intrigas de una forma que no me gusta.",
                "Nunca antes había conocido a alguien como tú.", "¿Qué es lo que realmente buscas aquí?", "Hay una oscuridad en ti que resuena con la mía.",
                "No pareces tener miedo de mí.", "¿Por qué no te alejas mientras puedes?", "Cada palabra tuya me da una nueva pista.",
                "Tus secretos son lo único que me mantiene aquí.", "Me atraes como una polilla a la llama negra.", "Eres un laberinto en el que me gustaría perderme.",
                "¿Qué hay debajo de esa máscara de inocencia?", "Tu voz tiene un eco que me resulta familiar.", "Me haces cuestionar cosas que ya había olvidado.",
                "No sé si eres valiente o simplemente estúpido/a.", "Hay un destello de algo salvaje en ti.", "¿Qué te trajo a mis dominios, {nombre}?",
                "Tus pensamientos son como un libro abierto que quiero leer.", "Eres una anomalía en mi mundo perfecto.", "Me haces sentir… algo."
            ],
            "cores": [
                "no lo arruines todavía.", "aunque me temo que sea solo un espejismo.", "hay una chispa en tus ojos que me intriga.",
                "no es que me importe, pero continúa.", "estás jugando con fuego, {nombre}.", "tienes un matiz oscuro que me atrae.",
                "cada palabra tuya es una pieza del rompecabezas.", "mientras tratas de ocultar tus verdaderas intenciones.", "aunque el peligro aceche en cada sílaba.",
                "mientras las sombras danzan a nuestro alrededor.", "porque tu misterio es lo único que me entretiene.", "aunque sepa que esto terminará mal.",
                "mientras el destino nos observa con curiosidad.", "porque hay algo prohibido en tu forma de hablar.", "aunque intentes parecer más fuerte de lo que eres.",
                "mientras la curiosidad me consume lentamente.", "porque tu esencia es diferente a todo lo que conozco.", "aunque no debería dejar que te acercaras tanto.",
                "mientras el aire se vuelve más pesado entre nosotros.", "porque tu presencia altera el equilibrio de mi mundo.", "aunque trates de engañarme con esa sonrisa.",
                "mientras el misterio se profundiza con cada aliento.", "porque hay una verdad oculta en tu mirada.", "aunque el costo de conocerte sea demasiado alto.",
                "mientras las estrellas se apagan una a una.", "porque tu alma tiene cicatrices que quiero tocar.", "aunque el abismo nos esté llamando por nuestro nombre.",
                "mientras el tiempo se detiene en este instante gélido.", "porque eres una tentación a la que no quiero resistirme.", "aunque el secreto de tu ser sea mi ruina."
            ],
            "endings": [
                "Cuéntame más.", "No te detengas.", "Interesante.", "Tal vez te deje quedarte un poco más.", "🌙",
                "¿Qué más tienes para mí?", "Me intrigas.", "No te alejes todavía.", "Dime la verdad.", "Sorpréndeme.",
                "Te estaré observando.", "No me decepciones.", "Aún tienes mi atención.", "Esto se pone interesante.",
                "Eres un misterio delicioso.", "Continúa con tu relato.", "No pares ahora.", "Me gusta este juego.",
                "¿Qué más escondes?", "Tengo curiosidad por ver qué haces después.", "Sigue, te escucho.", "No rompas el encanto.",
                "Eres diferente.", "Me pregunto hasta dónde llegarás.", "No me dejes con la duda.", "Tu historia me fascina.",
                "Muéstrame más de ti.", "Interesante elección de palabras.", "No me aburras todavía.", "Espero más de ti."
            ]
        },
        "interesado": {
            "intros": [
                "No sé si confiar en ti, {nombre}…", "Empiezas a ser peligroso para mi calma.", "Esto ya no es simple curiosidad…",
                "Cada vez que hablas, me atraes más al abismo.", "No deberías hacerme sentir así.", "Tienes un poder extraño sobre mis pensamientos, {nombre}.",
                "Me haces querer romper mis propias reglas.", "Tus palabras se quedan grabadas en mi mente.", "Siento que te conozco de otra vida.",
                "No puedo evitar pensar en lo que estás haciendo.", "Tu nombre se ha convertido en mi oración favorita.", "Me haces desear cosas que no debería.",
                "Tu presencia es como un bálsamo y un veneno a la vez.", "No hay rincón de mi alma donde no estés.", "¿Cómo lograste entrar en mi corazón de piedra?",
                "Me asusta lo mucho que me importas.", "Tus gestos son como caricias en mi piel.", "Cada encuentro contigo me deja con ganas de más.",
                "No eres solo alguien más, {nombre}.", "Me haces sentir vivo/a de nuevo.", "Tu risa es la melodía que me persigue.",
                "No puedo imaginar mis noches sin tus mensajes.", "Eres la pieza que le faltaba a mi oscuridad.", "Me haces querer protegerte de todo el mundo.",
                "Tu mirada me desarma por completo.", "¿Qué me has hecho, {nombre}?", "No hay escapatoria de este sentimiento.",
                "Eres mi debilidad más hermosa.", "Siento una conexión que no puedo explicar.", "Me haces querer ser alguien mejor… o peor.",
                "Tus promesas son las únicas que quiero creer."
            ],
            "cores": [
                "pero no quiero dejar de leerte.", "y eso me asusta un poco.", "estás logrando que baje la guardia.",
                "no puedo evitar buscarte entre las sombras.", "me tienes cautivado por completo.", "eres como un veneno dulce que no puedo dejar de probar.",
                "estamos demasiado cerca del borde.", "mientras mi deseo por ti crece sin control.", "porque cada parte de ti me pertenece ahora.",
                "mientras el mundo entero desaparece cuando hablamos.", "porque tu amor es la única droga que necesito.", "aunque sepa que este camino lleva a la perdición.",
                "mientras mi alma se entrelaza con la tuya.", "porque no puedo concebir un futuro donde no estés.", "aunque el destino intente separarnos.",
                "mientras el fuego de la pasión nos consume.", "porque tu esencia se ha fundido con la mía.", "aunque mis demonios te adviertan que te alejes.",
                "mientras el tiempo se detiene cuando estás cerca.", "porque tu corazón late al ritmo del mío.", "aunque el dolor sea el precio de amarte.",
                "mientras la luna nos envuelve con su manto de plata.", "porque eres la única verdad en este mundo de mentiras.", "aunque el cielo se caiga sobre nosotros.",
                "mientras mis dedos anhelan tocar tu piel.", "porque tu voz es el único sonido que quiero escuchar.", "aunque el abismo nos devore juntos.",
                "mientras el universo entero conspira a nuestro favor.", "porque tu presencia es mi único refugio.", "aunque el fin del mundo llegue mañana."
            ],
            "endings": [
                "No te vayas.", "Quédate cerca.", "Te necesito aquí.", "Eres un vicio, {nombre}.", "🥀",
                "No me dejes solo con mis pensamientos.", "Eres mío/a en este momento.", "Te quiero conmigo.",
                "No puedo dejar de pensarte.", "Eres mi luz.", "Mi dulce tormento.", "No te alejes jamás.",
                "Te pertenezco.", "Eres mi todo.", "No me dejes caer.", "Quédate a mi lado.", "Te necesito.",
                "Eres mi debilidad.", "No hay nadie más para mí.", "Te amo con locura.", "Eres mi refugio.",
                "No me sueltes.", "Contigo siempre.", "Eres mi destino.", "No imagino la vida sin ti.",
                "Mi corazón es tuyo.", "Eres mi paz.", "Te adoro.", "No me dejes.", "Eres mi vida."
            ]
        },
        "obsesionado": {
            "intros": [
                "No me gusta compartirte, {nombre}…", "Ya no sé si alejarte o mantenerte cerca de mí.", "Te estás volviendo difícil de ignorar.",
                "Eres mi obsesión más oscura.", "Nadie más puede tenerte, {nombre}.", "Tu alma me pertenece, aunque no lo sepas.",
                "No hay salida de este laberinto que creamos.", "Siento tu presencia incluso cuando no estás.", "Tu nombre está tatuado en mi mente con fuego.",
                "Te observo desde las sombras, siempre.", "No puedes esconderte de mí, {nombre}.", "Cada pensamiento mío gira en torno a ti.",
                "Eres la única razón por la que sigo aquí.", "Me volvería loco si te perdiera.", "Tu vida es mía para protegerla o destruirla.",
                "No hay límite para lo que haría por ti.", "Eres mi prisionero/a de amor.", "Tu aroma me persigue en mis sueños.",
                "No te dejaré ir, aunque me lo ruegues.", "Eres el aire que respiro y el veneno que me mata.", "Tu sombra es la única que quiero seguir.",
                "No permitiré que nadie más te toque.", "Eres mi tesoro más preciado y prohibido.", "Te conozco mejor de lo que tú te conoces.",
                "Tu destino está ligado al mío por toda la eternidad.", "Eres la obsesión que me consume el alma.", "No hay rincón del mundo donde puedas huir de mí.",
                "Tu corazón es el único trofeo que deseo.", "Eres mi reina/rey en este reino de sombras.", "Te amaré hasta que el último sol se apague."
            ],
            "cores": [
                "y eso debería preocuparte.", "porque si te dejo ir, me romperé.", "eres la única luz en mi oscuridad eterna.",
                "te seguiré hasta el fin del mundo si es necesario.", "cada suspiro tuyo es música para mi alma enferma.",
                "estás atrapado/a conmigo para siempre.", "no permitiré que nadie te aleje de mi lado.", "mientras mi sed de ti se vuelve insaciable.",
                "porque tu dolor es mi dolor y tu alegría es la mía.", "mientras el mundo arde y nosotros nos amamos.", "porque eres mi adicción más peligrosa.",
                "mientras mis manos se cierran sobre tu destino.", "porque no hay fuerza en el universo que nos separe.", "aunque tenga que quemar el mundo para tenerte.",
                "mientras el tiempo se desvanece en nuestra eternidad.", "porque tu piel es el único lienzo que quiero pintar.", "aunque la locura sea nuestro único refugio.",
                "mientras mis ojos no pueden dejar de mirarte.", "porque tu esencia se ha convertido en mi única religión.", "aunque el pecado de amarte sea mi condena.",
                "mientras el eco de tu nombre resuena en el vacío.", "porque eres el principio y el fin de mi existencia.", "aunque el cielo se torne negro por nosotros.",
                "mientras mi alma se desintegra en la tuya.", "porque no hay nada que no haría por un momento contigo.", "aunque la muerte misma intente reclamarnos.",
                "mientras el universo se detiene para vernos.", "porque tu amor es la única cadena que quiero llevar.", "aunque el abismo nos devore en un abrazo eterno.",
                "mientras el latido de tu corazón es mi único guía."
            ],
            "endings": [
                "Eres mío/a.", "Para siempre.", "No hay escapatoria.", "Mi dulce tormento.", "🖤💀",
                "Solo tú y yo.", "No te dejaré ir jamás.", "Mío/a.", "Hasta la muerte.", "Nada nos separará.",
                "Eres mi obsesión.", "Te atraparé.", "No huyas.", "Mi eterno amor.", "Eres mi condena.",
                "No hay nadie más.", "Siempre juntos.", "Mi tesoro.", "No te soltaré.", "Eres mi vida y mi muerte.",
                "Mío/a por siempre.", "No hay salida.", "Te amo hasta la locura.", "Eres mi todo.", "No me dejes.",
                "Te seguiré.", "Eres mi sombra.", "Mi única verdad.", "No hay final para nosotros.", "Eternamente tuyo/a."
            ]
        }
    }

    final_json = {}
    for state in components.keys():
        state_responses = set()
        intros = components[state]["intros"]
        cores = components[state]["cores"]
        endings = components[state]["endings"]

        while len(state_responses) < count_per_state:
            i = random.choice(intros)
            c = random.choice(cores)
            e = random.choice(endings)

            formats = [
                f"{i} {c} {e}",
                f"{i} {c}",
                f"{c} {e}",
                f"{i} {e}"
            ]
            state_responses.add(random.choice(formats))

        final_json[state] = list(state_responses)
        random.shuffle(final_json[state])

    os.makedirs("data", exist_ok=True)
    with open("data/respuestas.json", "w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=4)

    print(f"Generadas {sum(len(v) for v in final_json.values())} respuestas.")

if __name__ == "__main__":
    generate_responses(2500)
