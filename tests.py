"""
VerCon (VC)
-----------

Tests for a simple version control system for a single user.

This is part of package VerCon.

Released under GPL v3.
(c) 2023 by Mathieu Brèthes
"""

import unittest, os, tempfile, difflib,shutil
from vc import VerConRepository, VerConDirectory, VerConError, VerConFile

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
        datadir = os.path.join(repodir, "DATA")
        garbage = "1 Random garbage"
        os.mkdir(repodir)
        os.mkdir(datadir)
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
        datadir = os.path.join(repodir, "DATA")
        garbage = "1 Random garbage"
        
        os.mkdir(childdir)
        os.mkdir(repodir)
        os.mkdir(datadir)

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
        datadir = os.path.join(repodir2, "DATA")
        garbage = "1 Random garbage"
        
        os.mkdir(childdir)
        os.mkdir(repodir)
        os.mkdir(repodir2)
        os.mkdir(childdir2)
        os.mkdir(datadir)

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
        datadir = os.path.join(repodir, "DATA")
        os.mkdir(repodir)
        os.mkdir(datadir)
        logdata = "1. initial commit\n  +file A\n2. second commit\n  +file B"
        minlogd = "1. initial commit\n2. second commit\n"
        with open(os.path.join(repodir, "metadatadir.txt"),"w") as f:
            f.write("1 bleh")
        with open(os.path.join(repodir, "commits.txt"),"w") as f:
            f.write(logdata)
        rep = VerConRepository(self.tempDir.name)
        
        self.assertEqual(logdata, rep.list(1), "Verbose data incorrect")
        self.assertEqual(minlogd, rep.list(), "non-verbose data incorrect")                

class TestVerConDirectory(unittest.TestCase):
    """
    Unit tests checking if the VerConDirectory class properly works.
    """
    
    def test_metadata(self):
        """
        A test to see if proper metadata works, and improper metadata fails.
        """
        
        propermetadata = ["1,2,3 test"]
        improper=["1,2,3, test"]
        
        good = VerConDirectory(propermetadata)
        self.assertTrue(good.atPath("test") != None)
        
        with self.assertRaises(VerConError):
            bad = VerConDirectory(improper)
            
    def test_noSuchDir(self):
        """
        A test to see what happens if we request a directory that does not exist in the database."
        """
        propermetadata = ["1,2,3 test"]
        
        good = VerConDirectory(propermetadata)
        self.assertTrue(good.atPath("test") != None)
        
        with self.assertRaises(VerConError):
            self.assertTrue(good.atPath("unobtain") != None)     
        
            
    def test_active(self):
        """
        A test to see if a given directory is active or inactive
        
        First test case also allows to check if manual creation works
        """

        rev2 = VerConDirectory(["2 test"])
        self.assertTrue(rev2.atPath("test").isCurrentlyActive())
        self.assertFalse(rev2.atPath("test").isActiveAt(1))
        self.assertTrue(rev2.atPath("test").isActiveAt(2))
        self.assertTrue(rev2.atPath("test").isActiveAt(3))
        
        revm = VerConDirectory(["1,3 test"])
        self.assertFalse(revm.atPath("test").isCurrentlyActive())
        self.assertTrue(revm.atPath("test").isActiveAt(1))
        self.assertTrue(revm.atPath("test").isActiveAt(2))
        self.assertFalse(revm.atPath("test").isActiveAt(3))      
        self.assertFalse(revm.atPath("test").isActiveAt(4))            
        
        revrev = VerConDirectory(["1,3,5 test"])
        self.assertTrue(revrev.atPath("test").isCurrentlyActive())
        self.assertTrue(revrev.atPath("test").isActiveAt(1))
        self.assertTrue(revrev.atPath("test").isActiveAt(2))
        self.assertFalse(revrev.atPath("test").isActiveAt(3))      
        self.assertFalse(revrev.atPath("test").isActiveAt(4))       
        self.assertTrue(revrev.atPath("test").isActiveAt(5))   
        self.assertTrue(revrev.atPath("test").isActiveAt(6))           
        
    def test_child(self):
        """
        This test sees if directories are correctly created when a hierarchy is sent
        as a parameter.
        """
        
        # first a test with a child
        dirs = VerConDirectory(["1 test", " 1 subtest"])
        self.assertTrue(dirs.atPath("test").isCurrentlyActive())
        self.assertTrue(dirs.atPath(os.path.join("test", "subtest")).isCurrentlyActive())
        with self.assertRaises(VerConError):
            self.assertTrue(dirs.atPath("subtest").isCurrentlyActive())
            
        # now check if children functionnality works
        dir = dirs.atPath("test")
        self.assertTrue(dir.atPath("subtest").isCurrentlyActive())

        # then a test with 2 first-level directory
        dirs = VerConDirectory(["1 test", "1 test2"])
        self.assertTrue(dirs.atPath("test").isCurrentlyActive())
        self.assertTrue(dirs.atPath("test2").isCurrentlyActive())
        with self.assertRaises(VerConError):
            self.assertTrue(dirs.atPath(os.path.join("test", "test2")).isCurrentlyActive())
            

    def test_addDir(self):
        """
        This tests if it is possible to add a child to an existing directory.
        """
        
        dirs = VerConDirectory()
        
        dirs.Add("test", 1)
        self.assertTrue(dirs.atPath("test").isCurrentlyActive())
        
        dirs.Add("test2", 1)
        self.assertTrue(dirs.atPath("test2").isCurrentlyActive())
        
        dirs.Add(os.path.join("test3","subtest"), 1)
        self.assertTrue(dirs.atPath(os.path.join("test3","subtest")).isCurrentlyActive())        
        
        with self.assertRaises(VerConError):
            self.assertTrue(dirs.atPath("subtest") != None)     
            
        # we also ensure we can't create a directory twice
        with self.assertRaises(VerConError):
            self.assertTrue(dirs.Add("test", 1) != None)
            
        # can we add to an existing branch?
        dirs.Add(os.path.join("test","test3"),1)
        self.assertTrue(dirs.atPath(os.path.join("test","test3")).isCurrentlyActive())
        
    def test_addOnDeleted(self):
        """
        This tests if a directory added to a deleted directory, will reopen the directory
        with the correct revision number.
        """
        dirs = VerConDirectory(["1,2 test"])       
        dirs.Add(os.path.join("test","test2"),3)
        self.assertTrue(dirs.atPath("test").isCurrentlyActive())
        self.assertFalse(dirs.atPath("test").isActiveAt(2))
        self.assertTrue(dirs.atPath("test").isActiveAt(3))
        
    def test_serialize(self):
        """
        This tests if the directory class can output the file in the same state as it was input,
        and etc.
        """
        
        data = ["1 test"," 1 subtest","1 zorgl", " 1,2 bleh", " 1 car"]
        updd = ["1 test"," 1 subtest","1 zorgl", " 1,2,3 bleh", "  3 bar", "  3 foo"," 1 car"]
        
        dirs = VerConDirectory(data)
        self.assertEqual(dirs.Serialize(), data)
        dirs.Add(os.path.join("zorgl", "bleh", "foo"), 3)
        dirs.Add(os.path.join("zorgl", "bleh", "bar"), 3)
        self.assertEqual(dirs.Serialize(), updd)
        


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
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getDataDir(), dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1 %s"%dirname)
            
    def test_commitSubdirectory(self):
        """ But can it handle... A subdirectory?? """
        
        dirname = os.path.join("test","test2")
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,"test"))
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getDataDir(), dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1 %s\n 1 %s"%("test", "test2"))        
            
            
    def test_commitAndDelete(self):
        """ Is the directory still present when deleted, but indicated as such in the metadata? """
        dirname = "test"
                
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        
        vc = VerConRepository(self.tempDir.name)        
        os.rmdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Second test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getDataDir(), dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1,2 %s"%dirname)        
        
        
    def test_commitDeleteRecreate(self):
        """ So is the directory live again? After this, I think we are good. """
        dirname = "test"
                
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("First test")
        
        vc = VerConRepository(self.tempDir.name)        
        os.rmdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Second test")
        
        vc = VerConRepository(self.tempDir.name)        
        os.mkdir(os.path.join(self.tempDir.name,dirname))
        vc.commit("Third test")
        
        self.assertTrue(os.path.isdir(os.path.join(vc.getDataDir(), dirname)), "%s not created in REPO/DATA"%dirname)
        with open(os.path.join(vc.getRepoDir(), "metadatadir.txt"),"r") as f:
            self.assertEqual(f.read(), "1,2,3 %s"%dirname)            
        
