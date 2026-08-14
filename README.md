                    USER
                      │
                      ▼
              GitHub OAuth Login
                      │
                      ▼
                FastAPI API
                      │
                      ▼
             Select GitHub Repo
                      │
                      ▼
              Ingestion Pipeline
                      │
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
    File Filter    AST Parser    Metadata
        │             │              │
        └─────────────┼──────────────┘
                      ▼
                 Code Chunks
                      │
                      ▼
              Embedding Generator
                      │
                      ▼
              PostgreSQL/pgvector
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
     Vector Search           Dependency Graph
          │                        │
          └───────────┬────────────┘
                      ▼
                 RAG Pipeline
                      │
              ┌───────┴────────┐
              ▼                ▼
           Retriever         Reranker
              │                │
              └───────┬────────┘
                      ▼
                Context Builder
                      │
                      ▼
                  Groq LLM
                      │
                      ▼
                Final Answer





--------------------------------------------------------------------------






RepoRAG — Endpoint Execution Roadmap
1. Authentication

1. GET /api/v1/auth/github/login

No input

2. GET /api/v1/auth/github/callback

Query:
code=<GitHub_OAuth_code>

Example:

code=cdf8a76be338ccd93a9c

3. GET /api/v1/auth/me

Header:
Authorization: Bearer <RepoRAG_JWT>

4. POST /api/v1/auth/logout

Header:
Authorization: Bearer <RepoRAG_JWT>
2. Repositories

5. GET /api/v1/repositories

Header:
Authorization: Bearer <RepoRAG_JWT>

6. POST /api/v1/repositories

Header:
Authorization: Bearer <RepoRAG_JWT>
Body:
{
  "github_repo_id": 1059826317,
  "full_name": "SujayKumarMondal/ChatBot-FastAPI-NextJS"
}

7. GET /api/v1/repositories/{repository_id}

Path:
repository_id=<RepoRAG_repository_UUID>
Header:
Authorization: Bearer <RepoRAG_JWT>

Example:

repository_id=550e8400-e29b-41d4-a716-446655440000
3. Ingestion

8. POST /api/v1/repositories/{repository_id}/ingest

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>

9. GET /api/v1/repositories/{repository_id}/ingestion-status

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
4. Repository Files

10. GET /api/v1/repositories/{repository_id}/files

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>

11. GET /api/v1/repositories/{repository_id}/files/{file_id}

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
file_id=<file_UUID>
Header:
Authorization: Bearer <RepoRAG_JWT>
5. Symbols

12. GET /api/v1/repositories/{repository_id}/symbols

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
6. Dependencies

13. GET /api/v1/repositories/{repository_id}/dependencies

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
7. Search / RAG

14. POST /api/v1/repositories/{repository_id}/search

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
Body:
{
  "query": "Where is authentication implemented?"
}

Another:

{
  "query": "How does the application start?"
}
8. Chat

15. POST /api/v1/repositories/{repository_id}/chat

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
Body:
{
  "message": "Explain the payment flow."
}
9. Analysis

16. GET /api/v1/repositories/{repository_id}/analysis

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
10. Dependency Graph

17. GET /api/v1/repositories/{repository_id}/graph

Path:
repository_id=550e8400-e29b-41d4-a716-446655440000
Header:
Authorization: Bearer <RepoRAG_JWT>
Execution Order
1.  GET  /api/v1/auth/github/login
        ↓
2.  GET  /api/v1/auth/github/callback?code=<code>
        ↓
3.  GET  /api/v1/auth/me
        ↓
4.  GET  /api/v1/repositories
        ↓
5.  POST /api/v1/repositories
        ↓
6.  GET  /api/v1/repositories/{repository_id}
        ↓
7.  POST /api/v1/repositories/{repository_id}/ingest
        ↓
8.  GET  /api/v1/repositories/{repository_id}/ingestion-status
        ↓
9.  GET  /api/v1/repositories/{repository_id}/files
        ↓
10. GET  /api/v1/repositories/{repository_id}/files/{file_id}
        ↓
11. GET  /api/v1/repositories/{repository_id}/symbols
        ↓
12. GET  /api/v1/repositories/{repository_id}/dependencies
        ↓
13. POST /api/v1/repositories/{repository_id}/search
        ↓
14. POST /api/v1/repositories/{repository_id}/chat
        ↓
15. GET  /api/v1/repositories/{repository_id}/analysis
        ↓
16. GET  /api/v1/repositories/{repository_id}/graph
        ↓
17. POST /api/v1/auth/logout

Important: repository_id is the RepoRAG database UUID, e.g. 550e8400-e29b-41d4-a716-446655440000, not GitHub's numeric repository ID 1059826317.