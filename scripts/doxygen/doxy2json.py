#!/usr/bin/env python3

##
# @file      doxy2json.py
# @package   doxy2json
# @author    Andrea Zanellato
# @copyright MPL-2.0
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

## Creates a Markdown page index with the list of API version links.
#
# The result page will be placed in the docs directory as index for the list of
# API pages when placing several API versions documentation in subdirectories.
#
# @param dest_dir Destination directory for the resulting index.md file.
#
def create_api_index(dest_dir):

  dest = Path(dest_dir)
  if not dest.exists() and not dest.is_dir():
    print("Error: '{}' doesn't esists or not a directory.".format(dest))
  """
  repo = Repo(".")
  tags = [
    ref[10:].decode("utf-8")
    for ref in repo.refs.allkeys()
    if ref.startswith(b"refs/tags")
  ]
  """
  index  = Path(dest / "index.md")
  header = "---\ntitle: \"API\"\n---\n"
  with index.open('w') as file:
    file.write(header)
    file.write('\n'.join(["- [{}]({})".format(subdir, subdir) \
      for subdir in list(map(lambda p: p.name, filter(Path.is_dir, dest.iterdir())))]))

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

## Converts Doxygen XML output to JSON data and Markdown pages.
#
# Given a relative or absolute XML file path, generates a JSON data file
# to be saved in `_data/api` and the related Markdown page in the related
# docs directory.
#
# @param file     The input file path as string.
# @param dest_dir The destination directory name, e.g.: project version.
#
def from_xml(file, dest_dir):

# tag_name  = git_version()
  data_dir  = Path("_data/" + dest_dir)
  md_dir    = Path(dest_dir)
  xml_dir   = Path(file).parents[0]
  file_name = Path(file).name
  base_name = Path(file_name).stem

  if file_name == "index.xml":
    xsd_file = Path(xml_dir / "index.xsd")
  else:
    xsd_file = Path("scripts/doxygen/compound.xsd")

# JSON data files
  json_name = base_name + ".json"
  json_path = data_dir / json_name
  json_file = Path(json_path)

# Markdown content files
  md_hdr  = "---\nlayout: \"doxygen\"\nno_title_header: true\n---\n"
  md_name = base_name + ".md"
  md_path = md_dir / md_name
  md_file = Path(md_path)

  if not data_dir.exists():
    data_dir.mkdir(parents=True)

  if not md_dir.exists():
    md_dir.mkdir(parents=True)

  x = xmlschema.XMLSchema(str(xsd_file))
  d = x.to_dict(file)
  s = json.dumps(d, indent=2)

  # Fix datafiles to work with Jekyll
  s = s.replace("\"@",    "\"") \
       .replace("\"$\":", "\"value\":") \
       .replace("\"no\"", "\"false\"")

  print("Generating {:s}...".format(str(json_path)))
  json_file.open('w')
  json_file.write_text(s)

  if md_file.exists():
    print("Skipping {:s}...".format(str(md_path)))
  else:
    print("Generating {:s}...".format(str(md_path)))
    md_file.open('w')
    md_file.write_text(md_hdr)

## Parses a Doxyfile and save the result as a dict.
#
# @param doxyfile The file path to the Doxyfile as string.
#
# @todo Check for inline comments.
#
def load(doxyfile):

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
      key_multi= record[0].swapcase().strip()
      val_list.append(record[1].strip())
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
# @param doxyfile The name of the Doxygen configuration file.
# @param dest_dir The name of the destination directory.
#
# @todo Manage OUTPUT_DIRECTORY and XML_OUTPUT relation
#
def run(doxyfile="Doxyfile", dest_dir="api"):

  path = Path(doxyfile)
  if not path.exists():
    raise FileNotFoundError("No such file or directory: '{:s}'".format(doxyfile))

  subprocess.run(["doxygen", doxyfile])
  config = load(doxyfile)
  xmldir = Path(config.get("xml_output", "./xml"))

  print("Generating JSON and Markdown files from XML:")
  for xml in xmldir.iterdir():
    xmlname = str(xml)
    if xml.is_file() and \
      (not ".xsd" in xmlname and not ".xslt" in xmlname and not "dir_" in xmlname):
        from_xml(xmlname, dest_dir + '/' + config.get("project_number", "develop"))

  print("Generating API index page in `{}`...".format(dest_dir))
  create_api_index(dest_dir)
# print("Removing XML output...")
# shutil.rmtree(xmldir)
  print("Done.")

def main():

  parser = argparse.ArgumentParser(description=\
    "Loads a Doxyfile and runs the main documentation generation process.")

  parser.add_argument("-i", "--input", default="Doxyfile", help=\
    "The name of the Doxygen configuration file.")

  parser.add_argument("-o", "--output", default="api", help=\
    "The name of the destination directory.")

  args = parser.parse_args()

  if args.input != "":
    run(args.input, args.output)

if __name__ == "__main__":
  main()
