all: format test build

build:
	./build.sh

test:
	./test

clean:
	rm -rf ./build ./dist

format:
	./format

.PHONY: build test clean format
