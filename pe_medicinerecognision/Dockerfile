FROM node:18

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV NODE_ENV=development

EXPOSE 2077

CMD ["npx", "next", "start", "-p", "2077", "-H", "0.0.0.0"]
