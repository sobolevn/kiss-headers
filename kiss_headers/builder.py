from base64 import b64decode, b64encode
from datetime import datetime, timezone
from email import utils
from re import findall, fullmatch
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import quote as url_quote

from kiss_headers.models import Header
from kiss_headers.utils import (
    class_to_header_name,
    header_content_split,
    prettify_header_name,
    quote,
    unquote,
)


"""
Use https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/ to create subclasses of CustomHeader.
"""


class CustomHeader(Header):
    """
    This class is a helper to create ready-to-use Header object with creation assistance.
    Should NOT be instantiated.
    Use this class as a direct parent for creating ready-to-use header object. Inspire yourself with already defined
    class bellow this one.
    """

    __squash__: bool = False  # This value indicate whenever the representation of multiple entries should be squashed into one content.
    __tags__: List[str] = []

    __override__: Optional[
        str
    ] = None  # Create this static member in your custom header when the class name does not match the target header.

    def __init__(self, initial_content: str = "", **kwargs: Optional[str]):
        """
        :param initial_content: Initial content of the Header if any.
        :param kwargs: Provided args. Any key that associate a None value are just ignored.
        """
        if self.__class__ == CustomHeader:
            raise NotImplementedError(
                "You can not instantiate CustomHeader class. You may create first your class that inherit it."
            )

        super().__init__(
            class_to_header_name(self.__class__)
            if not self.__class__.__override__
            else prettify_header_name(self.__class__.__override__),
            initial_content,
        )

        for attribute, value in kwargs.items():
            if value is None:
                continue
            self[attribute] = value


class ContentSecurityPolicy(CustomHeader):
    """
    Content-Security-Policy is the name of a HTTP response header
    that modern browsers use to enhance the security of the document (or web page).
    The Content-Security-Policy header allows you to restrict how resources such as
    JavaScript, CSS, or pretty much anything that the browser loads.
    """

    __tags__ = ["response"]

    def __init__(self, *policies: List[str]):
        """
        :param policies: One policy consist of a list of str like ["default-src", "'none'"].
        >>> header = ContentSecurityPolicy(["default-src", "'none'"], ["img-src", "'self'", "img.example.com"])
        >>> repr(header)
        "Content-Security-Policy: default-src 'none'; img-src 'self' img.example.com"
        >>> header.get_policies_names()
        ['default-src', 'img-src']
        >>> header.get_policy_args("img-src")
        ["'self'", 'img.example.com']
        """
        super().__init__("")

        for policy in policies:
            if len(policy) == 0 or policy[0] not in {
                "default-src",
                "script-src",
                "style-src",
                "img-src",
                "connect-src",
                "font-src",
                "object-src",
                "media-src",
                "frame-src",
                "sandbox",
                "report-uri",
                "child-src",
                "form-action",
                "frame-ancestors",
                "plugin-types",
                "base-uri",
                "report-to",
                "worker-src",
                "manifest-src",
                "prefetch-src",
                "navigate-to",
            }:
                raise ValueError(
                    f"Policy {policy[0]} is not a valid one. See https://content-security-policy.com/ for instructions."
                )
            elif len(policy) == 1:
                raise ValueError(
                    f"Policy {policy[0]} need at least one argument to proceed."
                )

            self += " ".join(policy)  # type: ignore

    def get_policies_names(self) -> List[str]:
        """Fetch a list of policy name set in content."""
        return [member.split(" ")[0] for member in self.attrs]

    def get_policy_args(self, policy_name: str) -> Optional[List[str]]:
        """Retrieve given arguments for a policy."""
        policy_name = policy_name.lower()

        for member in self.attrs:
            parts: List[str] = member.split(" ")

            if parts[0].lower() == policy_name:
                return parts[1:]

        return None


class Accept(CustomHeader):
    """
    The Accept request HTTP header advertises which content types, expressed as MIME types,
    the client is able to understand. Using content negotiation, the server then selects one of
    the proposals, uses it and informs the client of its choice with the Content-Type response header.
    """

    __squash__: bool = True
    __tags__: List[str] = ["request"]

    def __init__(
        self, mime: str = "*/*", qualifier: float = 1.0, **kwargs: Optional[str],
    ):
        """
        :param mime: Describe the MIME using this syntax <MIME_type/MIME_subtype>
        :param qualifier: Any value used is placed in an order of preference expressed using relative quality value called the weight.
        :param kwargs:
        >>> header = Accept("text/html", qualifier=0.8)
        >>> header.content
        'text/html; q="0.8"'
        >>> repr(header)
        'Accept: text/html; q="0.8"'
        """
        if len(mime.split("/")) != 2:
            raise ValueError(
                f"The MIME should be described using this syntax <MIME_type/MIME_subtype> not '{mime}'"
            )

        args: Dict = {"q": qualifier if qualifier < 1.0 else None}

        args.update(kwargs)

        super().__init__(
            mime, **args,
        )

    def get_mime(self) -> Optional[str]:
        """Return defined mime in current accept header."""
        for el in self.attrs:
            if "/" in el:
                return el
        return None

    def get_qualifier(self, _default: Optional[float] = 1.0) -> Optional[float]:
        """Return defined qualifier for specified mime. If not set, output 1.0."""
        return float(str(self["q"])) if self.has("q") else _default


