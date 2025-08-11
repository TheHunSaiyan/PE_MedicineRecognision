FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install && \
    npm install @mui/material @emotion/react @emotion/styled react-select && \
    npm install @mui/icons-material && \
    npm install notistack && \
    npm install material-react-table

COPY . .

ENV NODE_ENV=development

EXPOSE 2077

CMD ["npx", "next", "start", "-p", "2077", "-H", "0.0.0.0"]
