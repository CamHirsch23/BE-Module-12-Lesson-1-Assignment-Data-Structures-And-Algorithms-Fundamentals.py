# server.py (Python backend using Flask and Flask-SocketIO)
"""Module for a text messaging app server using Flask and Flask-SocketIO."""

import time
from collections import defaultdict, deque
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, emit
from sortedcontainers import SortedList

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# In-memory data structures for demonstration purposes
messages = defaultdict(deque)  # Stores messages for each conversation
conversations = SortedList(key=lambda x: -x['last_message_time'])  # Sorted list of conversations


@app.route('/send-message', methods=['POST'])
def send_message():
    """Endpoint for sending a message and emitting it to a conversation room."""
    data = request.json
    message = {
        'text': data['message'],
        'timestamp': time.time(),
        'sender': data['sender']
    }
    conversation_id = data['conversationId']

    # Store the message in the appropriate data structure
    messages[conversation_id].append(message)

    # Update conversation metadata
    conversation_metadata = next(
        (item for item in conversations if item['id'] == conversation_id), None
    )
    if conversation_metadata:
        conversations.remove(conversation_metadata)
        conversation_metadata['last_message_time'] = message['timestamp']
        conversations.add(conversation_metadata)
    else:
        conversations.add({
            'id': conversation_id,
            'last_message_time': message['timestamp']
        })

    # Emit the message to the conversation room
    socketio.emit('new_message', message, room=conversation_id)

    return jsonify({'status': 'Message sent'}), 200


@socketio.on('join_conversation')
def handle_join_conversation(conversation_id):
    """WebSocket event for joining a conversation."""
    join_room(conversation_id)


@socketio.on('new_message')
def handle_new_message(data):
    """WebSocket event for handling a new message."""
    conversation_id = data['conversationId']
    message = {
        'text': data['text'],
        'timestamp': time.time(),
        'sender': data['sender']
    }

    # Store the message in the appropriate data structure
    messages[conversation_id].append(message)

    # Update conversation metadata
    conversation_metadata = next(
        (item for item in conversations if item['id'] == conversation_id), None
    )
    if conversation_metadata:
        conversations.remove(conversation_metadata)
        conversation_metadata['last_message_time'] = message['timestamp']
        conversations.add(conversation_metadata)
    else:
        conversations.add({
            'id': conversation_id,
            'last_message_time': message['timestamp']
        })

    emit('new_message', message, room=conversation_id)


@app.route('/conversations', methods=['GET'])
def get_conversations():
    """Endpoint to get the list of conversations."""
    return jsonify({'conversations': list(conversations)}), 200


@app.route('/messages/<conversation_id>', methods=['GET'])
def get_messages(conversation_id):
    """Endpoint to get messages for a specific conversation."""
    conv_messages = list(messages[conversation_id])
    conv_messages.reverse()  # Show latest messages first
    return jsonify({'messages': conv_messages}), 200


if __name__ == '__main__':
    socketio.run(app, debug=True)
