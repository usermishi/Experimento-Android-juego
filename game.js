// --- Game Logic & Systems ---

// State Management
const initialState = {
    day: 1,
    stats: { str: 10, cha: 10, wis: 10 },
    affinity: { kael: 0, rylan: 0, rival: 0, zarek: 0 },
    flags: {}, // For story tracking
    currentSceneId: 'intro_0',
    inventory: [],
    player: {
        name: "Anya",
        class: "noble",
        appearance: {
            hair: "bg-slate-800",
            clothing: "bg-slate-300"
        }
    }
};

let state = JSON.parse(localStorage.getItem('paladin_otome_save')) || JSON.parse(JSON.stringify(initialState));

// Constants
const LOCATIONS = ['training_grounds', 'grand_library', 'royal_gardens', 'dungeon_entrance'];
const ENEMIES = ['Slime Elegante', 'Goblin Romántico', 'Armadura Celosa', 'Príncipe Bandido'];

// Character Visual Data
const CHARACTERS = {
    narrator: { name: "", color: "text-gray-400" },
    protagonist: {
        name: "Anya",
        color: "text-pink-300",
        css: { body: "bg-slate-300", hair: "bg-slate-800", head: "bg-[#ffdbac]", aura: "bg-pink-500/10" }
    },
    kael: {
        name: "Sir Kael",
        color: "text-blue-400",
        css: { body: "bg-slate-300", hair: "bg-slate-800", head: "bg-[#ffdbac]", aura: "bg-blue-500/20" }
    },
    rylan: {
        name: "Mago Rylan",
        color: "text-purple-400",
        css: { body: "bg-indigo-900", hair: "bg-white", head: "bg-[#ffdbac]", aura: "bg-purple-500/20" }
    },
    rival: {
        name: "Lady Vex",
        color: "text-red-400",
        css: { body: "bg-red-900", hair: "bg-red-600", head: "bg-[#ffe0d0]", aura: "bg-red-500/20" }
    },
    zarek: {
        name: "Zarek",
        color: "text-gray-300",
        css: { body: "bg-gray-800", hair: "bg-black", head: "bg-[#e0e0e0]", aura: "bg-gray-500/20" }
    },
    enemy: {
        name: "Enemigo",
        color: "text-green-400",
        css: { body: "bg-green-800", hair: "bg-green-900", head: "bg-green-600", aura: "bg-green-500/20" }
    }
};

// DOM Elements
const el = {
    // Screens
    startMenu: document.getElementById('start-menu'),
    characterCreationScreen: document.getElementById('character-creation-screen'),
    gameWrapper: document.getElementById('game-wrapper'),
    // Start Menu
    playerNameInput: document.getElementById('player-name'),
    startGameBtn: document.getElementById('start-game-btn'),
    // Character Creation
    classSelect: document.getElementById('class-select'),
    hairColorSelect: document.getElementById('hair-color-select'),
    clothingColorSelect: document.getElementById('clothing-color-select'),
    confirmCharacterBtn: document.getElementById('confirm-character-btn'),
    // Game UI
    bg: document.getElementById('background'),
    goldCounter: document.getElementById('gold-counter'),
    speaker: document.getElementById('speaker-name'),
    text: document.getElementById('dialogue-text'),
    choices: document.getElementById('choices-container'),
    charSprite: document.getElementById('character-sprite'),
    charBody: document.getElementById('char-body'),
    charHairBack: document.getElementById('char-hair-back'),
    charHairFront: document.getElementById('char-hair-front'),
    charHead: document.getElementById('char-head'),
    charAura: document.getElementById('char-aura'),
    charEmotion: document.getElementById('char-emotion'),
    charBlush: document.getElementById('char-blush'),
    continueBtn: document.getElementById('continue-btn'),
    stats: {
        str: document.getElementById('stat-str'),
        cha: document.getElementById('stat-cha'),
        wis: document.getElementById('stat-wis'),
        valStr: document.getElementById('val-str'),
        valCha: document.getElementById('val-cha'),
        valWis: document.getElementById('val-wis')
    },
    hearts: {
        kael: document.getElementById('heart-kael'),
        rylan: document.getElementById('heart-rylan'),
        rival: document.getElementById('heart-rival'),
        zarek: document.getElementById('heart-zarek')
    },
    overlay: document.getElementById('full-overlay'),
    overlayTitle: document.getElementById('overlay-title'),
    overlayDesc: document.getElementById('overlay-desc'),
    fx: document.getElementById('fx-overlay')
};

