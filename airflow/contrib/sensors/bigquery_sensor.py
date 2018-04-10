# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from airflow.operators.sensors import BaseSensorOperator
from airflow.contrib.hooks.bigquery_hook import BigQueryHook
from airflow.contrib.hooks.bigquery_hook import BigQueryBaseCursor
from airflow.utils.decorators import apply_defaults


class BigQueryTableSensor(BaseSensorOperator):
    """
    Checks for the existence of a table in Google Bigquery.
    """
    template_fields = ('project_id', 'dataset_id', 'table_id',)
    ui_color = '#f0eee4'

    @apply_defaults
    def __init__(
            self,
            project_id,
            dataset_id,
            table_id,
            bigquery_conn_id='bigquery_default_conn',
            delegate_to=None,
            *args,
            **kwargs):
        """
        Create a new BigQueryTableSensor.

        :param project_id: The Google cloud project in which to look for the table. The connection supplied to the hook
        must provide access to the specified project.
        :type project_id: string
        :param dataset_id: The name of the dataset in which to look for the table.
            storage bucket.
        :type dataset_id: string
        :param table_id: The name of the table to check the existence of.
        :type table_id: string
        :param bigquery_conn_id: The connection ID to use when connecting to Google BigQuery.
        :type bigquery_conn_id: string
        :param delegate_to: The account to impersonate, if any.
            For this to work, the service account making the request must have domain-wide delegation enabled.
        :type delegate_to: string
        """
        super(BigQueryTableSensor, self).__init__(*args, **kwargs)
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        self.bigquery_conn_id = bigquery_conn_id
        self.delegate_to = delegate_to

    def poke(self, context):
        table_uri = '{0}:{1}.{2}'.format(self.project_id, self.dataset_id, self.table_id)
        logging.info('Sensor checks existence of table: %s', table_uri)
        hook = BigQueryHook(
            bigquery_conn_id=self.bigquery_conn_id,
            delegate_to=self.delegate_to)
        return hook.table_exists(self.project_id, self.dataset_id, self.table_id)

class BigQueryJobCompleteSensor(BaseSensorOperator):
    """
    Checks for the completion status of a job in Google Bigquery.
    """
    template_fields = ('project_id', 'job_id')
    ui_color = '#f0eee4'

    @apply_defaults
    def __init__(
            self,
            project_id,
            job_id,
            bigquery_conn_id='bigquery_default_conn',
            delegate_to=None,
            *args,
            **kwargs):
        """
        Create a new BigQueryJobCompleteSensor.

        :param project_id: The Google cloud project in which to look for the table. The connection supplied to the hook
        must provide access to the specified project.
        :type project_id: string
        :param job_id: The Google Bigquery jobId to poll for completion.
        :type job_id: string
        :param bigquery_conn_id: The connection ID to use when connecting to Google BigQuery.
        :type bigquery_conn_id: string
        :param delegate_to: The account to impersonate, if any.
            For this to work, the service account making the request must have domain-wide delegation enabled.
        :type delegate_to: string
        """
        super(BigQueryJobCompleteSensor, self).__init__(*args, **kwargs)
        self.project_id = project_id
        self.job_id = job_id
        self.bigquery_conn_id = bigquery_conn_id
        self.delegate_to = delegate_to

    def poke(self, context):
        from apiclient.discovery import HttpError, build

        hook = BigQueryHook(bigquery_conn_id=self.bigquery_conn_id,
            delegate_to=self.delegate_to)
        service = hook.get_service()

        bqCursor = BigQueryBaseCursor(service, self.project_id)

        logging.info('Polling jobID: %s', self.job_id)

        jobs = service.jobs()

        try:
            job = jobs.get(projectId=self.project_id, jobId=self.job_id).execute()
            if (job['status']['state'] == 'DONE'):
                return True
        except HttpError as err:
            if err.resp.status in [500, 503]:
                self.log.info(
                    '%s: Retryable error while polling job with id %s',
                    err.resp.status, self.job_id)
            else:
                raise Exception(
                    'BigQuery job status check failed. Final error was: %s',
                    err.resp.status)
        return False

        # ISSUE Not able to find poll_job_complete function
        #
        # result = bqCursor.poll_job_complete(job_id = jobId)
        # logging.info(result)
        # return result