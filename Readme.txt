GAEUnit: Google App Engine Unit Test Framework

http://code.google.com/p/gaeunit

Copyright (c) 2008 George Lei and Steven R. Farley.  All rights reserved.


SUMMARY

GAEUnit is a unit test framework that helps to automate testing of your Google App Engine application. With a single configuration (it can be completed within 30 seconds), your unit tests can be run in the real GAE app server environment. The results will be sent to web browser as an HTML web page.
 
GAEUnit is simple. It contains only one file, gaeunit.py. Just copy that file into your application directory, add the test URL to app.yaml, you can start testing your apps for Google App Engine. 


INSTALLATION

  1) Copy gaeunit.py into your web app root directory (the directory containing app.yaml).  

  2) Modify 'app.yaml' by adding the following mapping below the 'handlers:' section:

- url: /test.*
  script: gaeunit.py

The changed app.yaml should be like this

бн бн

handlers:
- url: /test.*
script: gaeunit.py
- url: .*
script: guestbook.py


USAGE

When writing your test code, please follow the Python unit test coding conventions (http://docs.python.org/lib/writing-tests.html). Here are some simple rules:
  * All test modules must be named like 'test_xxx'.
  * All test classes must extend unittest.TestCase
  * All test functions name must be in the format of 'testXxx'

Case 1: Running Single-Module Test

  1) Put your test module file (for example, test_guestbook.py) in the root directory of your web app.

  2) Launch dev_appserver.py

  3) Type http://localhost:8080/test?name=test_guestbook into the location bar of your browser. (change the port if necessary)

Case 2: Running Multi-Module Test

  1) Organize your test modules with 'test' package. And put your package into the root directory of your web app. The structure of your web app directory should be like the following

guestbook/
    |---- app.yaml
    |---- guestbook.py
    |---- another_mod.py
    |---- test/
            |---- __init__.py
            |---- test_guestbook.py
            |---- test_another_mod.py

  2) Launch dev_appserver.py

  3) Type http://localhost:8080/test into the location bar of your browser. (change the port if necessary)


OPTIONS

There are a few options for you to use in the URL parameter

package: Running all tests in package
  
  Example: http://localhost:8080/test?package=test_package

  Note: Request http://localhost:8080/test equals to http://localhost:8080/test?package=test

name: Running test object. Test object can be module, class, or method.

  Example 1: http://localhost:8080/test?name=test_module
  Example 2: http://localhost:8080/test?name=test_module.ClassTest
  Example 3: http://localhost:8080/test?name=test_module.ClassTest.testMethod

format: The type of displayed test result. The value can be 'html' for HTML format or 'plain' for plain text format.

  Example: http://localhost:8080/test?module=test_module&format=plain


  
