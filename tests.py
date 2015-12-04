################################################################################
# Brain Odyssey tests
################################################################################

import unittest
import doctest
import servercov
from server import app
from model import connect_to_db
from selenium import webdriver

# def load_tests(loader, tests, ignore):
#     """Run doctests and file-based doctests."""

#     tests.addTests(doctest.DocTestSuite(server))
#     tests.addTests(doctest.DocFileSuite('tests.txt'))
#     return tests

class MyAppUnitTestCast(unittest.TestCase):

    def setUp(self):
        self.client = server.app.test_client()
        self.browser = webdriver.Chrome()
        app.config['TESTING'] = True
        connect_to_db(app)

    def tearDown(self):
        self.browser.quit()

    def test_title(self):
        self.browser.get('http://localhost:5000/')
        self.assertEqual(self.browser.title, 'Brain Odyssey')

    def test_homepage(self):
        test_client = server.app.test_client()

        result = test_client.get('/')
        self.assertEqual(result.status_code, 200)

    def test_location(self):
        self.browser.get('http://localhost:5000/')
        x = self.browser.find_element_by_id('xcoord')
        x.send_keys('40')
        y = self.browser.find_element_by_id('ycoord')
        y.send_keys('-45')
        z = self.browser.find_element_by_id('zcoord')
        z.send_keys('-25')
        btn = self.browser.find_element_by_id('submit-xyz')
        btn.click()

        header = self.browser.find_element_by_id('header')
        self.assertEqual(header.text, 'Location:<br>40 -45 -25')
        references = self.browser.find_element_by_id('references_title')
        self.assertEqual(references.text, 'References')

    def test_word(self):
        self.browser.get('http://localhost:5000/')
        wordsearch = self.browser.find_element_by_id('word_search')
        wordsearch.send_keys('face')
        btn = self.browser.find_element_by_id('submit_word')
        btn.click()

        header = self.browser.find_element_by_id('header')
        self.assertEqual(header.text, 'Word:<br>face')
        references = self.browser.find_element_by_id('references_title')
        self.assertEqual(references.text, 'References')

## D3 ROUTES ###################################################################

    def test_d3_from_location(self):
        result = self.client.get('/d3.json?xcoord=40&ycoord=-45&zcoord=-25&options=location')
        # import pdb; pdb.set_trace()

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result, object)
        root_name = 'name'
        self.assertIn(root_name, result.data)

    def test_d3_from_reference(self):
        result = self.client.get('/d3.json?pmid=16990015&options=study')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result, object)
        root_name = 'name'
        self.assertIn(root_name, result.data)

    def test_d3_from_word(self):
        result = self.client.get('/d3word.json?word=face')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result, object)
        root_name = 'name'
        self.assertIn(root_name, result.data)

    def test_d3_from_topic(self):
        result = self.client.get('/d3topic.json?cluster=56')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result, object)
        root_name = 'name'
        self.assertIn(root_name, result.data)


# ## INTENSITY ROUTES ########################################################

# (Notes & todo: 
# Best practices for integration test: don't use actual data
# Mock out results with a mocking framework  
# Test what happens when we feed in a word that is not in the database) 

    def test_intensity_from_word(self):
        result = self.client.get('/intensity?word=pain&options=word')

        self.assertEqual(result.status_code, 200)
        intensity = '0.532713099492'
        self.assertIn(intensity, result.data)

    def test_intensity_from_cluster(self):
        result = self.client.get('/intensity?cluster=11&options=cluster')

        self.assertEqual(result.status_code, 200)
        intensity = '0.306829606337'
        self.assertIn(intensity, result.data)

    def test_intensity_from_ref(self):
        result = self.client.get('/intensity?pmid=11960899&options=study')

        self.assertEqual(result.status_code, 200)
        intensity = '0.5'
        self.assertIn(intensity, result.data)

    def test_colors(self):
        result = self.client.get('/colors')
        self.assertEqual(result.status_code, 200)


## REFERENCES ROUTES ##########################################################

    def test_citations_from_location(self):
        result = test_client.get('/citations.json?xcoord=40&ycoord=-45&zcoord=-25&options=location')
        self.assertEqual(result.status_code, 200)

    def test_citations_from_word(self):
        result = test_client.get('/citations.json?word=pain&options=word')
        self.assertEqual(result.status_code, 200)

    def test_citations_from_cluster(self):
        result = test_client.get('/citations.json?pmid=11960899&options=study')
        self.assertEqual(result.status_code, 200)


if __name__ == "__main__":

    unittest.main()

