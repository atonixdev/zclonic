from app import create_app  # or from core if you renamed app.py to core.py

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)