class ContentType(CustomHeader):
    """
    The Content-Type entity header is used to indicate the media type of the resource.

    In responses, a Content-Type header tells the client what the content type of the returned content actually is.
    Browsers will do MIME sniffing in some cases and will not necessarily follow the value of this header;
    to prevent this behavior, the header X-Content-Type-Options can be set to nosniff.
    """

    __tags__: List[str] = ["request", "response"]

    def __init__(
        self,
        mime: str,
        charset: Optional[str] = None,
        format_: Optional[str] = None,
        boundary: Optional[str] = None,
        **kwargs: Optional[str],
    ):
        """
        :param mime_type: The MIME type of the resource or the data. Format <MIME_type>/<MIME_subtype>.
        :param charset: The character encoding standard. Should be an IANA name.
        :param format_: Mostly used in IMAP, could be one of : original or flowed.
        :param boundary: For multipart entities the boundary directive is required, which consists of 1 to 70 characters from a set of characters known to be very robust through email gateways, and not ending with white space. It is used to encapsulate the boundaries of the multiple parts of the message.
        :param kwargs:
        >>> header = ContentType("text/html", charset="utf-8")
        >>> repr(header)
        'Content-Type: text/html; charset="UTF-8"'
        >>> header.get_charset()
        'UTF-8'
        >>> header.get_mime()
        'text/html'
        """

        if len(mime.split("/")) != 2:
            raise ValueError(
                f"The MIME should be described using this syntax <MIME_type/MIME_subtype> not '{mime}'"
            )

        args: Dict = {
            "charset": charset.upper() if charset else None,
            "format": format_,
            "boundary": boundary,
        }

        args.update(kwargs)

        super().__init__(mime, **args)

    def get_mime(self) -> Optional[str]:
        """Return defined mime in content type."""
        for el in self.attrs:
            if "/" in el:
                return el
        return None

    def get_charset(self, _default: Optional[str] = "ISO-8859-1") -> Optional[str]:
        """Extract defined charset, if not present will return 'ISO-8859-1' by default."""
        return str(self["charset"]) if self.has("charset") else _default


class XContentTypeOptions(CustomHeader):
    """
    The X-Content-Type-Options response HTTP header is a marker used by the server to indicate that
    the MIME types advertised in the Content-Type headers should not be changed and be followed.
    This allows to opt-out of MIME type sniffing, or, in other words, it is a way to say that
    the webmasters knew what they were doing.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, nosniff: bool = True, **kwargs: Optional[str]):
        """
        :param nosniff: see https://fetch.spec.whatwg.org/#x-content-type-options-header
        :param kwargs:
        >>> header = XContentTypeOptions(nosniff=True)
        >>> repr(header)
        'X-Content-Type-Options: nosniff'
        """
        super().__init__("nosniff" if nosniff else "", **kwargs)


class ContentDisposition(CustomHeader):
    """
    In a regular HTTP response, the Content-Disposition response header is a header indicating
    if the content is expected to be displayed inline in the browser, that is, as a Web page or
    as part of a Web page, or as an attachment, that is downloaded and saved locally.
    """

    __tags__: List[str] = ["request", "response"]

    def __init__(
        self,
        disposition: str = "inline",
        name: Optional[str] = None,
        filename: Optional[str] = None,
        fallback_filename: Optional[str] = None,
        boundary: Optional[str] = None,
        **kwargs: Optional[str],
    ):
        """
        :param disposition: Could be either inline, form-data, attachment or empty. Choose one. Default to inline.
        :param name: Is a string containing the name of the HTML field in the form that the content of this subpart refers to.
        :param filename: Is a string containing the original name of the file transmitted. The filename is always optional and must not be used blindly by the application. ASCII-US Only.
        :param fallback_filename: Fallback filename if filename parameter does not uses the encoding defined in RFC 5987.
        :param boundary: For multipart entities the boundary directive is required, which consists of 1 to 70 characters from a set of characters known to be very robust through email gateways, and not ending with white space. It is used to encapsulate the boundaries of the multiple parts of the message.
        :param kwargs:
        """
        if disposition not in ["attachment", "inline", "form-data", ""]:
            raise ValueError(
                "Disposition should be either inline, form-data, attachment or empty. Choose one."
            )

        if fallback_filename:
            try:
                fallback_filename.encode("ASCII")
            except UnicodeEncodeError:
                raise ValueError(
                    "The fallback filename should only contain valid ASCII characters. Not '{fb_filename}'. Use fallback_filename instead.".format(
                        fb_filename=fallback_filename
                    )
                )

        args: Dict = {
            "name": name,
            "filename": filename,
            "filename*": ("UTF-8''" + url_quote(fallback_filename))
            if fallback_filename
            else None,
            "boundary": boundary,
        }

        args.update(kwargs)

        super().__init__(
            disposition, **args,
        )


class Authorization(CustomHeader):
    """
    The HTTP Authorization request header contains the credentials to authenticate a user agent with a server,
    usually, but not necessarily, after the server has responded with a 401 Unauthorized status
    and the WWW-Authenticate header.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, type_: str, credentials: str, **kwargs: Optional[str]):
        """
        :param type_: Authentication type. A common type is "Basic". See IANA registry of Authentication schemes for others.
        :param credentials: Associated credentials to use. Preferably Base-64 encoded.
        >>> header = Authorization("Bearer", "base64encoded")
        >>> repr(header)
        'Authorization: Bearer base64encoded'
        """
        if type_.lower() not in [
            "basic",
            "bearer",
            "digest",
            "hoba",
            "mutual",
            "negotiate",
            "oauth",
            "scram-sha-1",
            "scram-sha-256",
            "vapid",
            "aws4-hmac-sha256",
            "ntlm",
        ]:
            raise ValueError(
                "Authorization type should exist in IANA registry of Authentication schemes"
            )

        super().__init__(
            "{type_} {credentials}".format(type_=type_, credentials=credentials),
            **kwargs,
        )

    def get_auth_type(self) -> str:
        """Return the auth type used in Authorization."""
        return self.content.split(" ", maxsplit=1)[0]

    def get_credentials(self) -> str:
        """Output the credentials."""
        return self.content.split(" ", maxsplit=1)[1]


