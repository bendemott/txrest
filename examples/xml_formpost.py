"""
The standard XML API expects a POST/PUT body to always be present, and to contain xml.
If you want different behavior, or expect Form-Encoded data, it's easy to accomdate that.
"""

from txrest.mixin import FormEncodedPost
