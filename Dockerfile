FROM alpine:latest

RUN apk -U add python py-yaml

ADD lighter.py /

ADD test.py /
ADD test /test/
RUN /test.py

ENTRYPOINT ["/lighter.py"]