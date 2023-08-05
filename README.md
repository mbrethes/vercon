# VerCon
A single-person, dead simple, revision control system.

## Version

This program is now in Beta 1.

## License

    Copyright (C) 2023 Mathieu Brèthes

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

## How to use

### Initialize the repository

Place yourself at the root folder where you want to create a VerCon repository.

Call "python vc.py commit My first commit"

A REPO folder will appear, containing the metadata of the repository.

Note: if you are in a subfolder of an existing repository, this repository will be used instead.

### Commit changes

In any of the subfolders of your directory:

Call "python vc.py commit A new commit"

The changes will be stored in the repository.

### List the revisions

In any of the subfolders:

Call "python vc.py list [verbose]"

To display the list of revisions. Use the "verbose" keyword to also see the list of added, modified, or deleted files.

### Revert a file(s) to a previous revision (EXPERIMENTAL)

In any of the subfolders:

Call "python vc.py revert"

To erase any changes you have made and revert to the last revision.

Call "python vc.py revert 1"

To restore all the files to revision 1. The command will fail if there are non-committed modification to your files, thus (hopefully) not erasing uncommitted data.
Replace 1 by any number to restore to any other revision (obviously).
If you use the last revision number, this should act like revert without a number (so your uncommitted files will be erased).

Call "python vc.py revert 1 "regular expression"

To restore files matching "regular expression" to revision 1.
The command will fail if matching files have uncommitted changes (hopefully).

The regular expression matches over the tree beginning at the root of the repository. Please use the correct \ or / sign depending on your operating system if you need to match files with specific directories.


