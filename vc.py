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
    * copy of the last version of the file preceded by ET<rev>- (latest revision) or D<rev>- (if deleted, file empty)
    * a list of deltas (+/- lines) in reverse order to reconstruct previous revisions, same file name with HT<rev>- for each delta.
      This information is stored as a series of 5-uples inspired by that in SequenceMatcher (cf https://docs.python.org/3/library/difflib.html?highlight=diff#difflib.SequenceMatcher)
      i count\n                                    (insert count characters in the new file)
      <count characters, possibly including\ns...>\n
      s count\n                                      (skip the next count characters of the old file)
      c count\n                                      (copy the next count to new file)
  - binary file, every time the file changes a new copy is stored.
    * latest version preceded with EB<rev>- (latest revision) or D<rev>- (if deleted, file empty)
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


Stages of a recovery (B1)
-------------------------

If the program crashed while doing a commit, the file database will be left in an inconsistent state.

Detection:

a "lock%d" file in REPO is created at the beginning of the commit operation, and deleted at the end, with %d replaced by commit number.

if "lock%d" is present, this means the program crashed during processing of the commit.

If so:
- copy (not move!) all the files starting with BAK%d- to their normal equivalents (with %d the failed revision number).
- delete any E/D files with %d as revision number
- remove lock
- if the program crashes while restoring, the files starting with BAK can be restored again.


Stages of safety mechanism (B1)
-------------------------------

Before commit:
- create "lock%d" file in REPO

During commit:
- every time a file is edited, first make a copy to BAK%d-<filename>.

After commit:
1. delete lock%d
2. delete any BAK%d- files where %d < last revision (to keep repo clean) (in that order)

        
v0
Let's first implement the directories organization.

A1
commit/restore basic working files+dirs
basic CLI.
need for a pretty commit list printer.

A2
SOLVED:
- BUG : difflib.sequencematcher extremely slow --> activate autojunk.
- BUG : filecmp.cmp says identical python files are different (try without shallow, make a real function?) --> put shallow to false, made test cases


B1
commit/rollback safety mechanism
prints > log system
code refactoring
more tests

03.07: almost finished
14.07: Alpha 1 reached
20.07: Alpha 2 reached, moved safety mechanism milestone for B1.


"""

import os,sys,re, difflib,shutil, filecmp

class VerConError(Exception):
    pass
    
class VerConEvent():
    """
    It's really just a data structure to help VerConFile.
    """
    def __init__(self, event, type, fname):
        self.event = event
        self.type = type
        self.fname = fname
        
    def historicize(self, newname):
        """
        This function transforms the event:
        if e : into a h
        if d : not touched
        if h : raises exception.
        """
        if self.event == "e":
            self.event = "h"
        elif self.event == "h":
            raise VerConError("Error: trying to historicize an event which is already history.")
        self.fname = newname
        
    def __repr__(self):
        """
        Pretty print
        """
        return "(event: %s, type: %s, file name: %s)"%(self.event, self.type, self.fname)
    
class VerConFile():
    """
    A helper class representing a file in the repository.
    
    A file contains:
    - a name (in the repository)
    - a list of events (create, modify, delete) with associated file names (in DATA) and types, and commit number
    
    It should be possible:
    - to randomly add events to the file (because directory traversal is not always ordered)
    - to compute the delta for two successive revisions
    - to get data information for a given revision.
    """
    
    def __init__(self, name, rootdirectorypath, datadirectorypath, filerelpath):
        """
        Creates a new file object, with name being the name in the repository (NOT the ET- file name...).
        
        name: the file name (in user's view, ex "test.txt")
        rootdirectorypath: location of base directory of the repository.
        datadirectorypath: location of directory REPO/DATA where the file's bits are somewhere located (with possible subdirectories omitted), absolute path or at least accessible to root.
        filerelpath: directory containing location of file in the user's arborescence, relative to the root (or to data). "" if at root.
        
        precise location of data files can be computed by joining datadierctorypath + filerelpath.
        precise location of user file can be computed by joining rootdirectorypath + filerelpath
        
        self.events contains a dictionnary of events, with the key being the revision number. Each event entry is a VerConEvent object (really just a data structure).
        self.hasE contains a revision number if an E event has been found, -1 otherwise.
        """
        
        self.name = name
        self.rootp = rootdirectorypath
        self.datap = datadirectorypath
        self.frelp = filerelpath
        
        self.events = {}
        self.hasE = -1
        self.lastrevision = -1
        self.touched = False
        
    def __repr__(self):
        """
        Pretty print, for debug purposes.
        """
        evtl = []
        for k,c in self.events.items():
            evtl.append(c.__repr__())
        return "(%s) %s : (hasE %d, last rev %d, touched %d, events %s)"%(self.frelp, self.name, self.hasE, self.lastrevision, self.touched, ", ".join(evtl))
        
    def isTouched(self):
        """
        Returns true if the file was visited during last commit (provided touch() is called...)
        """
        return self.touched
        
    def touch(self):
        """
        Sets self.touched to true. Marks file as processed during commit, even if no changes were made.
        Called automatically by createAtRevision and changeAtRevision
        """
        self.touched = True
        
        
    def getLastEventFileNameAndPath(self):
        """
        Returns the file name associated with the last event, for comparison purposes.
        
        Raises VerConError if there was no such event.
        """
        if len(self.events) == 0:
            raise VerConError("This file %s has never been commited!"%self.name)
        
        return os.path.join(self.datap, self.frelp, self.events[self.lastrevision].fname)
        
    def getLastRevision(self):
        """
        Returns the last revision.
        
        -1 if not initialized.
        """
        return self.lastrevision
        
    def loadEvent(self, event, revision, ftype, fname):
        """
        Loads a new event to the file. 
        
        event can be "h" (history), "e" (existing - also used for creation), "d" (deletion).
        revision is expected to be an integer > 0.
        ftype can be "t" or "b" (text or binary).
        fname is the matching filename in REPO/DATA/... (path not included): ex. ETxx, EBxx, Hxx, DTxx, DBxx, Hxx...
        
        the function is supposed to sort the dictionnary of events.
        
        Raise an error if:
        - there is already an "e" event.
        - a d or h event is added after the "e" event
        - two events exist for the same revision.    
        - event not in h, e, d, ftype not in t, b
        """
        if event not in ["h", "e", "d"]:
            raise VerConError("Invalid event type: %s"%event)
        if ftype not in ["t", "b"]:
            raise VerConError("Invalid file type: %s"%ftype)
        
        if revision in self.events.keys():
            raise VerConError("An event is already registered at this revision: %d"%revision)
        
        if event == "e" and self.hasE != -1:
            raise VerConError("A second 'e' event is being added, first one at revision %d - list of events %s!"%(self.hasE, self.events))
        
        if event in ["d", "h"] and self.hasE > -1 and revision > self.hasE:
            raise VerConError("A %s event is being added at revision %d, after a E event which should be final at revision %d"%(event, revision, self.hasE))
            
        self.events[revision] = VerConEvent(event,ftype,fname)
        if event == "e":
            self.hasE = revision
            
        if revision > self.lastrevision:
            self.lastrevision = revision

        
    def isNew(self):
        """
        Returns true if the file item has never been committed (0 element in history)
        """
        return len(self.events.keys()) == 0
        
    def existsAt(self, revision):
        """
        Returns true if file exists at given revision, false otherwise.
        
        We expect the event dictionnary to faithfully represent the file's change of states.
        
        """
       
        active = False
        for i in sorted(self.events.keys()):
            if i > revision:
                return active
            else:
                if self.events[i].event in ["e","h"]:
                    active = True
                else: # case of a deletion event
                    active = False
        
        return active
        
        
    def fTypeAt(self, revision):
        """
        Returns "t" or "b" depending on the type of the file at that point in time.
        
        Excepts that file exists at that revision, otherwise result is undefined.
        
        Not using a boolean function here because in the future maybe there can be different test files, to implement diffs for other text file formats.
        """
        type = ""
        for i in sorted(self.events.keys()):
            if i > revision:
                return type
            else:
                if self.events[i].event in ["e","h"]:
                    type = self.events[i].type
        
        return type
        
    def contentsAt(self, revision):
        """
        Returns the calculated content of the file at the given revision.
        
        THis is a stream that can be written to a file (note: currently, bytes or str).
        
        We first try to find the first revision equal or under "revision".
        
        then:
        - if it is E: we open and return the contents of the file (simple!).
        - if it is HB: we open and return the contents of the file (simple too!)
        - if it is HT: we start browsing up until we find either a HB, a D, a EB, or a ET.
          * if we find a ET: we then generate the file backwards with the diffs.
          * anything else: we open the previous element found (including the HT if exists) as a standard text file, and we diff with the previous ones back to the first (if not already used, if remain).
        """
        objective = -1
        data = None
        klist = list(self.events.keys())
        klist.sort(reverse=True)
        
        for i in klist:
            if i <= revision:
                objective = i
                break
                
        if objective == -1:
            raise VerConError("Trying to return contents of a file that was not added yet to the repository at this revision %d"%revision)
            
        if self.events[objective].event == "d":
            raise VerConError("Trying to return contents of a file which is deleted in tree at this revision %d"%revision)
            
        # the event is the last event, it's easy enough then.
        if self.events[objective].event == "e":
            rtype = "r"
            if self.events[objective].type == "t":
                rtype = "r"
            else:
                rtype = "rb"

            with open(os.path.join(self.datap, self.frelp, self.events[objective].fname),rtype) as f:
                data = f.read()

        elif self.events[objective].event == "h":
            # we have a history of a binary file, we just restore it as is.
            if self.events[objective].type == "b":
                with open(os.path.join(self.datap, self.frelp, self.events[objective].fname),"rb") as f:
                    data = f.read()        
                    
            else:
                # final case , we are at the history of a text file (HT)
                klist.reverse()
                begin = klist.index(objective)
                for i in klist[begin:]:
                    # case for the last event
                    if self.events[i].event == "e":
                        end = klist.index(i)
                        # if it is text, we need to take it into account, otherwise we will start at event -1.
                        if self.events[i].type == "t":
                            end += 1
                        break
                    # case for a deletion
                    elif self.events[i].event == "d":
                        end = klist.index(i)
                        break
                    else:
                        # case for a HB
                        if self.events[i].type == "b":
                            end = klist.index(i)
                            break
                        
                        # if we have a HT? we just continue.
                if end >= len(klist):
                    data = self.mergeTextBackwards(klist[begin:])
                else:
                    data = self.mergeTextBackwards(klist[begin:end])

        return data
    
    def calculateDelta(self, fromX, toY):
        """
        This function takes two files (loaded as strings) and returns the delta to go from the first to the second.
        """
        
        differ = difflib.SequenceMatcher(isjunk=None, a=fromX, b=toY, autojunk=True)
        res = differ.get_opcodes()
        
        outcodes = []
        for tag, i1, i2, j1, j2 in res:
            if tag == "delete":
                outcodes.append(("s", i2-i1, None))
            elif tag == "equal":
                outcodes.append(("c", i2-i1, None))
            elif tag == "insert":
                outcodes.append(("i", j2-j1, toY[j1:j2]))
            elif tag == "replace":
                outcodes.append(("s", i2-i1, None))
                outcodes.append(("i", j2-j1, toY[j1:j2]))
            else:
                raise VerConError("This should not happen.")
        
        soutcodes = []
        
        for type, count, st in outcodes:
            if st != None:
                soutcodes.append("%s %d\n%s"%(type, count, st))
            else:
                soutcodes.append("%s %d"%(type, count))
                
        return "\n".join(soutcodes)
    
    def mergeTextBackwards(self, revList):
        """
        This function returns the "merging" of successive revisions of
        text files, to obtain a previous version.
        The list is expected to be in order, and is crawled down,
        with the last item being a normal data, and all the previous items
        being history bits.
        
        The list should have at least 2 elements (otherwise it makes no sense),
        and all the elements except the last one should be HT; the last one can be HT or ET.
        
        It returns the data corresponding to the file at the earlier point in time.
        
        Delta file format:
        
        This information is stored as a series of 5-uples inspired by that in SequenceMatcher (cf https://docs.python.org/3/library/difflib.html?highlight=diff#difflib.SequenceMatcher)
          i count\n                                    (insert count characters in the new file)
          <count characters, possibly including\ns...>\n
          s count\n                                      (skip the next count characters of the old file)
          c count\n                                      (copy the next count to new file)
        """
        data = ""
        
        final = self.events[revList.pop()] # get the last event index
        
        with open(os.path.join(self.datap,self.frelp,final.fname), "r") as f:
            data = f.read()
            
        revList.reverse()
        matcher = re.compile("(^[isc]) (\d+)$", re.MULTILINE)
        for i in revList:
            with open(os.path.join(self.datap,self.frelp,self.events[i].fname), "r") as f:
                deltas = f.read()      
                newdata = []
                indexdelta = 0
                indexdata = 0
                while indexdelta < len(deltas):
                    command = matcher.match(deltas[indexdelta:])
                    if command == None:
                        raise VerConError("data %s does not start with a valid command."%deltas[indexdelta:])
                    
                    indexdelta += len(command.group(0)) + 1 # we need to add 1 extra character for the hidden \n at the end of each line.
                    action = command.group(1)
                    count = int(command.group(2))
                    
                    # skip action: we skip X characters of old data.
                    if action == "s":
                        indexdata += count
                    # copy action: we copy X characters of old data to new data.
                    elif action == "c":
                        newdata.append(data[indexdata:indexdata+count])
                        indexdata += count
                    # insert action: we insert X characters from deltas, to new data.
                    elif action == "i":
                        newdata.append(deltas[indexdelta:indexdelta+count])
                        indexdelta += count +1 # +1 for the extra \n at the end of the data that was inserted.
                    else:
                        raise VerConError("invalid action %s"%action)
                        
                # once we are here, we can assemble the bits and form the "new" file...
                data = "".join(newdata)
                    
        return data
        
    def textOrBinary(self, path):
        """
        A helper function that will return a 2-uple containg "t"/"b" + data either as a string
        or as a binary line.
        
        File must exist, otherwise...
        """
        data = None
        type = None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = f.read()
                type = "t"
        except UnicodeDecodeError:
            with open(path, 'rb') as f:
                data = f.read()
                type = "b"

        return (type, data)
        
    def createAtRevision(self, revision):
        """
        This is called during a commit when the file is created for the first time.
        
        It loads its data from the contents, calculates if it is binary or text,
        and creates the first file item in the DATA directories.
        
        We expect the file was never committed before.
        
        Automatically detects text or binary.
        """
        
        if len(self.events) > 0:
            raise VerConError("Trying to create a file that already has some historical data.")
        
        filename = os.path.join(self.rootp,self.frelp,self.name)
        type,data=self.textOrBinary(filename)
        if type == "t":
            datafname = "ET%d- %s"%(revision, self.name)
            mode = "w"
        elif type == "b":
            datafname = "EB%d- %s"%(revision, self.name)
            mode = "wb"
                
        self.loadEvent("e", revision, type, datafname)
        
        stinfo = os.stat(filename)
        
        with open(os.path.join(self.datap,self.frelp,datafname), mode) as f:
            f.write(data)
            
        os.utime(os.path.join(self.datap,self.frelp,datafname),ns=(stinfo.st_atime_ns, stinfo.st_mtime_ns))
            
        self.touch()
        
        
    def changeAtRevision(self, revision):
        """
        This is called during a commit when the file is already existent.
        
        This will create a new revision event, create and update the data files accordingly.
        
        This function is responsible for creating the diff (or is it?).
        
        Automatically detects text or binary.
        
        There should be no revisions equal to or after revision.
        """
        
        self.createBackup(revision)
        if self.hasE >= revision:
            raise VerConError("You are trying to do a commit at the same revision %d, or earlier as an existing commit %d. Please don't do that."%(revision, self.hasE))
            
        if revision <= self.lastrevision:
            raise VerConError("You are trying to do a commit at a version %d <= the latest version %d. This is bad. %s"%(revision, self.lastrevision, os.path.join(self.frelp,self.name)))
            
        if len(self.events) == 0:
            raise VerConError("You are trying to do a change to a file that has never been committed. That's a no-no")

        lastevent = self.events[self.lastrevision]

        filename = os.path.join(self.rootp,self.frelp,self.name)
        type,data=self.textOrBinary(filename)


        # the most simple case is for binary files: we need to copy existing E file into a H file, and create a new E file.
        if type == "b":
            # we move the previous file into history.
            if lastevent.event == "e":
                if lastevent.type == "b":
                    fnbit = "HB"
                elif lastevent.type == "t":
                    fnbit = "HT"
                else:
                    raise VerConError("File type %s not implemented."%type)
                    
                newnameforhistory = "%s%d- %s"%(fnbit, self.lastrevision,self.name)
                    
                shutil.move(os.path.join(self.datap, self.frelp, lastevent.fname), os.path.join(self.datap, self.frelp, newnameforhistory))
            
                # we move the previous event into history.
                self.events[self.lastrevision].historicize(newnameforhistory)
                # this is necessary so we can add the new E event.
                self.hasE = -1
            elif lastevent.event == "h":
                raise VerConError("This should just not be possible. Aborting.")
            else:
                # for d events (deletions), we do not need to do anything, they stay as-is in history.
                pass
            
            # we store the data into the new E event...
            
            datafname = "EB%d- %s"%(revision, self.name)
       

        # the more complex case: text files.
        elif type == "t":
            # if we had a deletion before, we don't need to do a thing, just store the new file.
            if lastevent.event == "d":
                pass
            elif lastevent.event == "e":
                # if the type of the last event is binary, we just need to move the last event's file to history.
                if lastevent.type == "b":                            
                    newnameforhistory = "HB%d- %s"%(self.lastrevision,self.name)                        
                    shutil.move(os.path.join(self.datap, self.frelp, lastevent.fname), os.path.join(self.datap, self.frelp, newnameforhistory))
                    
                # otherwise we need to calculate the delta...
                elif lastevent.type == "t":
                    newnameforhistory = "HT%d- %s"%(self.lastrevision,self.name)
                    
                    with open(os.path.join(self.datap,self.frelp,newnameforhistory), "w") as f:                    
                        olddata = ""
                        with open(os.path.join(self.datap, self.frelp, lastevent.fname),"r") as f2:
                            olddata = f2.read()                            
                        f.write(self.calculateDelta(data,olddata))
                    # we remove the now useless file (TODO : a rollback mechanism).
                    os.unlink(os.path.join(self.datap, self.frelp, lastevent.fname))  
                    
                else:
                    raise VerConError("FIle type %s not supported."%lastevent.type)
                    
                # we move the previous event into history.
                self.events[self.lastrevision].historicize(newnameforhistory)
                # this is necessary so we can add the new E event.
                self.hasE = -1
                
            else:
                raise VerConError("This should not happen. Aborting.")
                
            datafname = "ET%d- %s"%(revision, self.name)
        
        else:
            raise VerConError("File type %s not implemented."%type)
            
        opentype = ""
        if type == "b":
            opentype = "wb"
        elif type == "t":
            opentype = "w"
        else:
            raise VerConError("File type %s not implemented."%type)
         
        with open(os.path.join(self.datap, self.frelp, datafname),opentype) as f:
            f.write(data)            
            
        stinfo = os.stat(filename)
        os.utime(os.path.join(self.datap,self.frelp,datafname),ns=(stinfo.st_atime_ns, stinfo.st_mtime_ns))
        
        self.loadEvent("e", revision, type, datafname)
        self.lastrevision = revision

        self.touch()
        
    def deleteAtRevision(self, revision):
        """
        This is called during a commit when the file is deleted.
        
        This updates the data files accordingly.
        
        Check if double delete.
        """
        self.createBackup(revision)
        
        if revision <= self.lastrevision:
            raise VerConError("You are trying to do a delete at a version (%d) <= the latest version (%d). This is bad."%(revision, self.lastrevision))
            
        if len(self.events) == 0:
            raise VerConError("You are trying to delete a file that has never been committed. That's a no-no")

        lastevent = self.events[self.lastrevision]
        
        if lastevent.event != "e":
            raise VerConError("You are trying to delete an event that is either already deleted, or in a wrong state (final event is a h event instead of e or d). Aborting. (%s)"%self.name)
            
        bit = ""
        if lastevent.type == "b":
            bit = "HB"
        elif lastevent.type == "t":
            bit = "HT"
        else:
            raise VerConError("File type %s not implemented."%lastevent.type)
            
        newnameforhistory = "%s%d- %s"%(bit, self.lastrevision, self.name)
        
        shutil.move(os.path.join(self.datap, self.frelp, lastevent.fname), os.path.join(self.datap, self.frelp, newnameforhistory))
        self.events[self.lastrevision].historicize(newnameforhistory)
        self.hasE = -1
        
        # finally we create the delete event. It's just an empty file.
        
        newname = "D%d- %s"%(revision, self.name)
        with open(os.path.join(self.datap, self.frelp, newname), "w") as f:
            f.write("")
            
        self.loadEvent("d", revision, "b", newname)
        self.lastrevision = revision
        
        self.touch()
        
    def getEventAtRevision(self, revision):
        """
        Returns the event associated with revision, or None if file was not modified at that point.
        """
        if revision in self.events.keys():
            return self.events[revision]
        else:
            return None
            
    def isNewlyCreated(self):
        """
        Returns true if there is only one event.
        """
        return len(self.events.keys()) == 1
        
    def isModified(self):
        """
        Returns true if the file in user space is different than the file in the repository.
        """        
        return not filecmp.cmp(os.path.join(self.rootp, os.path.join(self.frelp, self.name)), self.getLastEventFileNameAndPath(), shallow=False)
        
    def createBackup(self, revision):
        """
        Creates the backup of the file at given revision (for the safety mechanism)
        """
        shutil.copy2(self.getLastEventFileNameAndPath(), os.path.join(self.datap, os.path.join(self.frelp, "BAK%d- %s"%(revision, self.events[self.lastrevision].fname))))
    

class VerConDirectory():
    """
    A helper class representing a hierarchy of directories in the repository.
    A directory contains:
    - a name (its path) --> if empty string "", this is the root directory.
    - children directories
    - a link to the parent
    
    And it can be in status active or deleted depending on the revision on which we are checking.
    
    This class does not handle the physical creation of directories (done during commit instead).
    """
    
    def __init__(self, metadata=[], parent=None):
        """
        Initialization using a list of lines from metadatadir.txt (as taken by readlines())
        lines of the form [<space>,[<space>]...]revision,[revision,[revision...]] directoryname
        
        - if space(s) are present, the directory is a subdirectory of the directory above it.

        - if parent is None, then we create the root and we expect the metadata as coming from a file like above
        - if parent is not none, we expect a 2-uple in the metadata : name, history.
        """
        
        if parent != None:
            self.name = metadata[0]
            self.children = {}
            self.childfiles = {}
            self.history = metadata[1]
            self.parent = parent
            self.maxrevision = metadata[1][-1]
            self.touched = False
        
        else:
            
            # default values (for the root node)
            self.name = ""
            self.children = {}
            self.childfiles = {}
            self.history = [0]
            self.parent = None
            self.maxrevision = 0
            self.touched = False

            # initial level (of the root) is -1
            level = -1
            currentpath = [self]
            lastnode = self
            
            # let's create the tree...
            for line in metadata:        
                data = re.match("^( *)(\d+(?:,\d+)*) (.*)$", line)
                if data != None:
                    newlevel = len(data.group(1))
                    if newlevel > level + 1:
                        raise VerConError("Data integrity issue: too many spaces")     

                    history = []
                    for d in data.group(2).split(","):
                        history.append(int(d))
                        if int(d) > self.maxrevision:
                            self.maxrevision = int(d)
                    name = data.group(3)

                    # do we have a child node?
                    if newlevel == level + 1:
                        currentpath.append(lastnode)
                    # do we have a sibling node?
                    elif newlevel == level:
                        pass
                    # are we going back up the tree?
                    else:
                        currentpath = currentpath[:(level - newlevel)]

                    node = currentpath[-1].addChild(name, history)
                    lastnode = node
                    level = newlevel
                else:
                    raise VerConError("Data integrity issue: line '%s' does not match regexp"%line)                
        

    def addContentFile(self, path, name, fileobject):
        """
        This function adds a new VerConFile object to the directory, possibly to be modified afterwards.
        name : the file name, in the user's sense (not the codes in REPO/DATA).
        path : the relative path of the file.
        fileobject : a new file object.
        
        Raises an exception if the file is already stored.
        
        """
        location = self
        if len(path) > 0:
            bits = path.split(os.sep)
            for b in bits:
                if b not in location.children.keys():
                    raise VerConError("Trying to add a file to a directory that was not initialized, what kind of joke is that")
                
                location = location.children[b]
        
        if name in location.childfiles.keys():
            raise VerConError("Trying to add file %s into database while it already exists."%name)
            
        if fileobject.getLastRevision() > self.maxrevision:
            self.maxrevision = fileobject.getLastRevision() 
        
        location.childfiles[name] = fileobject
        
    def findContentFile(self, path, name):
        """
        Returns a pointer to the file object if "name" is found, or None if not exist.
        """

        location = self
        if len(path) > 0:
            bits = path.split(os.sep)
            for b in bits:
                if b not in location.children.keys():
                    raise VerConError("Trying to find a file in a directory that was not initialized, what kind of joke is that")
                
                location = location.children[b]
        
        if name in location.childfiles.keys():
            return location.childfiles[name]
        
        else:
            return None

    def addChild(self, name, history):
        """
        Here we create a new node, set its history and name, and link it to its parent (self)
        
        returns the created node.
        """
        node = VerConDirectory([name, history], self)
        self.children[name] = node
        return node

    def touch(self):
        """
        Sets self.touched to True. Used for checking which folders were not processed during commit
        (if touch is false after directories are processed, this means folder has been deleted
        at this commit).
        """
        self.touched = True
        
    def isTouched(self):
        """
        Returns True if directory was checked during commit (marked as active).
        """
        return self.touched    

    def markUntouchedDeleted(self, revision):
        """
        Marked directories which has self.touch not true, to deleted.
        
        Returns the number of directories affected. 0 then means no change.
        """
        count = 0
        
        for k,c in self.children.items():
            # we delete active directories that are not touched.
            if not c.isTouched() and c.isActiveAt(revision):
                # print("%s was not touched, changing its status."%k)
                c.toggleState(revision)
                c.touch()
                if revision > self.getMaxRevision():
                    self.maxrevision = revision
                count += 1
            count += c.markUntouchedDeleted(revision)
            
        for k,c in self.childfiles.items():
            # we delete active files that are not touched.
            if (not c.isTouched()) and c.existsAt(revision) :
                # print("we delete a file")
                c.deleteAtRevision(revision)
                count += 1                
            
        return count

    def getMaxRevision(self):
        """
        Returns the maximal revision of the directory database (== last change of a directory in history)
        """
        return self.maxrevision
        
    def setMaxRevision(self, commitnumber):
        """
        Sets the maximal revision of the directory database (== last change of a directory + file in history)
        """
        self.maxrevision = commitnumber

    def getPath(self):
        """
        Returns the current path
        """
        if self.name != "":
            pathbits = [self.name]
        else:
            pathbits = []
        node = self.parent
        while node != None:
            pathbits.append(node.name)
            node = node.parent
            
        pathbits.reverse()
        if len(pathbits) > 1:
            bit = pathbits[0]
            for other in pathbits[1:]:
                bit = os.path.join(bit, other)
            return bit
        elif len(pathbits) == 1:
            return pathbits[0]
        else:
            return ""
        
    def atPath(self, path):
        """
        Returns a VerConDirectory pointer corresponding to the node at this path (relative to root of this directory)
        
        Raises VerConError if the path does not exist.
        
        if path is the empty string, returns self.
        """
        curnode = self
        
        if len(path) > 0:
            bits = path.split(os.sep)
            
            for b in bits:
                if b in curnode.children.keys():
                    curnode = curnode.children[b]
                else:
                    raise VerConError("Directory '%s' is not in repository"%path)
        return curnode
        
    def getChild(self, name):
        """
        Returns the child or None if name is not found.
        """
        if name not in self.children.keys():
            return None
        return self.children[name]
        
    def Add(self, path, revision):
        """
        Adds a new directory as a child somewhere in this current directory (self).
        revision indicates which revision is current.
        
        Recursive add is permitted if some more directories do not exist.
        
        Raises VerConError if path already exists.
        
        Returns the node.
        """
        bits = path.split(os.sep)
        curnode = self
        isnew = False
        for b in bits:
            if b in curnode.children.keys():
                curnode = curnode.children[b]
                if not curnode.isCurrentlyActive():
                    curnode.toggleState(revision)
            else:
                curnode.addChild(b, [revision])
                curnode = curnode.children[b]
                isnew = True
        
        if not isnew:
            raise VerConError("Directory already exists in database.")
            
        return curnode

                   
    def toggleState(self, revision):
        """
        Adds revision as the latest element to the nodes' history.
        This has the effect to activate or desactivate the directory.
        """
        self.history.append(revision)
        # print(self.getPath(), self.history)
                   
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
        
    def hasChildren(self):
        """
        Returns true if there are children.
        """
        return len(self.children) > 0

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
        
    def getDeleteList(self):
        """
        This function returns two lists of directory elements and file elements to delete.
        
        return: (files to delete, directories to delete)
        """
        fd = []
        dd = [self]
        #print("deleting %s"%self.getPath())

        for k,f in self.childfiles.items():
            fd.append(f)


        for k,d in self.children.items():
            rfd,rdd = d.getDeleteList()
            fd.extend(rfd)
            dd.extend(rdd)
            
        return (fd, dd)

    def restoreListPrepare(self, revision, regexp):
        """
        Does the heavy lifting for restoreTo.
        
        Prepares four lists:
        - list of files to delete (VerConFile)
        - list of files to restore
        - list of directories to delete (VerConDirectory)
        - list of directories to create
        
        revision: the revision number to restore to
        regexp: a compiled regular expression used as a filter
        dirElement: the directory root, used to travel recursively.
        
        returns: a 4-uple of lists like indicated above : (files to delete, directories to delete, files to restore, directories to create)   
        """
        filedelete = []
        filerestore = []
        dirdelete = []
        dircreate = []
        
        #print("Entering %s"%self.getPath())

        # the directory did not exist at revision X:
        if not self.isActiveAt(revision):
            #print(" %s not active at %d"%(self.getPath(), revision))
            tmpf, tmpd = self.getDeleteList()
            filedelete.extend(tmpf)
            dirdelete.extend(tmpd)
        else:
            #print(" %s active at %d"%(self.getPath(), revision))
            # here, do something, such as listing the files etc.
            dircreate.append(self)
            for k,f in self.childfiles.items():
                # process the files...
                # we check if matches regexp (this is only checked on FILES).
                if regexp.match(os.path.join(f.frelp, f.name)):
                    #print("Matched %s"%os.path.join(f.frelp, f.name))
                    if f.existsAt(revision):
                        filerestore.append(f)
                    else:
                        filedelete.append(f)
                else:
                    #print("Did not match %s"%os.path.join(f.frelp, f.name))
                    pass
            for k,d in self.children.items():
                tmpfd, tmpfr, tmpdd, tmpdc = d.restoreListPrepare(revision, regexp)
                filedelete.extend(tmpfd)
                filerestore.extend(tmpfr)
                dirdelete.extend(tmpdd)
                dircreate.extend(tmpdc)
        
        #print ("Leaving with:",filedelete, filerestore, dirdelete, dircreate)
                
        return (filedelete, filerestore, dirdelete, dircreate)
        
    def restoreTo(self, revision, regexp, rootdir):
        """
        Restores files and directories to the given revision.
        
        revision: the revision number to restore to
        regexp: a compiled regular expression used as a filter
        
        
        Stage 1 : browse DATA tree for matching directories and files.
        Stage 2 : for each file found, check if currently modified or not
        - if it is, raise exception (unless we ask to restore at last revision, which means we restore without prompting)
        - else:
          * if status is deleted, add file to delete list
          * otherwise, add file to restore list
        - for each directory found, check if currently active or not
          * if not active, check if any files in the subhierarchy are currently modified
          * if yes, crash and burn
          * if no, add file to delete list
          * add subdirs to delete list
          * add dir to delete list
        Stage 3:
        - if we have not failed here, perform the deletions / restores.  
        
        
        """       
        # Stage 1.
        filedelete, filerestore, dirdelete, dircreate = self.restoreListPrepare(revision, regexp)
        
        # print (filedelete, filerestore, dirdelete, dircreate)
        
        # Stage 2. Is something modified...
        # Stage 2a. ... in the files to be restored or deleted?
        for f in filerestore + filedelete:
            try:
                if f.isModified() and revision != self.getMaxRevision():
                    raise VerConError("%s is modified after last commit ; aborting. Please revert to last commit and retry, or commit your changes and retry."%(os.path.join(f.frelp, f.name)))
            except FileNotFoundError:
                # if the file is not found, then we just restore it.
                print("%s has been deleted in user space, we will just restore it as is (or ignore it)"%(os.path.join(f.frelp, f.name)))
            
            
        # Stage 2b. ... in the directories to be deleted?
        for d in dirdelete:
            self.CheckModifiedOrNewFilesInDir(revision, rootdir, d.getPath())
            
        # Stage 3: let's revert stuff!
        # 3.1 first create directories (if necessary)
        for d in dircreate:
            if os.path.exists(os.path.join(rootdir, d.getPath())):
                if not os.path.isdir(os.path.join(rootdir, d.getPath())):
                    raise VerConError("Trying to recreate %s but there is a file with the same name, aborting"%d.getPath())
            else:
                os.mkdir(os.path.join(rootdir, d.getPath()))
                
        # 3.2 then let's restore the files
        for f in filerestore:
            mode = "w"
            if f.fTypeAt(revision) == "b":
                mode = "wb"
            with open(os.path.join(rootdir, f.frelp, f.name), mode) as out:
                out.write(f.contentsAt(revision))
                
        # 3.3 finally we delete the files we don't want
        for f in filedelete:
            try:
                os.unlink(os.path.join(rootdir, f.frelp, f.name))
            except:
                raise VerConError("Could not delete %s, are you currently editing it?"%os.path.join(f.frelp, f.name))
                
        # 3.4 and the directories
        for d in dirdelete:
            try:
                os.rmdir(os.path.join(rootdir, d.getPath()))
            except FileNotFoundError:
                print("We can't remove a directory %s that has already been removed, skipping."%d.getPath())
            except:
                raise VerConError("Trying to remove a non-empty directory %s"%d.getPath())
                    
    
    def CheckModifiedOrNewFilesInDir(self, revision, rootdir, path):
        """
        This helper function raises VerConError if it finds a modified file in the tree
        under a directory that is flagged as "deletable" by restore To.
        """
        try:
            for item in os.scandir(os.path.join(rootdir, path)):
                if item.is_dir() and item.name != "REPO":
                    try:
                        d = self.atPath(os.path.join(path, item.name))
                    except VerConError:
                        raise VerConError("%s is a directory not committed to the tree. Please delete this directory or commit it. Aborting."%os.path.join(path, item.name))
                    self.CheckModifiedOrNewFilesInDir(rootdir, os.path.join(path, item.name))
                elif item.is_file():
                    f = None
                    try:
                        f = self.findContentFile(path, item.name)                    
                    except VerConError:
                        raise VerConError("%s is a file not committed to the tree. Please delete this file or commit it. Aborting."%os.path.join(path, item.name))
                    if f.isModified() and revision != self.getMaxRevision():
                        raise VerConError("%s has been modified since last commit, please revert or commit changes."%os.path.join(path, item.name))
        except FileNotFoundError:
            print("It seems that %s is not present in user space, skipping."%os.path.join(rootdir, path))
        
    def Serialize(self,level=-1, debug=False):
        """
        Returns a list of lines that can then be written into a file.
        
        If debug is true, also prints the list of files in the repository.
        """
        lines = []
        
        # if we are at root, we skip this.
        if self.name != "":        
            name = self.name
            history = self.history
            line = "%s"%(' '*level)
            h=[]
            for i in history:
                h.append(str(i))
            line += ",".join(h)
            line += " %s"%name
            lines.append(line)
        
        if debug:
            for f in sorted(self.childfiles.keys()):
                lines.append("%s- %s"%(' '*level, self.childfiles[f].__repr__()))      
        if self.hasChildren():                
            for k in sorted(self.children.keys()):
                lines.extend(self.children[k].Serialize(level + 1, debug=debug))

        return lines    
        
    def __repr__(self):
        """ Pretty printout """

        return  "\n".join(self.Serialize())
        
        
    def generateCommitLog(self, lastcommit):
        """
        Generates the log file and appends it to REPO/commits.txt
        
        Should be called at the end of each commit.
        
        dirdb: the current root.
        
        returns a list of lines to write to commits.txt.
        """
        
        lines = []
        
        if self.name != "":
            if self.history[-1] == lastcommit:
                if len(self.history) %2 == 0:
                    lines.append("  -d %s"%self.name)
                else:
                    lines.append("  +d %s"%self.name)                    
        for k,f in sorted(self.childfiles.items()):
            e = f.getEventAtRevision(lastcommit)
            if e != None:
                token = ""
                if e.event == "e":
                    if f.isNewlyCreated():
                        token = "+f%s"%e.type
                    else:
                        token = "*f%s"%e.type
                elif e.event == "h":
                    # pass, but this should not happen.
                    pass
                else:
                    token = "-f"
                lines.append("  %s %s"%(token, os.path.join(f.frelp,f.name)))
        for k, d in sorted(self.children.items()):
            lines.extend(d.generateCommitLog(lastcommit))
        
        # print(lines)
        return lines

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
        self.lastcommit = 0
        self.dirDb = None
        
        path = os.path.abspath(directory)
        drive,path = os.path.splitdrive(path)
        while len(path)>1 and self.repodir == None: # path will contain a leading / or \
            if not os.path.isdir(os.path.join(drive, path, "REPO")):
                path,end=os.path.split(path)
            else:
                self.datadir = os.path.join(drive,path,"REPO","DATA")
                self.repodir = os.path.join(drive,path,"REPO")
                self.basedir = os.path.join(drive,path)
                with open(os.path.join(self.repodir, "metadatadir.txt"),"r") as f:
                    self.dirDb   = VerConDirectory(f.readlines())
                    self.precomputeFileDB(self.datadir, "")
                    
                    self.lastcommit = max(self.dirDb.getMaxRevision(), self.lastcommit)
                    self.dirDb.setMaxRevision(self.lastcommit)
                    

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
            self.dirDb = VerConDirectory([])
            
    def getRepoDir(self):
        """
        Helper function that returns the REPO directory used by the version control system.
        """
        return self.repodir
        
    def getDataDir(self):
        """
        Helper function that returns the DATA directory used by the vcs.
        """
        return self.datadir
        
    def getBaseDir(self):
        """
        Helper function that returns the root directory of the repository (containing REPO as well as the rest)
        """
        return self.basedir
        
    def getLastCommit(self):
        """
        Returns the revision number of the last commit.
        """
        return self.lastcommit
        
    def commit(self, comment):
        """ commit changes to the repository in or above directory, with comment comment.
            creates new repository in directory if none found.
        """

        # Stage 0 : precompute file database. Now done in constructor.
        # self.precomputeFileDB(self.getDataDir(), "")
        
        # Stage 1 : check directories and files
        # print("Commit number %d"%self.lastcommit)
        newcommit = self.commitDirectories(self.lastcommit, self.getBaseDir(), "")
        
        # Stage 2 : check if anything is to be deleted:
        count = self.dirDb.markUntouchedDeleted(self.lastcommit + 1)
        if count > 0:
            haschanged = True
            newcommit = self.lastcommit + 1

        # Stage 3 : if something changed, save directory database.
        if newcommit > self.lastcommit:
            self.backupMetadata(newcommit)
            self.lastcommit = newcommit
                        
            with open(os.path.join(self.repodir, "metadatadir.txt"),"w") as f:
                f.write(self.dirDb.__repr__())
                       
            lines = ["%d. %s"%(self.lastcommit, comment)]
        
            lines.extend(self.dirDb.generateCommitLog(self.lastcommit))
            
            with open(os.path.join(self.repodir, "commits.txt"), "a") as f:
                f.write("\n".join(lines))
                f.write("\n\n")
                
    def backupMetadata(self, commitnumber):
        """
        This function saves metadatadir.txt and commits.txt into a backup of current commit.
        We suppose a clean directory.
        """
        shutil.copy2(os.path.join(self.repodir, "metadatadir.txt"),os.path.join(self.repodir, "BAK%d- metadatadir.txt"%commitnumber))
        shutil.copy2(os.path.join(self.repodir, "commits.txt"),os.path.join(self.repodir, "BAK%d- commits.txt"%commitnumber))            
        
    def commitDirectories(self, commitnumber, baseDir, relPath):
        """
        Checks for directories and adds, commits, or deletes them depending on their situation.
        
        For each directory, checks if files were modified. If so, commits the file change, depending on the situation.
        Files in deleted directories will be marked as deleted.
        
        Returns the commit number : same as commitnumber if nothing changed, commitnumber+1 if something changed.
        """
        haschanged = False
        newcommit = commitnumber + 1
        hasrepo = False
        
        # this is the root directory (relative to where we are talking about).
        rdir = self.dirDb.atPath(relPath)
        
        for item in os.scandir(baseDir):
            if item.is_dir() and item.name != "REPO":
                try:
                    #print("Checking if %s exists in db"%os.path.join(relPath, item.name))
                    dir = self.dirDb.atPath(os.path.join(relPath, item.name))
                    #print("It exists, continue.")
                    if not dir.isCurrentlyActive():
                        # print("reactivating %s"%dir.getPath())
                        dir.toggleState(newcommit)
                        haschanged = True
                        dir.touch()
                    # it already exists and is already active, we just touch it.
                    else:
                        dir.touch()
                    
                except VerConError:
                    # the directory did not exist, we create it in the db + physically in REPO/DATA
                    dir = self.dirDb.Add(os.path.join(relPath, item.name),newcommit)
                    dir.touch()
                    #print("Creating %s"%os.path.join(self.getDataDir(), relPath, item.name))
                    os.mkdir(os.path.join(self.getDataDir(), relPath, item.name))
                    haschanged = True         
                
                # recursive call for directory's childrens
                commit = self.commitDirectories(commitnumber, os.path.join(baseDir, item.name), os.path.join(relPath, item.name))
                if commit != commitnumber:
                    haschanged = True
            # let's handle file changes.
            elif item.is_file():
                fobj = rdir.findContentFile("", item.name)
                # file is already in database, let's see if it was modified...
                if fobj != None:
                    #print("Found file %s (working in %s)"%(fobj, relPath))
                    if fobj.isModified():
                        #print("- %s has changed."%fobj)
                        fobj.changeAtRevision(newcommit)
                        #print("- %s is now this"%fobj)
                        haschanged = True
                    else:
                        # we touch fobj, so as to avoid its deletion.
                        # but the directory has not changed.
                        #print("- %s has not changed."%fobj)
                        fobj.touch()
                # file not in database, we just add it...
                else:
                    fobj = VerConFile(item.name, self.getBaseDir(), self.getDataDir(), relPath)
                    fobj.createAtRevision(newcommit)
                    rdir.addContentFile("", item.name, fobj)
                    # print("we add file %s"%item.name)
                    haschanged = True
                            
        if haschanged:
            return newcommit
        else:
            return commitnumber
            
        
                                    
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
        
    def restoreTo(self, revision=None, filter=".*"):
        """ reverts change to a given revision.
        
        revision : if omitted, the repository is refreshed to last commit.
                    otherwise will revert to a previous commit, indicated by number
                    (note : using number of last commit has same effect as "cur")
                    if the revision to be reverted is equal to the last commit,
                    then the files will forcibly be erased, even if they were modified.
                    
                    Otherwise an exception will be raised if files to be reverted have been modified after
                    last commit.
        filter: a regular expression that will match file(s) or directory(ies) to be reverted.
                    This matches to the path. THe default will match all files and directories.
        """
        
        if revision == None or revision == self.lastcommit:
            revision = self.lastcommit
        
        if revision > self.lastcommit or revision <= 0:
            raise VerConError("Trying to revert to a revision %d that has not been yet created"%revision)
        
        try:
            match = re.compile(filter, re.I)
        except re.error:
            raise VerConError("Invalid filter provided %s"%filter)
        
        self.dirDb.restoreTo(revision, match, self.getBaseDir())
        
    def precomputeFileDB(self,dataDir, relPath):
        """
        This function is in charge of the IO. From REPO/DATA, it checks all the file bits and creates the
        corresponding FileObjects and stores them in self.dirDB(if they do not already exist in self.dirDB), populating them with events
        as they go (the browsing may not be in order).
        
        If not called, all committed files will be committed as "new".
        
        It is also in charge of updating the last revision if one is found to be higher than the existing.
        """
        regevent = re.compile("^([EH][BT]|D)(\d+)- (.+)$", re.I)
        regin = re.compile("^([EH])([BT])", re.I)
        for item in os.scandir(os.path.join(dataDir, relPath)):
            if item.is_file():
                match = regevent.match(item.name)
                if match != None:
                    evt = match.group(1)
                    rev = int(match.group(2))
                    name = match.group(3)
                    
                    if rev > self.lastcommit:
                        self.lastcommit = rev
                        # print("self.lastcommit is now at revision %d"%rev)
                    
                    obj = self.getFileObject(relPath, name)
                    
                    # no object, we create a new one.
                    if obj == None:
                        obj = VerConFile(name, self.getBaseDir(), self.getDataDir(), relPath)
                        self.dirDb.addContentFile(relPath, name, obj)
                        
                    if evt == "D":
                        obj.loadEvent("d", rev, "b", item.name)
                    
                    else:
                        match = regin.match(evt)
                        if match == None:
                            raise VerConError("Honestly I have no idea how you landed here.")
                        
                        evt = match.group(1).lower()
                        typ = match.group(2).lower()
                        
                        obj.loadEvent(evt, rev, typ, item.name)
            if item.is_dir():
                self.precomputeFileDB(dataDir, os.path.join(relPath, item.name))
                
        
    def getFileObject(self, path, name):
        """ Helper function. Returns the file object as it exists in dirDb.
        
        Returns None if file not found.
        
        path is relative to root of tree (without ".")"""
        
        return self.dirDb.findContentFile(path, name)
        
    def __repr__(self):
        """
        Pretty print, for debug purposes.
        """
        return "VerConRepository: last revision %d, directory database:\n%s"%(self.lastcommit, "\n".join(self.dirDb.Serialize(debug=True)))

        
if __name__ == "__main__":
    usagestring = "Usage: %s commit comment\n%s revert [revision number [filter (a regular expression)]]\n %s list [verbose]"%(sys.argv[0],sys.argv[0],sys.argv[0])
    if len(sys.argv) == 1:
        print(usagestring)
    else:
        if sys.argv[1].lower() == "commit":
            if len(sys.argv) == 2:
                print(usagestring)
            else:
                comment = " ".join(sys.argv[2:])
                vc = VerConRepository(".")
                vc.commit(comment)
                
        elif sys.argv[1].lower() == "revert":
            revision = None
            filter = ".*"
            if len(sys.argv) == 3:
                revision = int(sys.argv[2])
            if len(sys.argv) == 4:
                filter = sys.argv[4]

            vc = VerConRepository(".")
            vc.revertTo(revision, filter)

        elif sys.argv[1].lower() == "list":
            vc = VerConRepository(".")
            if len(sys.argv) == 3 and sys.argv[3].lower() == "verbose":
                vc.list(1)
            else:
                vc.list()
        else:
            print(usagestring)
            
