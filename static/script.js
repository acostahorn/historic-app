const state = {
    mode: "solo",
    view: "dashboard",
    isSending: false,
    characters: [],
    editingCharacterId: null,
    libraryFilter: "",
    session: { logged_in: false, user: null, is_admin: false },
    bootstrapAdmin: null,
};

const CHARACTER_IMAGES = {
    "Fidel Castro": "Castro.jpg",
    "Richard Nixon": "Nixon.jpg",
    "Winston Churchill": "Churchill.jpg",
    "Giuseppe Garibaldi": "Garibaldi.jpg",
    "Socrates": "Socrates.jpg",
    "Robert the Bruce": "Bruce.jpg",
    "Edward II of England": "Edward.jpg",
    "Queen Victoria": "Victoria.jpg",
    "Elizabeth I": "Elizabeth_I.jpg",
    "Alan Turing": "Turing.jpg",
    "Margaret Thatcher": "Thatcher.jpg",
    "Ernesto Che Guevara": "Che.jpg",
};

const form = document.getElementById("message-form");
const input = document.getElementById("user-input");
const sendButton = document.getElementById("send-button");
const chatWindow = document.getElementById("chat-window");
const clearButton = document.getElementById("clear-chat");
const soloControls = document.getElementById("solo-controls");
const debateControls = document.getElementById("debate-controls");
const title = document.getElementById("conversation-title");
const subtitle = document.getElementById("conversation-subtitle");
const debateTopic = document.getElementById("debate-topic");
const printButton = document.getElementById("print-chat");
const createCharacterToggle = document.getElementById("new-character-modal-toggle");
const createCharacterToggleInline = document.getElementById("new-character-modal-toggle-inline");
const characterDialog = document.getElementById("character-dialog");
const closeCharacterDialog = document.getElementById("close-character-dialog");
const characterForm = document.getElementById("character-form");
const characterDialogTitle = document.getElementById("character-dialog-title");
const deleteCharacterButton = document.getElementById("delete-character-button");
const characterSearch = document.getElementById("character-search");
const characterLibrary = document.getElementById("character-library");
const authStatus = document.getElementById("auth-status");
const authUsername = document.getElementById("auth-username");
const authPassword = document.getElementById("auth-password");
const authLoginButton = document.getElementById("auth-login");
const authRegisterButton = document.getElementById("auth-register");
const authLogoutButton = document.getElementById("auth-logout");
const sessionChip = document.getElementById("session-chip");
const profileUsername = document.getElementById("profile-username");
const viewTabs = document.querySelectorAll(".view-tab");
const dashboardView = document.getElementById("dashboard-view");
const conversationView = document.getElementById("conversation-view");
const goConversationButton = document.getElementById("go-conversation");
const bootstrapAdminBanner = document.getElementById("bootstrap-admin-banner");

const appShell = document.querySelector(".app-shell");

const characterFields = {
    name: document.getElementById("character-name"),
    type: document.getElementById("character-type"),
    language: document.getElementById("character-language"),
    sourceTitle: document.getElementById("character-source-title"),
    sourceAuthor: document.getElementById("character-source-author"),
    sourceUrl: document.getElementById("character-source-url"),
    bio: document.getElementById("character-bio"),
    systemPrompt: document.getElementById("character-system-prompt"),
    avatar: document.getElementById("character-avatar"),
    avatarPreview: document.getElementById("character-avatar-preview"),
};

let characterSource = "";

init();

async function init() {
    wireEvents();
    setMode("solo");
    setView(appShell?.dataset.startView || "dashboard");
    syncCharacterForm();
    await refreshSession();
    await refreshCharacters();
    renderAuth();
    updateDashboardCopy();
}

