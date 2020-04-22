#!/usr/bin/env python3
"""
  Converts Doxygen configuration and XML output to JSON.
  Copyright (C) 2020  Andrea Zanellato

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

##
# @file      doxy2json.py
# @package   doxy2json
# @author    Andrea Zanellato
# @copyright GPL-2.0-or-later
# @date      2020
# @brief     Converts Doxygen configuration and XML output to JSON.
# @details   The extracted data can be used by site generators like Jekyll.

from pathlib import Path
#from dulwich.repo import Repo
import argparse
import json
import shutil
import subprocess
import sys
import xmlschema

config   = {} # Doxygen config
settings = {} # App settings

# Undocumented
#
# Returns the current Git tag version if any, `develop` otherwise.
#
# Used when not using the Doxygen version but Git information instead.
#
def git_version():

  proc = subprocess.Popen(["git", "describe", "--exact-match", "--tags", "HEAD"], \
         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  tag  = proc.communicate()[0].decode('utf-8').rstrip()
  if tag == "": return("develop")

  regex = re.compile("^[0-9a-zA-Z_\-.]+$")
  match = regex.match(tag)

  if match is None:
    print("Error: invalid tag name \"{:s}\"".format(tag))
    sys.exit(1)

  return(tag)

## Creates a Markdown page index with the list of API version links.
#
# The result page will be placed in the docs directory as index for the list of
# API pages when placing several API versions documentation in subdirectories.
#
# @param dest_dir Destination directory Path for the resulting index.md file.
#
def create_api_index(dest_dir):

  if not dest_dir.exists() and not dest_dir.is_dir():
    print("Error: '{}' doesn't esists or not a directory.".format(dest_dir))
    exit(1)
  """
  repo = Repo(".")
  tags = [
    ref[10:].decode("utf-8")
    for ref in repo.refs.allkeys()
    if ref.startswith(b"refs/tags")
  ]
  """
  index  = Path(dest_dir / "index.md")
  header = "---\ntitle: \"API\"\n---\n"
  with index.open('w') as f:
    f.write(header)
    f.write('\n'.join(["- [{}]({})".format(subdir, subdir) \
      for subdir in \
        list(map(lambda p: p.name, filter(Path.is_dir, dest_dir.iterdir())))]))
    f.write('\n')

## Converts Doxygen XML output to JSON data and Markdown pages.
#
# Given a relative or absolute XML file path, generates a JSON data file
# to be saved in `_data/api` and the related Markdown page in the related
# docs directory.
#
# @param file_in  The input file Path.
# @param dest_dir The destination directory Path name.
#
def from_xml(file_in, dest_dir):

  """
  |                                    | cfg.get("use_subdirs") == False | use_subdirs == True
  | -----------------------------------------------------------------------------------------
  | file_in                            | ../path/to/api/xml/filename.xml | * same *
  | xml_dir     = file_in.parents[0]   | ../path/to/api/xml              | * same *
  | md_dir      = dest_dir             | ../path/to/api                  | ../path/to/api/1.2.3
  | data_prefix = dest_dir.parent      | ../path/to                      | * same *
  | data_suffix                        | api                             | api/1.2.3
  | file_name   = file_in.name         | filename.xml                    | * same *
  | base_name   = Path(file_name).stem | filename                        | * same *
  | api_dir     = dest_dir.name        | api                             | 1.2.3
  | data_dir                           | ../path/to/_data/api            | ../path/to/_data/api/1.2.3
  """
  dest_abs = Path(dest_dir).resolve() # can't do .parent on a relative '.'
  if settings.get("use_subdirs"):
    dir_prefix  = dest_abs.parents[1]
  else:
    dir_prefix  = dest_abs.parent

  data_prefix = str(dir_prefix)
  data_suffix = str(dest_abs).replace(data_prefix, '')
  datadirname = data_prefix + "/_data" + data_suffix
  data_dir = Path(datadirname)
  """
  print("[debug] dest_dir    = {:s}".format(str(dest_abs)))
  print("[debug] data_suffix = {:s}".format(data_suffix))
  print("[debug] data_dir    = {:s}".format(datadirname))
  """
  # XML schema
  xml_dir   = file_in.parent
  file_name = file_in.name
  base_name = Path(file_name).stem
  if file_name == "index.xml":
    xsd_file = Path(xml_dir / "index.xsd")
  else:
    xsd_file = Path("scripts/doxygen/compound.xsd")

  # JSON data files
  json_name = base_name + ".json"
  json_file = data_dir / json_name

  # Markdown content files
  md_hdr  = "---\nlayout: \"doxygen\"\nno_title_header: true\n---\n"
  md_name = base_name + ".md"
  md_file = dest_dir / md_name

  if not data_dir.exists():
    data_dir.mkdir(parents=True)

  if not dest_dir.exists():
    dest_dir.mkdir(parents=True)

  x = xmlschema.XMLSchema(str(xsd_file))
  d = x.to_dict(str(file_in))
  s = json.dumps(d, indent=2)

  # Fix datafiles to work with Jekyll
  s = s.replace("\"@",    "\"") \
       .replace("\"$\":", "\"value\":") \
       .replace("\"no\"", "\"false\"")

  print("Generating {:s}...".format(str(json_file)))
  json_file.open('w')
  json_file.write_text(s)

  if md_file.exists():
    print("Skipping {:s}...".format(str(md_file)))
  else:
    print("Generating {:s}...".format(str(md_file)))
    md_file.open('w')
    md_file.write_text(md_hdr)

## Parses a Doxyfile and save the result as a dict.
#
# @param doxyfile The file path to the Doxyfile as string.
#
# @todo Check for inline comments.
#
def load(doxyfile="Doxyfile"):

  f = Path(doxyfile)
  if not f.exists() or not f.is_file():
    print("File '{}' not found or not a file.".format(f))
    sys.exit(1)

  doxydict = {}
  doxyfile = open(doxyfile)
  lines    = doxyfile.readlines()

  # This is to have Doxygen version *before* run(), maybe unused and later removed
  lines[0] = lines[0].replace("# Doxyfile ", "VERSION=")
  is_multi = False
  key_multi= ""
  val_list = []

  for i in range(len(lines)):
    # Strip out comments and empty lines
    if lines[i].startswith('#') or(lines[i] == ''):
      continue

    # Value list: keep track of key and first value
    if lines[i].rstrip().endswith('\\'):
      line = lines[i].strip()[:-1]
      is_multi = True
      record   = line.split('=', 1)

      if len(record) > 1:
        # First line with key/value pair
        key_multi= record[0].swapcase().strip()
        val_list.append(record[1].strip())
      else:
        # Following line, only value
        val_list.append(record[0].strip())
      continue

    # Value list: append values to saved one, if last reset flags and continue
    if is_multi:
      val_list.append(lines[i].strip())
      if not lines[i].endswith('\\'):
        doxydict[key_multi] = val_list
        is_multi = False
        key_multi= ''
        val_list = []
      continue

    record    = lines[i].split('=', 1)
    record[0] = record[0].swapcase().strip()

    if(len(record) < 2):
      continue

    record[1] = record[1].strip().replace("YES", "true").replace("NO", "false")

    # Strip out null values
    if record[1] == '':
      continue

    doxydict[record[0]] = record[1]

  return(doxydict)

## Loads a Doxyfile and runs the main documentation generation process.
#
# @param doxyfile    The name of the Doxygen configuration file.
# @param use_subdirs Whether to use subdirectories named by the API version.
#
# @todo Manage OUTPUT_DIRECTORY and XML_OUTPUT relation
#
def run(doxyfile="Doxyfile", use_subdirs=False):

  f = Path(doxyfile)
  if not f.exists() or not f.is_file():
    print("Error: '{}' doesn't esists or not a file.".format(f))
    exit(1)

  if use_subdirs:
    settings["use_subdirs"] = True

  global config
  config = load(doxyfile)
  prjver = config.get("project_number", "development")
  outdir = Path(config.get("output_directory", "."))
  xmldir = Path(outdir / config.get("xml_output", "xml"))

  if use_subdirs:
    outdir = Path(outdir / prjver)

  if not outdir.exists():
    outdir.mkdir(parents=True)

  cp = subprocess.run(["doxygen", doxyfile])
  if cp.returncode != 0:
    exit(cp.returncode)

  print("Generating JSON and Markdown files from XML:")
  for f in xmldir.iterdir():
    fname = str(f)
    if f.is_file() and \
      (not ".xsd" in fname and not ".xslt" in fname and not "dir_" in fname):
        from_xml(f, outdir)

  print("Removing XML output...")
  shutil.rmtree(xmldir)

  if use_subdirs:
    print("Generating API index page in `{:s}`...".format(str(outdir.parent)))
    create_api_index(outdir.parent)

  print("Done.")

def main():

  parser = argparse.ArgumentParser(description=\
    "Loads a Doxyfile and runs the main documentation generation process.")

  parser.add_argument("-i", "--input", default="Doxyfile", help=\
    "The name of the Doxygen configuration file [default: \"Doxyfile\"]")

  parser.add_argument("-s", "--use_subdirs", action="store_true", help=\
    "Whether to use subdirectories named by the API version [default: False]")

  args = parser.parse_args()

  run(args.input, args.use_subdirs)

if __name__ == "__main__":
  main()
