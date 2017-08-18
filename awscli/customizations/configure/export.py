# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import sys

from awscli.customizations.commands import BasicCommand

from . import NOT_SET


class ExportCommand(BasicCommand):
    NAME = 'export'
    DESCRIPTION = "n/a"
    SYNOPSIS = 'aws configure export --profile foo'
    EXAMPLES = "n/a"
    ARG_TABLE = []

    def __init__(self, session, stream=sys.stdout, error_stream=sys.stderr):
        super(ExportCommand, self).__init__(session)
        self._stream = stream
        self._error_stream = error_stream

    def _run_main(self, args, parsed_globals):
        access_key, secret_key = self._lookup_credentials()
        print("export AWS_ACCESS_KEY_ID=%s" % access_key)
        print("export AWS_SECRET_ACCESS_KEY=%s" % secret_key)

        region = self._lookup_config('region')
        if region is not NOT_SET:
            print("export AWS_DEFAULT_REGION=%s" % region)

    def _lookup_credentials(self):
        # First try it with _lookup_config.  It's possible
        # that we don't find credentials this way (for example,
        # if we're using an IAM role).
        access_key = self._lookup_config('access_key')
        if access_key is not NOT_SET:
            secret_key = self._lookup_config('secret_key')
            return access_key, secret_key
        else:
            # Otherwise we can try to use get_credentials().
            # This includes a few more lookup locations
            # (IAM roles, some of the legacy configs, etc.)
            credentials = self._session.get_credentials()
            if credentials is None:
                return NOT_SET, NOT_SET
            else:
                # For the ConfigValue, we don't track down the
                # config_variable because that info is not
                # visible from botocore.credentials.  I think
                # the credentials.method is sufficient to show
                # where the credentials are coming from.
                return credentials.access_key, credentials.secret_key

    def _lookup_config(self, name):
        # First try to look up the variable in the env.
        value = self._session.get_config_variable(name, methods=('env',))
        if value is not None:
            return value
        # Then try to look up the variable in the config file.
        value = self._session.get_config_variable(name, methods=('config',))
        if value is not None:
            return value
        else:
            return NOT_SET
