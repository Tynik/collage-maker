import io
import zmq
import base64

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

zmq_context = zmq.Context()


def call_remote_cmd(name, params, receive_format='json'):
    with zmq_context.socket(zmq.REQ) as socket:
        socket.connect('tcp://handler:5555')
        socket.send_json({'cmd': name, 'params': params})
        if receive_format == 'json':
            return socket.recv_json()
        if receive_format == 'bytes':
            return socket.recv()


@app.route('/collage/', methods=['POST'])
def make_collage():
    git_hub_key = request.headers.get('X-GitHub-Access-Key')
    if not git_hub_key:
        return jsonify({'error': 'X-GitHub-Access-Key header is required and cannot be empty'}), 400

    q = request.json['q']
    size = request.json['size']

    return jsonify(call_remote_cmd('make_collage', {'q': q, 'git_hub_key': git_hub_key, 'size': size}))


@app.route('/collage/<uuid:collage_id>/status/', methods=['GET'])
def get_collage_status(collage_id):
    return jsonify(call_remote_cmd('get_collage_status', {'id': str(collage_id)}))


@app.route('/collage/<uuid:collage_id>/info/', methods=['GET'])
def get_collage_info(collage_id):
    return jsonify(call_remote_cmd('get_collage_info', {'id': str(collage_id)}))


@app.route('/collage/<uuid:collage_id>/', methods=['GET'])
def get_collage(collage_id):
    img_data = call_remote_cmd('get_collage', {'id': str(collage_id)}, receive_format='bytes')
    return send_file(
        io.BytesIO(base64.b64decode(img_data)),
        mimetype='image/png',
        as_attachment=True,
        attachment_filename='collage.png')