function wireEvents() {
    document.querySelectorAll(".mode-tab").forEach((button) => {
        button.addEventListener("click", () => setMode(button.dataset.mode));
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await sendMessage();
    });

    clearButton.addEventListener("click", () => {
        chatWindow.innerHTML = "";
        appendMessage(
            "Archive note",
            "Transcript cleared locally. The next exchange will continue using saved conversation memory.",
            "system"
        );
    });

    document.getElementById("char-debate-1").addEventListener("change", preventDuplicateDebaters);
    document.getElementById("char-debate-2").addEventListener("change", preventDuplicateDebaters);

    printButton.addEventListener("click", () => window.print());

    createCharacterToggle.addEventListener("click", () => openCharacterDialog());
    createCharacterToggleInline?.addEventListener("click", () => openCharacterDialog());
    closeCharacterDialog.addEventListener("click", () => closeCharacterDialogElement());
    characterForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        await saveCharacter();
    });
    deleteCharacterButton.addEventListener("click", async () => {
        await deleteCharacter();
    });

    characterSearch.addEventListener("input", () => {
        state.libraryFilter = characterSearch.value.trim().toLowerCase();
        renderLibrary();
    });

    authLoginButton.addEventListener("click", login);
    authRegisterButton.addEventListener("click", register);
    authLogoutButton.addEventListener("click", logout);
    goConversationButton.addEventListener("click", () => setView("conversation"));

    viewTabs.forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));

    document.getElementById("character-type").addEventListener("change", syncCharacterForm);
}

function openCharacterDialog(character = null) {
    if (character) {
        state.editingCharacterId = character.id;
        characterSource = "edit";
        characterDialogTitle.textContent = `Edit ${character.name}`;
        deleteCharacterButton.classList.toggle("hidden", !state.session.is_admin);
        characterFields.name.value = character.name || "";
        characterFields.type.value = character.character_type || "historical";
        characterFields.language.value = character.language || "English";
        characterFields.sourceTitle.value = character.source_title || "";
        characterFields.sourceAuthor.value = character.source_author || "";
        characterFields.sourceUrl.value = character.source_url || "";
        characterFields.bio.value = character.bio || "";
        characterFields.systemPrompt.value = character.system_prompt || "";
        setAvatarPreview(character.avatar_path || "");
    } else {
        state.editingCharacterId = null;
        characterSource = "new";
        characterDialogTitle.textContent = "Create a character";
        deleteCharacterButton.classList.add("hidden");
        characterForm.reset();
        characterFields.type.value = "historical";
        setAvatarPreview("");
    }
    syncCharacterForm();
    characterDialog.showModal();
}

function closeCharacterDialogElement() {
    characterDialog.close();
    state.editingCharacterId = null;
}

function setMode(mode) {
    state.mode = mode;

    document.querySelectorAll(".mode-tab").forEach((button) => {
        const isActive = button.dataset.mode === mode;
        button.classList.toggle("active", isActive);
        button.setAttribute("aria-selected", String(isActive));
    });

    const isDebate = mode === "debate";
    soloControls.classList.toggle("hidden", isDebate);
    debateControls.classList.toggle("hidden", !isDebate);

    title.textContent = isDebate ? "Impossible debate" : "One-on-one conversation";
    subtitle.textContent = isDebate
        ? "Choose two figures and generate a six-turn exchange with local memory."
        : "Choose a figure and write your opening line.";
    input.placeholder = isDebate
        ? "Optional: add a sharper angle for this exchange..."
        : "Ask a question or challenge the character...";
    sendButton.textContent = isDebate ? "Start exchange" : "Send";
}

function syncCharacterForm() {
    const isHistorical = characterFields.type.value === "historical";
    characterFields.sourceTitle.disabled = isHistorical;
    characterFields.sourceAuthor.disabled = isHistorical;
    characterFields.sourceUrl.disabled = isHistorical;
    if (isHistorical) {
        characterFields.sourceTitle.value = "";
        characterFields.sourceAuthor.value = "";
        characterFields.sourceUrl.value = "";
    }
}

