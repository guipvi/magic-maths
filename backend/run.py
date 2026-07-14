"""
Application entrypoint. Run with: python run.py
Creates the Flask app and starts the dev server on port 5555.
For production, use: gunicorn -w 4 -b 0.0.0.0:5555 run:app
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5555)
