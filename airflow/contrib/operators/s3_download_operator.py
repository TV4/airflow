# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import os
import sys
from tempfile import NamedTemporaryFile

from airflow.hooks.S3_hook import S3Hook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class S3DownloadOperator(BaseOperator):
    """
    Downloads a file from S3.

    :param key: The name of the key to download from S3.
    :type key: string
    :param filename: The file path on the local file system (where the
        operator is being executed) that the file should be downloaded to.
        If no filename passed, the downloaded data will be stored on a local
        file whose filename is returned upon task completion.
    :type filename: string
    :param aws_conn_id: The connection ID to use when
        connecting to Google cloud storage.
    :type aws_conn_id: string
    """
    template_fields = (
        'key',
        'filename',
        'store_to_xcom_key',
    )
    ui_color = '#f0eee4'

    @apply_defaults
    def __init__(self,
                 key,
                 filename=None,
                 store_to_xcom_key=None,
                 aws_conn_id='aws_default',
                 *args,
                 **kwargs):
        super(S3DownloadOperator, self).__init__(*args, **kwargs)
        self.key = key
        self.filename = filename
        self.store_to_xcom_key = store_to_xcom_key
        self.aws_conn_id = aws_conn_id

    def execute(self, context):
        hook = S3Hook(aws_conn_id=self.aws_conn_id)

        if not hook.check_for_key(self.key):
            raise AirflowException("The S3 key {0} does not exists".format(
                self.key))
        key_object = hook.get_key(self.key)

        if not self.filename:
            file = NamedTemporaryFile(delete=False)
            filename = file.name
        else:
            filename = self.filename

        self.log.info('Downloading S3 key {0} in local file at {1}'.format(
            self.key, filename))

        with open(filename, mode='wb') as f:
            key_object.download_fileobj(f)
            f.flush()

            if self.store_to_xcom_key:
                if sys.getsizeof(f) < 48000:
                    context['ti'].xcom_push(
                        key=self.store_to_xcom_key, value=f)
                else:
                    raise RuntimeError(
                        'The size of the downloaded file is too large to push '
                        'it to XCom. You can find it at {0}'.format(filename))

        # Clean up if needed and return file location if needed
        if self.store_to_xcom_key:
            os.remove(filename)
        else:
            return filename
