FROM alpine:latest

RUN apk -U add ca-certificates python py-yaml

ADD src/ /src/
ADD lighter /

ADD test /
RUN /test

ENTRYPOINT ["/lighter"]