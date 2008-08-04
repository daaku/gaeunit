#!/usr/bin/env python
'''
GAEUnit: Google App Engine Unit Test Framework

Usage:

1. Put gaeunit.py into your application directory.  Modify 'app.yaml' by
   adding the following mapping below the 'handlers:' section:

   - url: /test.*
     script: gaeunit.py

2. Write your own test cases by extending unittest.TestCase.

3. Launch the development web server.  Point your browser to:

     http://localhost:8080/test?module=my_test_module

   Replace 'my_test_module' with the module that contains your test cases,
   and modify the port if necessary.
   
   For plain text output add '&format=plain' to the URL.

4. The results are displayed as the tests are run.

Visit http://code.google.com/p/gaeunit for more information and updates.

------------------------------------------------------------------------------
Copyright (c) 2008, George Lei and Steven R. Farley.  All rights reserved.

Distributed under the following BSD license:

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
------------------------------------------------------------------------------
'''

__author__ = "George Lei and Steven R. Farley"
__email__ = "George.Z.Lei@Gmail.com"
__version__ = "#Revision: 1.1.1 $"[11:-2]
__copyright__= "Copyright (c) 2008, George Lei and Steven R. Farley"
__license__ = "BSD"
__url__ = "http://code.google.com/p/gaeunit"

import sys
import os
import unittest
import StringIO
import time
import re
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.api import apiproxy_stub_map  
from google.appengine.api import datastore_file_stub

##############################################################################
# Web Test Runner
##############################################################################
class _WebTestResult(unittest.TestResult):
    def __init__(self):
        unittest.TestResult.__init__(self)
        self.testNumber = 0

    def getDescription(self, test):
        return test.shortDescription() or str(test)

    def printErrors(self):
        stream = StringIO.StringIO()
        stream.write('{')
        self.printErrorList('ERROR', self.errors, stream)
        stream.write(',')
        self.printErrorList('FAIL', self.failures, stream)
        stream.write('}')
        return stream.getvalue()

    def printErrorList(self, flavour, errors, stream):
        stream.write('"%s":[' % flavour)
        for test, err in errors:
            stream.write('{"desc":"%s", "detail":"%s"},' %
                         (self.getDescription(test), self.escape(err)))
        if len(errors):
            stream.seek(-1, 2)
        stream.write("]")

    def escape(self, s):
        newstr = re.sub('"', '&quot;', s)
        newstr = re.sub('\n', '<br/>', newstr)
        return newstr
        

class WebTestRunner:
    def run(self, test):
        "Run the given test case or test suite."
        result = getTestResult(True)
        result.testNumber = len(test._tests)
        startTime = time.time()
        test(result)
        stopTime = time.time()
        timeTaken = stopTime - startTime
        return result

#############################################################
# Http request handler
#############################################################

