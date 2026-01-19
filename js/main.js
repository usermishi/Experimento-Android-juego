document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENTOS DEL DOM ---
    const scenarioBackground = document.getElementById('scenario-background');
    const characterContainer = document.getElementById('character-container');
    const speakerName = document.getElementById('speaker-name');
    const dialogueText = document.getElementById('dialogue-text');
    const choicesContainer = document.getElementById('choices-container');
    const backgroundMusic = document.getElementById('background-music');

    // --- MÚSICA ---
    let isMusicStarted = false;

    // --- GESTOR DE ESTADOS ---
    let gameState = {
        playerName: '',
        inventory: [],
        affinity: {},
        currentScene: 'scene1',
    };

    function saveState() {
        localStorage.setItem('darkRomanceGameState', JSON.stringify(gameState));
    }

    function loadState() {
        const savedState = localStorage.getItem('darkRomanceGameState');
        if (savedState) {
            gameState = JSON.parse(savedState);
        } else {
            gameState.playerName = prompt("Por favor, introduce tu nombre:") || "MC";
            saveState();
        }
    }

    // --- MOTOR DE DATOS ---
    let gameData = {
        characters: [],
        scenarios: [],
        dialogues: {}
    };

    async function loadGameData() {
        try {
            const [charResponse, scenResponse, dialogResponse] = await Promise.all([
                fetch('data/characters.json'),
                fetch('data/scenarios.json'),
                fetch('data/dialogues.json')
            ]);

            gameData.characters = await charResponse.json();
            gameData.scenarios = await scenResponse.json();
            gameData.dialogues = await dialogResponse.json();
        } catch (error) {
            console.error('Error al cargar los datos del juego:', error);
        }
    }

    // --- SISTEMA DE ESCENARIOS Y DIÁLOGOS ---
    function renderScene(sceneId) {
        const sceneDialogues = gameData.dialogues[sceneId];
        if (!sceneDialogues || sceneDialogues.length === 0) {
            console.error(`Escena no encontrada o vacía: ${sceneId}`);
            return;
        }

        const currentDialogue = sceneDialogues[0];
        const character = gameData.characters.find(c => c.id === currentDialogue.characterId);
        const scenario = gameData.scenarios.find(s => s.id === currentDialogue.scenarioId);

        // Renderizar Escenario y Música
        if (scenario) {
            scenarioBackground.src = scenario.background;
            scenarioBackground.alt = scenario.name;

            // Cambiar música si es diferente
            if (backgroundMusic.src !== scenario.music) {
                backgroundMusic.src = scenario.music;
                if (isMusicStarted) {
                    backgroundMusic.play();
                }
            }
        } else {
            console.error(`Escenario no encontrado: ${currentDialogue.scenarioId}`);
            scenarioBackground.src = '';
            backgroundMusic.pause();
        }

        // Renderizar Personaje
        characterContainer.innerHTML = ''; // Limpiar personajes anteriores
        if (character) {
            speakerName.textContent = character.name;
            const characterImg = document.createElement('img');
            characterImg.src = character.image;
            characterImg.alt = character.name;
            characterContainer.appendChild(characterImg);
        } else {
            speakerName.textContent = '';
        }

        dialogueText.textContent = currentDialogue.text.replace('{playerName}', gameState.playerName);

        choicesContainer.innerHTML = '';
        currentDialogue.choices.forEach(choice => {
            const button = document.createElement('button');
            button.textContent = choice.text;
            button.addEventListener('click', () => {
                if (!isMusicStarted) {
                    backgroundMusic.play();
                    isMusicStarted = true;
                }
                gameState.currentScene = choice.nextScene;
                saveState();
                renderScene(choice.nextScene);
            });
            choicesContainer.appendChild(button);
        });
    }

    // --- INICIALIZACIÓN DEL JUEGO ---
    async function initGame() {
        loadState();
        await loadGameData();
        renderScene(gameState.currentScene);
    }

    initGame();
});