// --- System Functions ---

function showScreen(screen) {
    el.startMenu.classList.add('hidden');
    el.characterCreationScreen.classList.add('hidden');
    el.gameWrapper.classList.add('hidden');
    if (screen === 'start') {
        el.startMenu.classList.remove('hidden');
    } else if (screen === 'creation') {
        el.characterCreationScreen.classList.remove('hidden');
        el.characterCreationScreen.classList.add('flex'); // Make it flex
    } else if (screen === 'game') {
        el.gameWrapper.classList.remove('hidden');
    }
}

function updateUI() {
    // Stats
    el.stats.str.style.width = `${Math.min(state.stats.str, 100)}%`;
    el.stats.valStr.innerText = state.stats.str;
    el.stats.cha.style.width = `${Math.min(state.stats.cha, 100)}%`;
    el.stats.valCha.innerText = state.stats.cha;
    el.stats.wis.style.width = `${Math.min(state.stats.wis, 100)}%`;
    el.stats.valWis.innerText = state.stats.wis;

    // Gold Counter for Merchant
    if (state.player.class === 'merchant') {
        const gold = state.inventory.find(i => i.item === 'gold')?.quantity || 0;
        el.goldCounter.classList.remove('hidden');
        el.goldCounter.querySelector('span').innerText = gold;
    } else {
        el.goldCounter.classList.add('hidden');
    }

    document.getElementById('day-counter').innerText = state.day;

    // Hearts
    el.hearts.kael.style.opacity = state.affinity.kael >= 5 ? '1' : '0.3';
    el.hearts.kael.style.transform = `scale(${1 + (state.affinity.kael/50)})`;
    el.hearts.rylan.style.opacity = state.affinity.rylan >= 5 ? '1' : '0.3';
    el.hearts.rylan.style.transform = `scale(${1 + (state.affinity.rylan/50)})`;
    el.hearts.rival.style.opacity = state.affinity.rival >= 5 ? '1' : '0.3';
    el.hearts.zarek.style.opacity = state.affinity.zarek >= 5 ? '1' : '0.3';
    el.hearts.zarek.style.transform = `scale(${1 + (state.affinity.zarek/50)})`;
}

function createSparkles(x, y) {
    for(let i=0; i<5; i++) {
        const s = document.createElement('div');
        s.className = 'sparkle-effect';
        s.style.left = (x + (Math.random()*60 - 30)) + 'px';
        s.style.top = (y + (Math.random()*60 - 30)) + 'px';
        el.fx.appendChild(s);
        setTimeout(() => s.remove(), 800);
    }
}

function shakeScreen() {
    document.body.classList.add('animate-shake');
    setTimeout(() => document.body.classList.remove('animate-shake'), 500);
}

function setCharacter(key, emotion = '') {
    if (!key || !CHARACTERS[key]?.css) {
        el.charSprite.classList.add('hidden');
        return;
    }

    let css = { ...CHARACTERS[key].css }; // Create a copy to modify
    el.charSprite.classList.remove('hidden');

    // If it's the protagonist, apply customization
    if (key === 'protagonist') {
        css.hair = state.player.appearance.hair;
        css.body = state.player.appearance.clothing;
    }

    el.charBody.className = `absolute bottom-0 left-1/2 -translate-x-1/2 w-40 h-56 rounded-t-[3rem] shadow-inner transition-colors duration-500 ${css.body}`;
    el.charHairBack.className = `absolute bottom-44 left-1/2 -translate-x-1/2 w-48 h-48 rounded-full -z-10 transition-colors duration-500 ${css.hair}`;
    el.charHairFront.className = `absolute bottom-64 left-1/2 -translate-x-1/2 w-36 h-20 rounded-t-full z-30 transition-colors duration-500 ${css.hair}`;
    el.charHead.className = `absolute bottom-48 left-1/2 -translate-x-1/2 w-32 h-36 rounded-2xl shadow-lg z-20 ${css.head}`;
    el.charAura.className = `absolute inset-0 rounded-full blur-xl transition-all duration-700 ${css.aura}`;

    el.charEmotion.innerText = emotion;

    // Blush Logic
    if(emotion.includes('😳') || emotion.includes('❤️') || emotion.includes('🥰')) {
        el.charBlush.style.opacity = 1;
        el.charSprite.classList.add('animate-heartbeat');
    } else {
        el.charBlush.style.opacity = 0;
        el.charSprite.classList.remove('animate-heartbeat');
    }
}