class GAEUnitTestRunner(webapp.RequestHandler):
    def __init__(self):
        self.package = "test"
        
    def get(self):
        """Major Request Handler
        The request URL should be in the following formats
        
        http://localhost:8080/test?package=test_package
        http://localhost:8080/test?module=test_module
        
        parameter 'package' and 'module' cannot be used at the same time.
        
        When 'package' is set, GAEUnit will search for the global function
        'makeTestSuite' in __init__.py. If this function is not found, 
        all test case classes similar to 'XxxTest' in modules similar to 
        'test_xxx" will be collected and executed.
        
        When 'module' is set and 'package' is not set, GAEUnit will search
        in the root directory or 'test' directory for the specified module.
        The module can also be in the long form that contains package 
        information. For example,
        
        http://localhost:8080/test?module=test_package.test_module
        
        The request URL can be in this format
        
        http://localhost:8080/test
        
        It is equivalent to 
        
        http://localhost:8080/test?package=test 
        """
        # Add './test' into the search scope
        if not "test" in sys.path:
            sys.path.insert(0, "test")
        srcErr = getServiceErrorStream()
        format = self.request.get("format")
        if not format or format not in ["html", "plain"]:
            format = "html"
        if format != "plain":
            self.response.out.write(testResultPageContent)
        package = self.request.get("package")
        module = self.request.get("module")
        if package:
            suite = self._searchPackage(package)
        elif module:
            suite = self._searchModule(module)
        else:
            suite = self._searchPackage("test")
        if not suite:
            if module:
                svcErr.write("Module '%s' does not contain any test case " %
                         module)
            else:
                svcErr.write("No test case is found in 'test' folder")
        else:
            if format == "html":
                runner = WebTestRunner()
            else:
                self.response.headers["Content-Type"] = "text/plain"
                self.response.out.write("====================\n" \
                                        "GAEUnit Test Results\n" \
                                        "====================\n\n")
                runner = unittest.TextTestRunner(self.response.out)
            self._runTestSuite(runner, suite)

    def _runTestSuite(self, runner, suite):
        """Run the test suite.

        Preserve the current development apiproxy, create a new apiproxy and
        temporary datastore that will be used for this test suite, run the
        test suite, and restore the development apiproxy.  This isolates the
        test and development datastores from each other.

        """        
        original_apiproxy = apiproxy_stub_map.apiproxy
        try:
           apiproxy_stub_map.apiproxy = apiproxy_stub_map.APIProxyStubMap() 
           temp_stub = datastore_file_stub.DatastoreFileStub(
               'GAEUnitDataStore', None, None)  
           apiproxy_stub_map.apiproxy.RegisterStub('datastore_v3', temp_stub)
           runner.run(suite)
        finally:
           apiproxy_stub_map.apiproxy = original_apiproxy

    def _searchPackage(self, package):
        """
        Searching rules:
        Naming convention: all test module in the target module must start with
        'test_', for example 'test_appengin', 'test_db', etc.

        'package' can be long form like 'google.appengine.ext.test'
        """
        suite = unittest.TestSuite()
        dirName = self._convertToPath(package)
        for file in os.listdir(dirName):
            if file.startswith("test_") and file.endswith(".py"):
                moduleName = file[:-3]
                s = self._searchModule(moduleName)
                suite.addTests(s)
        return suite
    
    def _convertToPath(self, package):
        """ Convert package name like 'google.appengine.ext' to directory name 
        like 'google/appengine/ext'
        """
        return re.sub("\.", "/", package)
    
    def _searchModule(self, moduleName):
        """Search the test cases.
        
        If the parameter 'moduleName' is specified, only test cases in this 
        module is search. 
        
        'module' can be either simple name or long name including package name.
        """
        # Test if given module can be valid
        # Clean the test suite data that is used by last round of test
        testModules = []
        testModules.append(moduleName)
        isPackage = ("__init__.py" in os.listdir("test"))
        # core
        for testModuleName in testModules:
            # Load the module
            try:
                __import__(moduleName)
                try:
                    module = sys.modules[testModuleName]
                except KeyError:
                    if isPackage:
                        module = __import__("test."+testModuleName, globals(), locals(), [testModuleName], -1)
                    else:
                        module = __import__(testModuleName)
            except ImportError:
                svcErr.write("Module '%s' cannot be found." % moduleName)
                return
            # Create the test suite
            suite = unittest.TestSuite()
            for testcase in dir(module):
                if testcase.endswith("Test"):
                    t = getattr(module, testcase)
                    self._addTestCase(suite, t)
        return suite

    def _addTestCase(self, suite, testcase):
        if issubclass(testcase, unittest.TestCase):
            s = unittest.makeSuite(testcase)
            suite.addTests(s)
                
class ResultSender(webapp.RequestHandler):
    def get(self):
        cache = StringIO.StringIO()
        result = getTestResult()
        if svcErr.getvalue() != "":
            cache.write('{"svcerr":%d, "svcinfo":"%s",' %
                        (1, svcErr.getvalue()))
        else:
            cache.write('{"svcerr":%d, "svcinfo":"%s",' % (0, ""))
            cache.write(('"runs":"%d", "total":"%d", ' \
                         '"errors":"%d", "failures":"%d",') %
                        (result.testsRun, result.testNumber,
                         len(result.errors), len(result.failures)))
            cache.write('"details":%s' % result.printErrors())
        cache.write('}')
        self.response.out.write(cache.getvalue())


svcErr = StringIO.StringIO()
testResult = None

def getServiceErrorStream():
    global svcErr
    if svcErr:
        svcErr.truncate(0)
    else:
        svcErr = StringIO.StringIO()

def getTestResult(createNewObject=False):
    global testResult
    if createNewObject or not testResult:
        testResult = _WebTestResult()
    return testResult




################################################
# Browser codes
################################################