async function sendMessage() {
    if (state.isSending) return;

    const payload = buildPayload();
    if (!payload.message) return;

    state.isSending = true;
    setBusy(true);

    appendMessage(state.mode === "solo" ? "You" : "Topic", payload.message, "user");
    input.value = "";

    const thinking = appendMessage("Archive", "Composing from local context...", "system thinking");

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        thinking.remove();

        if (!response.ok || data.error) {
            appendMessage("System", data.error || "The exchange could not be generated.", "system");
            return;
        }

        data.forEach((message) => appendMessage(message.sender, message.text, speakerClass(message.sender)));
    } catch (error) {
        thinking.remove();
        appendMessage("System", "Could not connect to the server.", "system");
        console.error("Fetch error:", error);
    } finally {
        state.isSending = false;
        setBusy(false);
    }
}

function buildPayload() {
    if (state.mode === "debate") {
        const topic = debateTopic.value.trim();
        const angle = input.value.trim();
        return {
            mode: "debate",
            message: angle ? `${topic}\n\nFocus the exchange on: ${angle}` : topic,
            char_id_1: document.getElementById("char-debate-1").value,
            char_id_2: document.getElementById("char-debate-2").value,
        };
    }

    return {
        mode: "solo",
        message: input.value.trim(),
        char_id_1: document.getElementById("char1").value,
    };
}

async function saveCharacter() {
    const payload = collectCharacterPayload();
    if (!payload) return;

    try {
        const url = state.editingCharacterId ? `/characters/${state.editingCharacterId}` : "/characters";
        const response = await fetch(url, {
            method: state.editingCharacterId ? "PUT" : "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok || data.error) {
            appendMessage("System", data.error || "Character save failed.", "system");
            return;
        }

        await refreshCharacters(data.character?.id);
        if (state.editingCharacterId && data.character) {
            setAvatarPreview(data.character.avatar_path || "");
        }
        closeCharacterDialogElement();
        characterForm.reset();
        syncCharacterForm();
        appendMessage("Archive", `${data.character.name} saved to the character library.`, "system");
    } catch (error) {
        console.error("Create character error:", error);
        appendMessage("System", "Could not save the character.", "system");
    }
}

function collectCharacterPayload() {
    const payload = {
        name: characterFields.name.value.trim(),
        character_type: characterFields.type.value,
        language: characterFields.language.value.trim(),
        source_title: characterFields.sourceTitle.value.trim(),
        source_author: characterFields.sourceAuthor.value.trim(),
        source_url: characterFields.sourceUrl.value.trim(),
        bio: characterFields.bio.value.trim(),
        system_prompt: characterFields.systemPrompt.value.trim(),
        is_deceased: true,
    };

    if (!payload.name || !payload.language || !payload.bio || !payload.system_prompt) {
        appendMessage("System", "Name, language, bio, and system prompt are required.", "system");
        return null;
    }

    if (payload.character_type === "literary" && (!payload.source_title || !payload.source_author)) {
        appendMessage("System", "Literary characters need a source title and author.", "system");
        return null;
    }

    return payload;
}

async function deleteCharacter() {
    if (!state.editingCharacterId) return;
    if (!state.session.is_admin) {
        appendMessage("System", "Admin privileges are required to remove characters.", "system");
        return;
    }
    if (!window.confirm("Delete this custom character?")) return;

    try {
        const response = await fetch(`/characters/${state.editingCharacterId}`, { method: "DELETE" });
        const data = await response.json();
        if (!response.ok || data.error) {
            appendMessage("System", data.error || "Character delete failed.", "system");
            return;
        }
        closeCharacterDialogElement();
        characterForm.reset();
        syncCharacterForm();
        await refreshCharacters();
        appendMessage("Archive", "Character deleted from the library.", "system");
    } catch (error) {
        console.error("Delete character error:", error);
        appendMessage("System", "Could not delete the character.", "system");
    }
}

async function refreshCharacters(selectId = null) {
    const response = await fetch("/characters");
    state.characters = await response.json();
    renderCharacterSelects(selectId);
    renderLibrary();
}

async function refreshSession() {
    const response = await fetch("/session");
    state.session = await response.json();
    state.bootstrapAdmin = state.session.bootstrap_admin || null;
    renderAuth();
    updateDashboardCopy();
}

async function login() {
    const payload = { username: authUsername.value.trim(), password: authPassword.value };
    const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
        appendMessage("System", data.error || "Login failed.", "system");
        return;
    }
    authPassword.value = "";
    await refreshSession();
    await refreshCharacters();
    appendMessage("Archive", `Logged in as ${state.session.user.username}.`, "system");
}

