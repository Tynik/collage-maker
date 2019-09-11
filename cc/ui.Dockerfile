FROM node:lts-alpine

WORKDIR /opt/app
RUN npm install -g http-server
COPY ./ui/package*.json ./
RUN npm install
COPY ./ui ./
CMD npm run build && npm run start