testResultPageContent = """
<html>
<head>
    <style>
        body {font-family:arial,sans-serif; text-align:center}
        #title {font-family:"Times New Roman","Times Roman",TimesNR,times,serif; font-size:28px; font-weight:bold; text-align:center}
        #version {font-size:87%; text-align:center;}
        #weblink {font-style:italic; text-align:center; padding-top:7px; padding-bottom:20px}
        #results {margin:0pt auto; text-align:center; font-weight:bold}
        #testindicator {width:950px; height:16px; border-style:solid; border-width:2px 1px 1px 2px; background-color:#f8f8f8;}
        #footerarea {text-align:center; font-size:83%; padding-top:25px}
        #errorarea {padding-top:25px}
        .error {border-color: #c3d9ff; border-style: solid; border-width: 2px 1px 2px 1px; width:945px; padding:1px; margin:0pt auto; text-align:left}
        .errtitle {background-color:#c3d9ff; font-weight:bold}
    </style>
    <script language="javascript" type="text/javascript">
        /* Create a new XMLHttpRequest object to talk to the Web server */
        var xmlHttp = false;
        /*@cc_on @*/
        /*@if (@_jscript_version >= 5)
        try {
          xmlHttp = new ActiveXObject("Msxml2.XMLHTTP");
        } catch (e) {
          try {
            xmlHttp = new ActiveXObject("Microsoft.XMLHTTP");
          } catch (e2) {
            xmlHttp = false;
          }
        }
        @end @*/
        if (!xmlHttp && typeof XMLHttpRequest != 'undefined') {
          xmlHttp = new XMLHttpRequest();
        }

        function callServer() {
          var url = "/testresult";
          xmlHttp.open("GET", url, true);
          xmlHttp.onreadystatechange = updatePage;
          xmlHttp.send(null);
        }

        function updatePage() {
          if (xmlHttp.readyState == 4) {
            var response = xmlHttp.responseText;
            var result = eval('(' + response + ')');
            if (result.svcerr) {
                document.getElementById("errorarea").innerHTML = result.svcinfo;
                testFailed();
            } else {                
                setResult(result.runs, result.total, result.errors, result.failures);
                var errors = result.details.ERROR;
                var failures = result.details.FAIL;
                var details = "";
                for(var i=0; i<errors.length; i++) {
                    details += '<p><div class="error"><div class="errtitle">ERROR '+errors[i].desc+'</div><div class="errdetail"><pre>'+errors[i].detail+'</pre></div></div></p>';
                }
                for(var i=0; i<failures.length; i++) {
                    details += '<p><div class="error"><div class="errtitle">FAILURE '+failures[i].desc+'</div><div class="errdetail"><pre>'+failures[i].detail+'</pre></div></div></p>';
                }
                document.getElementById("errorarea").innerHTML = details;
            }
          }
        }

        function testFailed() {
            document.getElementById("testindicator").style.backgroundColor="red";
        }
        
        function testSucceed() {
            document.getElementById("testindicator").style.backgroundColor="green";
        }

        function setResult(runs, total, errors, failures) {
            document.getElementById("testran").innerHTML = runs;
            document.getElementById("testtotal").innerHTML = total;
            document.getElementById("testerror").innerHTML = errors;
            document.getElementById("testfailure").innerHTML = failures;
            if (errors==0 && failures==0) {
                testSucceed();
            } else {
                testFailed();
            }
        }

        // Update page every 5 seconds
        setInterval(callServer, 5000);
    </script>
    <title>GAEUnit: Google App Engine Unit Test Framework</title>
</head>
<body>
    <div id="headerarea">
        <div id="title">GAEUnit: Google App Engine Unit Test Framework</div>
        <div id="version">version 1.1.1</div>
        <div id="weblink">Please check <a href="http://code.google.com/p/gaeunit">http://code.google.com/p/gaeunit</a> for the latest version</div>
    </div>
    <div id="resultarea">
        <table id="results"><tbody>
            <tr><td colspan="3"><div id="testindicator"> </div></td</tr>
            <tr>
                <td>Runs: <span id="testran">0</span>/<span id="testtotal">0</span></td>
                <td>Errors: <span id="testerror">0</span></td>
                <td>Failures: <span id="testfailure">0</span></td>
            </tr>
        </tbody></table>
    </div>
    <div id="errorarea">The test is running, please wait...</div>
    <div id="footerarea">
        Please write to the <a href="mailto:George.Z.Lei@Gmail.com">author</a> to report problems<br/>
        Copyright 2008 George Lei and Steven R. Farley
    </div>
</body>
</html>
"""

application = webapp.WSGIApplication([('/test', GAEUnitTestRunner),
                                      ('/testresult', ResultSender)],
                                      debug=True)

def main():
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