async function register() {
    const payload = { username: authUsername.value.trim(), password: authPassword.value };
    const response = await fetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok || data.error) {
        appendMessage("System", data.error || "Registration failed.", "system");
        return;
    }
    authPassword.value = "";
    await refreshSession();
    await refreshCharacters();
    appendMessage("Archive", `Registered and signed in as ${state.session.user.username}.`, "system");
}

async function logout() {
    await fetch("/auth/logout", { method: "POST" });
    state.session = { logged_in: false, user: null, is_admin: false };
    state.bootstrapAdmin = null;
    renderAuth();
    appendMessage("Archive", "Signed out.", "system");
}

function renderAuth() {
    const signedInLabel = state.session.logged_in
        ? `${state.session.user.username}${state.session.is_admin ? " · admin" : ""}`
        : "Not signed in";
    authStatus.textContent = signedInLabel;
    sessionChip.textContent = signedInLabel;
    profileUsername.textContent = signedInLabel;
    authLogoutButton.classList.toggle("hidden", !state.session.logged_in);
    deleteCharacterButton.classList.toggle("hidden", !state.session.is_admin || state.editingCharacterId === null);
    bootstrapAdminBanner.classList.toggle("hidden", !state.bootstrapAdmin);
    if (state.bootstrapAdmin) {
        bootstrapAdminBanner.innerHTML = `<strong>Bootstrap admin ready</strong><p>Use <code>${escapeHtml(state.bootstrapAdmin.username)}</code> / <code>${escapeHtml(state.bootstrapAdmin.password)}</code> to log in once.</p>`;
    }
    if (!state.session.logged_in) {
        authPassword.value = "";
    }
    updateDashboardCopy();
}

function setView(view) {
    state.view = view;
    viewTabs.forEach((button) => {
        const active = button.dataset.view === view;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
    });
    dashboardView.classList.toggle("hidden", view !== "dashboard");
    conversationView.classList.toggle("hidden", view !== "conversation");
    updateDashboardCopy();
}

function updateDashboardCopy() {
    const welcome = document.querySelector(".profile-panel .dashboard-lede");
    if (!welcome) return;
    welcome.textContent = state.session.logged_in
        ? "Pick a character, keep your account visible, and jump straight into a conversation."
        : "Sign in to save conversation memory, manage characters, and carry your profile between tabs.";
}

function openCharacterDialog(character = null) {
    if (state.view !== "conversation") setView("conversation");
    if (character) {
        state.editingCharacterId = character.id;
        characterSource = "edit";
        characterDialogTitle.textContent = `Edit ${character.name}`;
        deleteCharacterButton.classList.toggle("hidden", !state.session.is_admin);
        characterFields.name.value = character.name || "";
        characterFields.type.value = character.character_type || "historical";
        characterFields.language.value = character.language || "English";
        characterFields.sourceTitle.value = character.source_title || "";
        characterFields.sourceAuthor.value = character.source_author || "";
        characterFields.sourceUrl.value = character.source_url || "";
        characterFields.bio.value = character.bio || "";
        characterFields.systemPrompt.value = character.system_prompt || "";
        setAvatarPreview(character.avatar_path || "");
    } else {
        state.editingCharacterId = null;
        characterSource = "new";
        characterDialogTitle.textContent = "Create a character";
        deleteCharacterButton.classList.add("hidden");
        characterForm.reset();
        characterFields.type.value = "historical";
        setAvatarPreview("");
    }
    syncCharacterForm();
    characterDialog.showModal();
}

