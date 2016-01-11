all: format test build

build:
	./build.sh

test:
	./test

clean:
	rm -rf ./build ./dist

format:
	autopep8 -a -i -r .

.PHONY: build test clean format
