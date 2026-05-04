# Docker Data Persistence Flow (Detailed)

This system keeps data across container restarts and even container removal by using named Docker volumes. A named volume lives outside the container filesystem, so it is not destroyed when containers stop or are recreated.

## 1) High-Level Persistence Flow

```mermaid
flowchart LR
  U[User/Client] -->|docker compose up| D[Docker Engine]
  D --> C1[FastAPI Container]
  D --> C2[MongoDB Container]

  C1 -->|mounts| V1[(fastapi_data volume)]
  C2 -->|mounts| V2[(rag_mongo_db volume)]

  V1 --> H[(Host Volume Storage)]
  V2 --> H
```

What this means:

- The containers do not own the data.
- The volumes own the data.
- Containers are replaceable; volumes persist.

## 2) Lifecycle of Containers vs Volumes

```mermaid
sequenceDiagram
  participant User
  participant Docker
  participant FastAPI
  participant MongoDB
  participant Volume as Named Volume

  User->>Docker: docker compose up
  Docker->>Volume: create or reuse
  Docker->>FastAPI: start container
  Docker->>MongoDB: start container
  FastAPI->>Volume: read/write /app/assets
  MongoDB->>Volume: read/write /data/db

  User->>Docker: docker compose down
  Docker->>FastAPI: stop and remove
  Docker->>MongoDB: stop and remove
  Note over Volume: Volume stays intact

  User->>Docker: docker compose up (later)
  Docker->>Volume: reattach existing data
  Docker->>FastAPI: start container
  Docker->>MongoDB: start container
```

Key idea: docker compose down removes containers, not named volumes (unless you add -v).

## 3) Concrete Data Paths (Inside Containers)

```mermaid
flowchart TB
  subgraph FastAPI_Container
    A[/app/assets/]
  end

  subgraph MongoDB_Container
    B[/data/db/]
  end

  A --- V1[(fastapi_data)]
  B --- V2[(rag_mongo_db)]
```

Effect:

- Files written by the app to /app/assets persist.
- Database data written by MongoDB to /data/db persists.

## 4) Moving to Another Machine

Volumes live on the local Docker host. If you move the project to another machine, the named volumes do not come with the project folder automatically. You must:

1. Export the volumes from the old machine.
2. Import them into Docker on the new machine.
3. Run docker compose up to reattach the data.

```mermaid
flowchart LR
  A[Old Machine] -->|backup or export volume| B[(Volume Archive)]
  B -->|restore or import| C[New Machine]
  C -->|docker compose up| D[Containers reattach data]
```

## 5) Common Gotchas

- docker compose down -v deletes volumes (and data).
- docker system prune --volumes can remove unused volumes.
- Moving just the project folder does not move Docker volume data.
