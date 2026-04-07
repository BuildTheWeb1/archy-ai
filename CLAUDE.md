# Archy AI

## Project Overview
Archy AI is a web-based SaaS that extracts structural data from AutoCAD DWG/DXF files
and exports it to Google Sheets or Excel. Target users are construction firms and architecture
practices who currently do this manually.

## Tech Stack

### Frontend

- **Framework**: [React 19 + TypeScript + Vite]
- **Routing**: [TanStack Router (file-based, URL-driven state)]
- **Server state**: [TanStack Query (data fetching, polling, mutations)]
- **UI components**: [shadcn/ui]
- **UI components**: [shadcn/ui]
- **Styling**: [TailwindCSS (tw: prefix convention)]
- **Linting/formatting**: [Biome]

### Backend

- **API framework**: [Python 3.12 + FastAPI]
- **DXF parsing**: [ezdxf]
- **DWG → DXF conversion**: [ODA File Converter (CLI)]
- **Task queue**: [Celery + Redis]
- **Database**: [PostgreSQL (migrations via Alembic), Supabase]
- **Object storage**: [AWS S3 / Cloudflare R2 / Supabase]
- **Auth**: [Clerk (JWT middleware on FastAPI)]
- **Excel export**: [openpyxl]
- **Google Sheets**: [Google Sheets API v4 (OAuth2 per user)]

## Project Structure

```
archy-ai/
├── backend/
│   ├── main.py           # FastAPI app + all route handlers
│   ├── extractor.py      # ezdxf DXF parsing → structured JSON
│   ├── exporter.py       # openpyxl xlsx export + Google Sheets export
│   ├── tasks.py          # Celery tasks (ODA conversion + extraction pipeline)
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic request/response schemas
│   ├── auth.py           # Clerk JWT verification middleware
│   ├── alembic/          # DB migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/       # TanStack Router file-based routes
│   │   ├── components/
│   │   │   ├── FileUpload.tsx
│   │   │   ├── LayerExplorer.tsx
│   │   │   ├── MappingBuilder.tsx
│   │   │   └── DataPreview.tsx
│   │   ├── hooks/
│   │   │   └── useExtraction.ts   # TanStack Query hooks for API calls
│   │   └── types.ts               # Shared TypeScript interfaces
│   ├── vite.config.ts
│   └── package.json
└── sample-files/         # Test DXF files for development
```

## Development Guidelines

### Do
- Write tests for new features
- Use TypeScript strict mode
- Follow existing code patterns
- Keep functions small and focused

### Don't
- Add dependencies without good reason
- Skip error handling
- Use `any` type
- Leave console.logs in production code

## Common Patterns

### API Response Format
```typescript
{
  success: boolean;
  data?: T;
  error?: string;
}
```

## Customization Tips

### For a React/Next.js Project

Add:
```markdown
## State Management
- Use React Query for server state
- Use Zustand for client state
- Avoid prop drilling - use context

## Styling
- Tailwind CSS for all styling
- Use cn() helper for conditional classes
- Design tokens in tailwind.config.ts
```

### For an API/Backend Project

Add:
```markdown
## API Design
- RESTful endpoints
- Versioning: /api/v1/...
- Auth: Bearer token in Authorization header

## Error Handling
- Use custom error classes
- Log all errors to monitoring
- Return consistent error format
```

### For a CLI Tool

Add:
```markdown

## Testing
- Unit tests for each command
- Integration tests in /tests/integration
- Mock filesystem in tests
```

## Important
Always ask clarifying questions when you think it's nedded
