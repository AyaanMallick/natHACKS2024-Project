from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
from camera import VideoCamera
import eventlet  # Make sure eventlet is imported

# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')  # Specify async_mode as eventlet

@app.route('/')
def index():
    return render_template('index.html')  # Make sure this is an HTML file

def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# This will handle alerts sent from the backend
@socketio.on('alert')
def handle_alert(data):
    print(f"Alert received: {data['message']}")
    emit('alert', {'message': data['message']})

if __name__ == '__main__':
    # Running Flask with SocketIO support and eventlet for async operations
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False)
