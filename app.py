from flask import Flask, render_template, request, jsonify, session, send_from_directory
import os
import re
from pathlib import Path
from werkzeug.utils import secure_filename
import database as db
from database import (
    init_db,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_username,
    get_user_count,
    save_msg,
    get_history,
    get_persona_by_id,
    get_character_record_by_id,
    get_all_characters,
    get_character_by_name,
    get_custom_character_by_id,
    save_custom_character,
    update_custom_character,
    hide_character,
    get_character_memory,
    upsert_character_memory,
)
import database as db
from engine import get_ai_response

app = Flask(__name__)
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads" / "character_avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_AVATAR_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024

@app.route('/resources/<path:filename>')
def serve_resource(filename):
    return send_from_directory('resources', filename)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_key_123")
init_db()

DEBATE_TURNS = 6
SOLO_TEMPERATURE = 0.75
BASE_DEBATE_TEMPERATURE = 0.95
HARSH_DISAGREEMENT_TEMPERATURE = 1.08
HARSH_DISAGREEMENTS = {
    frozenset(("Fidel Castro", "Richard Nixon")),
    frozenset(("Fidel Castro", "Winston Churchill")),
    frozenset(("Richard Nixon", "Winston Churchill")),
    frozenset(("Socrates", "Richard Nixon")),
    frozenset(("Robert the Bruce", "Edward II")),
    frozenset(("Giuseppe Garibaldi", "Edward II")),
    frozenset(("Robert the Bruce", "Edward II of England")),
    frozenset(("Giuseppe Garibaldi", "Edward II of England")),
}
KNOWN_CHARACTER_TYPES = {"historical", "literary"}
NAME_PATTERN = re.compile(r"^[A-Za-zÀ-ÿ0-9'’ .\-()]+$")


@app.route('/')
def index():
    return render_template('index.html', characters=get_all_characters(), bootstrap_admin=db.BOOTSTRAP_ADMIN_CREDENTIALS)


@app.route('/dashboard')
def dashboard():
    return render_template('index.html', characters=get_all_characters(), bootstrap_admin=db.BOOTSTRAP_ADMIN_CREDENTIALS, start_view='dashboard')


@app.route('/conversation')
def conversation():
    return render_template('index.html', characters=get_all_characters(), bootstrap_admin=db.BOOTSTRAP_ADMIN_CREDENTIALS, start_view='conversation')


@app.route('/session', methods=['GET'])
def session_info():
    user = current_user()
    return jsonify({
        "logged_in": bool(user),
        "user": public_user(user) if user else None,
        "is_admin": bool(user and user['is_admin']),
        "bootstrap_admin": public_user_from_bootstrap(),
    })


@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if get_user_by_username(username):
        return jsonify({"error": "username already exists"}), 409

    is_admin = bool(data.get('is_admin', False))
    if get_user_count() > 0:
        is_admin = False
    user = create_user(username, password, is_admin=is_admin)
    session['user_id'] = user['id']
    return jsonify({"ok": True, "user": public_user(user)}), 201


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "invalid username or password"}), 401
    session['user_id'] = user['id']
    return jsonify({"ok": True, "user": public_user(user)})