class TestRevision(unittest.TestCase):
    """
    This class tests the various possibilities of revision problems.
    """
    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        
    def tearDown(self):
        self.tempDir.cleanup()
    
    def test_emptyRepo(self):
        """
        If this is a new repository, then revision number is 0.
        """
        vc = VerConRepository(self.tempDir.name)
        self.assertEqual(vc.getLastCommit(), 0)
        
    def test_loadedDirectories(self):
        """
        Tests if the repository correctly reports that the latest commit equals the highest number in the file.
        """
        os.mkdir(os.path.join(self.tempDir.name,"REPO"))    
        os.mkdir(os.path.join(self.tempDir.name,"REPO","DATA"))
        with open(os.path.join(self.tempDir.name,"REPO","metadatadir.txt"), "w") as f:
            f.write("1 test")
        
        vc = VerConRepository(self.tempDir.name)
        self.assertEqual(vc.getLastCommit(), 1)
        
        with open(os.path.join(self.tempDir.name,"REPO","metadatadir.txt"), "w") as f:
            f.write("1 test\n 1,2 subtest")
        
        vc = VerConRepository(self.tempDir.name)
        self.assertEqual(vc.getLastCommit(), 2)        
        
    def test_aftercommitsofadir(self):
        """
        Tests if the repository correctly gets incremented when a directory is added to the repository.
        """
        
        vc = VerConRepository(self.tempDir.name)
        
        os.mkdir(os.path.join(self.tempDir.name,"test"))
        vc.commit("first commit")
        
        self.assertEqual(vc.getLastCommit(), 1)        

        vc = VerConRepository(self.tempDir.name)

        os.rmdir(os.path.join(self.tempDir.name,"test"))
        vc.commit("second commit")
        self.assertEqual(vc.getLastCommit(), 2)          
        
        
