# Files Management API

A FastAPI application for managing files in a shared directory with upload, download, and delete capabilities.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Clone the Repository](#clone-the-repository)
  - [Environment Variables Configuration](#environment-variables-configuration)
  - [Manual Deployment](#manual-deployment)
  - [Deployment with Docker](#deployment-with-docker)
  - [Deployment with GitHub Actions](#deployment-with-github-actions)
- [API Documentation](#api-documentation)
  - [Authentication](#authentication)
  - [Endpoints](#endpoints)
- [Usage Examples](#usage-examples)
  - [Curl](#curl)
  - [Python](#python)
  - [JavaScript](#javascript)

## Prerequisites

- Python 3.11 or higher
- Redis (for background tasks)
- Docker and Docker Compose (optional, for container deployment)
- VPS server (for production deployment)

## Installation

### Clone the Repository

```bash
git clone <repository-url>
cd geca-files
```

### Environment Variables Configuration

Create a `.env` file in the root of the project with the following variables:

```
API_KEY=your_secret_api_key
FILES_DIR=/var/www/public.losbarryachis.fr/public/shared
REDIS_URL=redis://redis:6379/0
```

### Manual Deployment

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start the application:

```bash
uvicorn app:app --host 0.0.0.0 --port 5000
```

3. Start the Celery worker (in a separate terminal):

```bash
celery -A app worker --loglevel=info
```

### Deployment with Docker

1. Build and start the containers:

```bash
docker compose build
docker compose up -d
```

The API will be accessible at `http://localhost:7000`.

### Deployment with GitHub Actions

The GitHub Actions workflow is configured to automatically deploy the application to a VPS when changes are pushed to the `main` branch.

To configure automatic deployment, add the following secrets to your GitHub repository:

- `SSH_PRIVATE_KEY`: Your SSH private key
- `SSH_HOST`: The IP address or hostname of your VPS
- `SSH_PORT`: The SSH port of your VPS (usually 22)
- `SSH_USER`: Your SSH username
- `API_KEY`: The API key for authentication

## API Documentation

### Authentication

All API requests must include an `X-API-KEY` header with the API key specified in the `.env` file.

### Endpoints

#### GET /

Verify that the API is working correctly.

**Response:**

```json
{
  "message": "File Management API is running",
  "status": 200
}
```

#### GET /health

Check the health status of the API.

**Response:**

```json
{
  "status": "healthy"
}
```

#### GET /files

List all files and directories in the shared directory.

**Query Parameters:**
- `directory` (optional): Subdirectory to list

**Response:**

```json
{
  "data": [
    {
      "name": "example.jpg",
      "path": "example.jpg",
      "size": 12345,
      "modified": 1619712345.6789,
      "is_file": true
    },
    {
      "name": "documents",
      "path": "documents",
      "modified": 1619712345.6789,
      "is_file": false
    }
  ]
}
```

#### POST /files/upload

Upload a file to the shared directory.

**Form Data:**
- `file`: The file to upload
- `directory` (optional): Subdirectory to upload to

**Response:**

```json
{
  "filename": "example.jpg",
  "path": "example.jpg",
  "status": "success"
}
```

#### GET /files/{file_path}

Download a file from the shared directory.

**Parameters:**
- `file_path`: Path to the file relative to the shared directory

**Response:**
The file content with appropriate content type.

#### DELETE /files/{file_path}

Delete a file or directory from the shared directory.

**Parameters:**
- `file_path`: Path to the file or directory relative to the shared directory

**Response:**

```json
{
  "status": "success",
  "message": "File example.jpg deleted"
}
```

## Usage Examples

### Curl

```bash
# Check if the API is working
curl -X GET "http://localhost:7000/" \
  -H "X-API-KEY: your_api_key"

# List files
curl -X GET "http://localhost:7000/files" \
  -H "X-API-KEY: your_api_key"

# Upload a file
curl -X POST "http://localhost:7000/files/upload" \
  -H "X-API-KEY: your_api_key" \
  -F "file=@/path/to/local/file.jpg"

# Download a file
curl -X GET "http://localhost:7000/files/example.jpg" \
  -H "X-API-KEY: your_api_key" \
  --output downloaded_file.jpg

# Delete a file
curl -X DELETE "http://localhost:7000/files/example.jpg" \
  -H "X-API-KEY: your_api_key"
```

### Python

```python
import requests

API_URL = "http://localhost:7000"
API_KEY = "your_api_key"
HEADERS = {"X-API-KEY": API_KEY}

# Check if the API is working
response = requests.get(f"{API_URL}/", headers=HEADERS)
print(response.json())

# List files
response = requests.get(f"{API_URL}/files", headers=HEADERS)
files = response.json()
print(files)

# Upload a file
with open('/path/to/local/file.jpg', 'rb') as f:
    response = requests.post(
        f"{API_URL}/files/upload",
        headers=HEADERS,
        files={"file": f}
    )
print(response.json())

# Download a file
response = requests.get(
    f"{API_URL}/files/example.jpg",
    headers=HEADERS
)
with open('downloaded_file.jpg', 'wb') as f:
    f.write(response.content)

# Delete a file
response = requests.delete(
    f"{API_URL}/files/example.jpg",
    headers=HEADERS
)
print(response.json())
```

### JavaScript

```javascript
const API_URL = "http://localhost:7000";
const API_KEY = "your_api_key";
const HEADERS = {
  "X-API-KEY": API_KEY
};

// Check if the API is working
fetch(`${API_URL}/`, {
  headers: HEADERS
})
.then(response => response.json())
.then(data => console.log(data));

// List files
fetch(`${API_URL}/files`, {
  headers: HEADERS
})
.then(response => response.json())
.then(data => console.log(data.data));

// Upload a file (in browser)
async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch(`${API_URL}/files/upload`, {
    method: "POST",
    headers: {
      "X-API-KEY": API_KEY
    },
    body: formData
  });
  
  return await response.json();
}

// Delete a file
fetch(`${API_URL}/files/example.jpg`, {
  method: "DELETE",
  headers: HEADERS
})
.then(response => response.json())
.then(data => console.log(data));
```

## File Types

The API accepts the following file types:
- Images: png, jpg, jpeg, gif
- Documents: txt, pdf, doc, docx, xls, xlsx
- Media: mp4, webm
- Archives: zip

You can modify the allowed file types in the `ALLOWED_EXTENSIONS` variable in the code.