class BasicAuthorization(Authorization):
    """
    Same as Authorization header but simplified for the Basic method. Also an example of __override__ usage.
    """

    __override__ = "Authorization"

    def __init__(
        self,
        username: str,
        password: str,
        charset: str = "latin1",
        **kwargs: Optional[str],
    ):
        """
        :param username:
        :param password:
        :param charset: By default, credentials are encoded using latin1 charset. You may want to choose otherwise.
        :param kwargs:
        >>> header = BasicAuthorization("azerty", "qwerty")
        >>> header
        Authorization: Basic YXplcnR5OnF3ZXJ0eQ==
        >>> header.get_username_password()
        ('azerty', 'qwerty')
        """
        if ":" in username:
            raise ValueError("The username cannot contain a single colon in it.")

        b64_auth_content: str = b64encode(
            (username + ":" + password).encode(charset)
        ).decode("ascii")

        super().__init__("Basic", b64_auth_content, **kwargs)

    def get_credentials(self, __default_charset: str = "latin1") -> str:
        """Decode base64 encoded credentials from Authorization header."""
        if self.get_auth_type().lower() != "basic":
            raise ValueError(
                f"Only Authorization using Basic method is supported by BasicAuthorization. Given '{self.get_auth_type()}'."
            )

        return b64decode(super().get_credentials()).decode(__default_charset)

    def get_username_password(
        self, __default_charset: str = "latin1"
    ) -> Tuple[str, ...]:
        """Extract username and password as a tuple from Basic Authorization."""
        return tuple(self.get_credentials(__default_charset).split(":", maxsplit=1))


class ProxyAuthorization(Authorization):
    """
    The HTTP Proxy-Authorization request header contains the credentials to authenticate a user agent to a proxy server,
    usually after the server has responded with a 407 Proxy Authentication Required status
    and the Proxy-Authenticate header.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, type_: str, credentials: str):
        """
        :param type_: Authentication type. A common type is "Basic". See IANA registry of Authentication schemes for others.
        :param credentials: Associated credentials to use. Preferably Base-64 encoded.
        """
        super().__init__(type_, credentials)


class Host(CustomHeader):
    """
    The Host request header specifies the domain name of the server (for virtual hosting),
    and (optionally) the TCP port number on which the server is listening.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, host: str, port: Optional[int] = None, **kwargs: Optional[str]):
        """
        :param host: The domain name of the server (for virtual hosting).
        :param port: TCP port number on which the server is listening.
        >>> header = Host("www.python.org")
        >>> repr(header)
        'Host: www.python.org'
        >>> header = Host("www.python.org", port=8000)
        >>> repr(header)
        'Host: www.python.org:8000'
        """
        super().__init__(host + (":" + str(port) if port else ""), **kwargs)


class Connection(CustomHeader):
    """
    The Connection general header controls whether or not the network connection stays open after the current transaction finishes.
    If the value sent is keep-alive, the connection is persistent and not closed, allowing for subsequent requests to the same server to be done.
    """

    __tags__ = ["request", "response"]

    def __init__(self, should_keep_alive: bool, **kwargs: Optional[str]):
        """
        :param should_keep_alive: Indicates that the client would like to keep the connection open or not.
        :param kwargs:
        """
        super().__init__("keep-alive" if should_keep_alive else "close", **kwargs)


class ContentLength(CustomHeader):
    """
    The Content-Length entity header indicates the size of the entity-body, in bytes, sent to the recipient.
    """

    __tags__: List[str] = ["request", "response"]

    def __init__(self, length: int, **kwargs: Optional[str]):
        """
        :param length: The length in decimal number of octets.
        """
        super().__init__(str(length), **kwargs)


class Date(CustomHeader):
    """
    The Date general HTTP header contains the date and time at which the message was originated.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, my_date: Union[datetime, str], **kwargs: Optional[str]):
        """
        :param my_date: Can either be a datetime that will be automatically converted or a raw string.
        :param kwargs:
        """
        super().__init__(
            utils.format_datetime(my_date.astimezone(timezone.utc), usegmt=True)
            if not isinstance(my_date, str)
            else my_date,
            **kwargs,
        )

    def get_datetime(self) -> datetime:
        """Parse and return a datetime according to content."""
        return utils.parsedate_to_datetime(str(self))


class CrossOriginResourcePolicy(CustomHeader):
    """
    The HTTP Cross-Origin-Resource-Policy response header conveys a desire that
    the browser blocks no-cors cross-origin/cross-site requests to the given resource.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, policy: str, **kwargs: Optional[str]):
        """
        :param policy: Accepted values are same-site, same-origin or cross-origin.
        :param kwargs:
        """
        policy = policy.lower()

        if policy not in ["same-site", "same-origin", "cross-origin"]:
            raise ValueError(
                "'{policy}' is not a recognized policy for Cross-Origin-Resource-Policy. Accepted values are same-site, same-origin or cross-origin."
            )

        super().__init__(policy, **kwargs)


class Allow(CustomHeader):
    """
    The Allow header lists the set of methods supported by a resource.
    """

    __tags__ = ["response"]
    __squash__ = True

    def __init__(self, supported_verb: str, **kwargs: Optional[str]):
        """
        :param supported_verb: Choose exactly one of "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE", "PURGE", "CONNECT" or "TRACE" HTTP verbs.
        :param kwargs:
        >>> header = Allow("POST")
        >>> repr(header)
        'Allow: POST'
        """
        supported_verb = supported_verb.upper()

        if supported_verb not in [
            "HEAD",
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "PURGE",
            "CONNECT",
            "TRACE",
        ]:
            raise ValueError(
                "'{verb}' is not a supported verb. Please choose only one HTTP verb per Allow header."
            )

        super().__init__(supported_verb, **kwargs)


class Digest(CustomHeader):
    """
    The Digest response HTTP header provides a digest of the requested resource. RFC 7231.
    """

    __tags__ = ["response"]

    def __init__(self, algorithm: str, value: str, **kwargs: Optional[str]):
        """
        :param algorithm: Supported digest algorithms are defined in RFC 3230 and RFC 5843, and include SHA-256 and SHA-512.
        :param value: The result of applying the digest algorithm to the resource representation and encoding the result.
        :param kwargs:
        """
        args: Dict = {algorithm: value}
        args.update(kwargs)

        super().__init__("", **args)


