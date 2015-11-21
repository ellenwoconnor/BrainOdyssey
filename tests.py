################################################################################
# Brain odyssey unit tests
################################################################################

import unittest

class MyAppUnitTestCast(unittest.Testcase):

    def test_homepage(self):
        test_client = server.app.test_client()

        result = test_client.get('/')
        self.assertEqual(result.status_code, 200)


## D3 ROUTES ###################################################################

    def test_d3_from_location(self):
        test.client = server.app.test_client()
        result = test_client.get('/d3.json?xcoord=40&ycoord=-45&zcoord=-25&options=location')

        self.assertEqual(result.status_code, 200)
        self.assertIn('<svg>')
        self.assertIsInstance(result, object)
        root_name = "'name': ''"
        self.assertIn(root_name, result.data)

    def test_d3_from_reference(self):
        test.client = server.app.test_client()
        test_client.get('/d3.json?16990015&options=study')

        self.assertEqual(result.status_code, 200)
        self.assertIn('<svg>')
        self.assertIsInstance(response, object)

        root_name = "'name': ''"
        self.assertIn(root_name, response.data)


## INTENSITY D3 ROUTES ########################################################

    def test_intensity_from_word(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?word=pain&options=word')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(response, String)
        intensity = '0.0972065975894'
        self.assertIn(intensity, result.data)

    def test_intensity_from_cluster(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?cluster=11&options=cluster')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(response, String)
        intensity = '0.0478103814687'
        self.assertIn(intensity, result.data)

    def test_intensity_from_ref(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?pmid=11960899&options=study')

        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(response, String)
        intensity = '0.5'
        self.assertIn(intensity, result.data)


## REFERENCES ROUTES ##########################################################

    def test_citations_from_location(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?word=pain&options=word')

    def test_citations_from_word(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?word=pain&options=word')

    def test_citations_from_cluster(self):
        test.client = server.app.test_client()
        result = test_client.get('/intensity?word=pain&options=word')


        self.assertIn('<h4 id="references_title">References</h4>')


if __name__ == "__main__":

    unittest.main()