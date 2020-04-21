#!/usr/bin/env bash
set -e
cd ${PWD}

usage()
{
	echo ""
	echo "Usage: ${0} [option]"
	echo "Setup and run Jekyll"
	echo ""
	echo "Options are not mandatory, only one at a time."
	echo "-a, --assets    Build minimized css style and js script from sources."
	echo "-i, --install   Install Bundler and node modules using Yarn."
	echo "-d, --doxygen   Build Doxygen documentation"
	echo ""
}
assets_build()
{
	mkdir -p assets/js
	yarn dist
}
install()
{
	gem update
	gem install bundler
	bundle install
	yarn --no-bin-links
}
# FIXME: Process commands first, then handle directories absence
if [ "${1}" == "--help" ] || [ "${1}" == "-h" ]; then
	usage
	exit 0
fi
if [ ! -d "node_modules" ] || [ "${1}" == "-i" ] || [ "${1}" == "--install" ]; then
	install
	shift
fi
if [ ! -f "assets/css/style.min.css" ] || [ "${1}" == "-a" ] || [ "${1}" == "--assets" ]; then
	assets_build
	shift
fi
if [ ! -d "api" ] || [ "${1}" == "-d" ] || [ "${1}" == "--doxygen" ]; then
	python3 scripts/doxygen/doxy2json.py
	shift
fi
if [ "${1}" == "-b" ] || [ "${1}" == "--baseurl" ]; then
	shift
	baseurl="--baseurl ${1}"
fi
bundle exec jekyll serve --watch --host=0.0.0.0 ${baseurl}
