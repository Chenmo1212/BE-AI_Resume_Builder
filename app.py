import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)