function typeWriter(text, callback) {
    el.text.innerHTML = "";
    let i = 0;
    const speed = 20;

    function step() {
        if (i < text.length) {
            el.text.innerHTML += text.charAt(i);
            i++;
            setTimeout(step, speed);
        } else {
            if (callback) callback();
        }
    }
    step();
}

// --- Story Engine ---

function renderScene(sceneData) {
    // Background
    if (sceneData.bg) {
        el.bg.className = `absolute inset-0 bg-cover bg-center transition-all duration-1000 z-0 ${sceneData.bg}`;
    }

    // Character
    // If the speaker is the narrator and no specific character is set, show the protagonist.
    if (sceneData.speaker === 'narrator' && !sceneData.char) {
        setCharacter('protagonist', sceneData.emotion);
    } else {
        setCharacter(sceneData.char, sceneData.emotion);
    }

    // Speaker
    const speaker = CHARACTERS[sceneData.speaker] || CHARACTERS.narrator;
    el.speaker.innerText = speaker.name || '...';
    el.speaker.className = `font-bold text-lg title-font tracking-wide ${speaker.color}`;
    el.speaker.parentElement.style.opacity = speaker.name ? 1 : 0;

    // Reset UI
    el.continueBtn.classList.add('hidden');
    el.choices.style.transform = 'translateY(100%)';

    // Text
    typeWriter(sceneData.text, () => {
        if (sceneData.choices) {
            showChoices(sceneData.choices);
        } else if (sceneData.next) {
            el.continueBtn.classList.remove('hidden');
            const handler = () => {
                el.continueBtn.removeEventListener('click', handler);
                if (typeof sceneData.next === 'function') {
                    sceneData.next();
                } else {
                    loadScene(sceneData.next);
                }
            };
            el.continueBtn.addEventListener('click', handler);
        }
    });
}

function showChoices(choices) {
    el.choices.innerHTML = "";
    choices.forEach(c => {
        const btn = document.createElement('button');
        // Style based on type
        let baseClass = "w-full p-4 rounded-xl font-bold text-left transition-all active:scale-95 shadow-lg flex justify-between items-center group ";
        if(c.type === 'combat') baseClass += "combat-btn text-red-100 border border-red-400/50";
        else if(c.type === 'romance') baseClass += "romance-btn text-pink-100 border border-pink-400/50";
        else baseClass += "bg-slate-800 text-gray-200 border border-slate-600 hover:bg-slate-700";

        btn.className = baseClass;
        btn.innerHTML = `<span>${c.text}</span> <span class="text-xs opacity-50 group-hover:opacity-100">${c.hint || ''}</span>`;

        btn.onclick = () => {
            createSparkles(window.innerWidth/2, window.innerHeight - 100);
            handleChoice(c);
        };
        el.choices.appendChild(btn);
    });
    el.choices.style.transform = 'translateY(0)';
}

function handleChoice(c) {
    el.choices.style.transform = 'translateY(100%)';

    // Effects
    if(c.effect) {
        if(c.effect.str) state.stats.str += c.effect.str;
        if(c.effect.cha) state.stats.cha += c.effect.cha;
        if(c.effect.wis) state.stats.wis += c.effect.wis;
        if(c.effect.kael) state.affinity.kael += c.effect.kael;
        if(c.effect.rylan) state.affinity.rylan += c.effect.rylan;
        if(c.effect.rival) state.affinity.rival += c.effect.rival;
        if(c.effect.zarek) state.affinity.zarek += c.effect.zarek;
        updateUI();
        saveGame();
    }

    if(c.next) {
        if (typeof c.next === 'function') c.next();
        else loadScene(c.next);
    }
}

function loadScene(sceneId) {
    state.currentSceneId = sceneId;
    saveGame();

    if (SCENES[sceneId]) {
        renderScene(SCENES[sceneId]);
    } else if (sceneId === 'daily_loop') {
        startDailyLoop();
    } else {
        console.error("Unknown scene:", sceneId);
    }
}

// --- Random Event Generator ---

