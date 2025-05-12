from app import create_app

app = create_app()

if __name__ == '__main__':
    # Development configuration for VSCode
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=True,  # Enable debug mode for VSCode
        threaded=True,  # Better for Windows performance
        use_reloader=False  # Sometimes conflicts with VSCode debugger
    )