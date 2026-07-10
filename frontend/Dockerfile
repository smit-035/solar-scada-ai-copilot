# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package configs
COPY package*.json ./

# Install packages
RUN npm install

# Copy source code
COPY . .

# Build production bundle
RUN npm run build

# Nginx production stage
FROM nginx:stable-alpine

# Copy built assets to Nginx default folder
COPY --from=build /app/dist /usr/share/nginx/html

# Expose Nginx port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