class Cookie(CustomHeader):
    """The Cookie HTTP request header contains stored HTTP cookies previously sent by
    the server with the Set-Cookie header."""

    __tags__ = ["request"]

    def __init__(self, **kwargs: Optional[str]):
        """
        :param kwargs: Pair of cookie name associated with a value.
        """
        super().__init__("", **kwargs)

    def get_cookies_names(self) -> List[str]:
        """Retrieve all defined cookie names from Cookie header."""
        return self.attrs

    def get_cookie_value(
        self, cookie_name: str, __default: Optional[str] = None
    ) -> Optional[str]:
        """Retrieve associated value with a given cookie name."""
        return str(self[cookie_name]) if cookie_name in self else __default


class SetCookie(CustomHeader):
    """
    The Set-Cookie HTTP response header is used to send cookies from the server to the user agent,
    so the user agent can send them back to the server later.
    """

    __tags__: List[str] = ["response"]

    def __init__(
        self,
        cookie_name: str,
        cookie_value: str,
        expires: Optional[Union[datetime, str]] = None,
        max_age: Optional[int] = None,
        domain: Optional[str] = None,
        path: Optional[str] = None,
        samesite: Optional[str] = None,
        is_secure: bool = False,
        is_httponly: bool = True,
        **kwargs: Optional[str],
    ):
        """
        :param cookie_name: Can be any US-ASCII characters, except control characters, spaces, or tabs.
        :param cookie_value: Can include any US-ASCII characters excluding control characters, Whitespace, double quotes, comma, semicolon, and backslash.
        :param expires: The maximum lifetime of the cookie as an HTTP-date timestamp. Provided datetime will be converted automatically.
        :param max_age: Number of seconds until the cookie expires. A zero or negative number will expire the cookie immediately. If both Expires and Max-Age are set, Max-Age has precedence.
        :param domain: Hosts to where the cookie will be sent. If omitted, defaults to the host of the current document URL, not including subdomains.
        :param path: A path that must exist in the requested URL, or the browser won't send the Cookie header.
        :param samesite: Asserts that a cookie must not be sent with cross-origin requests, providing some protection against cross-site request forgery attacks.
        :param is_secure: A secure cookie is only sent to the server when a request is made with the https: scheme.
        :param is_httponly: Forbids JavaScript from accessing the cookie.
        :param kwargs:
        """

        for letter in cookie_name:
            if letter in {'<>@,;:\\"/[]?={}'}:
                raise ValueError(
                    'The cookie name can not contains any of the following char: <>@,;:"/[]?={}'
                )

        if samesite and samesite.lower() not in ["strict", "lax", "none"]:
            raise ValueError(
                "Samesite attribute can only be one of the following: Strict, Lax or None."
            )

        args: Dict = {
            cookie_name: cookie_value,
            "expires": utils.format_datetime(
                expires.astimezone(timezone.utc), usegmt=True
            )
            if isinstance(expires, datetime)
            else expires,
            "max-age": max_age,
            "domain": domain,
            "path": path,
            "samesite": samesite,
        }

        args.update(kwargs)

        super().__init__("", **args)

        if is_secure:
            self += "Secure"  # type: ignore
        if is_httponly:
            self += "HttpOnly"  # type: ignore

    def is_http_only(self) -> bool:
        """Determine if the cookie can only be accessed by the browser."""
        return "HttpOnly" in self

    def is_secure(self) -> bool:
        """Determine if the cookie is TLS/SSL only."""
        return "Secure" in self

    def get_expire(self) -> Optional[datetime]:
        """Retrieve the parsed expiration date."""
        return (
            utils.parsedate_to_datetime(str(self["expires"]))
            if self.has("expires")
            else None
        )

    def get_max_age(self) -> Optional[int]:
        """Getting the max-age value as an integer if set."""
        return int(str(self["max-age"])) if "max-age" in self else None

    def get_cookie_name(self) -> str:
        """Extract the cookie name."""
        return self.attrs[0]

    def get_cookie_value(self) -> str:
        """Extract the cookie value."""
        return str(self[self.get_cookie_name()])


class StrictTransportSecurity(CustomHeader):
    """
    The HTTP Strict-Transport-Security response header (often abbreviated as HSTS) lets a web site
    tell browsers that it should only be accessed using HTTPS, instead of using HTTP.
    """

    __tags__: List[str] = ["response"]

    def __init__(
        self,
        max_age: int,
        does_includesubdomains: bool = False,
        is_preload: bool = False,
        **kwargs: Optional[str],
    ):
        """
        :param max_age: The time, in seconds, that the browser should remember that a site is only to be accessed using HTTPS.
        :param does_includesubdomains: If this optional parameter is specified, this rule applies to all of the site's subdomains as well.
        :param is_preload: Preloading Strict Transport Security. Google maintains an HSTS preload service. By following the guidelines and successfully submitting your domain, browsers will never connect to your domain using an insecure connection.
        :param kwargs:
        """
        args: Dict = {"max-age": max_age}

        args.update(kwargs)

        super().__init__("", **args)

        if does_includesubdomains:
            self += "includeSubDomains"  # type: ignore

        if is_preload:
            self += "preload"  # type: ignore

    def does_includesubdomains(self) -> bool:
        """Verify if this rule applies to all of the site's subdomains."""
        return "includeSubDomains" in self

    def should_preload(self) -> bool:
        """Verify if Preloading Strict Transport Security should be set."""
        return "preload" in self

    def get_max_age(self) -> Optional[int]:
        """Get the time, in seconds, if set, that the browser should remember."""
        return int(str(self["max-age"])) if self.has("max-age") else None


