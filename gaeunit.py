#!/usr/bin/env python
'''
Usage:

1. Put gaeunit.py in app directory, and change the app.yaml to add the following 2 lines

- url: /test.*
  script: gaeunit.py

below

handlers:

2. Write your own test cases by extending unittest.TestCase.

3. Launch Dev App Server. Then input the following URL into your browser

http://localhost:8080/test?module=test_guestbook

Please replace 'test_guestbook' with your own module that contains the test cases

4. Wait and see the result.


Copyright (c) 2008 George Lei
This module is free software, and you may redistribute it and/or modify
it under the same terms as Python itself, so long as this copyright message
and disclaimer are retained in their original form.

IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF
THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
DAMAGE.

THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS,
AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
'''

__author__ = "George Lei"
__email__ = "George.Z.Lei@Gmail.com"
__version__ = "#Revision: 1.1.1 $"[11:-2]

import sys
import unittest
import StringIO
import time
import re
import wsgiref.handlers

from google.appengine.ext import webapp

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
            stream.write('{"desc":"%s", "detail":"%s"},' % (self.getDescription(test), self.escape(err)))
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
    def get(self):
        self.response.out.write(testResultPageContent)
        srcErr = getServiceErrorStream()
        module = self.request.get("module")
        if not module:
            svcErr.write("Please specify the module name in url<p><strong>Example:</strong><br/>\thttp://localhost:8080/test?module=test_guestbook</p>")
            return
        try:
            __import__(module)
        except ImportError:
            svcErr.write("Module '" + module + "' cannot be found.")
            return
        self.findTestPackage(module)
        if not self.testsuite:
            svcErr.write("No test case is found in the specified module '" + module + "'.")
        else:
            runner = WebTestRunner()
            runner.run(self.testsuite)

    def findTestPackage(self, moduleName):
        self.testsuite = None
        try:
            module = sys.modules[moduleName]
        except KeyError:
            module = __import__(moduleName)
        for testcase in dir(module):
            if testcase.endswith("Test"):
                t = getattr(module, testcase)
                self.addTestCase(t)

    def addTestCase(self, testcase):
        if issubclass(testcase, unittest.TestCase):
            s = unittest.makeSuite(testcase)
            if self.testsuite:
                self.testsuite.addTests(s)
            else:
                self.testsuite = s
                
class ResultSender(webapp.RequestHandler):
    def get(self):
        cache = StringIO.StringIO()
        result = getTestResult()
        if svcErr.getvalue() != "":
            cache.write('{"svcerr":%d, "svcinfo":"%s",' % (1, svcErr.getvalue()))
        else:
            cache.write('{"svcerr":%d, "svcinfo":"%s",' % (0, ""))
            cache.write('"runs":"%d", "total":"%d", "errors":"%d", "failures":"%d",' % (result.testsRun, result.testNumber, len(result.errors), len(result.failures)))
            cache.write('"details":%s' % result.printErrors())
        cache.write('}')
        self.response.out.write(cache.getvalue())


svcErr = StringIO.StringIO()
resultResult = None

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
        #testindicator {width:950px; height:16px; background-color:green;}
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

        function setResult(runs, total, errors, failures) {
            document.getElementById("testran").innerHTML = runs;
            document.getElementById("testtotal").innerHTML = total;
            document.getElementById("testerror").innerHTML = errors;
            document.getElementById("testfailure").innerHTML = failures;
            if (errors || failures) {
                testFailed();
            }
        }

        // Update page every 3 seconds
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
        Copyright 2008 George Lei
    </div>
</body></html>
"""

application = webapp.WSGIApplication([
  ('/test', GAEUnitTestRunner),
  ('/testresult', ResultSender)
], debug=True)


def main():
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
        