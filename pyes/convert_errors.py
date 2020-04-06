# -*- coding: utf-8 -*-


"""
Routines for converting error responses to appropriate exceptions.
"""
from . import exceptions

__all__ = ['raise_if_error']

# Patterns used to map exception strings to classes.

# First, exceptions for which the messages start with the error name,
# and then contain the error description wrapped in [].
# https://github.com/elastic/elasticsearch/tree/0.90/src/main/java/org/elasticsearch
# Every Exception is defined inside an separate file.
exceptions_by_name = dict((name, getattr(exceptions, name))
for name in (
    "DocumentAlreadyExistsEngineException",
    "DocumentAlreadyExistsException",
    "TypeMissingException",
    "VersionConflictEngineException",
    'ClusterBlockException',
    'ElasticSearchIllegalArgumentException',
    'IndexAlreadyExistsException',
    'IndexMissingException',
    'InvalidIndexNameException',
    'MapperParsingException',
    'ReduceSearchPhaseException',
    'ReplicationShardOperationFailedException',
    'SearchPhaseExecutionException',
    'DocumentMissingException',
    )
)

# Second, patterns for exceptions where the message is just the error
# description, and doesn't contain an error name.  These patterns are matched
# at the end of the exception.
exception_patterns_trailing = {
    '] missing': exceptions.NotFoundException,
    '] Already exists': exceptions.AlreadyExistsException,
    }


# ALternatively, new ES version combine all exceptions inside one class
# https://github.com/elastic/elasticsearch-py/blob/master/elasticsearch/exceptions.py
# Reference:
# https://github.com/elastic/elasticsearch/blob/master/server/src/main/java/org/elasticsearch/ElasticsearchException.java#L743
# Throwed error example:
# {'error': {'index': 'stories-index',
#                      'index_uuid': 'SYE0_RANDOM_ID_54A',
#                      'reason': 'index [stories-index/SYE0_RANDOM_ID_54A] already exists',
#                      'root_cause': [{'index': 'stories-index',
#                                      'index_uuid': 'SYE0_RANDOM_ID_54A',
#                                      'reason': 'index [stories-index/SYE0_RANDOM_ID_54A] already exists',
#                                      'type': 'resource_already_exists_exception'}],
#                      'type': 'resource_already_exists_exception'},
#            'status': 400}
exceptions_by_type = {
    "index_not_found_exception": exceptions.IndexMissingException,
    "resource_already_exists_exception": exceptions.IndexAlreadyExistsException,
    "reduce_search_phase_exception": exceptions.ReduceSearchPhaseException,
    "version_conflict_engine_exception": exceptions.VersionConflictEngineException,
    "illegal_argument_exception": exceptions.ElasticSearchIllegalArgumentException,
}


def raise_if_error(status, result, request=None):
    """Raise an appropriate exception if the result is an error.

    Any result with a status code of 400 or higher is considered an error.

    The exception raised will either be an ElasticSearchException, or a more
    specific subclass of ElasticSearchException if the type is recognised.

    The status code and result can be retrieved from the exception by accessing its
    status and result properties.

    Optionally, this can take the original RestRequest instance which generated
    this error, which will then get included in the exception.

    """
    assert isinstance(status, int)
    print "DEBUG: raise_if_error status:%d result:%s" % (status, result)

    if status < 400:
        return

    if status == 404 and isinstance(result, dict) and 'error' not in result:
        raise exceptions.NotFoundException("Item not found", status, result, request)

    if not isinstance(result, dict) or 'error' not in result:
        raise exceptions.ElasticSearchException("Unknown exception type: %d, %s" % (status, result), status,
            result, request)

    error = result['error']
    if isinstance(error, str):
        if '; nested: ' in error:
            error_list = error.split('; nested: ')
            error = error_list[len(error_list) - 1]

        bits = error.split('[', 1)
        if len(bits) == 2:
            excClass = exceptions_by_name.get(bits[0], None)
            if excClass is not None:
                msg = bits[1]
                if msg.endswith(']'):
                    msg = msg[:-1]
                '''
                if request:
                    msg += ' (' + str(request) + ')'
                '''
                raise excClass(msg, status, result, request)

        for pattern, excClass in list(exception_patterns_trailing.items()):
            if not error.endswith(pattern):
                continue
                # For these exceptions, the returned value is the whole descriptive
            # message.
            raise excClass(error, status, result, request)
    elif isinstance(error, dict) and "type" in error:
        excClass = exceptions_by_type.get(error["type"])
        if excClass is not None:
            msg = error.get("reason", "unknown reason: " + str(error))
            raise excClass(msg, status, result, request)

    raise exceptions.ElasticSearchException(error, status, result, request)