class UpgradeInsecureRequests(CustomHeader):
    """
    The HTTP Upgrade-Insecure-Requests request header sends a signal to the server expressing
    the client’s preference for an encrypted and authenticated response, and that it
    can successfully handle the upgrade-insecure-requests CSP directive.
    """

    __tags__: List[str] = ["request", "response"]

    def __init__(self, **kwargs: Optional[str]):
        super().__init__("1", **kwargs)


class TransferEncoding(CustomHeader):
    """
    The Transfer-Encoding header specifies the form of encoding used to safely transfer the payload body to the user.
    """

    __tags__: List[str] = ["response"]
    __squash__: bool = True

    def __init__(
        self, method: str, **kwargs: Optional[str],
    ):
        """
        :param method: Either chunked, compress, deflate, gzip, identity or br.
        :param kwargs:
        """

        method = method.lower()

        if method not in [
            "chunked",
            "compress",
            "deflate",
            "gzip",
            "identity",
            "br",
            "*",
        ]:
            raise ValueError(
                "You should choose between 'chunked', 'compress', 'deflate', 'gzip', 'identity' or 'br' for the encoding method."
            )

        super().__init__(method, **kwargs)


class ContentEncoding(TransferEncoding):
    """
    The Content-Encoding entity header is used to compress the media-type. When present,
    its value indicates which encodings were applied to the entity-body. It lets the client
    know how to decode in order to obtain the media-type referenced by the Content-Type header.

    If multiple, keep them in the order in which they were applied.
    """

    __tags__ = ["request", "response"]

    def __init__(self, method: str, **kwargs: Optional[str]):
        """
        :param method: Either chunked, compress, deflate, gzip, identity or br.
        :param kwargs:
        """

        super().__init__(method, **kwargs)


class AcceptEncoding(TransferEncoding):
    """
    The Accept-Encoding request HTTP header advertises which content encoding, usually a compression algorithm,
    the client is able to understand. Using content negotiation, the server selects one of the proposals,
    uses it and informs the client of its choice with the Content-Encoding response header.
    """

    __tags__ = ["request"]

    def __init__(self, method: str, qualifier: float = 1.0, **kwargs: Optional[str]):
        """
        :param method: Either chunked, compress, deflate, gzip, identity, br or a wildcard.
        :param qualifier: Any value used is placed in an order of preference expressed using relative quality value called the weight.
        :param kwargs:
        """
        args: Dict = {"q": qualifier if qualifier != 1.0 else None}

        args.update(kwargs)

        super().__init__(method, **args)

    def get_qualifier(self, _default: Optional[float] = 1.0) -> Optional[float]:
        """Return defined qualifier for specified encoding. If not set, output 1.0."""
        return float(str(self["q"])) if self.has("q") else _default


class Dnt(CustomHeader):
    """
    The DNT (Do Not Track) request header indicates the user's tracking preference.
    It lets users indicate whether they would prefer privacy rather than personalized content.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, tracking_consent: bool = False, **kwargs: Optional[str]):
        """
        :param tracking_consent: The user prefers to allow tracking on the target site or not.
        :param kwargs:
        """
        super().__init__("0" if tracking_consent else "1", **kwargs)


class UserAgent(CustomHeader):
    """
    The User-Agent request header is a characteristic string that lets servers and network
    peers identify the application, operating system, vendor, and/or version of the requesting user agent.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, characteristics: str, **kwargs: Optional[str]):
        super().__init__(characteristics, **kwargs)


class AltSvc(CustomHeader):
    """
    The Alt-Svc HTTP response header is used to advertise alternative services through which
    the same resource can be reached. An alternative service is defined by a protocol/host/port combination.
    """

    __tags__: List[str] = ["response"]
    __squash__: bool = True

    def __init__(
        self,
        protocol_id: str,
        alt_authority: str,
        max_age: Optional[int] = None,
        versions: Optional[List[str]] = None,
        do_persist: Optional[bool] = None,
        **kwargs: Optional[str],
    ):
        """
        :param protocol_id: The ALPN protocol identifier. Examples include h2 for HTTP/2 and h3-25 for draft 25 of the HTTP/3 protocol.
        :param alt_authority: The quoted string specifying the alternative authority which consists of an optional host override, a colon, and a mandatory port number.
        :param max_age: The number of seconds for which the alternative service is considered fresh. If omitted, it defaults to 24 hours.
        :param versions: List of supported versions of the protocol id if the protocol id can be ambiguous. (like QUIC)
        :param do_persist: Use the parameter to ensures that the entry is not deleted through network configuration changes.
        :param kwargs:
        """
        args: Dict = {
            protocol_id: alt_authority,
            "ma": max_age,
            "persist": 1 if do_persist else None,
            "v": ",".join(versions) if versions else None,
        }

        args.update(kwargs)

        super().__init__(**args)

    def get_protocol_id(self) -> str:
        """Get the ALPN protocol identifier."""
        return self.attrs[0]

    def get_alt_authority(self) -> str:
        """Extract the alternative authority which consists of an optional host override, a colon, and a mandatory port number."""
        return str(self[self.get_protocol_id()])

    def get_max_age(self) -> Optional[int]:
        """Output the number of seconds for which the alternative service is considered fresh. None if undefined."""
        return int(str(self["ma"])) if "ma" in self else None

    def get_versions(self) -> Optional[List[str]]:
        """May return, if available, a list of versions of the ALPN protocol identifier."""
        return str(self["v"]).split(",") if "v" in self else None

    def should_persist(self) -> Optional[bool]:
        """Verify if the entry should not be deleted through network configuration changes. None if no indication."""
        return str(self["persist"]) == "1" if "persist" in self else None