class TestCommitFiles(unittest.TestCase):
    """
    And finally, the class to test what happens when files are committed!
    
    The program needs to:
    a) differentiate between binary and text file
    b) be able to regenerate the file contents at any revision
    c) store when files are deleted or not deleted.
    """
    
    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        self.datat = "some text\nextra text\n"
        self.datab = bytes.fromhex('d3ad b33f 0100 0011')
        
    def tearDown(self):
        self.tempDir.cleanup()
        
    def test_commitNewFiles(self,nocheck=False):
        """
        The most simple test. We create two files in the repository
        and commit them : a binary file, and a text file. Are the files stored in the database?
        Do the files contain the correct data?
        
        set nocheck to True to skip the checks (useful if you call this test from another test as a setup)
        
        """
        
        vc = VerConRepository(self.tempDir.name)
        
        datat = self.datat
        datab = self.datab
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)
            
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)
            
        vc.commit("no reason")
        
        if not nocheck:
            self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "ET1- textfile.txt")), "ET1- textfile.txt not created in REPO/DATA")
            self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "EB1- binfile.bin")), "EB1- binfile.bin not created in REPO/DATA")       

            with open(   os.path.join(vc.getDataDir(), "ET1- textfile.txt"),"r") as f:
                self.assertEqual(f.read(), datat)
                
            with open(os.path.join(vc.getDataDir(), "EB1- binfile.bin"), "rb") as f:
                self.assertEqual(f.read(), datab)
            
    def test_commitAndDelete(self):
        """
        We will now delete both files, are the deleted files stored in database?
        """
        self.test_commitNewFiles(True)
        
        datat = self.datat
        datab = self.datab
        
        os.unlink(os.path.join(self.tempDir.name, "textfile.txt"))
        os.unlink(os.path.join(self.tempDir.name, "binfile.bin"))
        
        # what is the sequence of operations to transform new revision ("") into old revision (datat)?
        differ = difflib.SequenceMatcher(a="", b=datat)
        data = differ.get_opcodes()
        datah = []
        for tag, i1, i2, j1, j2 in data:
            if tag == "insert":
                datah.append("i %d\n%s"%(j2-j1, datat[j1:j2]))
            elif tag == "replace":
                datah.append("s %d"%(i2-i1))
                datah.append("i %d\n%s"%(j2-j1, datat[j1:j2]))
            elif tag == "delete":
                datah.append("s %d"%(i2-i1))
            else:
                datah.append("c %d"%(i2-i1))
        datah = "\n".join(datah)
        # print(datah)
        
        vc = VerConRepository(self.tempDir.name)
        vc.commit("deleted those files")


        self.assertFalse(os.path.isfile(os.path.join(vc.getDataDir(), "ET1- textfile.txt")), "ET1- textfile.txt is still in REPO/DATA")
        self.assertFalse(os.path.isfile(os.path.join(vc.getDataDir(), "EB1- binfile.bin")), "EB1- binfile.bin is still in REPO/DATA")    
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "HT1- textfile.txt")), "HT1- textfile.txt not created in REPO/DATA")
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "HB1- binfile.bin")), "HB1- binfile.bin not created in REPO/DATA")               
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "D2- textfile.txt")), "D2- textfile.txt not created in REPO/DATA")
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "D2- binfile.bin")), "D2- binfile.bin not created in REPO/DATA")       

        with open(   os.path.join(vc.getDataDir(), "D2- textfile.txt"),"r") as f:
            self.assertEqual(f.read(), "")
            
        with open(os.path.join(vc.getDataDir(), "D2- binfile.bin"), "r") as f:
            self.assertEqual(f.read(), "")        

        with open(   os.path.join(vc.getDataDir(), "HT1- textfile.txt"),"r") as f:
            self.assertEqual(f.read(), datah)
            
        with open(os.path.join(vc.getDataDir(), "HB1- binfile.bin"), "rb") as f:
            self.assertEqual(f.read(), datab)
        
    def test_commitDeleteRecreate(self):
        """
        What if we create the files again?
        """
        self.test_commitAndDelete()
        
        vc = VerConRepository(self.tempDir.name)
        
        datat = self.datat
        datab = self.datab
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)
            
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)
            
        vc.commit("no reason")
        

        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "ET3- textfile.txt")), "ET3- textfile.txt not created in REPO/DATA")
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "EB3- binfile.bin")), "EB3- binfile.bin not created in REPO/DATA")       

        with open(   os.path.join(vc.getDataDir(), "ET3- textfile.txt"),"r") as f:
            self.assertEqual(f.read(), datat)
            
        with open(os.path.join(vc.getDataDir(), "EB3- binfile.bin"), "rb") as f:
            self.assertEqual(f.read(), datab)       
            
            
    def test_commitFileCheckEncoding(self):
        """
        This test checks that the files are stored as Text or Binary depending on their encoding.
        
        Text files at this point are considered readable via the UTF-8 codec. Everything that does not
        contain valid UTF-8 characters is considered binary.
        
        Files are stored in the local testdata/utf8file.txt / nonutffile.txt / binfile.bin
        """
        
        shutil.copyfile(os.path.join("testdata","testutf8.txt"), os.path.join(self.tempDir.name, "testutf8.txt"))
        shutil.copyfile(os.path.join("testdata","nonutffile.txt"), os.path.join(self.tempDir.name, "nonutffile.txt"))
        shutil.copyfile(os.path.join("testdata","binfile.bin"), os.path.join(self.tempDir.name, "binfile.bin")) 

        vc = VerConRepository(self.tempDir.name)
        vc.commit("no reason")
        
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "ET1- testutf8.txt")), "ET1- testutf8.txt not created in REPO/DATA")
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "EB1- binfile.bin")), "EB1- binfile.bin not created in REPO/DATA")             
        self.assertTrue(os.path.isfile(os.path.join(vc.getDataDir(), "EB1- nonutffile.txt")), "EB1- nonutffile.txt not created in REPO/DATA")    


    def test_precomputeFileDB(self):
        """
        This function ensures that the file database is properly populated (at least when there is proper file data in REPO/DATA).
        """
        datadir = os.path.join(self.tempDir.name,"REPO","DATA")
        os.mkdir(os.path.join(self.tempDir.name,"REPO"))
        os.mkdir(os.path.join(datadir))
        with open(os.path.join(self.tempDir.name,"REPO","metadatadir.txt"),"w") as f:
            f.write("")

        vc = VerConRepository(self.tempDir.name)
        
        # vc.precomputeFileDB(datadir,"")
        
        self.assertIsNone(vc.getFileObject("","test"))
        
        # tests for files with just 1 revision
        with open(os.path.join(datadir, "ET1- tes1"), "w") as f:
            f.write("test")        
        with open(os.path.join(datadir, "EB1- bin1"), "wb") as f:
            f.write(bytes.fromhex("0000 FFFF 1010 1111"))
        # tests for files with some history
        with open(os.path.join(datadir, "HB1- bin2"), "wb") as f:
            f.write(bytes.fromhex("0000 0101 FFFF 1111")            )
        with open(os.path.join(datadir, "EB2- bin2"), "wb") as f:
            f.write(bytes.fromhex("1111 FFFF 0101 0000") )
        with open(os.path.join(datadir, "HT1- tes2"), "w") as f: # revision 1 should be equal to foo when restoring
            f.write("s 3\ni 3\nfoo")            
        with open(os.path.join(datadir, "ET2- tes2"), "w") as f:
            f.write("bar")             
        # tests for files that have been deleted
        with open(os.path.join(datadir, "HT1- tes3"), "w") as f:
            f.write("test")
        with open(os.path.join(datadir, "D2- tes3"), "w") as f:
            f.write("")     
        with open(os.path.join(datadir, "HB1- tes4"), "wb") as f:
            f.write(bytes.fromhex("0000 0101 FFFF 1111")  )
        with open(os.path.join(datadir, "D2- tes4"), "w") as f:
            f.write("")  
            
        # tests for mixed files
        with open(os.path.join(datadir, "HB1- tes5"), "wb") as f:
            f.write(bytes.fromhex("0000 FFFF 1010 1111")  )
        with open(os.path.join(datadir, "ET2- tes5"), "w") as f:
            f.write("test")  
        with open(os.path.join(datadir, "HT1- tes6"), "w") as f:
            f.write("test")
        with open(os.path.join(datadir, "EB2- tes6"), "wb") as f:
            f.write(bytes.fromhex("0000 0101 FFFF 1111"))                 

        vc = VerConRepository(self.tempDir.name)
        # vc.precomputeFileDB(datadir, "")            

        # now...
        self.assertTrue(vc.getFileObject("","tes1").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes1").ftypeAt(1),"t")
        self.assertEqual(vc.getFileObject("","tes1").contentsAt(1),"test")
        
        self.assertTrue(vc.getFileObject("","bin1").existsAt(1))
        self.assertEqual(vc.getFileObject("","bin1").ftypeAt(1),"b")
        self.assertEqual(vc.getFileObject("","bin1").contentsAt(1),bytes.fromhex("0000 FFFF 1010 1111"))
        
        self.assertTrue(vc.getFileObject("","tes2").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes2").ftypeAt(1),"t")
        self.assertEqual(vc.getFileObject("","tes2").contentsAt(1),"foo")        
        
        self.assertTrue(vc.getFileObject("","tes2").existsAt(2))
        self.assertEqual(vc.getFileObject("","tes2").ftypeAt(2),"t")
        self.assertEqual(vc.getFileObject("","tes2").contentsAt(2),"bar")     

        self.assertTrue(vc.getFileObject("","bin2").existsAt(1))
        self.assertEqual(vc.getFileObject("","bin2").ftypeAt(1),"b")
        self.assertEqual(vc.getFileObject("","bin2").contentsAt(1),bytes.fromhex("0000 0101 FFFF 1111"))    

        self.assertTrue(vc.getFileObject("","bin2").existsAt(2))
        self.assertEqual(vc.getFileObject("","bin2").ftypeAt(2),"b")
        self.assertEqual(vc.getFileObject("","bin2").contentsAt(2),(bytes.fromhex("1111 FFFF 0101 0000") ))
        
        self.assertTrue(vc.getFileObject("","tes3").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes3").ftypeAt(1),"t")
        self.assertEqual(vc.getFileObject("","tes3").contentsAt(1),"test")        
        
        self.assertFalse(vc.getFileObject("","tes3").existsAt(2))
        
        self.assertTrue(vc.getFileObject("","tes4").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes4").ftypeAt(1),"b")
        self.assertEqual(vc.getFileObject("","tes4").contentsAt(1),bytes.fromhex("0000 0101 FFFF 1111") )        
        
        self.assertFalse(vc.getFileObject("","tes4").existsAt(2))
        
        self.assertTrue(vc.getFileObject("","tes5").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes5").ftypeAt(1),"b")
        self.assertEqual(vc.getFileObject("","tes5").contentsAt(1),bytes.fromhex("0000 FFFF 1010 1111") )        
        
        self.assertTrue(vc.getFileObject("","tes5").existsAt(2))
        self.assertEqual(vc.getFileObject("","tes5").ftypeAt(2),"t")
        self.assertEqual(vc.getFileObject("","tes5").contentsAt(2),"test")     
        
        self.assertTrue(vc.getFileObject("","tes6").existsAt(1))
        self.assertEqual(vc.getFileObject("","tes6").ftypeAt(1),"t")
        self.assertEqual(vc.getFileObject("","tes6").contentsAt(1),"test")   
        
        self.assertTrue(vc.getFileObject("","tes6").existsAt(2))
        self.assertEqual(vc.getFileObject("","tes6").ftypeAt(2),"b")
        self.assertEqual(vc.getFileObject("","tes6").contentsAt(2),bytes.fromhex("0000 0101 FFFF 1111") )        
          
        
class TestRetrievePreviousData(unittest.TestCase):
    """
    And finally, the most important class, making sure we can restore the files
    and directories to a previous state.
    """
    
    def setUp(self):
        self.tempDir = tempfile.TemporaryDirectory()
        self.datat = "some text\nextra text\n"
        self.datab = bytes.fromhex('d3ad b33f 0100 0011')
        
    def tearDown(self):
        self.tempDir.cleanup()
        
    def test_twoCommitsAndARestoreText(self):
        """
        We commit a text file and a binary file twice, and see if we can restore the version of first commit.
        """
        
        datat = self.datat
        
        newdatat = "some extra\ntext text\n"
        
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)

        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")        
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(newdatat) 
        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("more no reason")        
        
        vc = VerConRepository(self.tempDir.name)   
        vc.restoreTo(1)
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"),"r") as f:
            self.assertEqual(f.read(), datat)          
            
    def test_twoCommitsAndARestoreBinary(self):
        """
        We do a similar test as for text, but for a binary file.
        """
        datab = self.datab
        
        newdatab = bytes.fromhex('0101 1010 0101 0101')        


            
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)

        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")        

            
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(newdatab)        
        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("more no reason")        
        
        vc = VerConRepository(self.tempDir.name)   
        vc.restoreTo(1)

            
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "rb") as f:
            self.assertEqual(f.read(), datab)               

    def test_twoCommitsAndDirectories(self):
        """
        Let's see if the directory structure is restored after a delete.
        """
        
        os.mkdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")    

        os.rmdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")   

        vc = VerConRepository(self.tempDir.name)   
        vc.restoreTo(1)

        self.assertTrue(os.path.isdir(os.path.join(self.tempDir.name, "test")), "test should exist at revision 1")
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")   

        vc = VerConRepository(self.tempDir.name)   
        vc.restoreTo(2)        

        self.assertFalse(os.path.isdir(os.path.join(self.tempDir.name, "test")), "test should not exist at revision 2")        
        
    def test_directoryNotYetCommited(self):
        """
        Let's see if we revert before the first creation of a directory works
        """
        
        os.mkdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")    

        os.mkdir(os.path.join(self.tempDir.name, "test2"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")    

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)
        self.assertFalse(os.path.join(self.tempDir.name, "test2"), "test2 should not exist yet at revision 1")     

    def test_fileDeletedText(self):
        """
        Do files disappear if they are in status deleted?
        """
        datat = self.datat
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")  

        os.unlink(os.path.join(self.tempDir.name, "textfile.txt"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason") 

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)        
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "textfile.txt")), "testfile.txt existed in revision 1")
        with open(os.path.join(self.tempDir.name, "textfile.txt"),"r") as f:
            self.assertEqual(f.read(), datat)   

    def test_fileDeletedBinary(self):
        """
        Do binary files disappear when they are in status deleted?
        """
        datab = self.datab
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")  

        os.unlink(os.path.join(self.tempDir.name, "binfile.bin"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason") 

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)        
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "binfile.bin")), "binfile.bin existed in revision 1")
        with open(os.path.join(self.tempDir.name, "binfile.bin"),"rb") as f:
            self.assertEqual(f.read(), datab)           
        
    def test_fileRecreatedText(self):
        """ if we revert to a state where the file was deleted, it should not be present. """
        datat = self.datat
        self.test_fileDeletedText()
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write("this is new data")        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")         
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)         
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "textfile.txt")), "testfile.txt existed in revision 1")
        with open(os.path.join(self.tempDir.name, "textfile.txt"),"r") as f:
            self.assertEqual(f.read(), datat)       

        # we restore last good point of repository
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)         
        self.assertFalse(os.path.isfile(os.path.join(self.tempDir.name, "textfile.txt")), "testfile.txt did not exist in revision 2")

    def test_fileRecreatedBinary(self):
        """ if we revert to a state where the bin file was deleted, it should not be present. """
        datab = self.datab
        self.test_fileDeletedBinary()
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(bytes.fromhex("0101 1010 0101 1010")    )    
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")         
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)         
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "binfile.bin")), "binfile.bin existed in revision 1")
        with open(os.path.join(self.tempDir.name, "binfile.bin"),"rb") as f:
            self.assertEqual(f.read(), datab)       

        # we restore last good point of repository
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)         
        self.assertFalse(os.path.isfile(os.path.join(self.tempDir.name, "binfile.bin")), "binfile.bin did not exist in revision 2")        


    def test_fileTextToBin(self):
        """
        Test if the restore of a file which has changed type (text to bin or bin to text)
        from a revision to another one
        properly works too.
        """
        datat = self.datat
        datab = self.datab
        newdatab = bytes.fromhex("0001 1010 0101 0101")
        newdatat = "This is \n a test among tests."
        
        with open(os.path.join(self.tempDir.name, "dualfile"), "w") as f:
            f.write(datat)
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")         
        
        with open(os.path.join(self.tempDir.name, "dualfile"), "wb") as f:
            f.write(datab)        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")     

        os.unlink(os.path.join(self.tempDir.name, "dualfile"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")    

        with open(os.path.join(self.tempDir.name, "dualfile"), "wb") as f:
            f.write(newdatab)            
        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")  

        with open(os.path.join(self.tempDir.name, "dualfile"), "w") as f:
            f.write(newdatat) 

        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason") 

        os.unlink(os.path.join(self.tempDir.name, "dualfile"))
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")    

        with open(os.path.join(self.tempDir.name, "dualfile"), "w") as f:
            f.write(datat)            
        
        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason")  

        with open(os.path.join(self.tempDir.name, "dualfile"), "wb") as f:
            f.write(datab) 

        vc = VerConRepository(self.tempDir.name)            
        vc.commit("no reason") 


        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)            
        
        with open(os.path.join(self.tempDir.name, "dualfile"), "r") as f:
            self.assertEqual(f.read(), datat)
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()         

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)         
        
        with open(os.path.join(self.tempDir.name, "dualfile"), "rb") as f:
            self.assertEqual(f.read(), datab)        

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()         

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(4)      

        with open(os.path.join(self.tempDir.name, "dualfile"), "rb") as f:
            self.assertEqual(f.read(), newdatab)      

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()         

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(5)      

        with open(os.path.join(self.tempDir.name, "dualfile"), "r") as f:
            self.assertEqual(f.read(), newdatat)      

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()   
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(7)            
        
        with open(os.path.join(self.tempDir.name, "dualfile"), "r") as f:
            self.assertEqual(f.read(), datat)
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo()   

        with open(os.path.join(self.tempDir.name, "dualfile"), "rb") as f:
            self.assertEqual(f.read(), datab)     

    def test_fileRestoreBetweenRevisionsText_ExistBefore(self):
        """
        Tests what happens in case a revert is asked for a revision where
        there is no info for given file or directory.
        --> should restore active file if file was active before revision X
        --> should not create a file if file was deleted or never checked
        """
        datat = self.datat
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)                
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write(datat)   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write("e")   
        os.unlink(os.path.join(self.tempDir.name, "textfile.txt"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")        
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)
        
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "textfile.txt")))
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "r") as f:
            self.assertEqual(f.read(), datat)
            
    def test_fileRestoreBetweenRevisionsBinary_ExistBefore(self):
        """
        Tests what happens in case a revert is asked for a revision where
        there is no info for given file or directory.
        --> should restore active file if file was active before revision X
        --> should not create a file if file was deleted or never checked
        """
        datab = self.datab
        datat = self.datat
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)                
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write(datat)   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write("e")   
        os.unlink(os.path.join(self.tempDir.name, "binfile.bin"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")        
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)
        
        self.assertTrue(os.path.isfile(os.path.join(self.tempDir.name, "binfile.bin")))
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "rb") as f:
            self.assertEqual(f.read(), datat)           
        
    def test_fileRestoreBetweenRevisionsText_DeleteBefore(self):
        """
        Tests what happens in case a revert is asked for a revision where
        there is no info for given file or directory.
        --> should restore active file if file was active before revision X
        --> should not create a file if file was deleted or never checked
        """
        datat = self.datat
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)                
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        os.unlink(os.path.join(self.tempDir.name, "textfile.txt"))
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write(datat)   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write("e")   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")   
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write("some new stuff yeah")                        
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 4")  
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(3)
        
        self.assertFalse(os.path.isfile(os.path.join(self.tempDir.name, "textfile.txt")))


    def test_fileRestoreBetweenRevisionsBinary_DeletedBefore(self):
        """
        Tests what happens in case a revert is asked for a revision where
        there is no info for given file or directory.
        --> should restore active file if file was active before revision X
        --> should not create a file if file was deleted or never checked
        """
        datab = self.datab
        datat = self.datat
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(datab)                
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        os.unlink(os.path.join(self.tempDir.name, "binfile.bin"))
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write(datat)   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")
        with open(os.path.join(self.tempDir.name, "textfile2.txt"), "w") as f:
            f.write("e")   
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")   
        with open(os.path.join(self.tempDir.name, "binfile.bin"), "wb") as f:
            f.write(bytes.fromhex("0101 1010 1111 0000")   )                     
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 4")  
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(3)
        
        self.assertFalse(os.path.isfile(os.path.join(self.tempDir.name, "binfile.bin")))
        
    def test_dirRestoreBetweenRevision_ExistBefore(self):
        """
        We test if the directorires are restored for an arbitrary revision number.
        
        here test is created at revision 1 and deleted at revision 3, we restore to revision 2: it should be there.
        """
        
        os.mkdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        os.mkdir(os.path.join(self.tempDir.name, "test2"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")      
        os.rmdir(os.path.join(self.tempDir.name, "test"))
        os.mkdir(os.path.join(self.tempDir.name, "test3"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")     

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(2)

        self.assertTrue(os.path.isdir(os.path.join(self.tempDir.name, "test")))
        
    def test_dirRestoreBetweenRevision_DeleteBefore(self):
        """
        We test if the directorires are restored for an arbitrary revision number.
        
        here, test is created in revision 1, deleted in 2, and recreated in 4
        we ask a revert to revision 3: test should not exist
        """
        
        os.mkdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        os.rmdir(os.path.join(self.tempDir.name, "test"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")      
        os.mkdir(os.path.join(self.tempDir.name, "test3"))
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")   
        os.mkdir(os.path.join(self.tempDir.name, "test"))        
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 4")   

        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(3)

        self.assertFalse(os.path.isdir(os.path.join(self.tempDir.name, "test")))        
        
        
    def test_fileRestoreTwoRevisionsText(self):
        """
        Can we revert the file to 2 revisions in the past properly?
        
        If yes, the process will work for an indefinite amount of revisions.
        """
        
        datat = self.datat
        newd1 = "some text\nThis is new text"
        newd2 = "some\ntext\nThis is newer text\n"
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(datat)
            
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 1")
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(newd1)
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 2")      
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "w") as f:
            f.write(newd2)        
        vc = VerConRepository(self.tempDir.name)
        vc.commit("test 3")               
        
        vc = VerConRepository(self.tempDir.name)
        vc.restoreTo(1)
        
        with open(os.path.join(self.tempDir.name, "textfile.txt"), "r") as f:
            self.assertEqual(f.read(), datat)     
            
    
    
class testVerConFile(unittest.TestCase):
    """
    Unit testing for the VerConFile class.
    """
    
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.rootDir = self.td.name
        self.dataDir = os.path.join(self.rootDir,"DATA")
        
        self.subdir = "subdir"

        os.mkdir(self.dataDir)
        
        self.t1 = "this is text data"
        self.t2 = "this is modified text data"
        self.t3 = "even more modified text"
        self.b1 = bytes.fromhex("0000 FFFF 1010 1111")
        self.b2 = bytes.fromhex("1111 1010 FFFF 0000")
        self.b3 = bytes.fromhex("FFFF DEAD BEEF 1111")
        
    def tearDown(self):
        self.td.cleanup()    

        
    def test_loadEvent(self):
        """
        Checks if the loadEvent function raises VerConError when event types are neither c, m, d
        and ftype not t or b.
        
        Checks if loadEvent raises verConError if 2 events are stored for same revision.
        
        There is no check for a create event being created 2 times, as loadEvent is not necessarily called in order.
        
        loadEvent must raise an error if someone tries to load twice a "e" event.
        """

        f = VerConFile("foo", ".", ".", "")
      
        revision = 1
        for event in ["h","e","d"]:
            for type in ["t","b"]:
                f = VerConFile("foo", ".", ".", "")
                f.loadEvent(event, revision, type, "foo")
                revision += 1

        f = VerConFile("foo", ".", ".", "")
        f.loadEvent("e",1,"t","foo")
        with self.assertRaises(VerConError):
            f.loadEvent("e",2,"t","foo")
        
        with self.assertRaises(VerConError):
            f.loadEvent("x", 2, type, "foo")

        with self.assertRaises(VerConError):
            f.loadEvent("m", 2, "x", "foo")            

        f = VerConFile("foo", ".", ".", "")
        f.loadEvent("h",1,"t","foo")
        f.loadEvent("e",2,"t","foo")
        
        # revision 1 is already stored.
        with self.assertRaises(VerConError):
            f.loadEvent("h", 1, "t", "foo")
        
        
    def test_isNew(self):
        """
        Ensures that isNew only returns true if the file has never seen any commit.
        
        Note that the commits are dependent on loadEvent to be called by the higher level commit routine to populate
        VerConFile's event list.
        """
        f = VerConFile("foo", ".", ".", "")
        self.assertTrue(f.isNew())
        
        f.loadEvent("e", 1,"t","foo")
        
        self.assertFalse(f.isNew())

        
    def test_existsAt(self):
        """
        Checks that the function returns true:
        - if last revision at or before request is a creation or a modification
        
        Checks function returns false, otherwise.
        """
        f = VerConFile("foo", ".", ".", "")
        self.assertFalse(f.existsAt(1))
        f.loadEvent("e",2,"t","foo")
        self.assertFalse(f.existsAt(1))
        self.assertTrue(f.existsAt(2))
        self.assertTrue(f.existsAt(3))
        
        f = VerConFile("foo", ".", ".", "")
        f.loadEvent("h",2,"t","foo")
        f.loadEvent("d",3,"t","foo")
        self.assertFalse(f.existsAt(1))
        self.assertTrue(f.existsAt(2))
        self.assertFalse(f.existsAt(3))        
        self.assertFalse(f.existsAt(4))     

        
    def test_ftypeAt(self):
        """
        Checks "t" or "b" is correctly returned depending on circumstances.
        
        this considers the file is already created, return of this function is undefined if file is deleted or never exists.
        """
        f = VerConFile("foo", ".", ".", "")
        f.loadEvent("h",2,"t","foo")
        f.loadEvent("e",4,"b","foo")
        
        self.assertEqual(f.ftypeAt(2), "t")
        self.assertEqual(f.ftypeAt(3), "t")
        self.assertEqual(f.ftypeAt(4), "b")
        self.assertEqual(f.ftypeAt(5), "b")
        
    def test_contentAtLastRevision(self):
        """
        Check that file can be properly restored from the latest revision in the repository,
        and incidentally, on first revision.
        """

        with open(os.path.join(self.rootDir, "test.txt"), "w") as f:
            f.write(self.t1)
            
        f = VerConFile("test.txt", self.rootDir, self.dataDir, "")
        f.createAtRevision(1)
        
        data = f.contentsAt(1)
        with open(os.path.join(self.rootDir, "test.txt"), "r") as f:
            self.assertEqual(f.read(),self.t1)        
        
        
        with open(os.path.join(self.rootDir, "test.bin"), "wb") as f:
            f.write(self.b1)
            
        f = VerConFile("test.bin", self.rootDir, self.dataDir, "")
        f.createAtRevision(1)
        
        data = f.contentsAt(1)
        with open(os.path.join(self.rootDir, "test.bin"), "rb") as f:
            self.assertEqual(f.read(),self.b1)    

    def test_contentAtPreviousRevision_TT(self):
        """
        Checks that file can be restored at a previous revision (scenario of two commits of a text file : TT)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB, BB
        """
        
        with open(os.path.join(self.rootDir, "test.txt"), "w") as f:
            f.write(self.t1)
            
        vcf = VerConFile("test.txt", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        with open(os.path.join(self.rootDir, "test.txt"), "w") as f:
            f.write(self.t2)
            
        vcf.changeAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.t1)     

    def test_contentAtPreviousRevision_BB(self):
        """
        Checks that file can be restored at a previous revision (scenario of two commits of a binary file : BB)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB, BB
        """
        
        with open(os.path.join(self.rootDir, "test.bin"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.bin", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        with open(os.path.join(self.rootDir, "test.bin"), "wb") as f:
            f.write(self.b2)
            
        vcf.changeAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.b1)          
        
        
    def test_contentAtPreviousRevision_TB(self):
        """
        Checks that file can be restored at a previous revision (scenario of a commit of a binary file over a text file : TB)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """

        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b2)
            
        vcf.changeAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.t1)   

    def test_contentAtPreviousRevision_BT(self):
        """
        Checks that file can be restored at a previous revision (scenario of a commit of a text file over a binary file : BT)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """

        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t2)
            
        vcf.changeAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.b1)            

 
    def test_contentAtPreviousRevision_TD(self):
        """
        Checks that file can be restored at a previous revision (text file now deleted: TD)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """

        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        os.unlink(os.path.join(self.rootDir,"test.tst"))
            
        vcf.deleteAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.t1)            
  
        
    def test_contentAtPreviousRevision_DT(self):
        """
        Checks that file can be restored at a previous revision (scenario of a deleted then recreated file - need to first create, then delete, then recreate, then modify)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """

        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        os.unlink(os.path.join(self.rootDir,"test.tst"))
            
        vcf.deleteAtRevision(2)
        
        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t2)
            
        vcf.changeAtRevision(3)
        
        with open(os.path.join(self.rootDir, "test.tst"), "w") as f:
            f.write(self.t3)        
            
        vcf.changeAtRevision(4)
        
        data = vcf.contentsAt(3)
        self.assertEqual(data,self.t2)      
        

        
    def test_contentAtPreviousRevision_BD(self):
        """
        Checks that file can be restored at a previous revision (scenario of two commits of a binary file then deleted: BD)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        os.unlink(os.path.join(self.rootDir,"test.tst"))
            
        vcf.deleteAtRevision(2)
        
        data = vcf.contentsAt(1)
        self.assertEqual(data,self.b1)   
        
    def test_contentAtPreviousRevision_DB(self):
        """
        Checks that file can be restored at a previous revision (scenario of a binary file recreated after deletion: create, delete, * modify, modify)
        
        Other scenarios to be tested : TB, BT, TD, DT, BD, DB
        """
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        os.unlink(os.path.join(self.rootDir,"test.tst"))
            
        vcf.deleteAtRevision(2)
        
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b2)
            
        vcf.changeAtRevision(3)
        
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b3)        

        vcf.changeAtRevision(4)            
        
        data = vcf.contentsAt(3)
        self.assertEqual(data,self.b2)      
        
        
    def test_createAtRevision(self):
        """
        Ensures an exception is raised if there is already anything in the history (created or modified event).
        """
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        vcf.createAtRevision(1)
        
        self.assertEqual(vcf.ftypeAt(1), "b")

        with self.assertRaises(VerConError):
            vcf.createAtRevision(2)
            
            
    def test_textOrBinary(self):
        """
        Ensures binary files are detected as binary, and text files as unicode.
        """
        with open(os.path.join(self.rootDir, "test.bin"), "wb") as f:
            f.write(self.b1)        
        with open(os.path.join(self.rootDir, "test.txt"), "w") as f:
            f.write(self.t1)     
            
        vcf = VerConFile("test.bin", "", "", "")
        type,data = vcf.textOrBinary(os.path.join(self.rootDir, "test.bin"))
        self.assertEqual(type, "b")
        self.assertEqual(data, self.b1)
        type,data = vcf.textOrBinary(os.path.join(self.rootDir, "test.txt"))
        self.assertEqual(type, "t")
        self.assertEqual(data, self.t1)        
            
    def test_createAtRevisionSubdir(self):
        """
        Ensures an exception is raised if there is already anything in the history (created or modified event).
        
        Also tests if creation correctly done in a subdirectory.
        """
        
        os.mkdir(os.path.join(self.rootDir, self.subdir))
        os.mkdir(os.path.join(self.dataDir, self.subdir))

        with open(os.path.join(self.rootDir, self.subdir,"test.tst"), "wb") as f:
            f.write(self.b1)
        with open(os.path.join(self.rootDir, self.subdir,"test.txt"), "w") as f:
            f.write(self.t1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, self.subdir)
        vcf.createAtRevision(1)

        with self.assertRaises(VerConError):
            vcf.createAtRevision(2)
            
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, self.subdir, "EB1- test.tst")))
        self.assertFalse(os.path.isfile(os.path.join(self.dataDir, "EB1- test.tst")))       

        vcf = VerConFile("test.txt", self.rootDir, self.dataDir, self.subdir)
        vcf.createAtRevision(1)

        with self.assertRaises(VerConError):
            vcf.createAtRevision(2)
            
        self.assertTrue(os.path.isfile(os.path.join(self.dataDir, self.subdir, "ET1- test.txt")))
        self.assertFalse(os.path.isfile(os.path.join(self.dataDir, "ET1- test.txt")))            

        
    def test_changeAtRevision(self):
        """
        Ensures an exception is raised if no "create" event was recorded, or if the change event is
        created before the revision of the creation.
        """
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        
        with self.assertRaises(VerConError):
            vcf.changeAtRevision(1)
            
        vcf.createAtRevision(2)       

        with self.assertRaises(VerConError):
            vcf.changeAtRevision(1)        
        
    def test_deleteAtRevision(self):
        """
        Ensures an exception is raised if no "create" event was recorded, or if the change event is
        created before the revision of the creation.
        """
        with open(os.path.join(self.rootDir, "test.tst"), "wb") as f:
            f.write(self.b1)
            
        vcf = VerConFile("test.tst", self.rootDir, self.dataDir, "")
        
        with self.assertRaises(VerConError):
            vcf.deleteAtRevision(1)
            
        vcf.createAtRevision(2)       

        with self.assertRaises(VerConError):
            vcf.deleteAtRevision(1)        
    
    def test_mergeTextBackwards(self):
        """
        Ensures that the data is correctly restored between revisions.
        
        Tests different uses cases for the expression language designed to store the deltas:
        """
        
        datalist = [
            {"file1": "baz", "file2": "foo", "file3": "bar", "delta2-1": "s 3\ni 3\nbaz" , "delta3-2": "s 3\ni 3\nfoo"},
            {"file1": "baz", "file2": "sad", "file3": "bar", "delta2-1": "s 1\ni 1\nb\nc 1\ni 1\nz" , "delta3-2": "s 1\ni 1\ns\nc 1\ni 1\nd"},
            ]

        for t in datalist:
            with open(os.path.join(self.dataDir, "HT1- test"), "w") as f: 
                f.write(t["delta2-1"])            
            with open(os.path.join(self.dataDir, "HT2- test"), "w") as f:
                f.write(t["delta3-2"])      
            with open(os.path.join(self.dataDir, "ET3- test"), "w") as f:
                f.write(t["file3"])

            vcf = VerConFile("test", self.rootDir, self.dataDir, "")    
            vcf.loadEvent("h",1,"t","HT1- test")
            vcf.loadEvent("h",2,"t","HT2- test")
            vcf.loadEvent("e",3,"t","ET3- test")
            
            self.assertEqual(vcf.mergeTextBackwards([2,3]),t["file2"],"Could not compute %s from %s with '%s' as transform"%(t["file2"],t["file3"],t["delta3-2"]))
            self.assertEqual(vcf.mergeTextBackwards([1,2,3]),t["file1"], "Could not compute %s from %s with '%s' and '%s' as transform"%(t["file1"],t["file3"],t["delta3-2"], t["delta2-1"]))


    def test_calculateDelta(self):
        """
        Ensures that delta is correctly generated.
        """
        vcf = VerConFile("test","","","")
        self.assertEqual(vcf.calculateDelta("foo","bar"),"s 3\ni 3\nbar")
        self.assertEqual(vcf.calculateDelta("foo","boo"),"s 1\ni 1\nb\nc 2")
        self.assertEqual(vcf.calculateDelta("","boo"),"i 3\nboo")
        self.assertEqual(vcf.calculateDelta("foo",""),"s 3")

if __name__ == '__main__':
    unittest.main()