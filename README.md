# LiveLOL
A Discord bot that tracks League of Legends player ranks in real-time. 

## System Architecture
graph LR
    %% Actors
    Dev((Developer))
    User((Discord User))

    subgraph GH [GitHub CI/CD]
        Repo[GitHub Repo]
        Secrets[GitHub Secrets]
        Actions[Actions Runner]
    end

    subgraph AWS [AWS EC2 Instance]
        subgraph Docker [Docker Container]
            Bot[Discord Bot Core]
            Env[Environment Variables]
        end
    end

    subgraph Discord [Discord Platform]
        Server[Discord Server / Guild]
    end

    subgraph External [External Services]
        Riot{{Riot Games API}}
        Firebase[(Firestore DB)]
        Sentry{{Sentry.io}}
    end

    %% Deployment Path
    Dev -->|Push Code| Repo
    Repo -->|Trigger Build| Actions
    Secrets -->|Inject Secrets| Actions
    Actions -->|Deploy Image| Bot
    Actions -.->|Configures| Env

    %% User Interaction Path
    User -->|Sends Command| Server
    Server <-->|Event/Response| Bot

    %% Application Logic
    Bot <-->|API Request/Data| Riot
    Bot <-->|Read/Write State| Firebase
    Bot -- Telemetry/Errors --> Sentry
    Env -.->|Read at Runtime| Bot

    %% Styling
    style GH fill:#ececec,stroke:#333,stroke-width:2px,color:#000000
    style AWS fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#000000
    style Docker fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000000
    style Discord fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000000
    style External fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000000

## Core Features
1. Observability
    * Sentry Integration
    * Structured Logging
2. Asychronous API Management
    * Custom handling for Riot API 429 errors to ensure combatability with API rate limits
    * Persistent Sessions that reduce latency and resource consumption
3. Scalable Data Architecture
    * NoSQL Storage using Google Firestore
    * Hosted on AWS EC2
4. DevOps Pipeline
    * Containerization for consistent deployment
    * Github Actions workflow for CI/CD
    * Linting via Ruff enforced before every push

## Tech Stack & Design Decisions
| Category | Tool | Why this choice? |
| :--- | :--- | :--- |
| **Language** | Python 3.12 | Stable Python version with solid performance. |
| **Environment** | UV & Ruff | Chosen for dependency resolution and flexible linting. |
| **Infrastructure** | AWS EC2 & Docker | Ensures 24/7 uptime and environment parity between local dev and production. |
| **Database** | Firebase Firestore | NoSQL structure allows for flexible "tracked user" schema and real-time updates. |
| **Observability**| Sentry.io | Provides proactive error tracking and performance monitoring in the cloud. |

## Getting Started
1. Prerequisites
    * Python 3.12+
    * Docker & Docker Compose
    * Riot Games API Key - Via Riot Developer Portal
    * Firebase Credentials (Base 64 Encoded) - Via Google Firestore
    * Discord Credentials - Via Discord Developer Portal
    * Sentry Credentials - Via Sentry.io
2. Clone the repository
    * git clone [https://github.com/IanStacked/livelol.git](https://github.com/IanStacked/livelol.git)
    * cd LiveLOL
3. Install Dependencies
    * uv sync
4. Configure Environment
    * Create a .env file with your credentials
5. Run the Bot
    * docker-compose up --build

