document.addEventListener('DOMContentLoaded', () => {
    // Referencias a los elementos del DOM
    const backgroundImage = document.getElementById('background-image');
    const backgroundMusic = document.getElementById('background-music');
    const characterNameElement = document.getElementById('character-name');
    const dialogueTextElement = document.getElementById('dialogue-text');
    const optionsContainer = document.getElementById('options-container');

    // Estado del juego
    let gameState = {
        playerName: '',
        inventory: [],
        characterAffinities: {}
    };

    // Base de datos del juego cargada desde JSON
    let db = {
        characters: [],
        scenarios: [],
        dialogues: []
    };

    // --- Gestor de Estado (LocalStats) ---

    function saveGameState() {
        localStorage.setItem('darkRomanceGameState', JSON.stringify(gameState));
    }

    function loadGameState() {
        const savedState = localStorage.getItem('darkRomanceGameState');
        if (savedState) {
            gameState = JSON.parse(savedState);
        } else {
            // Inicializa las afinidades si no hay estado guardado
            db.characters.forEach(char => {
                gameState.characterAffinities[char.id] = {
                    affection: 0,
                    obsession: 0
                };
            });
        }
    }

    // --- Motor de Datos y Escenarios ---

    async function loadGameData() {
        try {
            const [charactersRes, scenariosRes, dialoguesRes] = await Promise.all([
                fetch('data/characters.json'),
                fetch('data/scenarios.json'),
                fetch('data/dialogues.json')
            ]);

            db.characters = await charactersRes.json();
            db.scenarios = await scenariosRes.json();
            db.dialogues = await dialoguesRes.json();

        } catch (error) {
            console.error("Error al cargar los datos del juego:", error);
            dialogueTextElement.textContent = "Error: No se pudieron cargar los archivos del juego. Revisa la consola para más detalles.";
        }
    }

    function showDialogue(dialogueId) {
        const dialogue = db.dialogues.find(d => d.id === dialogueId);
        if (!dialogue) {
            console.error(`No se encontró el diálogo con ID: ${dialogueId}`);
            return;
        }

        const character = db.characters.find(c => c.id === dialogue.character_id);
        const scenario = db.scenarios.find(s => s.id === dialogue.scenario_id);

        // Actualizar escenario
        if (scenario) {
            backgroundImage.src = scenario.background_image;
            // Para evitar errores si los assets no existen aún, lo dejamos comentado
            // backgroundMusic.src = scenario.background_music;
            // backgroundMusic.play().catch(e => console.log("La interacción del usuario es necesaria para reproducir audio."));
        }

        // Actualizar caja de diálogo
        characterNameElement.textContent = character ? character.name : '';
        dialogueTextElement.textContent = dialogue.text;

        // Limpiar opciones anteriores
        optionsContainer.innerHTML = '';

        // Mostrar nuevas opciones
        dialogue.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option.text;
            button.addEventListener('click', () => {
                // Aquí se manejaría la lógica de afinidad y consecuencias
                if (option.next_dialogue_id) {
                    showDialogue(option.next_dialogue_id);
                } else {
                    // Fin de la rama de diálogo
                    dialogueTextElement.textContent = "Continuará...";
                    optionsContainer.innerHTML = '';
                }
                saveGameState(); // Guardar el progreso después de cada decisión
            });
            optionsContainer.appendChild(button);
        });
    }

    // --- Inicialización del Juego ---

    async function init() {
        await loadGameData();
        loadGameState();

        // Pedir nombre del jugador si no existe
        if (!gameState.playerName) {
            gameState.playerName = prompt("Por favor, introduce tu nombre:") || "Viajera";
            saveGameState();
        }

        // Iniciar el juego
        showDialogue(1);
    }


    init();
});
