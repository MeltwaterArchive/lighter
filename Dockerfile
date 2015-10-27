FROM alpine:latest

RUN apk -U add ca-certificates python py-yaml py-pip
RUN pip install mock

ADD src/ /src/
ADD lighter /

# Run unit tests
ADD test /
RUN /test

# Expect config directory tree to be mounted into /site
VOLUME /site
WORKDIR /site

ENTRYPOINT ["/lighter"]
