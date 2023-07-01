"""
VerCon (VC)
-----------

A simple version control system for a single user.

Released under GPL v3.
(c) 2023 by Mathieu Brèthes


Goals of the project:

- should not require any tool beyond Python and standard Python library
- basic version control : only one branch with successive commits.
- implements 3 commands:
	* python vc.py commit comment :
	  - checks if there is a repository in or above this directory.
	  - if not, creates repository in current directory.
	  - stores all the changes into the repository.
	  - includes all files and directories.
	  - if a file is deleted, it is kept in history.
	  - if a subdirectory is deleted, it is kept in history.
	  - returns a new version number, starting from 1.
	* python vc.py list [verbose]:
	  - prints the list of all commits (number, date + comment) in reverse order.
	  - if verbose is set, also prints the list of added/deleted/modified files+directories.
	* python vc.py revert [number/cur] [file/directory]:
	  - if number is "cur", overwrites changes and reverts to last commit.
	  - else, if any changes are not committed, refuses to do anything.
	  - if number is not specified reverts the repository to the N-1 commit (if no number is specified)
	  - else, to commit of specified number.
	  - can be framed to use a single file/files or directory/ies using a regular expression.
	  
- does handle text files with a "diff" system, data files as binary blobs.
- data stored textually if possible to ease backups.
- a mechanism needs to be implemented to minimize database corruption in case of commit interruption.


the database
------------

A directory named REPO

stores:
- a mirror of the tree under subdirectory DATA:
  - all the directories, whether created or deleted (this info is stored in metadata)
- for each file:
  - text file:
    * copy of the last version of the file preceded by ET<rev>- (latest revision) or D<rev>- (if deleted)
    * a list of deltas (+/- lines) in reverse order to reconstruct previous revisions, same file name with HT<rev>- for each delta.
  - binary file, every time the file changes a new copy is stored.
    * latest version preceded with EB<rev>- (latest revision) or D<rev>- (if deleted)
    * copies preceded with HB<rev>-
- metadata:
  * a text file listing the commits, with additions and deletions: commits.txt
  * a text file listing all the directories, and for each directory, the succession of revisions where the directory was created, (deleted, recreated, ...): metadatadir.txt

stages of a commit
------------------

during a commit:

a) check if there are new or deleted directories:

- if new directory, the directory is created in the tree
- if deleted directory, all files in the hierarchy move to D<rev>- status
- for both scenarios, the list of directories is checked and amended with latest information (creation revision or deletion revision)

b) check if there are new or deleted files:

- if new files, copy file into tree as ET<rev>- or EB<rev>-
- if deleted files, create an empty D<rev>- with the filename.

c) check if there are modified files:

- check file type:
  * if file is binary, and previous revision is also binary:
      * store previous revision in HB<prev>- where rev remains the same as EB<prev>-
      * store new bin file as EB<rev>
  * if file is text, and previous revision is also text:
      * calculate the delta that enables to create the previous revision ET<prev>- from current revision 
      * store the delta into HT<prev>- 
      * save new file as ET<rev>- 
  * if file is binary, and previous revision was text:
      * calculate the delta from an empty file to ET<prev>- and store it into HT<prev>-
      * store new file into EB<rev>-
  * if file is text, and previous revision was binary:
      * move previous revision to HB<prev>-
      * copy new file into ET<rev>- 


stages of a revert
------------------

during a revert to revision X:

a) check if there are any modifications to the repository. If they are any, stop (list them?).

b) delete the files and directories to be reverted.

c) restore the directories from the tree:

- create all directories that are "created" according to the directory metadata

d) restore the files from the tree:

- for each file in the directories created above, browse file history in reverse to create file as it appeared in revision X:
  (or revision < X if the file was not committed in revision X)
  * take last revision, copy into file. Note format (binary or text). cur := Last revision
  * for each N >= 1 and < cur, going in reverse:
    * check if exist HB<N>- / HT<N>- / D<N>-
    * if yes:
        * if revN is text and cur is binary --> restore data from HT<N>- by comparing to an empty file, overwrite cur with this data.
        * if revN is binary and cur is text, or N is binary and cur is binary --> overwrite file with HB<N>-
        * if revN and cur are text --> calculate old revision by comparing delta to cur, and overwrite cur with the result.
        * if revN is Deleted (D<N> exists) --> delete cur.
        * cur := N
        * if cur <= X ; stop the loop.
        
        
v0

Let's first implement the directories organization.


"""

import os,sys,re

class VerConError(Exception):
    pass

