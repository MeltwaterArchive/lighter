all: format test build

build:
	./build.sh

test:
	./test

clean:
	rm -rf ./build ./dist

format:
	autopep8 -a -i -r --max-line-length=160 --ignore E301,E302,E309 .

.PHONY: build test clean format