@app.route('/auth/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({"ok": True})


@app.route('/chat', methods=['POST'])
def chat_handler():
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401

    data = request.get_json(silent=True) or {}
    mode = data.get('mode')
    char_id_1 = data.get('char_id_1')
    char_id_2 = data.get('char_id_2')

    p1 = get_persona_by_id(char_id_1)
    if not p1:
        return jsonify({"error": "Character 1 not found"}), 404

    if mode == 'solo':
        user_text = (data.get('message') or '').strip()
        if not user_text:
            return jsonify({"error": "Message is required"}), 400

        context_key = solo_context_key(user['id'], p1['id'])
        save_msg(user['id'], "User", user_text, context_key, character_id=p1['id'])
        history = build_history_with_memory(user['id'], p1, context_key)

        reply = get_ai_response(
            build_character_system_prompt(p1, user['id']),
            history,
            temperature=SOLO_TEMPERATURE,
            language=p1['language'] or 'English',
            force_english=False,
        )
        save_msg(user['id'], p1['name'], reply, context_key, character_id=p1['id'])
        update_memory_from_exchange(user['id'], p1, user_text, reply)
        return jsonify([{"sender": p1['name'], "text": reply}])

    if mode == 'debate':
        p2 = get_persona_by_id(char_id_2)
        if not p2:
            return jsonify({"error": "Character 2 not found"}), 404
        if p1['id'] == p2['id']:
            return jsonify({"error": "Choose two different historical figures for debate"}), 400

        continue_flag = data.get('continue', False)
        user_text = (data.get('message') or '').strip()
        if not continue_flag and not user_text:
            return jsonify({"error": "Debate topic is required"}), 400

        context_key = debate_context_key(p1['id'], p2['id'])
        if not continue_flag:
            save_msg(user['id'], "User", user_text, context_key, character_id=None)

        history = build_debate_history(user['id'], p1, p2, context_key, user_text, continue_flag)
        debate_temperature = get_debate_temperature(p1['name'], p2['name'])
        speakers = [p1, p2]
        replies = []

        for turn_index in range(DEBATE_TURNS):
            speaker = speakers[turn_index % 2]
            opponent = speakers[(turn_index + 1) % 2]
            history.append({
                "role": "user",
                "content": build_debate_turn_instruction(
                    turn_index,
                    speaker['name'],
                    opponent['name'],
                    user_text,
                    speaker_language=speaker['language'],
                    opponent_language=opponent['language'],
                )
            })
            reply = get_ai_response(
                build_character_system_prompt(speaker, user['id']),
                history,
                temperature=debate_temperature,
                language=speaker['language'] or 'English',
                force_english=False,
            )
            save_msg(user['id'], speaker['name'], reply, context_key, character_id=speaker['id'])
            history.append({"role": "assistant", "content": reply})
            replies.append({"sender": speaker['name'], "text": reply})

        update_memory_from_debate(user['id'], p1, p2, user_text, replies)
        return jsonify(replies)

    return jsonify({"error": "Mode must be solo or debate"}), 400


@app.route('/characters', methods=['GET'])
def list_characters():
    user = current_user()
    include_hidden = bool(user and user['is_admin'])
    return jsonify([row_to_dict(row) for row in get_all_characters(include_hidden=include_hidden)])


@app.route('/characters', methods=['POST'])
def create_character():
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401

    data = parse_character_request()
    validated, error = validate_character_payload(data)
    if error:
        return jsonify({"error": error}), 400
    if get_character_by_name(validated["name"]):
        return jsonify({"error": "A character with that name already exists"}), 409

    if validated["character_type"] == 'historical':
        if not data.get('is_deceased', True) or data.get('is_living', False):
            return jsonify({"error": "Historical figures must be deceased"}), 400
    else:
        if not validated["source_title"]:
            return jsonify({"error": "Literary characters require a source_title"}), 400
        if not validated["source_author"]:
            return jsonify({"error": "Literary characters require a source_author"}), 400

    avatar_path = save_avatar_file(data.get('avatar'))
    created = save_custom_character(created_by_user_id=user['id'], avatar_path=avatar_path, **validated)
    return jsonify({"ok": True, "character": row_to_dict(created)}), 201


@app.route('/characters/<int:char_id>', methods=['PUT'])
def update_character(char_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401

    existing = get_custom_character_by_id(char_id)
    if not existing:
        return jsonify({"error": "Only custom characters can be edited"}), 404

    data = parse_character_request()
    validated, error = validate_character_payload(data, editing=True, current_id=char_id)
    if error:
        return jsonify({"error": error}), 400

    if validated["character_type"] == 'historical':
        if not data.get('is_deceased', True) or data.get('is_living', False):
            return jsonify({"error": "Historical figures must be deceased"}), 400
    else:
        if not validated["source_title"]:
            return jsonify({"error": "Literary characters require a source_title"}), 400
        if not validated["source_author"]:
            return jsonify({"error": "Literary characters require a source_author"}), 400

    avatar_path = save_avatar_file(data.get('avatar'), existing_avatar=existing['avatar_path'])
    ok = update_custom_character(char_id, avatar_path=avatar_path, **validated)
    if not ok:
        return jsonify({"error": "Could not update character"}), 500
    return jsonify({"ok": True, "character": row_to_dict(get_persona_by_id(char_id))})


@app.route('/characters/<int:char_id>', methods=['DELETE'])
def remove_character(char_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401
    if not user['is_admin']:
        return jsonify({"error": "Admin privileges required"}), 403

    existing = get_character_record_by_id(char_id)
    if not existing or not existing['is_custom']:
        return jsonify({"error": "Only custom characters can be deleted"}), 404
    if hide_character(char_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Could not delete character"}), 500


@app.route('/memory/<int:char_id>', methods=['GET'])
def get_memory_endpoint(char_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401
    character = get_persona_by_id(char_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    memory = get_character_memory(user['id'], char_id)
    return jsonify({"memory": row_to_dict(memory)})


@app.route('/memory/<int:char_id>', methods=['PUT'])
def set_memory_endpoint(char_id):
    user = current_user()
    if not user:
        return jsonify({"error": "Please log in first"}), 401
    character = get_persona_by_id(char_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    data = request.get_json(silent=True) or {}
    summary = (data.get('summary') or '').strip()
    tone = (data.get('tone') or 'neutral').strip()
    last_topic = (data.get('last_topic') or '').strip()
    upsert_character_memory(user['id'], char_id, summary, tone, last_topic)
    return jsonify({"ok": True})


def parse_character_request():
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        form = request.form
        files = request.files
        return {
            "name": form.get('name', '').strip(),
            "character_type": form.get('character_type', '').strip().lower(),
            "language": form.get('language', '').strip() or 'English',
            "source_title": form.get('source_title', '').strip() or None,
            "source_author": form.get('source_author', '').strip() or None,
            "source_url": form.get('source_url', '').strip() or None,
            "bio": form.get('bio', '').strip(),
            "system_prompt": form.get('system_prompt', '').strip(),
            "is_deceased": form.get('is_deceased', 'true').lower() != 'false',
            "is_living": form.get('is_living', 'false').lower() == 'true',
            "avatar": files.get('avatar'),
        }
    data = request.get_json(silent=True) or {}
    data["avatar"] = None
    return data


def save_avatar_file(uploaded_file, existing_avatar=None):
    if not uploaded_file or not getattr(uploaded_file, 'filename', ''):
        return existing_avatar
    filename = secure_filename(uploaded_file.filename)
    if not filename or '.' not in filename:
        raise ValueError("Invalid avatar file")
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError("Avatar must be a PNG, JPG, JPEG, WEBP, or GIF file")
    uploaded_file.stream.seek(0, os.SEEK_END)
    size = uploaded_file.stream.tell()
    uploaded_file.stream.seek(0)
    if size > MAX_AVATAR_BYTES:
        raise ValueError("Avatar file is too large")
    unique_name = f"{secure_filename(Path(filename).stem)}_{os.urandom(6).hex()}.{ext}"
    dest = UPLOAD_DIR / unique_name
    uploaded_file.save(dest)
    return f"/uploads/{unique_name}"


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_user_by_id(user_id)


def public_user(user):
    if not user:
        return None
    return {
        "id": user['id'],
        "username": user['username'],
        "is_admin": bool(user['is_admin']),
    }


def public_user_from_bootstrap():
    credentials = db.BOOTSTRAP_ADMIN_CREDENTIALS
    if not credentials:
        return None
    return {
        "username": credentials['username'],
        "password": credentials['password'],
    }


def validate_character_payload(data, editing=False, current_id=None):
    name = (data.get('name') or '').strip()
    system_prompt = (data.get('system_prompt') or '').strip()
    bio = (data.get('bio') or '').strip()
    language = (data.get('language') or '').strip() or 'English'
    character_type = (data.get('character_type') or '').strip().lower()
    source_title = (data.get('source_title') or '').strip() or None
    source_author = (data.get('source_author') or '').strip() or None
    source_url = (data.get('source_url') or '').strip() or None

    if not name or not system_prompt or not bio or not language or not character_type:
        return None, "name, system_prompt, bio, language, and character_type are required"
    if len(name) > 80:
        return None, "Character name is too long"
    if not NAME_PATTERN.match(name):
        return None, "Character name contains unsupported characters"
    if character_type not in KNOWN_CHARACTER_TYPES:
        return None, "character_type must be historical or literary"

    duplicate = get_character_by_name(name)
    if duplicate and (not editing or int(duplicate['id']) != int(current_id)):
        return None, "A character with that name already exists"

    return {
        "name": name,
        "system_prompt": system_prompt,
        "bio": bio,
        "language": language,
        "character_type": character_type,
        "source_title": source_title,
        "source_author": source_author,
        "source_url": source_url,
    }, None


def row_to_dict(row):
    return dict(row) if row is not None else None


@app.route('/bootstrap-admin', methods=['GET'])
def bootstrap_admin_hint():
    credentials = db.BOOTSTRAP_ADMIN_CREDENTIALS
    if not credentials:
        return jsonify({"ok": False, "error": "bootstrap admin already claimed or unavailable"}), 404
    return jsonify({"ok": True, **credentials})


def solo_context_key(user_id, character_id):
    return f"solo:{user_id}:{character_id}"


def debate_context_key(char_id_1, char_id_2):
    return "debate:" + "|".join(map(str, sorted((char_id_1, char_id_2))))


def get_debate_temperature(name_1, name_2):
    if frozenset((name_1, name_2)) in HARSH_DISAGREEMENTS:
        return HARSH_DISAGREEMENT_TEMPERATURE
    return BASE_DEBATE_TEMPERATURE


def build_character_system_prompt(character, user_id):
    memory = get_character_memory(user_id, character['id'])
    memory_text = ""
    if memory and (memory['summary'] or memory['tone'] or memory['last_topic']):
        memory_text = (
            "\n\nUSER-CONTEXT MEMORY:\n"
            f"Summary: {memory['summary'] or 'No prior memory.'}\n"
            f"Tone: {memory['tone'] or 'neutral'}\n"
            f"Last topic: {memory['last_topic'] or 'none'}\n"
            "Remember this when responding; stay consistent with prior interactions."
        )
    return character['system_prompt'] + memory_text


def build_history_with_memory(user_id, character, context_key):
    history = get_history(user_id, [character['name']], context_key, limit=16)
    memory = get_character_memory(user_id, character['id'])
    if memory and memory['summary']:
        history.insert(0, {
            "role": "user",
            "content": (
                f"Prior relationship memory for {character['name']}: {memory['summary']}\n"
                f"Relationship tone: {memory['tone'] or 'neutral'}\n"
                f"Last topic: {memory['last_topic'] or 'none'}"
            )
        })
    return history


def build_debate_history(user_id, p1, p2, context_key, user_text, continue_flag):
    history = get_history(user_id, [p1['name'], p2['name']], context_key, limit=18)
    if not continue_flag:
        history.append({
            "role": "user",
            "content": (
                f"Debate topic: {user_text}\n"
                f"This is an animated four-turn debate between {p1['name']} and {p2['name']}. "
                "Each turn should advance the argument, rebut the previous strongest point, and sound like a real historical disagreement. "
                "Keep it persuasive, historically plausible, civil, and safe. Use prior local conversation context when it helps."
            )
        })
    return history


def update_memory_from_exchange(user_id, character, user_text, reply_text):
    lowered = user_text.lower()
    tone = "neutral"
    if any(word in lowered for word in ["idiot", "stupid", "shut up", "rude", "nonsense"]):
        tone = "wary"
    summary = f"User previously discussed {character['name']} and was {tone} during at least one exchange."
    upsert_character_memory(user_id, character['id'], summary, tone, user_text[:160])


def update_memory_from_debate(user_id, p1, p2, user_text, replies):
    tone = "neutral"
    if any(word in user_text.lower() for word in ["idiot", "stupid", "shut up", "rude"]):
        tone = "wary"
    summary = f"User staged a debate involving {p1['name']} and {p2['name']}. Tone detected: {tone}."
    upsert_character_memory(user_id, p1['id'], summary, tone, user_text[:160])
    upsert_character_memory(user_id, p2['id'], summary, tone, user_text[:160])


def build_debate_turn_instruction(turn_index, speaker_name, opponent_name, topic, speaker_language='English', opponent_language='English'):
    native_language = speaker_language or 'English'
    if turn_index == 0:
        opening = (
            f"{speaker_name}, open the debate on '{topic}' with a forceful thesis addressed to {opponent_name}. "
            "Make one clear historical argument and leave room for rebuttal."
        )
    elif turn_index == DEBATE_TURNS - 1:
        opening = (
            f"{speaker_name}, deliver the final turn. Directly answer {opponent_name}'s previous argument, "
            "tighten your strongest claim, and end with a memorable but safe closing line."
        )
    else:
        opening = (
            f"{speaker_name}, rebut {opponent_name}'s previous argument directly. "
            "Press the disagreement, cite historically plausible values or events, and add one new persuasive point."
        )

    if native_language.lower() == 'scots':
        language_rule = (
            "Write in broad Scots, not modern English. Keep Scots even if the opponent speaks modern English. "
            "Only add an English gloss if the interlocutor explicitly fails to understand."
        )
    else:
        language_rule = (
            f"Write in {native_language}. If the opponent does not understand, offer a brief English clarification after the original language."
        )

    return f"{opening} {language_rule}"


if __name__ == "__main__":
    print("Connecting to Database...")
    print("Database Ready. Starting Server...")
    app.run(debug=True, port=5000)
