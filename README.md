# doxy2json

**Experimental, alpha stage** tool to convert [Doxygen] XML output to JSON
to be used with [Jekyll].

1. Runs `doxygen` to parse a `Doxyfile` configuration and convert it to
   a dictionary, which can be saved as JSON.
   This step generates also the XML output from the current project source code.

2. Converts the resulting XML output to JSON files to be stored in the `_data`
   directory managed by Jekyll in the website source.
   This also generates related markdown files to display the resulting data.

3. `jekyll` will generate the resulting HTML pages,
   using the current theme style and layout.

The process can be also automated using tools like Travis-CI.

## Usage

- Run `./scripts/doxygen/doxy2json.py` from the directory
  where the `Doxyfile` is stored,
  in this case `_data` and `api` directories will be created

- Switch to the website source tree: `git checkout gh-pages`

Now the files should be ready to be processed by Jekyll,
a `setup.sh` script will facilitate the process.

## TODO

- A better XML schema to facilitate parsing.

- Some commands are not parsed correctly, like `\details` and `\todo`,
  mainly when using markdown.

- Better and complete management of the generated Doxyfile configuration.

- CREATE_SUBDIRS is not (yet) supported.

[Doxygen]: http://doxygen.nl/
[Jekyll]:  https://jekyllrb.com/
