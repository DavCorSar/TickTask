# TickTask

⚠️ **This project is currently under active development and not yet ready for production use. Expect changes, bugs, and incomplete features.**

**TickTask** is a web application designed to clock in/out and track time spent on various tasks. It's built with a modern stack: Django + Django Ninja for the backend and Nuxt + Vuetify for the frontend.

---

# Installation Steps

## Backend: Django + Django Ninja

```sh
uv add django django-ninja django-cors-headers
```

Initialize the project:

```sh
uv run django-admin startproject ticktask .
uv run python manage.py startapp api
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

### Run backend

```sh
uv run python manage.py runserver
```

## Frontend: Nuxt + Vuetify

```sh
npx nuxi@latest init gui
cd gui
npm install
```

### Disable SSR

```ts
export default defineNuxtConfig({
  ssr: false,
});
```

### Add Vuetify

Use the official module to add Vuetify:

```sh
npx nuxi@latest module add vuetify-nuxt-module
```

### Run frontend

```sh
npm run dev
```

### Run celery

To run the celery app, first we need to make sure that `redis` is installed using:

```sh
docker run -d --name redis -p 6379:6379 redis:7
```

then we need to run in a first terminal:

```sh
celery -A ticktask worker -l info
```

and in a diferent terminal:

```sh
celery -A ticktask worker -l info
```
