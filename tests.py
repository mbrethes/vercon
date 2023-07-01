"""
VerCon (VC)
-----------

Tests for a simple version control system for a single user.

This is part of package VerCon.

Released under GPL v3.
(c) 2023 by Mathieu Brèthes
"""

import unittest, os, tempfile
from vc import VerConRepository, VerConDirectory, VerConError

class TestConstructor(unittest.TestCase):
    """
    General tests for the constructor of VerConRepository.
    """

    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.tempDir.cleanup()

    def test_emptyRepo(self):
        """
        - a test repository is created in a mock directory by calling the constructor
        - the test repository should contain:
          * the REPO directory
          * the REPO/DATA directory
          * an empty metadatadir.txt file
          * an empty commits.txt file
        """
        setupDir = self.tempDir.name
        repodir = os.path.join(self.tempDir.name, "REPO")
        rep = VerConRepository(setupDir)
        self.assertTrue(os.path.isdir(repodir), "REPO directory not created")
        self.assertTrue(os.path.isdir(os.path.join(repodir,"DATA")), "DATA directory not created")
        self.assertTrue(os.path.isfile(os.path.join(repodir, "metadatadir.txt")), "metadatadir.txt is missing in REPO")
        self.assertTrue(os.path.isfile(os.path.join(repodir, "commits.txt")), "commits.txt is missing in REPO")
        self.assertEqual(os.path.getsize(os.path.join(repodir, "metadatadir.txt")),0, "metadatadir.txt is not empty?")
        self.assertEqual(os.path.getsize(os.path.join(repodir, "commits.txt")),0, "commits.txt is not empty?")
        
    def test_existRepo(self):
        """
        - there is an existing repository in a the folder, containing non-empty data files.
        - the data files should not be erased or reset.
        """
        repodir = os.path.join(self.tempDir.name, "REPO")
        garbage = "Random garbage"
        os.mkdir(repodir)
        with open(os.path.join(repodir, "metadatadir.txt"),"w") as f:
            f.write(garbage)
        with open(os.path.join(repodir, "commits.txt"),"w") as f:
            f.write(garbage)
            
        rep = VerConRepository(self.tempDir.name)
        
        with open(os.path.join(repodir, "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), garbage)
        with open(os.path.join(repodir, "commits.txt"),"r") as f:
            self.assertEqual(f.read(), garbage)
        
    def test_repoHierarchy(self):
        """
        - there is an existing repository in the parent folder of the test folder, containing non-empty data files.
        - there should be no REPO created in the test folder itself
        - the REPO of parent folder should be left alone without touching
        """
        
        childdir = os.path.join(self.tempDir.name, "child")
        repodir = os.path.join(self.tempDir.name, "REPO")
        garbage = "Random garbage"
        
        os.mkdir(childdir)
        os.mkdir(repodir)

        with open(os.path.join(repodir, "metadatadir.txt"),"w") as f:
            f.write(garbage)
        with open(os.path.join(repodir, "commits.txt"),"w") as f:
            f.write(garbage)        

        rep = VerConRepository(childdir)
        self.assertFalse(os.path.isdir(os.path.join(childdir,"REPO")))
        
        with open(os.path.join(repodir, "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), garbage)
        with open(os.path.join(repodir, "commits.txt"),"r") as f:
            self.assertEqual(f.read(), garbage)        
            
            
    def test_repoHierarchy2(self):
        """
        - if two parents contain a REPO directory, the svn folder should use the one closest to the directory
          on which it is invoked, not the one at the bottom:
          .../ A (REPO) / B (REPO) / C (invokation) --> uses B (REPO)
        """
        
        childdir = os.path.join(self.tempDir.name, "child")
        childdir2 = os.path.join(childdir, "grandchild")
        repodir = os.path.join(self.tempDir.name, "REPO")
        repodir2 = os.path.join(childdir, "REPO")
        garbage = "Random garbage"
        
        os.mkdir(childdir)
        os.mkdir(repodir)
        os.mkdir(repodir2)
        os.mkdir(childdir2)

        with open(os.path.join(repodir, "metadatadir.txt"),"w") as f:
            f.write(garbage)
        with open(os.path.join(repodir, "commits.txt"),"w") as f:
            f.write(garbage)        
        with open(os.path.join(repodir2, "metadatadir.txt"),"w") as f:
            f.write(garbage)
        with open(os.path.join(repodir2, "commits.txt"),"w") as f:
            f.write(garbage)    

        rep = VerConRepository(childdir2)
        self.assertTrue(rep.getBaseDir(), childdir)
        self.assertTrue(rep.getRepoDir(), repodir2)

class TestLogging(unittest.TestCase):
    """
    Specific tests for the display of logging information.
    """

    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.tempDir.cleanup()

    def test_showLog(self):
        """ checks whether the log function displays the log file. """
        
        repodir = os.path.join(self.tempDir.name, "REPO")
        os.mkdir(repodir)
        logdata = "1. initial commit\n  +file A\n2. second commit\n  +file B"
        minlogd = "1. initial commit\n2. second commit\n"
        with open(os.path.join(repodir, "metadatadir.txt"),"w") as f:
            f.write("bleh")
        with open(os.path.join(repodir, "commits.txt"),"w") as f:
            f.write(logdata)
        rep = VerConRepository(self.tempDir.name)
        
        self.assertEqual(logdata, rep.list(1), "Verbose data incorrect")
        self.assertEqual(minlogd, rep.list(), "non-verbose data incorrect")                

class TestDirectory(unittest.TestCase):
    """
    Unit tests checking if the Directory class properly works.
    """
    
    def test_metadata(self):
        """
        A test to see if proper metadata works, and improper metadata fails.
        """
        
        propermetadata = "1,2,3 ./test"
        improper="1,2,3, ./test"
        
        good = VerConDirectory(propermetadata)
        self.assertEqual(good.getPath(), "./test")
        
        with self.assertRaises(VerConError):
            bad = VerConDirectory(improper)
            
    def test_active(self):
        """
        A test to see if a given directory is active or inactive
        
        First test case also allows to check if manual creation works
        """
        
        rev2 = VerConDirectory("./test", 2)
        self.assertEqual(rev2.getPath(), "./test")
        self.assertTrue(rev2.isCurrentlyActive())
        self.assertFalse(rev2.isActiveAt(1))
        self.assertTrue(rev2.isActiveAt(2))
        self.assertTrue(rev2.isActiveAt(3))
        
        revm = VerConDirectory("1,3 ./test")
        self.assertFalse(revm.isCurrentlyActive())
        self.assertTrue(revm.isActiveAt(1))
        self.assertTrue(revm.isActiveAt(2))
        self.assertFalse(revm.isActiveAt(3))      
        self.assertFalse(revm.isActiveAt(4))            
        
        revrev = VerConDirectory("1,3,5 ./test")
        self.assertTrue(revrev.isCurrentlyActive())
        self.assertTrue(revrev.isActiveAt(1))
        self.assertTrue(revrev.isActiveAt(2))
        self.assertFalse(revrev.isActiveAt(3))      
        self.assertFalse(revrev.isActiveAt(4))       
        self.assertTrue(revrev.isActiveAt(5))   
        self.assertTrue(revrev.isActiveAt(6))           

class TestCommitDirectories(unittest.TestCase):
    """
    Unit tests related to the commit ability for directories.
    """
    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.tempDir.cleanup()
    
    def test_commitDirectory(self):
        """
        In this first test, we create and add a directory to the repository,
        commit it, and check whether the directory appears as committed in
        the metadata file, and if it appears in the REPO structure.
        """
        
        dirname = "test"
                
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getRepoDir(), "DATA", dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1 %s\n"%dirname)
            
    def test_commitSubdirectory(self):
        """ But can it handle... A subdirectory?? """
        
        dirname = os.path.join("test","test2")
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getRepoDir(), "DATA", dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1 %s\n1 %s\n"%("test", dirname))        
            
            
    def test_commitAndDelete(self):
        """ Is the directory still present when deleted, but indicated as such in the metadata? """
        dirname = "test"
                
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        os.rmdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Second test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getRepoDir(), "DATA", dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1,2 %s\n"%dirname)        
        
        
    def test_commitDeleteRecreate(self):
        """ So is the directory live again? After this, I think we are good. """
        dirname = "test"
                
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        os.rmdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Second test")
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Third test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getRepoDir(), "DATA", dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1,2,3 %s\n"%dirname)            
        


if __name__ == '__main__':
    unittest.main()