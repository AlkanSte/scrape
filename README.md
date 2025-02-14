# Worker Log Parser

A web interface for parsing and analyzing worker log files.

## Setup

1. Clone the repository
2. Run setup script:
```bash
chmod +x setup.sh
./setup.sh
```

3. Activate virtual environment:
```bash
source venv/bin/activate
```

4. Run the application:
```bash
python app.py
```

5. Open http://localhost:5000 in your browser

## Project Structure
```
project/
├── app.py                     # Flask application
├── enhanced_worker_log_parser.py  # Log parser implementation
├── log_patterns.py           # Log pattern definitions
├── log_line.py              # Log line data structure
├── requirements.txt         # Python dependencies
├── setup.sh                # Setup script
├── uploads/                # Temporary upload directory
└── templates/              # HTML templates
    └── index.html         # Main page template
``` 