class VerConDirectory():
    """
    A helper class representing a directory in the repository.
    A directory corresponds to a path relative to the root of the repository (always!)
    And it can be in status active or deleted depending on the revision on which we are checking.
    """
    
    def __init__(self, metadataorpath, revision=None):
        """
        Initialization using a line of metadata from metadatadir.txt
        of the form revision,[revision,[revision...]] directoryname
        
        Excepts a valid line from metadatadir.txt to work if Revision is None,
        or a path + a revision number.
        
        There can't be multiple constructors in Python, so that's the way for now...
        """

        if revision == None:
            data = re.match("^(\d+(?:,\d+)*) (.*)$", metadataorpath)
            if data != None:
                self.history = []
                for d in data.group(1).split(","):
                    self.history.append(int(d))
                self.path = data.group(2)
            else:
                raise VerConError()
                
        else:
            self.history = [revision]
            self.path = metadataorpath       

    def getPath(self):
        return self.path
        
    def isCurrentlyActive(self):
        """
        A directory is active if its current history count is odd (history contains a list of successive creations and deletions).
        """
        return (len(self.history)%2 == 1)
        
    def isActiveAt(self, revision):
        """
        Returns true if the directory is active at a given revision number.
        """
        
        # by default, the directory does not exist.
        active = False
        for arev in self.history:
            if arev > revision:
                break
            active = not active
        
        return active

    def __lt__(self, other):
        """
        Useful to implement a sorted list of directories. Directories are sorted by path.
        """        
        return self.getPath() < other.getPath()
        
    def __hash__(self):
        """
        Useful if those damn things are stored into a dictionnary.
        """
        return hash(self.getPath())


class VerConRepository():
    """
    The main class implementing the version control system.
    """

    def __init__(self, directory):
        """ Constructor initialization. Will create an empty repository in directory
            if there is none up to the root of the filesystem.
        """
        self.repodir = None
        self.basedir = None
        self.datadir = None
        self.lastcommit = None
        
        path = os.path.abspath(directory)
        drive,path = os.path.splitdrive(path)
        while len(path)>1 and self.repodir == None: # path will contain a leading / or \
            if not os.path.isdir(os.path.join(drive, path, "REPO")):
                path,end=os.path.split(path)
            else:
                self.datadir = os.path.join(drive,path,"REPO","DATA")
                self.repodir = os.path.join(drive,path,"REPO")
                self.basedir = os.path.join(drive,path)

        if self.repodir == None:
            os.mkdir(os.path.join(directory, "REPO"))
            os.mkdir(os.path.join(directory, "REPO", "DATA"))
            self.repodir = os.path.join(directory, "REPO")
            self.datadir = os.path.join(directory, "REPO", "DATA")
            self.basedir = directory
            with open(os.path.join(self.repodir, "metadatadir.txt"),"w") as f:
                f.close()
            with open(os.path.join(self.repodir, "commits.txt"),"w") as f:
                f.close()
            self.lastcommit = 0
            
    def getRepoDir(self):
        """
        Helper function that returns the REPO directory used by the version control system.
        """
        return self.repodir
        
    def getBaseDir(self):
        """
        Helper function that returns the root directory of the repository (containing REPO as well as the rest)
        """
        return self.basedir
        
    def commit(self, comment):
        """ commit changes to the repository in or above directory, with comment comment.
            creates new repository in directory if none found.
        """
        
        # Stage 1 : are there any changes?
        count = 0
        for root, dirs, files in os.walk(self.getBaseDir()):
            pass
        
        pass
        
    def list(self, verbose=0):
        """ returns a list of all the changes in the repository, one per line.
            if verbose is 1, also lists the files added/deleted/modified.
            if verbose is 2, also lists the changes for each file.
            
            v0 : only a verbose list.
            v1 : implemented level 1, level 2 not just yet.
        """
        data = []
        with open(os.path.join(self.repodir, "commits.txt"),"r") as f:
            for line in f.readlines():
                if verbose > 0:
                    data.append(line)
                else:
                    if not line.startswith("  "):
                        data.append(line)
        return "".join(data)
        
    def revert(self, revision, filter=""):
        """ reverts change to a given revision.
        
        revision : can be set to "cur" to revert to the last commit
                    otherwise will revert to a previous commit, indicated by number
                    (note : using number of last commit has same effect as "cur")
        filter: a regular expression that will matche file(s) or directory(ies) to be reverted.
                    paths are always Unix (slashes)
        """
        pass
        
if __name__ == "__main__":
    print("The future is bright!")