class Forwarded(CustomHeader):
    """
    The Forwarded header contains information from the client-facing side of proxy servers
    that is altered or lost when a proxy is involved in the path of the request.
    """

    __tags__: List[str] = ["request", "response"]

    def __init__(
        self,
        by: str,
        for_: str,
        using_proto: str,
        host: Optional[str] = None,
        **kwargs: Optional[str],
    ):
        """
        :param by: The interface where the request came in to the proxy server. Could be an IP address, an obfuscated identifier or "unknown".
        :param for_: The client that initiated the request and subsequent proxies in a chain of proxies.
        :param host: The Host request header field as received by the proxy.
        :param using_proto: Indicates which protocol was used to make the request (typically "http" or "https").
        :param kwargs:
        """
        args: Dict = {"by": by, "for": for_, "host": host, "proto": using_proto}

        args.update(kwargs)

        super().__init__("", **args)


class LastModified(Date):
    """
    The Last-Modified response HTTP header contains the date and time at which the origin server
    believes the resource was last modified. It is used as a validator
    to determine if a resource received or stored is the same.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, my_date: Union[datetime, str], **kwargs: Optional[str]):
        """
        :param my_date:
        :param kwargs:
        """
        super().__init__(my_date, **kwargs)


class Referer(CustomHeader):
    """
    The Referer request header contains the address of the previous web page from which a link to the currently
    requested page was followed. The Referer header allows servers to identify where people are
    visiting them from and may use that data for analytics, logging, or optimized caching, for example.

    Note that referer is actually a misspelling of the word "referrer". See https://en.wikipedia.org/wiki/HTTP_referer
    """

    __tags__: List[str] = ["request"]

    def __init__(self, url: str, **kwargs: Optional[str]):
        """
        :param url: An absolute or partial address of the previous web page from which a link to the currently requested page was followed. URL fragments not included.
        :param kwargs:
        """
        super().__init__(url, **kwargs)


class ReferrerPolicy(CustomHeader):
    """
    The Referrer-Policy HTTP header controls how much referrer information
    (sent via the Referer header) should be included with requests.
    """

    __tags__: List[str] = ["response"]
    __squash__ = True

    def __init__(self, policy: str, **kwargs: Optional[str]):
        """
        :param policy: Either "no-referrer", "no-referrer-when-downgrade", "origin", "origin-when-cross-origin", "same-origin", "strict-origin", "strict-origin-when-cross-origin", "unsafe-url"
        :param kwargs:
        """
        if policy not in [
            "no-referrer",
            "no-referrer-when-downgrade",
            "origin",
            "origin-when-cross-origin",
            "same-origin",
            "strict-origin",
            "strict-origin-when-cross-origin",
            "unsafe-url",
        ]:
            raise ValueError(
                f"'{policy}' is not a valid referrer policy. Please choose only one per ReferrerPolicy instance"
            )

        super().__init__(policy, **kwargs)


class RetryAfter(Date):
    """
    The Retry-After response HTTP header indicates how long the user agent should wait
    before making a follow-up request.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, delay_or_date: Union[datetime, int], **kwargs: Optional[str]):
        super().__init__(
            delay_or_date
            if isinstance(delay_or_date, datetime)
            else str(delay_or_date),
            **kwargs,
        )


class AcceptLanguage(CustomHeader):
    """
    The Accept-Language request HTTP header advertises which languages the client is able to understand,
    and which locale variant is preferred. (By languages, we mean natural languages,
    such as English, and not programming languages.)
    """

    __squash__: bool = True
    __tags__: List[str] = ["request"]

    def __init__(
        self, language: str = "*", qualifier: float = 1.0, **kwargs: Optional[str]
    ):
        """
        :param language: A language tag (which is sometimes referred to as a "locale identifier"). This consists of a 2-3 letter base language tag representing the language.
        :param qualifier: Any value placed in an order of preference expressed using a relative quality value called weight.
        :param kwargs:
        """
        args: Dict = {"q": qualifier if qualifier < 1.0 else None}

        args.update(kwargs)

        super().__init__(
            language, **args,
        )

    def get_qualifier(self, _default: Optional[float] = 1.0) -> Optional[float]:
        """Return defined qualifier for specified language. If not set, output 1.0."""
        return float(str(self["q"])) if self.has("q") else _default


class Etag(CustomHeader):
    """
    The ETag HTTP response header is an identifier for a specific version of a resource.
    It lets caches be more efficient and save bandwidth, as a web server does not need to
    resend a full response if the content has not changed.
    """

    __tags__: List[str] = ["response"]

    def __init__(
        self,
        etag_value: str,
        is_a_weak_validator: bool = False,
        **kwargs: Optional[str],
    ):
        """
        :param etag_value: Entity tag uniquely representing the requested resource. ASCII string only. Not quoted.
        :param is_a_weak_validator: Indicates that a weak validator is used. Weak etags are easy to generate, but are far less useful for comparisons.
        :param kwargs:
        """
        super().__init__(
            "{weak_validation_cond}{etag}".format(
                weak_validation_cond="W/" if is_a_weak_validator else "",
                etag=quote(etag_value),
            ),
            **kwargs,
        )


class XFrameOptions(CustomHeader):
    """
    The X-Frame-Options HTTP response header can be used to indicate whether or not a browser
    should be allowed to render a page in a <frame>, <iframe>, <embed> or <object>. Sites can use this to
    avoid clickjacking attacks, by ensuring that their content is not embedded into other sites.
    """

    __tags__: List[str] = ["response"]

    def __init__(self, policy: str, **kwargs: Optional[str]):
        """
        :param policy: Can be either DENY or SAMEORIGIN.
        :param kwargs:
        """
        policy = policy.upper()

        if policy not in ["DENY", "SAMEORIGIN"]:
            raise ValueError(
                "'{policy}' is not a valid X-Frame-Options policy. Choose between DENY and SAMEORIGIN."
            )

        super().__init__(policy, **kwargs)


