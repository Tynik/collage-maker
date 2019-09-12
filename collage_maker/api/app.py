import io
import zmq
import base64

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

zmq_context = zmq.Context()


@app.route('/collage/', methods=['POST'])
def make_collage():
    git_hub_key = request.headers.get('X-GitHub-Access-Key')
    if not git_hub_key:
        return jsonify({'error': 'X-GitHub-Access-Key header is required and cannot be empty'}), 400

    with zmq_context.socket(zmq.REQ) as socket:
        socket.connect('tcp://handler:5555')
        socket.send_json({
            'cmd': 'make_collage',
            'params': {'q': request.json['q'], 'git_hub_key': git_hub_key, 'size': [900, 600]}})

        return jsonify(socket.recv_json())


@app.route('/collage/status/<uuid:collage_id>/', methods=['GET'])
def collage_status(collage_id):
    with zmq_context.socket(zmq.REQ) as socket:
        socket.connect('tcp://handler:5555')
        socket.send_json({'cmd': 'make_collage_status', 'params': {'id': str(collage_id)}})
        return jsonify(socket.recv_json())


@app.route('/collage/<uuid:collage_id>/', methods=['GET'])
def get_collage(collage_id):
    with zmq_context.socket(zmq.REQ) as socket:
        socket.connect('tcp://handler:5555')
        socket.send_json({'cmd': 'get_collage', 'params': {'id': str(collage_id)}})

        return send_file(
            io.BytesIO(base64.b64decode(socket.recv())),
            mimetype='image/png',
            as_attachment=True,
            attachment_filename='collage.png')