function startDailyLoop() {
    // Determine Phase
    const choices = [
        { text: "Campo de Entrenamiento", hint: "+Fuerza", next: () => runEvent('training') },
        { text: "Gran Biblioteca", hint: "+Sabiduría", next: () => runEvent('library') },
        { text: "Jardines Reales", hint: "+Carisma", next: () => runEvent('garden') },
        { text: "Callejón Sombrío", hint: "???", next: () => runEvent('alley') }
    ];

    if (state.player.class === 'merchant') {
        choices.push({ text: "Ir al Mercado", hint: "+Oro", next: () => runEvent('market') });
    }

    renderScene({
        bg: "bg-gradient-to-b from-sky-900 to-slate-900",
        speaker: "narrator",
        text: `Día ${state.day}. El sol brilla. ¿Dónde pasarás la mañana?`,
        choices: choices
    });
}

function runEvent(location) {
    const roll = Math.random();
    let scene = {};

    // Update Background based on location
    let bg = "";
    if(location === 'training') bg = "bg-gradient-to-b from-red-900 to-stone-900";
    if(location === 'library') bg = "bg-gradient-to-b from-indigo-950 to-slate-900";
    if(location === 'garden') bg = "bg-gradient-to-b from-emerald-900 to-teal-950";
            if(location === 'alley') bg = "bg-gradient-to-b from-gray-900 to-black";
            if(location === 'market') bg = "bg-gradient-to-b from-yellow-800 to-stone-900";

            // Merchant event
            if (location === 'market') {
                state.inventory.find(i => i.item === 'gold').quantity += 10;
                scene = { bg: bg, speaker: "narrator", text: "Pasas la mañana comerciando. ¡Ganas 10 de oro!", next: endDay };
                renderScene(scene);
                return;
            }

            // 80% chance to meet Zarek in the alley
            if (location === 'alley' && roll < 0.8) {
                scene = generateCharacterEvent('alley', bg);
            } // 30% Chance of Main Character Encounter, 30% Combat, 40% Generic Stat
            else if (roll < 0.3) {
        scene = generateCharacterEvent(location, bg);
    } else if (roll < 0.6) {
        scene = generateCombatEvent(location, bg);
    } else {
        scene = generateTrainingEvent(location, bg);
    }

    renderScene(scene);
}

function generateCharacterEvent(loc, bg) {
    // Pick char based on location preference
    let charKey = 'kael';
    if (loc === 'library') charKey = 'rylan';
    if (loc === 'garden') charKey = Math.random() > 0.5 ? 'rival' : 'kael';
            if (loc === 'alley') charKey = 'zarek';

            let interactions = [];
            if (charKey === 'zarek') {
                interactions = [
                    { t: "No deberías estar aquí. Es peligroso.", e: "😒", r: "dark" },
                    { t: "Vete. No me interesan los héroes.", e: "😠", r: "dark" },
                    { t: "Te estoy vigilando. No me decepciones.", e: "😏", r: "dark" }
                ];
            } else {
                 interactions = [
                    { t: "¡Ah, te encuentro aquí! ¿Me ayudas con esto?", e: "🙂", r: "romance" },
                    { t: "Estaba pensando en ti... digo, en la estrategia.", e: "😳", r: "romance" },
                    { t: "Oye, tienes algo en la cara. Déjame... quitarlo.", e: "✨", r: "romance" }
                ];
            }

    const i = interactions[Math.floor(Math.random() * interactions.length)];

            if (charKey === 'zarek') {
                 return {
                    bg: bg,
                    char: charKey,
                    speaker: charKey,
                    emotion: i.e,
                    text: i.t,
                    choices: [
                        {
                            text: "No te tengo miedo",
                            type: "romance",
                            hint: "Fuerza Check",
                            effect: { [charKey]: 3, str: 2 },
                            next: () => resultScene(bg, charKey, "😏", "Una sonrisa se dibuja en su rostro. Interesante.", true)
                        },
                        {
                            text: "Quizás tengas razón...",
                            hint: "Seguro",
                            effect: { [charKey]: 1, wis: 2 },
                            next: () => resultScene(bg, charKey, "😒", "Te mira con desdén mientras te vas.", true)
                        }
                    ]
                };
            }

    return {
        bg: bg,
        char: charKey,
        speaker: charKey,
        emotion: i.e,
        text: i.t,
        choices: [
            {
                text: "Flirtear descaradamente",
                type: "romance",
                hint: "Carisma Check",
                effect: { [charKey]: 3, cha: 2 },
                next: () => resultScene(bg, charKey, "🥰", "¡Wow! Se ha puesto rojo como un tomate. Le gustas.", true)
            },
            {
                text: "Actuar profesional",
                hint: "Seguro",
                effect: { [charKey]: 1, wis: 2 },
                next: () => resultScene(bg, charKey, "🙂", "Asiente con respeto. Buena interacción.", true)
            }
        ]
    };
}

