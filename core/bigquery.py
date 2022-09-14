"""
Copyright 2022 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from enum import Enum
from typing import Iterable, Mapping, Optional, cast

from google.cloud.bigquery import Client as BigQueryLegacyClient
from google.cloud.bigquery_storage import BigQueryReadClient, ReadSession
from pydantic import BaseModel

from .auth import Credentials

BQ_SCOPES = ('https://www.googleapis.com/auth/bigquery')


class TableMetadata(BaseModel):
    """
    Represents the necessary metadata to locate a BigQuery table.
    """
    project_id: str
    dataset_id: str
    table_name: str


def build_table_path(metadata: TableMetadata) -> str:
    """
    Builds a fully qualified BigQuery table path from its parts.

    Args:
        * project_id: GCP Project ID
        * dataset_id: Dataset name
        * table_name: Table name

    Returns:
        * Formatted table path
    """
    return f"projects/{metadata.project_id}" + \
        f"/datasets/{metadata.dataset_id}" + \
        f"/tables/{metadata.table_name}"


def get_bq_legacy_client(project_id: str,
                         credentials: Credentials) -> BigQueryLegacyClient:
    """
    Get an authenticated BigQuery API client (legacy), as per the \
    [docs](https://googleapis.dev/python/bigquery/latest/index.html).

    Args:
        * project_id: GCP Project ID
        * credentials: Credentials for User having \
            "BigQuery Data Viewer" permission

    Returns:
        * BigQuery API client
    """
    return BigQueryLegacyClient(project=project_id, credentials=credentials)


def get_bq_storage_read_client(credentials: Credentials) -> BigQueryReadClient:
    """
    Get an authenticated BigQuery Storage API client, as per the \
    [docs](https://cloud.google.com/python/docs/reference/bigquerystorage/latest).

    Args:
        * credentials: Credentials for User having \
            "BigQuery Data Viewer" & "BigQuery Read Session User" permissions

    Returns:
        * BigQuery Storage API client
    """
    return BigQueryReadClient(credentials=credentials)


class DataFormat(Enum):
    """
    Data format for BigQuery Storage API input or output data.

    Note: Reproduced from bigquery_storage_v1/types/stream.py
    """
    DATA_FORMAT_UNSPECIFIED = 0
    AVRO = 1
    ARROW = 2


def get_readrows_iterator(
        bq_storage_read_client: BigQueryReadClient,
        table_metadata: TableMetadata,
        columns: Optional[Iterable[str]] = None,
        data_format: DataFormat = DataFormat.AVRO) -> Iterable[Mapping]:
    """
    Get an Iterator of Row Mappings with the requested columns of the table, \
    using an authenticated BigQuery Storage API client.

    Note: Max read stream count is 1, as DQM parallelizes at the column level.

    Args:
        * bq_storage_read_client: BigQuery Storage API client
        * table_metadata: TableMetadata object
        * columns: List of columns to select
        * data_format: Format to fetch data in, one of:
            * DataFormat.AVRO
            * DataFormat.ARROW

    Defaults:
        * columns: None, i.e. select all columns
        * data_format: AVRO, since it auto-parses to Dict

    Returns:
        * Iterator of Row Mappings
    """
    table_path = build_table_path(table_metadata)

    requested_session = ReadSession(table=table_path,
                                    data_format=data_format.value,
                                    read_options={"selected_fields": columns})

    session = bq_storage_read_client.create_read_session(
        parent=f"projects/{table_metadata.project_id}",
        read_session=requested_session,
        max_stream_count=1,
    )

    # Use 0th stream because because max_stream_count=1
    stream_name = session.streams[0].name

    reader = bq_storage_read_client.read_rows(stream_name)
    rows = reader.rows(session)

    # Docstring return type is Iterable[Mapping]
    # cast for mypy to prevent [no-any-return] error
    return cast(Iterable[Mapping], rows)
