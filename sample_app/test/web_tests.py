import unittest
from webtest import TestApp
from google.appengine.ext import webapp
import index

class IndexTest(unittest.TestCase):

  def setUp(self):
    self.application = webapp.WSGIApplication([('/', index.IndexHandler)], debug=True)

  def tearDown(self):
    pass

  def test_default_page(self):
      app = TestApp(self.application)
      res = app.get('/')
      self.assertEqual("200 OK", res.status)