function generateCombatEvent(loc, bg) {
    const enemies = ['Slime Pegajoso', 'Duende Burlón', 'Armadura Vieja'];
    const enemy = enemies[Math.floor(Math.random() * enemies.length)];

    return {
        bg: bg,
        char: 'enemy',
        speaker: 'narrator',
        text: `¡Un ${enemy} salvaje bloquea tu camino! Parece hostil... y un poco lindo.`,
        emotion: '👿',
        choices: [
            {
                text: "¡Atacar!",
                type: "combat",
                hint: `Fuerza ${state.stats.str}/100`,
                next: () => resolveCombat('str', 20, bg)
            },
            {
                text: "¡Seducir!",
                type: "romance",
                hint: `Carisma ${state.stats.cha}/100`,
                next: () => resolveCombat('cha', 20, bg)
            }
        ]
    };
}

function resolveCombat(statType, threshold, bg) {
    const val = state.stats[statType];
    const win = val + (Math.random() * 20) > threshold;

    if (win) {
        shakeScreen();
        return {
            bg: bg,
            speaker: "narrator",
            text: statType === 'str' ? "¡BAM! Le diste una paliza. Ganaste experiencia." : "¡Le guiñaste el ojo y se desmayó de amor! Ganaste experiencia.",
            choices: [{ text: "Victoria", effect: { [statType]: 5 }, next: endDay }]
        };
    } else {
        shakeScreen();
        return {
            bg: bg,
            speaker: "narrator",
            text: "Fallaste... Te golpeó en el orgullo (y en la cara).",
            choices: [{ text: "Ouch...", effect: { [statType]: 1 }, next: endDay }]
        };
    }
}

function generateTrainingEvent(loc, bg) {
    let stat = 'str';
    let txt = "Entrenas duro.";
            let bonus = 0;

            if(loc === 'library') {
                stat = 'wis';
                txt = "Lees libros aburridos pero útiles.";
                if (state.player.class === 'scholar') bonus = 3;
            }
            if(loc === 'garden') {
                stat = 'cha';
                txt = "Practicas tu sonrisa en el reflejo del agua.";
                if (state.player.class === 'noble') bonus = 3;
            }
            if(loc === 'training') {
                if (state.player.class === 'guard') bonus = 3;
            }

            if (bonus > 0) {
                txt += ` Gracias a tu origen como ${state.player.class}, aprendes más rápido.`
            }


    return {
        bg: bg,
        speaker: "narrator",
        text: txt,
        next: () => {
                    state.stats[stat] += 5 + bonus;
            updateUI();
            endDay();
        }
    };
}

function resultScene(bg, char, emo, txt, isDayEnd) {
    renderScene({
        bg: bg,
        char: char,
        emotion: emo,
        speaker: "narrator",
        text: txt,
        next: isDayEnd ? endDay : 'daily_loop'
    });
}

function endDay() {
    el.overlay.classList.remove('hidden');
    setTimeout(() => { el.overlay.style.opacity = 1; }, 50);

    el.overlayTitle.innerText = `Día ${state.day} Completado`;
    el.overlayDesc.innerText = "Descansas y recuperas energías. Tus sueños son... interesantes.";

    state.day++;
    saveGame();
}

function hideOverlay() {
    el.overlay.style.opacity = 0;
    setTimeout(() => { el.overlay.classList.add('hidden'); }, 1000);

    if (state.day > 5) {
        // Ending Check
        checkEnding();
    } else {
        startDailyLoop();
    }
}

