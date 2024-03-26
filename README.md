# AWS Credentials Detector

Detects hardcoded AWS credentials in a local git repository.

## Prerequisites

- Python 3.8+ (for running in a virtual environment)
- Docker (for running in a container)
- Git

## Installation & Running Instructions

### Using Python Virtual Environment

1. Clone this repository and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
    ```bash
   pip install -r requirements.txt
   ```
4. Run the tool:
   ```bash
   python detect.py /path/to/local/repo
   ```

### Using Docker
1. Build the docker image
   ```bash
   docker build -t aws-credentials-detector .
   ```
2. Run the tool in Docker, mounting the local repository:
   ```bash
   docker run --rm -v /path/to/local/repo:/usr/src/app/repo aws-credentials-detector /usr/src/app/repo
   ```

