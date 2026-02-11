# GEMINI.md - Project Overview: 公文文件号管理系统

This document provides an overview of the "公文文件号管理系统" (Official Document Number Management System) project, intended as instructional context for interactions with the Gemini CLI.

## 1. Project Overview

This project is a document management system built with FastAPI and PostgreSQL, focusing on official document numbering, role-based access control, and comprehensive approval workflows.

**Purpose:** To manage official document numbering, provide a robust role-permission system, and facilitate document approval, proofreading, and lifecycle management.

**Main Technologies:**
*   **Backend:** Python 3.11+ with FastAPI
*   **Database:** PostgreSQL 15+
*   **Frontend:** (Inferred from `frontend/` directory, likely Vue.js based on `App.vue`, `main.js`, `vite.config.js`)
*   **Database Migrations:** Alembic

**Architecture Highlights:**
*   **Role-Permission System:** Defines distinct roles (USER, NUMBER_ADMIN, APPROVER, SYSTEM_ADMIN) with specific privileges.
*   **State Machine:** Manages document lifecycle (DRAFT → PROOFREADING → APPROVAL → APPROVED), including rejection and destruction flows.
*   **Modular API Design:** Organized API routes, core configurations, data models, Pydantic schemas, authentication, and utility functions within the `app/` directory.
*   **Document Management:** Features for creating, modifying, uploading Word documents.
*   **Proofreading & Approval Workflows:** Supports parallel proofreading, sequential approvals, and node-based control.
*   **Numbering Management:** Includes numbering pool, allocation, and recycling.
*   **Security:** Features like document locking, audit logs for sensitive operations, and document destruction workflows.

## 2. Building and Running

### Environment Setup

1.  **Prerequisites:**
    *   Python 3.11+
    *   PostgreSQL 15+

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Configuration:**
    *   Edit `config.yaml` to specify your PostgreSQL connection details:
        ```yaml
        database:
          url: "postgresql://user:password@localhost:5432/fawen"
        ```

4.  **Initialize Database:**
    *   Create the database (if not already existing):
        ```bash
        createdb fawen
        ```
    *   Run database migrations:
        ```bash
        alembic upgrade head
        ```
    *   Initialize data (creates default admin user: `admin`/`admin123`):
        ```bash
        python scripts/init_data.py
        ```
        **Security Note:** Change the default admin password immediately after setup.

### Starting the Application

*   **Linux / macOS (using script):**
    ```bash
    ./start.sh
    ```
*   **Windows (using script):**
    ```cmd
    start.bat
    ```
*   **Manual Start:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be available at `http://localhost:8000`. API documentation (Swagger UI, ReDoc) can be accessed at `http://localhost:8000/docs` and `http://localhost:8000/redoc` respectively.

## 3. Development Conventions

**Project Structure:**
The project follows a well-organized structure, with key directories including:
*   `app/`: Contains the core application logic, API routes, models, schemas, authentication, and utilities.
*   `docs/`: Holds design and deployment documentation.
*   `tests/`: Unit and integration tests.
*   `scripts/`: Utility scripts (e.g., data initialization).
*   `alembic/`: Database migration scripts.
*   `storage/`: Stores destroyed documents and other files.
*   `frontend/`: Contains the frontend application code (likely Vue.js).

**Coding Style & Guidelines:**
Detailed development guidelines, including data model design, state machine design, permission matrix, business process design, and security considerations, can be found in `docs/DESIGN.md`.

## 4. Testing

**Running Tests:**

1.  **Install Test Dependencies:**
    ```bash
    pip install pytest pytest-asyncio
    ```
2.  **Execute Tests:**
    ```bash
    pytest tests/
    ```

## 5. Deployment

For detailed deployment instructions, refer to the `docs/DEPLOYMENT.md` file.