function renderCharacterSelects(selectId = null) {
    ["char1", "char-debate-1", "char-debate-2"].forEach((id) => {
        const select = document.getElementById(id);
        const previousValue = select.value;
        select.innerHTML = "";
        state.characters.forEach((character) => {
            const option = document.createElement("option");
            option.value = character.id;
            option.textContent = character.name;
            select.appendChild(option);
        });
        if (selectId) {
            select.value = String(selectId);
        } else if (previousValue) {
            select.value = previousValue;
        }
    });
    preventDuplicateDebaters();
}

function renderLibrary() {
    const term = state.libraryFilter;
    characterLibrary.innerHTML = "";

    const filtered = state.characters.filter((character) => {
        const haystack = [
            character.name,
            character.bio || "",
            character.language || "",
            character.character_type || "",
            character.source_title || "",
            character.source_author || "",
        ].join(" ").toLowerCase();
        return haystack.includes(term);
    });

    if (!filtered.length) {
        characterLibrary.innerHTML = '<p class="library-empty">No characters match that search.</p>';
        return;
    }

    filtered.forEach((character) => {
        const card = document.createElement("article");
        card.className = "character-card" + (character.is_custom ? " custom" : " builtin");

        const header = document.createElement("div");
        header.className = "character-card-header";

        const identity = document.createElement("div");
        identity.className = "character-card-identity";

        const titleWrap = document.createElement("div");
        titleWrap.className = "character-card-titlewrap";
        const nameEl = document.createElement("strong");
        nameEl.textContent = character.name;
        const langEl = document.createElement("span");
        langEl.textContent = character.language || "Unknown";
        titleWrap.append(nameEl, langEl);

        if (character.avatar_path) {
            const avatar = document.createElement("img");
            avatar.src = character.avatar_path;
            avatar.alt = `${character.name} avatar`;
            avatar.className = "library-avatar";
            identity.appendChild(avatar);
        }
        identity.appendChild(titleWrap);
        header.appendChild(identity);

        const meta = document.createElement("p");
        meta.className = "character-card-meta";
        const typeBits = [character.character_type || "character", character.is_custom ? "custom" : "built-in"];
        if (character.source_title) typeBits.push(character.source_title);
        if (character.source_author) typeBits.push(character.source_author);
        meta.textContent = typeBits.join(" • ");

        const bio = document.createElement("p");
        bio.className = "character-card-bio";
        bio.textContent = character.bio || "No biography provided.";

        card.append(header, meta, bio);

        const actions = document.createElement("div");
        actions.className = "character-card-actions";

        const useButton = document.createElement("button");
        useButton.type = "button";
        useButton.textContent = "Use";
        useButton.addEventListener("click", () => selectCharacter(character.id));
        actions.appendChild(useButton);

        if (character.is_custom) {
            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.textContent = "Edit";
            editButton.addEventListener("click", () => openCharacterDialog(character));
            actions.appendChild(editButton);

            if (state.session.is_admin) {
                const deleteButton = document.createElement("button");
                deleteButton.type = "button";
                deleteButton.textContent = "Delete";
                deleteButton.addEventListener("click", async () => {
                    state.editingCharacterId = character.id;
                    await deleteCharacter();
                });
                actions.appendChild(deleteButton);
            }
        }

        if (character.avatar_path) {
            const avatarSrc = character.avatar_path;
            const preview = document.createElement("img");
            preview.src = avatarSrc;
            preview.alt = `${character.name} avatar preview`;
            preview.className = "library-avatar";
            header.prepend(preview);
        }

        card.appendChild(actions);
        characterLibrary.appendChild(card);
    });
}

