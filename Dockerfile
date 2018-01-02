FROM alpine:3.7

RUN apk -U add ca-certificates python py-yaml py-pip gcc libffi-dev musl-dev \
               python-dev make

ADD lighter requirements.txt /app/
RUN pip install -r /app/requirements.txt

ADD src/ /app/src/
ADD lighter test common.sh setup.cfg /app/

# Run unit tests
RUN /app/test

# Expect config directory tree to be mounted into /site
VOLUME /site
WORKDIR /site

ENTRYPOINT ["/app/lighter"]
