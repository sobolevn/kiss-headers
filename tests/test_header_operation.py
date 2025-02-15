import unittest

from kiss_headers import Header


class MyKissHeaderOperation(unittest.TestCase):
    def test_isub_adjective_error(self):
        content_type = Header("Content-Type", 'text/html; charset="utf-8"')

        self.assertNotIn("text/xml", content_type)

        with self.assertRaises(ValueError):
            content_type = content_type - "text/xml"

        with self.assertRaises(TypeError):
            content_type = content_type - 1

    def test_isub_adjective(self):
        content_type = Header("Content-Type", 'text/html; charset="utf-8"')

        self.assertIn("text/html", content_type)

        content_type = content_type - "text/html"

        self.assertNotIn("text/html", content_type)

        self.assertEqual('charset="utf-8"', str(content_type))

    def test_iadd_adjective(self):

        content_type = Header("Content-Type", 'charset="utf-8"')

        self.assertNotIn("text/html", content_type)

        content_type = content_type + "text/html"

        self.assertIn("text/html", content_type)

        self.assertEqual('charset="utf-8"; text/html', str(content_type))

    def test_subtract_adjective(self):
        content_type = Header("Content-Type", 'text/html; charset="utf-8"')

        self.assertIn("text/html", content_type)

        content_type -= "text/html"

        self.assertNotIn("text/html", content_type)

        self.assertEqual('charset="utf-8"', str(content_type))

    def test_add_adjective(self):

        content_type = Header("Content-Type", 'charset="utf-8"')

        self.assertNotIn("text/html", content_type)

        content_type += "text/html"

        self.assertIn("text/html", content_type)

        self.assertEqual('charset="utf-8"; text/html', str(content_type))

    def test_simple_attr_removal(self):
        content_type = Header("Content-Type", 'text/html; charset="utf-8"')

        self.assertIn("charset", content_type)

        self.assertEqual("utf-8", content_type.charset)

        del content_type.charset

        self.assertNotIn("charset", content_type)

        self.assertEqual(str(content_type), "text/html")

    def test_complex_attr_removal(self):
        content_type = Header(
            "Content-Type",
            'text/html; charset="utf-8"; format=flowed; format="origin";',
        )

        del content_type.format

        self.assertEqual('text/html; charset="utf-8"', str(content_type))

        with self.assertRaises(AttributeError):
            del content_type.format

        del content_type["charset"]

        self.assertEqual("text/html", str(content_type))

        with self.assertRaises(KeyError):
            del content_type["charset"]

    def test_complex_second_attr_removal(self):
        content_type = Header(
            "Content-Type",
            'text/html; format=flowed; charset="utf-8"; format=flowed; format="origin";',
        )

        del content_type.format

        self.assertEqual('text/html; charset="utf-8"', str(content_type))

    def test_simple_attr_add(self):

        content_type = Header("Content-Type", 'text/html; charset="utf-8"')

        self.assertNotIn("format", content_type)

        content_type.format = "flowed"

        self.assertIn("format", content_type)

        self.assertEqual("flowed", content_type.format)

        self.assertEqual('text/html; charset="utf-8"; format="flowed"', content_type)


if __name__ == "__main__":
    unittest.main()
