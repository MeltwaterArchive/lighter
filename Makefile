all: test build verify

build:
	./build.sh

test:
	./test

verify:
	./dist/lighter-$$(uname -s)-$$(uname -m) verify src/resources/yaml/staging/myservice.yml

clean:
	rm -rf ./build ./dist

format:
	./format

.PHONY: build test verify clean format
