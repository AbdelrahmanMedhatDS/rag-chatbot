# Docker Setup Guide for Legal RAG Chatbot

This guide walks you through setting up and running the Legal RAG Chatbot using Docker containers with Ollama LLM running on Google Colab via ngrok.

## Prerequisites

- Docker and Docker Compose installed on your system
- A Google account (for Google Colab)
- An ngrok account (free tier works fine)
- A Cohere account (for embeddings API key)

---

## Step 1: Get Your ngrok Authentication Token

1. Go to [ngrok.com](https://ngrok.com/)
2. Click **"Sign up"** and create a free account
3. After signing in, navigate to your dashboard
4. Go to **"Your Authtoken"** section or visit directly: [https://dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken)
5. **Copy your authentication token** - you'll need this in the next step

---

## Step 2: Run Ollama LLM on Google Colab

1. **Open that** [Ollama Colab notebook](https://colab.research.google.com/drive/19-XrO71n7A0Aj_tD7f7L88giyhnmbu33?usp=sharing)

2. **In the Colab notebook:**
   - open the serects section and set your ngrok authentication token and name it `colab_ngrok` 
  (paste the token you copied from ngrok in the value field and name it `colab_ngrok` then click on the save button)  
   - Run all cells in the notebook sequentially (click "Runtime" > "Run all" in the Colab menu)
   - Wait for Ollama to download and start (this may take a few minutes)

3. **After the notebook finishes running**, you'll see an ngrok public URL in the output that looks like:
   ```
   https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app
   ```
   
4. **Copy this entire URL** - you'll need it for the environment configuration in the next step

   > **Important:** Keep the Colab notebook running! If you close it or it disconnects, the Ollama server will stop.

---

## Step 3: Configure Environment Variables

1. **Navigate to the `docker/env` directory:**
   
   On Windows (cmd):
   ```cmd
   cd docker\env
   ```
   
   On Linux:
   ```bash
   cd docker/env
   ```

2. **Copy the example environment file:**
   
   On Windows (cmd):
   ```cmd
   copy .env.example.app .env.app
   copy .env.example.grafana .env.grafana
   copy .env.example.mongodb .env.mongodb
   copy .env.example.mongodb-exporter .env.mongodb-exporter

   ```
   
   On Linux:
   ```bash
   cp .env.example.app .env.app
   cp .env.example.grafana .env.grafana
   cp .env.example.mongodb .env.mongodb
   cp .env.example.mongodb-exporter .env.mongodb-exporter

   ```

3. **Open `.env.app` in your text editor**

4. **Update the following configuration values:**

   ### LLM Configuration
   
   Set `OPENAI_API_URL` to your ngrok URL from Step 2 + `/v1`:
   
   ```env
   OPENAI_API_URL="https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app/v1"
   ```
   
   > **Note:** Make sure to add `/v1` at the end of the URL!

   ### API Keys
   
   - `OPENAI_API_KEY`: Set to any value (e.g., `"not-needed"` or `"ollama"`) since Ollama doesn't require authentication
   - `COHERE_API_KEY`: Get your free API key from [Cohere Dashboard](https://dashboard.cohere.com/api-keys) for embeddings  



5. **Save the file**

---

## Step 4: Start the Docker Containers

1. **Navigate to the docker directory:**
   
   ```cmd
   cd docker
   ```
   
2. **Start all services using Docker Compose:**
   
   ```bash
   docker compose up -d -f docker-compose.yml
   ```
   
   > The `-d` flag runs containers in detached mode (background)

3. **Wait for all containers to start.** You can check the status with:
   
   ```bash
   docker compose ps
   ```
   
   You should see:
   - `fastapi` - Running
   - `nginx` - Running
   - `mongodb` - Running (healthy)

4. **View logs to ensure everything is running correctly:**
   
   ```bash
   docker compose logs -f
   ```
   
   Press `Ctrl+C` to stop viewing logs


---

## Available Services

Once running, you'll have access to:

| Service | URL | Port | Description |
|---------|-----|------|-------------|
| **API (via Nginx)** | http://localhost | 80 | Main API endpoint (proxied through Nginx) |
| **FastAPI Direct** | http://localhost:5000 | 5000 | Direct access to FastAPI (bypassing Nginx) |
| **MongoDB** | localhost:27017 | 27017 | MongoDB database |
| **API Documentation** | http://localhost/docs | 80 | Interactive Swagger UI |


---

## Common Docker Commands

### Starting and Stopping

**Stop all containers:**
```bash
docker compose down
```

**Stop and remove all data (volumes):**
```bash
docker compose down -v
```

**Start containers:**
```bash
docker compose up -d
```

**Restart all containers:**
```bash
docker compose restart
```

**Restart a specific service:**
```bash
docker compose restart fastapi
```

### Viewing Logs

**View logs for all services:**
```bash
docker compose logs -f
```

**View logs for a specific service:**
```bash
docker compose logs -f fastapi
docker compose logs -f mongodb
docker compose logs -f nginx
```

**View last 100 lines of logs:**
```bash
docker compose logs --tail=100 fastapi
```

### Rebuilding

**Rebuild containers after code changes:**
```bash
docker compose up -d --build
```

**Rebuild a specific service:**
```bash
docker compose up -d --build fastapi
```

### Checking Status

**Check container status:**
```bash
docker compose ps
```

**Check container resource usage:**
```bash
docker stats
```
