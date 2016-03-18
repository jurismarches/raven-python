"""
raven.contrib.django.middleware
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""

from __future__ import absolute_import

import threading
import logging

from django.conf import settings


def is_ignorable_404(uri):
    """
    Returns True if a 404 at the given URL *shouldn't* notify the site managers.
    """
    return any(
        pattern.search(uri)
        for pattern in getattr(settings, 'IGNORABLE_404_URLS', ())
    )


def get_grouping_fingerprint(uri):
    """
    Returns the corresponding fingerprint if the given URL matches a pattern
    of URLs that who should be grouped

    """
    for pattern, fingerprint in getattr(settings, 'GROUPING_404_URLS', ()):
        if pattern.search(uri):
            return fingerprint
    return None


class Sentry404CatchMiddleware(object):
    def process_response(self, request, response):
        from raven.contrib.django.models import client

        if response.status_code != 404 or is_ignorable_404(request.get_full_path()) or not client.is_enabled():
            return response

        kwargs = {}

        data = client.get_data_from_request(request)
        data.update({
            'level': logging.INFO,
            'logger': 'http404',
        })
        kwargs.update({
            'data': data
        })

        fingerprint = get_grouping_fingerprint(request.get_full_path())
        if fingerprint:
            kwargs.update({
                'fingerprint': fingerprint
            })

        message = 'Page Not Found: %s' % request.build_absolute_uri()

        result = client.captureMessage(message=message, **kwargs)

        request.sentry = {
            'project_id': data.get('project', client.remote.project),
            'id': client.get_ident(result),
        }
        return response

    # sentry_exception_handler(sender=Sentry404CatchMiddleware, request=request)


class SentryResponseErrorIdMiddleware(object):
    """
    Appends the X-Sentry-ID response header for referencing a message within
    the Sentry datastore.
    """
    def process_response(self, request, response):
        if not getattr(request, 'sentry', None):
            return response
        response['X-Sentry-ID'] = request.sentry['id']
        return response


class SentryLogMiddleware(object):
    # Create a threadlocal variable to store the session in for logging
    thread = threading.local()

    def process_request(self, request):
        self.thread.request = request