class XXssProtection(CustomHeader):
    """
    The HTTP X-XSS-Protection response header is a feature of Internet Explorer, Chrome and Safari that
    stops pages from loading when they detect reflected cross-site scripting (XSS) attacks.
    Although these protections are largely unnecessary in modern browsers when sites implement a strong
    Content-Security-Policy that disables the use of inline JavaScript
    """

    __tags__: List[str] = ["response"]

    def __init__(
        self,
        enable_filtering: bool = True,
        enable_block_rendering: bool = False,
        report_uri: Optional[str] = None,
        **kwargs: Optional[str],
    ):
        """
        :param enable_filtering: Enables XSS filtering (usually default in browsers). If a cross-site scripting attack is detected, the browser will sanitize the page (remove the unsafe parts).
        :param enable_block_rendering: Rather than sanitizing the page, the browser will prevent rendering of the page if an attack is detected.
        :param report_uri: (Chromium only) If a cross-site scripting attack is detected, the browser will sanitize the page and report the violation. This uses the functionality of the CSP report-uri directive to send a report.
        :param kwargs:
        """
        if enable_filtering is False:
            super().__init__("0", **kwargs)
            return

        args: Dict = {
            "mode": "block" if enable_block_rendering else None,
            "report": report_uri,
        }

        args.update(kwargs)

        super().__init__("1", **args)


class WwwAuthenticate(CustomHeader):
    """
    The HTTP WWW-Authenticate response header defines the authentication
    method that should be used to gain access to a resource.
    Fair-Warning : This header is like none other and is harder to parse. It need a specific case.
    """

    __tags__: List[str] = ["response"]
    __squash__ = True

    def __init__(
        self,
        auth_type: Optional[str] = None,
        challenge: str = "realm",
        value: str = "Secured area",
        **kwargs: Optional[str],
    ):
        """
        >>> www_authenticate = WwwAuthenticate("Basic", "realm", "Secured area")
        >>> repr(www_authenticate)
        'Www-Authenticate: Basic realm="Secured area"'
        >>> headers = www_authenticate + WwwAuthenticate(challenge="charset", value="UTF-8")
        >>> repr(headers)
        'Www-Authenticate: Basic realm="Secured area", charset="UTF-8"'
        >>> www_authenticate.get_challenge()
        ('realm', 'Secured area')
        >>> www_authenticate.get_auth_type()
        'Basic'
        """
        super().__init__(
            f'{auth_type+" " if auth_type else ""}{challenge}="{value}"', **kwargs
        )

    def get_auth_type(self) -> Optional[str]:
        """Retrieve given authentication method if defined."""
        parts: List[str] = header_content_split(str(self), " ")

        if len(parts) >= 1 and "=" not in parts:
            return parts[0]

        return None

    def get_challenge(self) -> Tuple[str, str]:
        """Output a tuple containing the challenge and the associated value. Raises :ValueError:"""
        parts: List[str] = header_content_split(str(self), " ")

        for part in parts:
            if "=" in part:
                challenge, value = tuple(part.split("=", maxsplit=1))
                return challenge, unquote(value)

        raise ValueError(
            f"WwwAuthenticate header does not seems to contain a valid content. No challenge detected."
        )


class XDnsPrefetchControl(CustomHeader):
    """
    The X-DNS-Prefetch-Control HTTP response header controls DNS prefetching, a feature by which browsers proactively
    perform domain name resolution on both links that the user may choose to follow as well as URLs
    for items referenced by the document, including images, CSS, JavaScript, and so forth.
    """

    __tags__ = ["response"]

    def __init__(self, enable: bool = True, **kwargs: Optional[str]):
        """
        :param enable: Toggle the specified behaviour.
        :param kwargs:
        """
        super().__init__("on" if enable else "off", **kwargs)


class Location(CustomHeader):
    """
    The Location response header indicates the URL to redirect a page to.
    It only provides a meaning when served with a 3xx (redirection) or 201 (created) status response.
    """

    __tags__ = ["response"]

    def __init__(self, uri: str, **kwargs: Optional[str]):
        """
        :param uri: A relative (to the request URL) or absolute URL.
        :param kwargs:
        """
        super().__init__(uri, **kwargs)


class From(CustomHeader):
    """
    The From request header contains an Internet email address for a human user who controls the requesting user agent.
    If you are running a robotic user agent (e.g. a crawler), the From header should be sent, so you can be contacted
    if problems occur on servers, such as if the robot is sending excessive, unwanted, or invalid requests.
    """

    __tags__: List[str] = ["request"]

    def __init__(self, email: str, **kwargs: Optional[str]):
        """
        :param email: A machine-usable email address. See RFC 5322.
        :param kwargs:
        """
        if (
            fullmatch(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email)
            is None
        ):
            raise ValueError(f"'{email}' is not a valid RFC 5322 email.")

        super().__init__(email, **kwargs)


class ContentRange(CustomHeader):
    """
    The Content-Range response HTTP header indicates where in a full body message a partial message belongs.
    """

    __tags__ = ["response"]

    def __init__(
        self,
        unit: str,
        start: int,
        end: int,
        size: Union[str, int],
        **kwargs: Optional[str],
    ):
        """
        :param unit: The unit in which ranges is specified. This is usually bytes.
        :param start: An integer in the given unit indicating the beginning of the request range.
        :param end: An integer in the given unit indicating the end of the requested range.
        :param size: The total size of the document (or '*' if unknown).
        :param kwargs:
        >>> header = ContentRange("bytes", 0, 1024, 4096)
        >>> repr(header)
        'Content-Range: bytes 0-1024/4096'
        >>> header.get_size()
        4096
        >>> header.unpack()
        ('bytes', '0', '1024', '4096')
        """
        super().__init__(f"{unit} {start}-{end}/{size}", **kwargs)

    def unpack(self) -> Tuple[str, str, str, str]:
        """Provide a basic way to parse ContentRange format."""
        return findall(
            r"^([0-9a-zA-Z*]+) ([0-9a-zA-Z*]+)-([0-9a-zA-Z*]+)/([0-9a-zA-Z*]+)$",
            str(self),
        )[0]

    def get_unit(self) -> str:
        """Retrieve the unit in which ranges is specified."""
        return self.unpack()[0]

    def get_start(self) -> int:
        """Get the beginning of the request range."""
        return int(self.unpack()[1])

    def get_end(self) -> int:
        """Get the end of the requested range."""
        return int(self.unpack()[2])

    def get_size(self) -> Union[str, int]:
        """Get the total size of the document (or '*' if unknown)."""
        size: str = self.unpack()[3]
        return int(size) if size.isdigit() else size