function selectCharacter(id) {
    const mainSelect = document.getElementById("char1");
    const debate1 = document.getElementById("char-debate-1");
    mainSelect.value = String(id);
    debate1.value = String(id);
    preventDuplicateDebaters();
    setMode("solo");
}

function setView(view) {
    state.view = view;
    viewTabs.forEach((button) => {
        const active = button.dataset.view === view;
        button.classList.toggle("active", active);
        button.setAttribute("aria-selected", String(active));
    });
    dashboardView.classList.toggle("hidden", view !== "dashboard");
    conversationView.classList.toggle("hidden", view !== "conversation");
    updateDashboardCopy();
}

function updateDashboardCopy() {
    const welcome = document.querySelector(".profile-panel .dashboard-lede");
    if (!welcome) return;
    welcome.textContent = state.session.logged_in
        ? "Pick a character, keep your account visible, and jump straight into a conversation."
        : "Sign in to save conversation memory, manage characters, and carry your profile between tabs.";
}

function openCharacterDialog(character = null) {
    if (state.view !== "conversation") setView("conversation");
    if (character) {
        state.editingCharacterId = character.id;
        characterSource = "edit";
        characterDialogTitle.textContent = `Edit ${character.name}`;
        deleteCharacterButton.classList.toggle("hidden", !state.session.is_admin);
        characterFields.name.value = character.name || "";
        characterFields.type.value = character.character_type || "historical";
        characterFields.language.value = character.language || "English";
        characterFields.sourceTitle.value = character.source_title || "";
        characterFields.sourceAuthor.value = character.source_author || "";
        characterFields.sourceUrl.value = character.source_url || "";
        characterFields.bio.value = character.bio || "";
        characterFields.systemPrompt.value = character.system_prompt || "";
        setAvatarPreview(character.avatar_path || "");
    } else {
        state.editingCharacterId = null;
        characterSource = "new";
        characterDialogTitle.textContent = "Create a character";
        deleteCharacterButton.classList.add("hidden");
        characterForm.reset();
        characterFields.type.value = "historical";
        setAvatarPreview("");
    }
    syncCharacterForm();
    characterDialog.showModal();
}

function appendMessage(sender, text, className = "") {
    const message = document.createElement("article");
    message.className = (`message ${className}`).trim();

    const characterRecord = state.characters.find((character) => character.name === sender);
    const avatarPath = characterRecord?.avatar_path || (CHARACTER_IMAGES.hasOwnProperty(sender) ? `/resources/${CHARACTER_IMAGES[sender]}` : "");
    if (avatarPath) {
        const img = document.createElement("img");
        img.src = avatarPath;
        img.alt = `${sender} avatar`;
        img.className = "avatar";
        img.style.width = "100px";
        img.style.height = "100px";
        img.style.objectFit = "cover";
        img.style.borderRadius = "4px";
        message.appendChild(img);
    }

    const label = document.createElement("strong");
    label.textContent = sender;

    const body = document.createElement("p");
    body.textContent = text;

    message.append(label, body);
    chatWindow.appendChild(message);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return message;
}

function speakerClass(sender) {
    return sender.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function setBusy(isBusy) {
    sendButton.disabled = isBusy;
    input.disabled = isBusy;
    debateTopic.disabled = isBusy;
    sendButton.textContent = isBusy ? "Composing..." : (state.mode === "debate" ? "Start exchange" : "Send");
}

function preventDuplicateDebaters() {
    const first = document.getElementById("char-debate-1");
    const second = document.getElementById("char-debate-2");
    if (first.value !== second.value) return;
    const replacement = Array.from(second.options).find((option) => option.value !== first.value);
    if (replacement) second.value = replacement.value;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function setAvatarPreview(src) {
    if (!characterFields.avatarPreview) return;
    if (!src) {
        characterFields.avatarPreview.innerHTML = "";
        return;
    }
    characterFields.avatarPreview.innerHTML = `<img src="${escapeHtml(src)}" alt="Character avatar preview">`;
}
