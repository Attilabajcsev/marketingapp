# svelte-django-template
Template to build applications with SvelteKit frontend with Django backend

## Project Structure:
The project is running on separate frontend and backend modules. 
Frontend: SvelteKit application with a BFF (backend for frontend) with TailwindCSS and DaisyUI
Backend: Django Rest Framework server providing API endpoints
Database: SQLite (for now)

## Infrastucture
The template uses Docker for development to create images and containers, which can be deployed to production.
Dockerfiles are defined in the app root folders separately for frontend and backend.

### Development

Use docker-compose to orchastrate the build and run of both images and containers in parallel.
Run `docker-compose up` in the root project folder to create the containers.

### Production
Production build to be described here..

## Authentication
The project comes with prebuilt JWT token authentication using django-restframework-simplejwt. 
The django backend can create, verify and refresh tokens for users. The tokens are sent to SvelteKit's Nodejs server, saved in HttpOnly cookies.
A proxy API endpoint makes sure to include these cookies when sending request from the frontend application to the backend.
A SvelteKit server hook runs server side before every page load function to check for cookies.

Users can also login through OAuth2 providers like Google. This will initiate a flow that redirects to the provider. On successfull authentication SvelteKit exchanges tokens with the Django backend, then sets HttpOnly cookies in the client.

## REST API
The frontend application can send requests to the Django backend if needed. The request is sent through a proxy, which attaches the cookie headers to the request. A
BACKEND_URL env variable must be set, which must be the root url of the django backend app. From the client you can call the `api/{path}` endpoint which will send a request to the django backend through the proxy. Currently possible requests: GET, POST 