class CacheControl(CustomHeader):
    """
    The Cache-Control HTTP header holds directives (instructions) for caching in
    both requests and responses. A given directive in a request does not mean the
    same directive should be in the response.
    """

    __tags__ = ["request", "response"]
    __squash__ = True

    def __init__(
        self,
        directive: Optional[str] = None,
        max_age: Optional[int] = None,
        max_stale: Optional[int] = None,
        min_fresh: Optional[int] = None,
        s_maxage: Optional[int] = None,
        **kwargs: Optional[str],
    ):
        """
        Pass only one parameter per CacheControl instance.
        :param directive: Could be one of must-revalidate, no-cache, no-store, no-transform, public, private, proxy-revalidate, only-if-cached, no-transform.
        :param max_age: The maximum amount of time a resource is considered fresh. Unlike Expires, this directive is relative to the time of the request.
        :param max_stale: Indicates the client will accept a stale response. An optional value in seconds indicates the upper limit of staleness the client will accept.
        :param min_fresh: Indicates the client wants a response that will still be fresh for at least the specified number of seconds.
        :param s_maxage: Overrides max-age or the Expires header, but only for shared caches (e.g., proxies). Ignored by private caches.
        :param kwargs:
        """
        if [
            directive is not None,
            max_age is not None,
            max_stale is not None,
            min_fresh is not None,
            s_maxage is not None,
        ].count(True) != 1:
            raise ValueError(
                "You should only pass one parameter to a single CacheControl instance."
            )

        args: Dict = {
            "max-age": max_age,
            "max-stale": max_stale,
            "min-fresh": min_fresh,
            "s-maxage": s_maxage,
        }

        args.update(kwargs)

        super().__init__(directive if directive is not None else "", **args)


class Expires(Date):
    """
    The Expires header contains the date/time after which the response is considered stale.
    Invalid dates, like the value 0, represent a date in the past and mean that the resource is already expired.
    """

    __tags__ = ["response"]

    def __init__(
        self, datetime_or_custom: Union[datetime, str], **kwargs: Optional[str]
    ):
        super().__init__(datetime_or_custom, **kwargs)


class IfModifiedSince(Date):
    """
    The If-Modified-Since request HTTP header makes the request conditional
    """

    __tags__ = ["request"]

    def __init__(self, dt: Union[datetime, str], **kwargs: Optional[str]):
        """
        :param dt:
        :param kwargs:
        """
        super().__init__(dt, **kwargs)


class IfUnmodifiedSince(Date):
    """
    The If-Unmodified-Since request HTTP header makes the request conditional
    """

    def __init__(self, dt: Union[datetime, str], **kwargs: Optional[str]):
        """
        :param dt:
        :param kwargs:
        """
        super().__init__(dt, **kwargs)


class KeepAlive(CustomHeader):
    """
    The Keep-Alive general header allows the sender to hint about how the connection may be used to
    set a timeout and a maximum amount of requests.
    """

    __squash__ = True
    __tags__ = ["request", "response"]

    def __init__(
        self,
        timeout: Optional[int] = None,
        max_: Optional[int] = None,
        **kwargs: Optional[str],
    ):
        """
        :param timeout: indicating the minimum amount of time an idle connection has to be kept opened (in seconds).
        :param max: indicating the maximum number of requests that can be sent on this connection before closing it.
        :param kwargs:
        """
        if timeout is not None and max_ is not None:
            raise ValueError(
                "Can only provide one parameter per KeepAlive instance, either timeout or max, not both."
            )

        args: Dict = {"timeout": timeout, "max": max_}

        args.update(kwargs)

        super().__init__("", **args)


class IfMatch(CustomHeader):
    """
    The If-Match HTTP request header makes the request conditional. For GET and HEAD methods,
    the server will send back the requested resource only if it matches one of the listed ETags.
    For PUT and other non-safe methods, it will only upload the resource in this case.
    """

    __squash__ = True
    __tags__ = ["request"]

    def __init__(self, etag_value: str, **kwargs: Optional[str]):
        """
        :param etag_value: Entity tags uniquely representing the requested resources. They are a string of ASCII characters placed between double quotes (like "675af34563dc-tr34").
        :param kwargs:
        """
        super().__init__(quote(etag_value), **kwargs)


class IfNoneMatch(IfMatch):
    """
    The If-None-Match HTTP request header makes the request conditional. For GET and HEAD methods,
    the server will send back the requested resource, with a 200 status, only if it doesn't have an ETag matching
    the given ones. For other methods, the request will be processed only if the eventually existing resource's
    ETag doesn't match any of the values listed.
    """

    def __init__(self, etag_value: str, **kwargs: Optional[str]):
        super().__init__(etag_value, **kwargs)


class Server(CustomHeader):
    """The Server header describes the software used by the origin server that handled the request —
    that is, the server that generated the response."""

    __tags__ = ["response"]

    def __init__(self, product: str, **kwargs: Optional[str]):
        """
        :param product: The name of the software or product that handled the request. Usually in a format similar to User-Agent.
        :param kwargs:
        """
        super().__init__(product, **kwargs)


class Vary(CustomHeader):
    """The Vary HTTP response header determines how to match future request headers to decide whether a cached response
    can be used rather than requesting a fresh one from the origin server."""

    __squash__ = True
    __tags__ = ["response"]

    def __init__(self, header_name: str, **kwargs: Optional[str]):
        """
        :param header_name: An header name to take into account when deciding whether or not a cached response can be used.
        :param kwargs:
        """
        super().__init__(prettify_header_name(header_name), **kwargs)
