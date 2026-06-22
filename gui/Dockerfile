# Frontend image: Nuxt dev server.
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV HOST=0.0.0.0 \
    PORT=3000

CMD ["npm", "run", "dev"]
