### Setup

To import `kiss_headers` :

```python
from kiss_headers import parse_it
from requests import get

headers = parse_it(get('https://www.python.org'))
```

### Check existence of an attribute in header

Choose any flavour you like when checking for an attribute like `charset=utf-8`.

```python
'charset' in headers.content_type
# OR
hasattr(headers.content_type, 'charset')
# OR
headers.content_type.has('charset')
```

### Accessing an attribute

```python
headers.content_type.charset
# OR
headers.content_type['charset']
# OR
headers.content_type.get('charset')
```

### Remove an attribute

If attribute exists multiple times, this removes all entries.

```python
del headers.content_type.charset
# OR
del headers.content_type['charset']
```

### Create an attribute on the fly

```python
headers.content_type.charset = 'utf-8'
# OR
headers.content_type['charset'] = 'utf-8'
```