function checkEnding() {
    let ending = 'normal';
    if (state.affinity.kael > 15) ending = 'kael_love';
    else if (state.affinity.rylan > 15) ending = 'rylan_love';
    else if (state.stats.str > 50) ending = 'warrior';
    else if (state.stats.cha > 50) ending = 'queen';

    const endings = {
        'normal': { t: "Paladín Promedio", d: "Sobreviviste, pero nadie escribirá canciones sobre ti." },
        'kael_love': { t: "Corazón de Acero", d: "Tú y Sir Kael luchan espalda con espalda... y mano con mano." },
        'rylan_love': { t: "Amor Mágico", d: "Dejaste la espada por los hechizos... y por Rylan." },
        'warrior': { t: "Diosa de la Guerra", d: "Tu fuerza aterroriza a todos. Mueres soltera pero gloriosa." },
        'queen': { t: "Reina del Harem", d: "¡Todos te aman! Tienes un club de fans oficial." }
    };

    el.overlay.classList.remove('hidden');
    el.overlay.style.opacity = 1;
    el.overlayTitle.innerText = endings[ending].t;
    el.overlayDesc.innerText = endings[ending].d;

    // Override button to reset
    const btn = el.overlay.querySelector('button');
    btn.innerText = "JUGAR DE NUEVO";
    btn.onclick = resetGame;
}

function saveGame() {
    localStorage.setItem('paladin_otome_save', JSON.stringify(state));
}

function resetGame() {
    localStorage.removeItem('paladin_otome_save');
    location.reload();
}

// --- Initial Scenes ---
const SCENES = {
    'intro_0': {
        bg: "bg-slate-900",
        text: "Bienvenida a 'Corazón de Paladín'. ¿Estás lista para encontrar el amor en el campo de batalla?",
        next: 'intro_1'
    },
    'intro_1': {
        bg: "bg-gradient-to-b from-slate-700 to-slate-900",
        speaker: "narrator",
        text: "Eres una nueva recluta. Tienes 5 días para demostrar tu valía... y quizás encontrar pareja.",
        next: 'daily_loop'
    }
};

// --- Boot ---

function init() {
    el.startGameBtn.addEventListener('click', () => {
        const playerName = el.playerNameInput.value.trim();
        if (playerName) {
            state.player.name = playerName;
            CHARACTERS.protagonist.name = playerName;
        } else {
            // Keep default name if input is empty
            state.player.name = "Anya";
            CHARACTERS.protagonist.name = "Anya";
        }
        showScreen('creation');
    });

    el.hairColorSelect.addEventListener('click', (e) => {
        if (e.target.dataset.color) {
            state.player.appearance.hair = e.target.dataset.color;
            // Visual feedback
            el.hairColorSelect.querySelectorAll('button').forEach(btn => btn.classList.remove('border-yellow-400'));
            e.target.classList.add('border-yellow-400');
        }
    });

    el.clothingColorSelect.addEventListener('click', (e) => {
        if (e.target.dataset.color) {
            state.player.appearance.clothing = e.target.dataset.color;
             // Visual feedback
            el.clothingColorSelect.querySelectorAll('button').forEach(btn => btn.classList.remove('border-yellow-400'));
            e.target.classList.add('border-yellow-400');
        }
    });

    el.confirmCharacterBtn.addEventListener('click', () => {
        // 1. Get selected class
        state.player.class = el.classSelect.value;

        // 2. Reset progress to a clean slate but keep customization
        const cleanState = JSON.parse(JSON.stringify(initialState));
        state.stats = cleanState.stats;
        state.affinity = cleanState.affinity;
        state.day = 1;
        state.flags = {};
        state.inventory = [];
        state.currentSceneId = 'intro_1'; // Start game right after intro

        // 3. Apply class bonuses
        applyClassBonuses();

        // 4. Save and start the game
        saveGame();
        showScreen('game');
        updateUI();
        loadScene(state.currentSceneId);
    });

    // On boot, check if a game is in progress.
    if (!localStorage.getItem('paladin_otome_save') || state.currentSceneId === 'intro_0') {
        // If there's no save file OR if the save file is at the very beginning,
        // just show the start menu.
        showScreen('start');
    } else {
        // If a save file exists and they've made progress, load the game.
        CHARACTERS.protagonist.name = state.player.name; // Set the name
        showScreen('game');
        updateUI();
        loadScene(state.currentSceneId);
    }
}

function applyClassBonuses() {
    const playerClass = state.player.class;
    if (playerClass === 'noble') {
        state.stats.cha += 5;
    } else if (playerClass === 'guard') {
        state.stats.str += 5;
    } else if (playerClass === 'merchant') {
        state.inventory.push({ item: 'gold', quantity: 20 });
    } else if (playerClass === 'scholar') {
        state.stats.wis += 5;
    } else if (playerClass === 'urchin') {
        state.stats.str += 2;
        state.stats.cha += 2;
    }
}

init();
