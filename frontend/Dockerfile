# Frontend dev image: Vite dev server with hot reload. Source is bind-mounted by compose;
# node_modules lives in an anonymous volume so host (Windows) modules never leak in.
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
