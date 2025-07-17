from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, join_room, emit
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import base64
import logging
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'
# Use threading for better performance (or eventlet/gevent if installed)
socketio = SocketIO(app, async_mode="threading")

# Configure logging (set to WARNING for less overhead in production)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
app.logger.setLevel(logging.WARNING) # Set to WARNING for production, INFO for detailed debugging

# MongoDB setup
try:
    client = MongoClient("mongodb+srv://<username>:<db_password>cluster1.nykrkvq.mongodb.net/?retryWrites=true&w=majority")# Replace <username> and <db_password> with your actual username and password
    db = client["chat_db"]
    messages = db["messages"]
    dba = client["travis_db"]
    users = dba["users"]
    responses = dba["intent_responses"]
    app.logger.info("MongoDB connected successfully.")
except Exception as e:
    app.logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
    # In a real application, you might want to exit or show an error page
    # For now, we'll allow the app to run but log the error.

# In-memory tracking (consider using a more persistent store for production if needed)
online_customers = set()

# IMPORTANT: Ensure this URL is EXACTLY correct from your ngrok output, no trailing spaces!
# This URL will change every time you restart ngrok in Colab.

# Updated ngrok URL as per user's request
COLAB_URL = "https://9fe110d854d2.ngrok-free.app"

# Add route for About page
@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'customer':
        return redirect(url_for('chat_customer'))
    else:
        return redirect(url_for('chat_agent'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']     
        role = request.form['role']
        language = request.form['language']

        if users.find_one({'username': username}):
            message = "❌ User already exists!"
        else:
            hashed_pw = generate_password_hash(password)
            users.insert_one({
                'username': username,
                'password': hashed_pw,
                'role': role,
                'language': language,
                'is_online': False
            })
            message = "✅ Registration successful! Please login."
            return render_template('login.html', message=message)

    return render_template('register.html', message=message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username})

        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            session['language'] = user.get('language', 'en')

            if user['role'] == 'customer':
                online_customers.add(username)
                users.update_one({'username': username}, {'$set': {'is_online': True}})
                # Notify all agents that a customer is online
                socketio.emit('customer_status', {'username': username, 'status': 'online'})
                return redirect(url_for('chat_customer'))
            else:
                return redirect(url_for('chat_agent'))
        else:
            message = "❌ Invalid username or password!"

    return render_template('login.html', message=message)


@app.route('/logout')
def logout():
    username = session.get('username')
    role = session.get('role')

    if role == 'customer':
        online_customers.discard(username)
        users.update_one({'username': username}, {'$set': {'is_online': False}})
        # Notify all agents that a customer went offline
        socketio.emit('customer_status', {'username': username, 'status': 'offline'})

    session.clear()
    return redirect(url_for('login'))


@app.route('/chat/customer')
def chat_customer():
    if 'username' not in session or session['role'] != 'customer':
        return redirect(url_for('login'))
    # Pass the user's language to the template
    return render_template('chat_customer.html', username=session['username'], user_language=session.get('language', 'en'))


@app.route('/chat/agent')
def chat_agent():
    if 'username' not in session or session['role'] != 'agent':
        return redirect(url_for('login'))
    online = users.find({'role': 'customer', 'is_online': True})
    online_customers_list = [c['username'] for c in online]
    return render_template('chat.html', username=session['username'], customers=online_customers_list)


@socketio.on('join')
def handle_join(data):
    room = data['room']
    username = data['username']

    join_room(room)

    # Fetch last 100 messages for faster load, sorted by timestamp
    # Using a projection to only fetch necessary fields can also improve performance
    history_cursor = messages.find({"room": room}).sort("timestamp", 1).limit(100)
    history_list = []

    user_in_session = users.find_one({'username': username})
    user_role = user_in_session['role'] if user_in_session else None
    user_lang = user_in_session.get('language', 'en') if user_in_session else 'en'

    for msg in history_cursor:
        if 'username' in msg and 'message' in msg:
            original_sender = msg['username']
            original_message_text = msg['message']
            intent_val = msg.get('intent', None)
            detected_lang_code = msg.get('detected_lang_code', 'eng_Latn')
            translated_text = msg.get('translated_text', original_message_text)

            display_text = original_message_text
            speech_text = original_message_text
            message_lang = 'en'

            if user_role == 'agent':
                if original_sender != username and original_sender != 'Agent' and original_sender != 'AI':
                    display_text = f"<b>{original_sender}</b> (original {detected_lang_code.split('_')[0]}): {original_message_text}<br>(translated): {translated_text}"
                    if intent_val and intent_val not in ['unknown', 'error_classifier']:
                        display_text += f"<br>(intent: {intent_val})"
                    speech_text = translated_text
                    message_lang = 'en'
                elif original_sender == 'Agent':
                    display_text = f"<b>Agent:</b> {original_message_text}"
                    speech_text = original_message_text
                    message_lang = 'en'
                elif original_sender == 'AI':
                    display_text = f"<b>AI:</b> {original_message_text}"
                    speech_text = original_message_text
                    message_lang = 'en'
                else:
                    display_text = f"<b>{original_sender}:</b> {original_message_text}"
                    speech_text = original_message_text
                    message_lang = 'en'
            elif user_role == 'customer':
                if original_sender == 'Agent' or original_sender == 'AI':
                    code = "hin_Deva" if user_lang == "hi" else "tel_Telu" if user_lang == "te" else "eng_Latn"
                    try:
                        resp = requests.post(f"{COLAB_URL}/translate", json={
                            "text": original_message_text,
                            "target_lang": code
                        })
                        resp.raise_for_status()
                        translated_customer = resp.json().get('translation', original_message_text)
                        display_text = f"<b>{original_sender}</b> (original): {original_message_text}<br>(translated): {translated_customer}"
                        speech_text = translated_customer
                        message_lang = user_lang
                    except Exception as e:
                        app.logger.error(f"Error translating {original_sender} history message for customer: {e}")
                        display_text = f"<b>{original_sender}</b> (translation error): {original_message_text}"
                        speech_text = original_message_text
                        message_lang = user_lang
                else:
                    display_text = f"<b>{original_sender}:</b> {original_message_text}"
                    speech_text = original_message_text
                    message_lang = user_lang
            history_list.append({
                "sender": original_sender,
                "original_text": original_message_text,
                "display_text": display_text,
                "speech_text": speech_text,
                "message_lang": message_lang,
                "intent": intent_val
            })
        else:
            app.logger.warning(f"Skipping malformed message in history (missing 'username' or 'message'): {msg}")
    emit('history', history_list, room=request.sid)


@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = data['username']
    text = data['message']
    mode = data.get('mode', 'ai')

    intent_val = None # Initialize intent

    customer_user_data = users.find_one({'username': username})
    customer_lang = customer_user_data.get('language', 'en') if customer_user_data else 'en'

    # Detect language, translate, and classify ONCE, and store all in DB
    detected_lang_code = 'eng_Latn'
    translated_for_agent = text
    # Detect language
    try:
        detect_resp = requests.post(f"{COLAB_URL}/detect_language", json={"text": text})
        detect_resp.raise_for_status()
        detected_lang_code = detect_resp.json().get('lang', 'eng_Latn')
    except Exception as e:
        app.logger.error(f"Error detecting language: {e}")
        detected_lang_code = 'eng_Latn'
    # Translate
    if customer_lang != 'en':
        try:
            resp = requests.post(f"{COLAB_URL}/translate", json={
                "text": text,
                "target_lang": "eng_Latn"
            })
            resp.raise_for_status()
            translated_for_agent = resp.json().get('translation', text)
        except Exception as e:
            app.logger.error(f"Error calling translation API for customer message to agent: {e}")
            translated_for_agent = f"Translation error: {text}"
    # Classify
    try:
        response = requests.post(f"{COLAB_URL}/classify", json={"message": text})
        response.raise_for_status()
        intent_val = response.json().get('intent', 'unknown')
    except Exception as e:
        app.logger.error(f"Error calling classifier API for customer message: {e}")
        intent_val = 'error_classifier'

    # Store all info in DB for fast history fetch
    messages.insert_one({
        "room": room,
        "username": username,
        "message": text,
        "timestamp": datetime.utcnow(),
        "intent": intent_val,
        "detected_lang_code": detected_lang_code,
        "translated_text": translated_for_agent
    })

    # Prepare display and speech text for agent's view of customer message
    agent_display_text = f"<b>{username}</b> (original {detected_lang_code.split('_')[0]}): {text}<br>(translated): {translated_for_agent}"
    if intent_val and intent_val not in ['unknown', 'error_classifier']:
        agent_display_text += f"<br>(intent: {intent_val})"
    agent_speech_text = translated_for_agent

    # Emit to customer only if the sender is a customer (right side for customer)
    # The customer sees their own message as plain text, no translation needed for display
    emit('new_message', {
        "sender": username,
        "original_text": text,
        "display_text": f"<b>{username}:</b> {text}", # Customer's own message, no translation for display
        "speech_text": text, # Customer's own message, spoken in their language
        "message_lang": customer_lang,
        "intent": None
    }, room=request.sid)

    # Emit to agent(s) only (left side for agent)
    emit('new_message', {
        "sender": username,
        "original_text": text,
        "display_text": agent_display_text,
        "speech_text": agent_speech_text,
        "message_lang": 'en', # Agent will read this in English
        "intent": intent_val
    }, room=room, include_self=False)


    if mode == 'ai':
        # Emit AI typing indicator to customer before generating the reply
        emit('ai_typing', {}, room=request.sid)

        doc = responses.find_one({'intent': intent_val})
        ai_reply = doc['response'] if doc else "Sorry, I don’t know how to answer that."

        # Store AI's reply in the database (original English)
        messages.insert_one({
            "room": room,
            "username": "AI",
            "message": ai_reply,
            "timestamp": datetime.utcnow(),
            "intent": intent_val # Store intent with AI message
        })

        # Emit AI's reply to the customer's view (translated if necessary, left side)
        translated_ai_reply = ai_reply
        if customer_lang != 'en':
            code = "hin_Deva" if customer_lang == "hi" else "tel_Telu" if customer_lang == "te" else "eng_Latn"
            try:
                resp = requests.post(f"{COLAB_URL}/translate", json={
                    "text": ai_reply,
                    "target_lang": code
                })
                resp.raise_for_status()
                translated_ai_reply = resp.json().get('translation', ai_reply)
            except requests.exceptions.RequestException as e:
                app.logger.error(f"Error translating AI reply for customer: {e}")
                translated_ai_reply = f"AI (translation error): {ai_reply}"

        # Prepare display and speech text for AI message for customer
        customer_ai_display_text = f"<b>AI</b> (original): {ai_reply}<br>(translated): {translated_ai_reply}"
        customer_ai_speech_text = translated_ai_reply

        # Emit to the customer only (not to the room)
        emit('new_message', {
            "sender": "AI",
            "original_text": ai_reply,
            "display_text": customer_ai_display_text,
            "speech_text": customer_ai_speech_text,
            "message_lang": customer_lang, # AI message language for customer
            "intent": intent_val
        }, room=request.sid)

        # Prepare display and speech text for AI message for agent (always English)
        agent_ai_display_text = f"<b>AI:</b> {ai_reply}"
        agent_ai_speech_text = ai_reply

        # Emit to agent(s) only (not to the customer again)
        emit('new_message', {
            "sender": "AI",
            "original_text": ai_reply,
            "display_text": agent_ai_display_text,
            "speech_text": agent_ai_speech_text,
            "message_lang": 'en', # AI message language for agent
            "intent": intent_val
        }, room=room, include_self=False)


@socketio.on('agent_message')
def handle_agent_message(data):
    room = data['room']
    message = data['message']
    agent_name = session.get('username', 'Agent')

    # Store the original message in the database
    messages.insert_one({
        "room": room,
        "username": agent_name,
        "message": message,
        "timestamp": datetime.utcnow(),
        "intent": None # Agent's messages don't have an intent from classification
    })

    # Emit the original message to the agent's own view (right side for agent)
    emit('new_message', {
        "sender": agent_name,
        "original_text": message,
        "display_text": f"<b>Agent:</b> {message}", # Agent's own message, no translation needed for display
        "speech_text": message,
        "message_lang": 'en', # Agent's own message is in English
        "intent": None
    }, room=request.sid)

    # Translate agent's message to the customer's language for the customer's view
    customer_name = room.replace('room_', '')
    customer = users.find_one({'username': customer_name})
    customer_lang = customer['language'] if customer else 'en'

    translated_for_customer = message
    if customer_lang != 'en':
        code = "hin_Deva" if customer_lang == "hi" else "tel_Telu" if customer_lang == "te" else "eng_Latn"
        try:
            resp = requests.post(f"{COLAB_URL}/translate", json={
                "text": message,
                "target_lang": code
            })
            resp.raise_for_status()
            translated_for_customer = resp.json().get('translation', message)
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error calling translation API for agent message to customer: {e}")
            translated_for_customer = f"Translation error: {message}"

    # Prepare display and speech text for customer's view of agent message
    customer_display_text = f"<b>Agent</b> (original): {message}<br>(translated): {translated_for_customer}"
    customer_speech_text = translated_for_customer

    # Emit the translated message to the customer's room (left side for customer)
    emit('new_message', {
        "sender": agent_name,
        "original_text": message,
        "display_text": customer_display_text,
        "speech_text": customer_speech_text,
        "message_lang": customer_lang, # Agent's message language for customer
        "intent": None
    }, room=room)


@socketio.on('transcribe_audio')
def handle_transcribe_audio(data):
    audio_base64 = data.get('audio')
    lang = data.get('lang', 'en')  # Get language from frontend

    if not audio_base64:
        app.logger.error("Received transcribe_audio event with no 'audio' data.")
        emit('transcribed_text', {'text': 'Error: No audio data received.'}, room=request.sid)
        return

    try:
        audio_bytes = base64.b64decode(audio_base64)
        app.logger.info(f"Decoded audio bytes length: {len(audio_bytes)}")

        audio_file_object = BytesIO(audio_bytes)
        audio_file_object.name = "audio.webm"

        files_to_send = {
            'audio': (audio_file_object.name, audio_file_object, 'audio/webm')
        }
        data_to_send = {
            'lang': lang
        }

        app.logger.info(f"Sending audio as multipart/form-data to Colab /transcribe: {COLAB_URL}/transcribe with lang={lang}")
        response = requests.post(f"{COLAB_URL}/transcribe", files=files_to_send, data=data_to_send)
        response.raise_for_status()

        transcribed_data = response.json()
        transcribed_text = transcribed_data.get('text', '')
        if not transcribed_text:
            app.logger.warning("Colab /transcribe endpoint returned no text.")
            emit('transcribed_text', {'text': 'Transcription returned empty.'}, room=request.sid)
            return

        app.logger.info(f"Transcription successful: {transcribed_text[:50]}...")
        emit('transcribed_text', {'text': transcribed_text}, room=request.sid)
    except requests.exceptions.HTTPError as e:
        error_message = f"HTTP Error {e.response.status_code}: {e.response.text}"
        app.logger.error(f"Error calling transcribe API: {error_message}")
        emit('transcribed_text', {'text': f'Transcription Error: {error_message}'}, room=request.sid)
    except Exception as e:
        app.logger.error(f"An unexpected error occurred during transcription: {e}", exc_info=True)
        emit('transcribed_text', {'text': 'Transcription Error: An unexpected server error occurred.'}, room=request.sid)

@socketio.on('clear_chat_history')
def handle_clear_chat_history(data):
    room = data.get('room')
    if room:
        try:
            result = messages.delete_many({"room": room})
            app.logger.info(f"Cleared {result.deleted_count} messages from room: {room}")
            # Optionally, emit a confirmation back to the client
            emit('chat_history_cleared', {'room': room, 'count': result.deleted_count}, room=request.sid)
        except Exception as e:
            app.logger.error(f"Error clearing chat history for room {room}: {e}")
            emit('chat_history_clear_error', {'room': room, 'error': str(e)}, room=request.sid)
    else:
        app.logger.warning("Received clear_chat_history with no room specified.")


if __name__ == '__main__':
    socketio.run(app, debug=True)


