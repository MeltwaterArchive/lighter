all: build test

build:
	./build.sh

test:
	./test

clean:
	rm -rf ./build ./dist

.PHONY: build test clean
