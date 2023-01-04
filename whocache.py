# python-whois==0.8.0
# stem==1.8.1

import os
import shelve
import socket
import sys
import timeit
import typing

from whois import WhoisEntry, whois as whois_impl, IPV4_OR_V6, extract_domain

from stem import Signal
from stem.control import Controller
from whois.parser import PywhoisError


def _reload_tor():
    with Controller.from_port(port=9051) as controller:
        controller.authenticate(password=None)
        controller.signal(Signal.NEWNYM)
        controller.close()


def _whois_tor_wrapper(
        domain: str,
        retries: int = 3,
        cached: typing.Optional[WhoisEntry] = None
) -> typing.Union[WhoisEntry, PywhoisError]:
    os.environ['SOCKS'] = '127.0.0.1:9050'

    if retries == 0:
        if cached is None:
            raise Exception(f"{retries=} but {cached=}")
        return cached

    text: str
    try:
        result = whois_impl(domain)
        text = result.text
    except PywhoisError as e:
        result = e
        text = str(e)

    if 'WHOIS LIMIT EXCEEDED' in text:
        _reload_tor()
        return _whois_tor_wrapper(domain, retries - 1, result)

    return result


def _ip_or_domain(url_or_domain: str) -> str:
    # clean domain to expose netloc
    ip_match = IPV4_OR_V6.match(url_or_domain)
    if ip_match:
        domain = url_or_domain
        try:
            result = socket.gethostbyaddr(domain)
        except socket.herror as e:
            pass
        else:
            domain = extract_domain(result[0])
    else:
        domain = extract_domain(url_or_domain)
    return domain


def _whois(domain: str, file_name: str) -> typing.Union[WhoisEntry, PywhoisError]:
    existing: typing.Optional[str]
    key = _ip_or_domain(domain)

    with shelve.open(file_name) as db:
        try:
            existing = db[key]
        except KeyError:
            existing = None
    if existing is not None:
        try:
            r = WhoisEntry.load(key, existing)
        except PywhoisError as e:
            r = e
        return r

    result = _whois_tor_wrapper(domain)
    with shelve.open(file_name) as db:
        if type(result) == PywhoisError:
            db[key] = str(result)
        else:
            db[key] = result.text
        db.sync()

    return result


def whois(domain: str, file_name: str) -> typing.Union[WhoisEntry, PywhoisError]:
    start = timeit.default_timer()
    result = _whois(domain, file_name)
    end = timeit.default_timer()
    duration = end - start
    print(f"[whois] {domain=} took {duration:.3f}s", file=sys.stderr)
    return result
