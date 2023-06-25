FROM python:3.11-alpine

RUN apk add --no-cache gcc libc-dev libffi-dev zlib-dev openssl-dev jpeg-dev ffmpeg freetype-dev
RUN apk add --no-cache make

WORKDIR /usr/bmas

COPY . ./
RUN make setup

COPY . .

EXPOSE 8088

CMD [ "make", "run" ]