// This is a mock test file to verify the game's logic.

// Mocking localStorage
const localStorageMock = (function() {
    let store = {};
    return {
        getItem: function(key) {
            return store[key] || null;
        },
        setItem: function(key, value) {
            store[key] = value.toString();
        },
        removeItem: function(key) {
            delete store[key];
        },
        clear: function() {
            store = {};
        }
    };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mocking DOM elements
document.body.innerHTML = `
    <div id="start-menu">
        <input id="player-name" value="Test Player">
        <button id="start-game-btn"></button>
    </div>
    <div id="character-creation-screen" class="hidden">
        <select id="class-select">
            <option value="noble"></option>
            <option value="guard"></option>
            <option value="merchant"></option>
        </select>
        <div id="hair-color-select">
            <button data-color="bg-red-600"></button>
        </div>
        <div id="clothing-color-select">
            <button data-color="bg-red-900"></button>
        </div>
        <button id="confirm-character-btn"></button>
    </div>
    <div id="game-wrapper" class="hidden">
        <div id="background"></div>
        <span id="speaker-name"></span>
        <p id="dialogue-text"></p>
        <div id="choices-container"></div>
        <div id="continue-btn"></div>
        <span id="val-str"></span>
        <div id="stat-str"></div>
        <span id="val-cha"></span>
        <div id="stat-cha"></div>
        <span id="val-wis"></span>
        <div id="stat-wis"></div>
        <span id="day-counter"></span>
        <span id="heart-kael"></span>
        <span id="heart-rylan"></span>
        <span id="heart-rival"></span>
        <span id="heart-zarek"></span>
        <div id="character-sprite">
            <div id="char-body"></div>
            <div id="char-hair-back"></div>
            <div id="char-hair-front"></div>
            <div id="char-head"></div>
            <div id="char-aura"></div>
            <div id="char-emotion"></div>
            <div id="char-blush"></div>
        </div>
        <div id="fx-overlay"></div>
        <div id="full-overlay">
            <h1 id="overlay-title"></h1>
            <p id="overlay-desc"></p>
        </div>
    </div>
`;

console.log('--- Running Tests ---');

// Test 1: Initial state
console.log('Test 1: Initial state');
if (state.day === 1 && state.stats.str === 10) {
    console.log('  OK');
} else {
    console.error('  Failed');
}

// Test 2: Start menu logic
console.log('Test 2: Start menu logic');
init();
el.startGameBtn.click();
if (state.player.name === 'Test Player' && !el.characterCreationScreen.classList.contains('hidden')) {
    console.log('  OK');
} else {
    console.error('  Failed');
}

// Test 3: Character creation
console.log('Test 3: Character creation');
el.classSelect.value = 'guard';
el.confirmCharacterBtn.click();
if (state.player.class === 'guard' && state.stats.str === 15 && !el.gameWrapper.classList.contains('hidden')) {
    console.log('  OK');
} else {
    console.error('  Failed');
}

// Test 4: Zarek event
console.log('Test 4: Zarek event');
runEvent('alley');
// This is harder to test without seeing the output, but we can check if affinity can be changed.
handleChoice({ effect: { zarek: 5 } });
if (state.affinity.zarek === 5) {
    console.log('  OK');
} else {
    console.error('  Failed');
}

console.log('--- Tests Finished ---');
