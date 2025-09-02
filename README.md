# Marketing Content Automation Platform
RAG-powered system for generating contextually-aware marketing content using company data and customer feedback.

Built on svelte-django-template - Template to build applications with SvelteKit frontend with Django backend.

## ⚠️ IMPORTANT: Protected Features (DO NOT MODIFY)
The following features are fully implemented and working. **DO NOT MODIFY THESE DURING DEVELOPMENT:**
- JWT token authentication (django-restframework-simplejwt)
- Google OAuth2 login flow  
- HttpOnly cookie management
- User registration and login endpoints
- Token refresh mechanism (automatic refresh using refresh tokens)
- SvelteKit server hooks for auth (`hooks.server.ts`)
- Proxy API endpoints with cookie headers
- Docker development setup
- PostgreSQL database configuration
- User model and authentication serializers

## Project Structure:
The project is running on separate frontend and backend modules. 
Frontend: SvelteKit application with a BFF (backend for frontend) with TailwindCSS and DaisyUI
Backend: Django Rest Framework server providing API endpoints
Database: SQLite (for now)

## Infrastructure
The template uses Docker for development to create images and containers, which can be deployed to production.
Dockerfiles are defined in the app root folders separately for frontend and backend.

### Development

Use docker-compose to orchestrate the build and run of both images and containers in parallel.
Run `docker-compose up` in the root project folder to create the containers.

### Production
Production build to be described here..

## Authentication (EXISTING - DO NOT MODIFY)
The project comes with prebuilt JWT token authentication using django-restframework-simplejwt. 
The django backend can create, verify and refresh tokens for users. The tokens are sent to SvelteKit's Nodejs server, saved in HttpOnly cookies.
A proxy API endpoint makes sure to include these cookies when sending request from the frontend application to the backend.
A SvelteKit server hook runs server side before every page load function to check for cookies.

Users can also login through OAuth2 providers like Google. This will initiate a flow that redirects to the provider. On successful authentication SvelteKit exchanges tokens with the Django backend, then sets HttpOnly cookies in the client.

## REST API (EXISTING - DO NOT MODIFY)
The frontend application can send requests to the Django backend if needed. The request is sent through a proxy, which attaches the cookie headers to the request. A
BACKEND_URL env variable must be set, which must be the root url of the django backend app. From the client you can call the `api/{path}` endpoint which will send a request to the django backend through the proxy. Currently possible requests: GET, POST

## Current Working Features
✅ User authentication (email/password)  
✅ Google OAuth2 login  
✅ Protected routes with automatic token refresh  
✅ User profile endpoint  
✅ Logout functionality  
✅ Responsive UI with DaisyUI components  
✅ Docker containerization  

## Planned Features (To Build)

### Phase 1: Data Ingestion
- [ ] Upload historical email campaigns (CSV/TXT files)
- [ ] Scrape Trustpilot reviews for social proof
- [ ] Scrape company website content for product info
- [ ] Extract and store blog posts/articles

### Phase 2: Context Configuration  
- [ ] Tone of voice parameter settings
- [ ] Brand guidelines storage interface
- [ ] Reusable context templates
- [ ] Company-specific vocabulary/terminology

### Phase 3: Content Generation
- [ ] Vector database integration for RAG
- [ ] Simple prompt interface  
- [ ] Context-aware content generation using ingested data
- [ ] Export generated content (email, social posts, marketing copy)

## Development Rules

1. **NEVER modify existing authentication logic** - JWT, OAuth, cookies all working
2. **NEVER change the User model** - extend with new models if needed
3. **NEVER alter hooks.server.ts** - auth flow is complete
4. **Build features as additions** - new endpoints, new models, new pages
5. **All new endpoints must use existing authentication** - use the `@permission_classes([IsAuthenticated])` decorator
6. **Test in Docker environment** - ensure both containers run properly
7. **Keep the proxy API pattern** - frontend calls go through `/api/` proxy

## Technical Approach for New Features

- **Data Storage**: New Django models for content storage
- **Vector Database**: Integration for RAG context storage  
- **Scraping**: Backend implementation for web data collection
- **LLM Integration**: API calls from Django backend
- **Frontend**: New SvelteKit pages under protected routes

## Environment Variables

Existing (DO NOT CHANGE):
- `BACKEND_URL` - Django backend URL
- `SECRET_KEY` - Django secret key
- `GOOGLE_CLIENT_ID` - Google OAuth client ID  
- `GOOGLE_CLIENT_SECRET` - Google OAuth secret
- `POSTGRES_*` - Database credentials

To Add:
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` - For LLM calls
- `VECTOR_DB_*` - Vector database configuration

## Getting Started

1. Clone the repository
2. Set up environment variables in `.env` files
3. Run `docker-compose up` to start both frontend and backend
4. Access the application at `http://localhost:5173`
5. Backend API available at `http://localhost:8000`